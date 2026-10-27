"""Wärmepumpe – PV-Warmwasserboost.

Button, Switch und Input-Boolean lösen eine WW-Ladung genau einmal aus. Die WP
übernimmt den Zyklus; SEP sendet kein Abbruchsignal bei sinkendem PV-Ertrag.
Ein konfigurierbares, mindestens einstündiges Startintervall wird vor dem
Auslösen dauerhaft gespeichert und überlebt damit einen HA-Neustart.

Ein veränderter Temperatur-Sollwert (Number) benötigt hingegen weiterhin eine
aktive Rückstellung und behält deshalb den bisherigen Regelmodus.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from ..const import (
    BOOST_BUTTON,
    BOOST_NUMBER,
    CONF_BOOST_ENTITY,
    CONF_BOOST_TYPE,
    CONF_TEMP_SENSOR,
    CONF_WW_ACTIVE_ENTITY,
    CONF_WW_BOOST_TEMP_ENTITY,
)
from ..forecast_window import rolling_energy
from ..helpers import ParamSpec, SensorSpec, is_on, power_w, state_float, state_str
from .base import BaseDevice, Context, Decision, PlanDemand


class HeatPumpDevice(BaseDevice):
    TYPE = "heatpump"
    ICON = "mdi:heat-pump"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state.setdefault("day", None)
        self.state.setdefault("boost_min", 0.0)
        self.state.setdefault("active", False)
        self.state.setdefault("started", None)
        self.state.setdefault("stopped", None)
        self.state.setdefault("last_trigger", None)
        self._deficit_since: datetime | None = None
        self._idle_since: datetime | None = None

    def param_specs(self) -> list[ParamSpec]:
        specs = [
            ParamSpec("nominal_power", "number", float(self.cfg.get("nominal_power", 2000)),
                      "mdi:flash", 200, 10000, 50, "W"),
            ParamSpec("target_temp", "number", 55, "mdi:thermometer-high", 30, 75, 0.5, "°C"),
            ParamSpec("boost_hysteresis", "number", 4, "mdi:thermometer", 0, 30, 0.5, "K"),
            ParamSpec("idle_minutes", "number", 15, "mdi:timer-sand", 1, 180, 1, "min"),
            ParamSpec("idle_power_threshold", "number", 5, "mdi:flash", 0, 1000, 1, "W"),
            ParamSpec("trigger_cooldown", "number", 60, "mdi:timer-lock-outline", 60, 720, 5, "min"),
            ParamSpec("sun_filter_active", "switch", False, "mdi:weather-sunny"),
            ParamSpec("sun_angle_min", "number", self.cfg.get("sun_angle_min"),
                      "mdi:sun-angle", -90, 90, 0.5, "°"),
            ParamSpec("boost_start_filter", "select", "none", "mdi:weather-partly-cloudy",
                      options=["none", "cloud", "pv_forecast"]),
            ParamSpec("boost_forecast_hours", "select", "2", "mdi:timeline-clock", options=["1", "2"]),
            ParamSpec("boost_forecast_min_kwh", "number", 2.0, "mdi:solar-power", 0.1, 100, 0.1, "kWh"),
            ParamSpec("cloud_now_max", "number", self.cfg.get("cloud_now_max"),
                      "mdi:weather-cloudy", 0, 100, 1, "%"),
            ParamSpec("cloud_next_max", "number", self.cfg.get("cloud_next_max"),
                      "mdi:weather-cloudy-clock", 0, 100, 1, "%"),
        ]
        if self.one_shot:
            specs.append(ParamSpec("ww_active_minutes", "number", self.cfg.get("ww_active_minutes", 10),
                                   "mdi:timer-sand", 0, 180, 1, "min"))
        if self.cfg.get(CONF_BOOST_TYPE) == BOOST_NUMBER:
            specs += [
                ParamSpec("min_on", "number", 30, "mdi:timer-lock-outline", 5, 180, 5, "min"),
                ParamSpec("min_off", "number", 60, "mdi:timer-lock-open-outline", 5, 360, 5, "min"),
                ParamSpec("max_per_day", "number", 120, "mdi:timer-alert-outline", 0, 720, 10, "min"),
                ParamSpec("stop_delay", "number", 10, "mdi:timer-pause", 1, 60, 1, "min"),
                ParamSpec("boost_value", "number", 55, "mdi:arrow-up-bold", 0, 80, 0.5),
                ParamSpec("normal_value", "number", 46, "mdi:arrow-down-bold", 0, 80, 0.5),
            ]
        return specs

    def load(self, data: dict) -> None:
        # Removing a configured threshold must also remove its stored parameter.
        data = dict(data)
        data["params"] = dict(data.get("params") or {})
        old_cfg = data.get("cfg") or {}
        for key in ("sun_angle_min", "cloud_now_max", "cloud_next_max"):
            if old_cfg.get(key) != self.cfg.get(key):
                data["params"].pop(key, None)
        # Preserve the previously enabled cloud filter on upgrade.
        if "boost_start_filter" not in data["params"]:
            data["params"]["boost_start_filter"] = "cloud" if data["params"].get("cloud_filter_active") else "none"
        super().load(data)
        # Migration from earlier SEP releases: their 'started' timestamp
        # is the safest available approximation of the last WW command.
        if self.state.get("last_trigger") is None and self.state.get("started") is not None:
            self.state["last_trigger"] = self.state["started"]

    def _weather_checks(self) -> dict[str, dict]:
        """Optional start gates. Incomplete/disabled gates do not read inputs."""
        result = {}
        groups = (
            ("sun", "sun_filter_active", (("sun_angle_entity", "sun_angle_min", -90, 90),)),
            ("cloud", "cloud_filter_active", (
                ("cloud_now_entity", "cloud_now_max", 0, 100),
                ("cloud_next_entity", "cloud_next_max", 0, 100),
            )),
        )
        for name, active, fields in groups:
            enabled = self.p("boost_start_filter") == "cloud" if name == "cloud" else bool(self.p(active))
            configured = all(self.cfg.get(entity) and self.p(limit) is not None
                             for entity, limit, _, _ in fields)
            check = {"aktiv": enabled, "vollstaendig": bool(configured), "wirksam": False,
                     "erlaubt": True, "grund": "Ignoriert: ausgeschaltet" if not enabled
                     else "Ignoriert: Entität oder Grenzwert fehlt"}
            result[name] = check
            if not enabled or not configured:
                continue
            check.update(wirksam=True, erlaubt=True, grund="Bedingung erfüllt")
            for entity, limit, low, high in fields:
                value = state_float(self.hass, self.cfg[entity])
                try:
                    threshold = float(self.p(limit))
                except (TypeError, ValueError):
                    threshold = math.nan
                label = {"sun_angle_entity": "Sonnenwinkel", "cloud_now_entity": "Bewölkung aktuelle Stunde",
                         "cloud_next_entity": "Bewölkung kommende Stunde"}[entity]
                if (value is None or not math.isfinite(value) or not low <= value <= high
                        or not math.isfinite(threshold) or not low <= threshold <= high):
                    check.update(erlaubt=False, grund=f"{label}: Messwert oder Grenzwert ungültig")
                    break
                passed = value >= threshold if name == "sun" else value < threshold
                if not passed:
                    unit = "°" if name == "sun" else "%"
                    relation = "mindestens" if name == "sun" else "unter"
                    check.update(erlaubt=False, grund=f"{label}: {value:g}{unit}, benötigt {relation} {threshold:g}{unit}")
                    break
        return result

    def _forecast_check(self, now: datetime) -> dict:
        check = {"aktiv": self.p("boost_start_filter") == "pv_forecast", "erlaubt": True,
                 "zeitraum_h": self.p("boost_forecast_hours"),
                 "minimum_kwh": self.p("boost_forecast_min_kwh"), "prognose_kwh": None,
                 "grund": "Ignoriert: PV-Forecast nicht ausgewählt"}
        if not check["aktiv"]:
            return check
        try:
            hours = int(self.p("boost_forecast_hours"))
            minimum = float(self.p("boost_forecast_min_kwh"))
            if hours not in (1, 2) or not math.isfinite(minimum) or not 0.1 <= minimum <= 100:
                raise ValueError
        except (TypeError, ValueError):
            check.update(erlaubt=False, grund="PV-Forecast-Einstellung ungültig")
            return check
        energy, error = rolling_energy(getattr(self.manager, "forecast", None), now, hours)
        if error:
            check.update(erlaubt=False, grund=error)
            return check
        kwh = energy / 1000
        check.update(prognose_kwh=round(kwh, 3), erlaubt=kwh >= minimum,
                     grund=f"PV-Forecast nächste {hours} h: {kwh:.2f} kWh; benötigt {minimum:g} kWh")
        return check

    def _start_filter_error(self, now: datetime) -> str | None:
        if self.p("boost_start_filter") not in ("none", "cloud", "pv_forecast"):
            return "WW-Boost-Startfilter ungültig"
        check = self._forecast_check(now)
        return None if check["erlaubt"] else check["grund"]

    def status_attrs(self) -> dict:
        return {
            **super().status_attrs(),
            "boost_startbedingungen": self._weather_checks(),
            "boost_startfilter": self.p("boost_start_filter"),
            "pv_forecast_startbedingung": self._forecast_check(datetime.now().astimezone()),
            "warmwasser_aktiv": self.ww_active,
            "ww_aktiv_mindestdauer_min": self.p("ww_active_minutes"),
            "ww_aktiv_seit_min": self._ww_active_minutes(datetime.now().astimezone()),
            "ww_zyklus_bereits_boost": self._ww_cycle_already_boosted(),
            "ww_aktiv_entitaet": self.cfg.get(CONF_WW_ACTIVE_ENTITY),
            "letzte_ausloesung": self.state.get("last_trigger"),
            "startsperre_rest_min": self._cooldown_remaining(datetime.now().astimezone()),
            "einmaliger_ww_start": self.one_shot,
            "ww_boost_sollwert_entitaet": self.cfg.get(CONF_WW_BOOST_TEMP_ENTITY),
            "ww_boost_sollwert_aktiv": self.target_temperature,
        }

    def sensor_specs(self) -> list[SensorSpec]:
        return super().sensor_specs() + [
            SensorSpec("boost_today", lambda: round(self.state["boost_min"]), unit="min",
                       icon="mdi:timer-check-outline", state_class="measurement"),
        ]

    @property
    def entity(self) -> str:
        return self.cfg[CONF_BOOST_ENTITY]

    @property
    def one_shot(self) -> bool:
        """Button, switch and input_boolean are start commands, not load regulators."""
        return self.cfg.get(CONF_BOOST_TYPE) != BOOST_NUMBER

    @property
    def ww_active(self) -> bool | None:
        """External confirmation of an active WW cycle; None means unknown."""
        ent = self.cfg.get(CONF_WW_ACTIVE_ENTITY)
        if not ent:
            return False
        value = state_str(self.hass, ent)
        if value not in ("on", "off"):
            return None
        return value == "on"

    @property
    def target_temperature(self) -> float | None:
        """Use an optional HA temperature entity in place of fixed target."""
        source = self.cfg.get(CONF_WW_BOOST_TEMP_ENTITY)
        raw = state_float(self.hass, source) if source else self.p("target_temp")
        try:
            value = float(raw)
        except (ValueError, TypeError):
            return None
        if not math.isfinite(value) or not 30 <= value <= 75:
            return None
        return value

    def _cooldown_remaining(self, now: datetime) -> int:
        """Minutes until the next permitted *start*, including after restart."""
        ts = self.state.get("last_trigger")
        if ts is None:
            return 0
        try:
            cooldown_min = max(60.0, float(self.p("trigger_cooldown") or 60))
            remaining = float(ts) + 60 * cooldown_min - now.timestamp()
            return max(0, math.ceil(remaining / 60))
        except (TypeError, ValueError, OverflowError):
            # Corrupt timestamps must not inadvertently enable rapid retries.
            return 60

    def is_on(self) -> bool:
        if self.one_shot:
            if self.cfg.get(CONF_WW_ACTIVE_ENTITY):
                return self.ww_active is True
            return is_on(self.hass, self.entity) if self.cfg.get(CONF_BOOST_TYPE) != BOOST_BUTTON else False
        return bool(self.state.get("active"))

    @property
    def temp(self) -> float | None:
        return state_float(self.hass, self.cfg.get(CONF_TEMP_SENSOR))

    def on_param_changed(self, key: str) -> None:
        if key == "idle_power_threshold":
            self._idle_since = None

    def observe_power(self, now: datetime) -> None:
        """Track every power event, including brief activity before a debounced run."""
        value = power_w(self.hass, self.cfg.get("power_sensor"))
        if value is None or not math.isfinite(value) or value >= float(self.p("idle_power_threshold")):
            self._idle_since = None
        elif self._idle_since is None:
            self._idle_since = now

    def pre_update(self, ctx: Context) -> None:
        self.observe_power(ctx.now)
        today = ctx.now.date().isoformat()
        if self.state.get("day") != today:
            self.state.update(day=today, boost_min=0.0)
        if self.is_on():
            self.state["boost_min"] += ctx.dt / 60

    def _elapsed(self, key: str, now: datetime) -> float:
        ts = self.state.get(key)
        return (now.timestamp() - float(ts)) / 60 if ts else 1e9

    def _ww_active_minutes(self, now: datetime) -> float | None:
        """Uninterrupted ON duration, based on Home Assistant's state timestamp."""
        ent = self.cfg.get(CONF_WW_ACTIVE_ENTITY)
        state = self.hass.states.get(ent) if ent else None
        if state is None or state.state != "on":
            return None
        return max(0.0, (now - state.last_changed).total_seconds() / 60)

    def _ww_cycle_already_boosted(self) -> bool:
        """Prevent repeated commands within one continuous WW charging cycle."""
        ent = self.cfg.get(CONF_WW_ACTIVE_ENTITY)
        state = self.hass.states.get(ent) if ent else None
        ts = self.state.get("last_trigger")
        return bool(state and state.state == "on" and ts is not None
                    and float(ts) >= state.last_changed.timestamp())

    def _decide_ww_once(self, ctx: Context, budget_left: float) -> Decision:
        """Determine whether to send a single WW-start command."""
        active = self.ww_active
        if active is None:
            self.status = "wartet"
            return Decision(False, 0, "Warmwasser-aktiv-Signal nicht verfügbar")
        # Existing WW cycle: after the configured duration a single boost is permitted
        # with nonnegative current priority-adjusted control budget.
        active_minutes = self._ww_active_minutes(ctx.now) if active else None
        wait_minutes = float(self.p("ww_active_minutes"))
        if not math.isfinite(wait_minutes) or not 0 <= wait_minutes <= 180:
            return Decision(False, 0, "WW-Aktiv-Mindestdauer ungültig")
        if active and wait_minutes == 0:
            self.status = "wartet"
            return Decision(False, 0, "WW läuft – Sonderfreigabe deaktiviert (0 Minuten)")
        running_boost = active and active_minutes is not None and active_minutes >= wait_minutes
        if active and not running_boost:
            self.status = "wartet"
            return Decision(False, 0, f"WW läuft – Boost frühestens nach {wait_minutes:g} Minuten")
        if running_boost and self._ww_cycle_already_boosted():
            self.status = "boost"
            return Decision(False, 0, "WW-Zyklus bereits geboostet")
        if (self.cfg.get(CONF_BOOST_TYPE) != BOOST_BUTTON
                and is_on(self.hass, self.entity)):
            self.status = "wartet"
            return Decision(False, 0, "WW-Auslöser ist noch EIN – auf AUS warten")
        rest = self._cooldown_remaining(ctx.now)
        if rest:
            self.status = "wartet"
            return Decision(False, 0, f"WW-Boost-Startsperre: noch {rest} min")
        temp = self.temp
        target = self.target_temperature
        if target is None:
            self.status = "wartet"
            return Decision(False, 0, "WW-Boost-Solltemperatur fehlt oder ist ungültig")
        if temp is None or not math.isfinite(temp):
            self.status = "wartet"
            return Decision(False, 0, "Warmwassertemperatur fehlt oder ist ungültig")
        if temp >= target - float(self.p("boost_hysteresis")):
            self.status = "bereit"
            return Decision(False, 0, f"Warmwasserspeicher warm ({temp:.1f} °C)")
        if (not running_boost and (self._idle_since is None or
                ctx.now - self._idle_since < timedelta(minutes=float(self.p("idle_minutes"))))):
            self.status = "wartet"
            return Decision(False, 0, "Wärmepumpe noch nicht lange genug in Ruhe")
        for name, check in self._weather_checks().items():
            # Running WW uses the current budget, not cloud forecasts.
            if running_boost and name == "cloud":
                continue
            if not check["erlaubt"]:
                self.status = "wartet"
                return Decision(False, 0, check["grund"])
        if not running_boost and (error := self._start_filter_error(ctx.now)):
            self.status = "wartet"
            return Decision(False, 0, error)
        left_now = ctx.now_left(budget_left)
        left_avg = budget_left if ctx.history_ready else left_now
        need = self.nominal
        if running_boost:
            if left_now >= 0:
                self.status = "bereit"
                return Decision(True, 0,
                                f"WW seit {active_minutes:.0f} min aktiv; "
                                f"Steuerbudget {left_now:.0f} W >= 0 W – Boost auslösen")
            self.status = "wartet"
            return Decision(False, 0,
                            f"WW aktiv, Steuerbudget {left_now:.0f} W < 0 W")
        if left_now >= need and left_avg >= need:
            self.status = "bereit"
            return Decision(True, need, "PV-Budget ausreichend – WW-Boost einmalig auslösen")
        self.status = "wartet"
        return Decision(False, 0, f"WW-Budget zu gering ({min(left_now, left_avg):.0f} W < {need:.0f} W)")

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        if self.one_shot:
            return self._decide_ww_once(ctx, budget_left)
        on = self.is_on()
        need = self.nominal
        temp = self.temp
        target = self.target_temperature
        left_now = ctx.now_left(budget_left)
        left_avg = budget_left if ctx.history_ready else left_now
        if target is None:
            return Decision(False, 0, "WW-Boost-Solltemperatur fehlt oder ist ungültig")
        own = self.power_now() if on else 0.0

        if on:
            self.status = "boost"
            if self.state["boost_min"] >= float(self.p("max_per_day")):
                return Decision(False, 0, "Tageslimit erreicht")
            if temp is not None and temp >= target:
                return Decision(False, 0, f"Zieltemperatur erreicht ({temp:.1f} °C)")
            if self._elapsed("started", ctx.now) < float(self.p("min_on")):
                return Decision(True, max(own, need), "Mindestlaufzeit läuft")
            if ctx.short_left(budget_left) >= need * 0.8:
                self._deficit_since = None
            else:
                self._deficit_since = self._deficit_since or ctx.now
                if ctx.now - self._deficit_since >= timedelta(minutes=float(self.p("stop_delay"))):
                    return Decision(False, 0, "Überschuss fehlt")
            return Decision(True, max(own, need), "PV-Boost")

        self.status = "bereit"
        rest = self._cooldown_remaining(ctx.now)
        if rest:
            return Decision(False, 0, f"WW-Boost-Startsperre: noch {rest} min")
        if self.state["boost_min"] >= float(self.p("max_per_day")):
            return Decision(False, 0, "Tageslimit erreicht")
        if temp is None or not math.isfinite(temp):
            return Decision(False, 0, "Temperatursensor fehlt oder ungültig")
        if temp >= target - float(self.p("boost_hysteresis")):
            return Decision(False, 0, f"Speicher warm ({temp:.1f} °C)")
        if self._idle_since is None or ctx.now - self._idle_since < timedelta(minutes=float(self.p("idle_minutes"))):
            return Decision(False, 0, f"Warte auf {float(self.p('idle_minutes')):g} Minuten WP-Leistung unter Ruheschwelle")
        if self._elapsed("stopped", ctx.now) < float(self.p("min_off")):
            return Decision(False, 0, "Mindestpause läuft")
        for check in self._weather_checks().values():
            if not check["erlaubt"]:
                return Decision(False, 0, check["grund"])
        if error := self._start_filter_error(ctx.now):
            return Decision(False, 0, error)
        if left_now >= need and left_avg >= need:
            return Decision(True, need, "PV-Überschuss – Boost")
        return Decision(False, 0, f"Überschuss zu niedrig ({min(left_now, left_avg):.0f} W < {need:.0f} W)")

    async def _commit_trigger(self, now: datetime) -> None:
        """Reserve a trigger before calling the WP to survive abrupt HA restarts."""
        self.state["last_trigger"] = now.timestamp()
        self.state["started"] = now.timestamp()
        await self.manager.async_save_now()

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        if self.one_shot:
            if not decision.on:
                return  # WW is controlled by the heat pump, never send OFF.
            await self._commit_trigger(ctx.now)
            # The write is durable before dispatch; a failed/uncertain service
            # call retains the cooldown to avoid a duplicate on retry.
            await self._set(True)
            self.state["active"] = False
            self._idle_since = None
            return
        if decision.on == self.is_on():
            return
        if decision.on:
            await self._commit_trigger(ctx.now)
        await self._set(decision.on)
        self.state["active"] = decision.on
        if decision.on:
            self._idle_since = None
        self.state["started" if decision.on else "stopped"] = ctx.now.timestamp()
        self._deficit_since = None

    async def async_disabled(self, ctx: Context) -> None:
        if self.one_shot:
            return  # A WW one-time cycle is never stopped or reset by SEP.
        if self.is_on():
            await self._set(False)
            self.state["active"] = False
            self.state["stopped"] = ctx.now.timestamp()

    async def _set(self, on: bool) -> None:
        if self.cfg.get(CONF_BOOST_TYPE) == BOOST_BUTTON:
            # Trigger once per boost session; buttons cannot stop a physical cycle.
            if on:
                await self._call_actor(
                    self.entity.split(".")[0], "press",
                    {"entity_id": self.entity}, blocking=True
                )
            return
        if self.cfg.get(CONF_BOOST_TYPE) == BOOST_NUMBER:
            value = (self.target_temperature if on and self.cfg.get(CONF_WW_BOOST_TEMP_ENTITY)
                     else float(self.p("boost_value" if on else "normal_value")))
            if value is None:
                raise ValueError("WW-Boost-Solltemperatur nicht verfügbar")
            await self._call_actor(self.entity.split(".")[0], "set_value",
                                                {"entity_id": self.entity, "value": value}, blocking=True)
        else:
            await self._switch(self.entity, on)

    def plan_demand(self, now: datetime) -> PlanDemand | None:
        if self.ww_active is not False or self._cooldown_remaining(now):
            return None
        if self.one_shot:
            return PlanDemand(self.nominal, self.nominal * 0.5,
                              now.replace(hour=18, minute=0), interruptible=False)
        rest = float(self.p("max_per_day")) - self.state["boost_min"]
        if rest <= 0:
            return None
        return PlanDemand(self.nominal, self.nominal * min(rest, float(self.p("min_on"))) / 60,
                          now.replace(hour=18, minute=0), interruptible=False)
