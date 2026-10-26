"""Wärmepumpe – PV-Boost (z. B. Warmwasser-Einmalladung über EMS-ESP).

Boost-Arten:
  Schalter  – z. B. switch.boiler_dhw_one_time_charging (Einmalladung)
  Sollwert  – Number-Entity wird auf Boost-Wert gesetzt und danach auf den Normalwert zurück
              (z. B. number.boiler_dhw_selected_temperature)
Start bei Überschuss (aktuell + Mittel), Stopp nach Mindestlaufzeit, wenn Überschuss fehlt,
die Zieltemperatur erreicht ist oder das Tageslimit verbraucht ist.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import math

from ..const import BOOST_BUTTON, BOOST_NUMBER, CONF_BOOST_ENTITY, CONF_BOOST_TYPE, CONF_TEMP_SENSOR
from ..helpers import ParamSpec, SensorSpec, is_on, state_float, power_w
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
            ParamSpec("min_on", "number", 30, "mdi:timer-lock-outline", 5, 180, 5, "min"),
            ParamSpec("min_off", "number", 60, "mdi:timer-lock-open-outline", 5, 360, 5, "min"),
            ParamSpec("max_per_day", "number", 120, "mdi:timer-alert-outline", 0, 720, 10, "min"),
            ParamSpec("sun_filter_active", "switch", False, "mdi:weather-sunny"),
            ParamSpec("sun_angle_min", "number", self.cfg.get("sun_angle_min"),
                      "mdi:sun-angle", -90, 90, 0.5, "°"),
            ParamSpec("cloud_filter_active", "switch", False, "mdi:weather-cloudy"),
            ParamSpec("cloud_now_max", "number", self.cfg.get("cloud_now_max"),
                      "mdi:weather-cloudy", 0, 100, 1, "%"),
            ParamSpec("cloud_next_max", "number", self.cfg.get("cloud_next_max"),
                      "mdi:weather-cloudy-clock", 0, 100, 1, "%"),
            ParamSpec("stop_delay", "number", 10, "mdi:timer-pause", 1, 60, 1, "min"),
        ]
        if self.cfg.get(CONF_BOOST_TYPE) == BOOST_NUMBER:
            specs += [
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
        super().load(data)

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
            enabled = bool(self.p(active))
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

    def status_attrs(self) -> dict:
        return {**super().status_attrs(), "boost_startbedingungen": self._weather_checks()}

    def sensor_specs(self) -> list[SensorSpec]:
        return super().sensor_specs() + [
            SensorSpec("boost_today", lambda: round(self.state["boost_min"]), unit="min",
                       icon="mdi:timer-check-outline", state_class="measurement"),
        ]

    @property
    def entity(self) -> str:
        return self.cfg[CONF_BOOST_ENTITY]

    def is_on(self) -> bool:
        if self.cfg.get(CONF_BOOST_TYPE) in (BOOST_NUMBER, BOOST_BUTTON):
            return bool(self.state.get("active"))
        return is_on(self.hass, self.entity)

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

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        on = self.is_on()
        need = self.nominal
        temp = self.temp
        target = float(self.p("target_temp"))
        left_now = ctx.now_left(budget_left)
        left_avg = budget_left if ctx.history_ready else left_now
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
        if left_now >= need and left_avg >= need:
            return Decision(True, need, "PV-Überschuss – Boost")
        return Decision(False, 0, f"Überschuss zu niedrig ({min(left_now, left_avg):.0f} W < {need:.0f} W)")

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        if decision.on == self.is_on():
            return
        await self._set(decision.on)
        self.state["active"] = decision.on
        if decision.on:
            self._idle_since = None
        self.state["started" if decision.on else "stopped"] = ctx.now.timestamp()
        self._deficit_since = None

    async def async_disabled(self, ctx: Context) -> None:
        if self.is_on():
            await self._set(False)
            self.state["active"] = False
            self.state["stopped"] = ctx.now.timestamp()

    async def _set(self, on: bool) -> None:
        if self.cfg.get(CONF_BOOST_TYPE) == BOOST_BUTTON:
            # Trigger once per boost session; buttons cannot stop a physical cycle.
            if on:
                await self.hass.services.async_call(
                    self.entity.split(".")[0], "press",
                    {"entity_id": self.entity}, blocking=True
                )
            return
        if self.cfg.get(CONF_BOOST_TYPE) == BOOST_NUMBER:
            value = float(self.p("boost_value" if on else "normal_value"))
            await self.hass.services.async_call(self.entity.split(".")[0], "set_value",
                                                {"entity_id": self.entity, "value": value}, blocking=True)
        else:
            await self._switch(self.entity, on)

    def plan_demand(self, now: datetime) -> PlanDemand | None:
        rest = float(self.p("max_per_day")) - self.state["boost_min"]
        if rest <= 0:
            return None
        return PlanDemand(self.nominal, self.nominal * min(rest, float(self.p("min_on"))) / 60,
                          now.replace(hour=18, minute=0), interruptible=False)
