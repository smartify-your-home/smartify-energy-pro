"""Wallbox / E-Auto.

Ladestrom folgt dem PV-Überschuss (optional mit 1/3-Phasen-Umschaltung).
Ziel-Modi:
  Nur PV            – lädt ausschließlich mit Überschuss
  km bis Uhrzeit    – benötigte Energie für X km bis zur Uhrzeit, Rest aus dem Netz
  Tage-Konfigurator – km des nächsten Fahrtags aus input_text ([["MO",km,büro],…])
  Sofort            – mit Maximalstrom
Pflichtladung startet so spät wie möglich, damit vorher möglichst viel PV genutzt wird.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, time, timedelta

from ..const import (
    CONF_CAPACITY,
    CONF_CONNECTED_ENTITY,
    CONF_CONNECTED_STATES,
    CONF_CONSUMPTION,
    CONF_CONTROL_ENTITY,
    CONF_CONTROL_OFF,
    CONF_CONTROL_ON,
    CONF_CURRENT_ENTITY,
    CONF_DAYS_ENTITY,
    CONF_EFFICIENCY,
    CONF_MAX_CURRENT,
    CONF_MIN_CURRENT,
    CONF_PHASE_1,
    CONF_PHASE_3,
    CONF_PHASE_ENTITY,
    CONF_PHASES,
    CONF_SOC_SENSOR,
    CONF_VOLTAGE,
    EV_GOAL_DAYS,
    EV_GOAL_KM,
    EV_GOAL_NOW,
    EV_GOAL_PV,
    EV_GOALS,
    EV_PHASE_1,
    EV_PHASE_3,
    EV_PHASE_AUTO,
    EV_PHASE_MODES,
)
from ..helpers import ParamSpec, SensorSpec, clamp, power_w, state_float, state_str, time_from_str
from .base import BaseDevice, Context, Decision, PlanDemand

_LOGGER = logging.getLogger(__name__)

DAY_LABELS = {"MO": 0, "DI": 1, "TU": 1, "MI": 2, "WE": 2, "DO": 3, "TH": 3,
              "FR": 4, "SA": 5, "SO": 6, "SU": 6}
NOT_CONNECTED = {"off", "idle", "disconnected", "not_connected", "unplugged", "unavailable", "unknown"}
PHASE_SWITCH_INTERVAL = timedelta(minutes=10)


class EvDevice(BaseDevice):
    TYPE = "ev"
    ICON = "mdi:ev-station"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state.setdefault("charged_wh", 0.0)    # seit Zielsetzung geladen (ohne SoC-Sensor)
        self.state.setdefault("phase_switch", None)
        self.state.setdefault("phases", None)
        self._deficit_since: datetime | None = None
        self._need_wh = 0.0
        self._deadline: datetime | None = None
        self._latest_start: datetime | None = None
        self._target_km: float | None = None

    # ── Konfiguration ────────────────────────────────────────────────────────
    def _c(self, key: str, default: float) -> float:
        try:
            return float(self.cfg.get(key, default))
        except (TypeError, ValueError):
            return default

    @property
    def voltage(self) -> float:
        return self._c(CONF_VOLTAGE, 230)

    @property
    def min_a(self) -> float:
        return self._c(CONF_MIN_CURRENT, 6)

    @property
    def max_a(self) -> float:
        return self._c(CONF_MAX_CURRENT, 16)

    @property
    def max_phases(self) -> int:
        return int(self._c(CONF_PHASES, 3))

    @property
    def efficiency(self) -> float:
        return clamp(self._c(CONF_EFFICIENCY, 90) / 100, 0.5, 1.0)

    @property
    def nominal(self) -> float:
        return self.max_a * self.voltage * self.max_phases

    def param_specs(self) -> list[ParamSpec]:
        has_days = bool(self.cfg.get(CONF_DAYS_ENTITY))
        specs = [
            ParamSpec("goal", "select", EV_GOAL_DAYS if has_days else EV_GOAL_PV, "mdi:target",
                      options=EV_GOALS, config=False),
            ParamSpec("target_km", "number", 50, "mdi:map-marker-distance", 0, 1000, 5, "km", config=False),
            ParamSpec("deadline", "time", "06:00", "mdi:clock-end", config=False),
            ParamSpec("reserve_soc", "number", 20, "mdi:battery-low", 0, 100, 5, "%"),
            ParamSpec("max_soc", "number", 100, "mdi:battery-charging-high", 10, 100, 5, "%"),
            ParamSpec("consumption", "number", self._c(CONF_CONSUMPTION, 18), "mdi:gauge", 5, 40, 0.5, "kWh/100km"),
            ParamSpec("pv_share", "number", 100, "mdi:solar-power-variant", 10, 100, 5, "%"),
            ParamSpec("stop_delay", "number", 5, "mdi:timer-pause", 1, 30, 1, "min"),
        ]
        if self.cfg.get(CONF_PHASE_ENTITY):
            specs.append(ParamSpec("phase_mode", "select", EV_PHASE_AUTO, "mdi:sine-wave", options=EV_PHASE_MODES))
        return specs

    def on_param_changed(self, key: str) -> None:
        if key in ("goal", "target_km", "deadline"):
            self.state["charged_wh"] = 0.0

    def sensor_specs(self) -> list[SensorSpec]:
        return super().sensor_specs() + [
            SensorSpec("energy_needed", lambda: round(self._need_wh / 1000, 2), unit="kWh",
                       device_class="energy", icon="mdi:battery-arrow-up",
                       attrs=lambda: {
                           "ziel_km": self._target_km,
                           "faellig": self._deadline.isoformat() if self._deadline else None,
                           "spaetester_netzstart": self._latest_start.isoformat() if self._latest_start else None,
                           "soc": self.soc,
                       }),
            SensorSpec("charge_current", lambda: (self.last_decision.setpoint.get("current")
                                                  if self.last_decision else None),
                       unit="A", icon="mdi:current-ac"),
        ]

    # ── Messwerte ────────────────────────────────────────────────────────────
    @property
    def soc(self) -> float | None:
        return state_float(self.hass, self.cfg.get(CONF_SOC_SENSOR))

    @property
    def connected(self) -> bool:
        ent = self.cfg.get(CONF_CONNECTED_ENTITY)
        if not ent:
            return True
        st = state_str(self.hass, ent)
        if st is None:
            return False
        allowed = [s.strip().lower() for s in str(self.cfg.get(CONF_CONNECTED_STATES) or "").split(",") if s.strip()]
        if allowed:
            return st.lower() in allowed
        return st.lower() not in NOT_CONNECTED

    def is_on(self) -> bool:
        ent = self.cfg.get(CONF_CONTROL_ENTITY)
        if ent:
            st = state_str(self.hass, ent)
            if ent.split(".")[0] in ("select", "input_select"):
                return st == self.cfg.get(CONF_CONTROL_ON)
            return st == "on"
        return self.power_now() > 300

    def power_now(self) -> float:
        if self.cfg.get("power_sensor"):
            return super().power_now()
        if not self.is_on():
            return 0.0
        amps = state_float(self.hass, self.cfg.get(CONF_CURRENT_ENTITY), self.min_a) or 0
        return amps * self.voltage * (self.current_phases or self.max_phases)

    def _can_reclaim_pv_power(self) -> bool:
        """Only an active, metered, modulated PV charge has immediately reducible power."""
        return bool(
            self.mode == "auto"
            and self.p("goal") == EV_GOAL_PV
            and self.connected
            and self.is_on()
            and self.cfg.get("power_sensor")
            and self.cfg.get(CONF_CURRENT_ENTITY)
        )

    def reclaimable_power(self) -> float:
        if not self._can_reclaim_pv_power():
            return 0.0
        measured = power_w(self.hass, self.cfg.get("power_sensor"))
        if measured is None:
            return 0.0
        # The current minimum remains drawn during the stop delay. Do not
        # promise it to a different consumer as instantly available power.
        minimum = self.min_a * self.voltage * (self.current_phases or self.max_phases)
        return max(0.0, measured - minimum)

    def own_budget_power(self, measured_w: float, reclaimed_w: float) -> float:
        # The wallbox may account for its already-running minimum when
        # modulating itself, but may not offer that minimum to other loads.
        return max(0.0, measured_w - reclaimed_w) if self._can_reclaim_pv_power() else 0.0

    @property
    def current_phases(self) -> int | None:
        ent = self.cfg.get(CONF_PHASE_ENTITY)
        if not ent:
            return self.max_phases
        st = state_str(self.hass, ent)
        if st == self.cfg.get(CONF_PHASE_1):
            return 1
        if st == self.cfg.get(CONF_PHASE_3):
            return 3
        return self.state.get("phases") or self.max_phases

    # ── Ziel/Energiebedarf ───────────────────────────────────────────────────
    def _next_deadline(self, now: datetime) -> datetime:
        t = time_from_str(self.p("deadline"), time(6, 0))
        dl = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return dl if dl > now else dl + timedelta(days=1)

    def _days_km(self, deadline: datetime) -> float | None:
        raw = state_str(self.hass, self.cfg.get(CONF_DAYS_ENTITY))
        if not raw:
            return None
        try:
            days = json.loads(raw)
        except ValueError:
            return None
        wd = deadline.weekday()
        for entry in days:
            if isinstance(entry, (list, tuple)) and entry and DAY_LABELS.get(str(entry[0]).upper()[:2]) == wd:
                return float(entry[1]) if len(entry) > 1 else 0.0
        return None

    def _update_need(self, now: datetime) -> None:
        goal = self.p("goal")
        self._deadline, self._latest_start, self._target_km = None, None, None
        self._need_wh = 0.0
        if goal in (EV_GOAL_PV, EV_GOAL_NOW):
            return
        deadline = self._next_deadline(now)
        km = float(self.p("target_km")) if goal == EV_GOAL_KM else self._days_km(deadline)
        if km is None:
            return
        self._target_km, self._deadline = km, deadline
        trip_wh = km * float(self.p("consumption")) * 10  # kWh/100km → Wh/km
        cap_wh = self._c(CONF_CAPACITY, 0) * 1000
        soc = self.soc
        if soc is not None and cap_wh > 0:
            usable = max(0.0, (soc - float(self.p("reserve_soc"))) / 100 * cap_wh)
            need_batt = max(0.0, trip_wh - usable)
            need_batt = min(need_batt, max(0.0, (float(self.p("max_soc")) - soc) / 100 * cap_wh))
            self._need_wh = need_batt / self.efficiency
        else:
            self._need_wh = max(0.0, trip_wh / self.efficiency - self.state["charged_wh"])
        if self._need_wh > 0:
            hours = self._need_wh / self.nominal
            self._latest_start = deadline - timedelta(hours=hours * 1.15) - timedelta(minutes=10)

    # ── Zyklus ───────────────────────────────────────────────────────────────
    def pre_update(self, ctx: Context) -> None:
        if not self.connected:
            self.state["charged_wh"] = 0.0
        elif self.is_on():
            self.state["charged_wh"] += self.power_now() * ctx.dt / 3600
            if self.state.get("since") is None:
                self.state["since"] = ctx.now.timestamp()
        if not self.is_on():
            self.state["since"] = None
        self._update_need(ctx.now)

    def _phases_for(self, avail: float, ctx: Context) -> int:
        if not self.cfg.get(CONF_PHASE_ENTITY):
            return self.max_phases
        mode = self.p("phase_mode")
        if mode == EV_PHASE_1:
            return 1
        if mode == EV_PHASE_3:
            return 3
        cur = self.current_phases or 3
        p3 = self.min_a * self.voltage * 3
        want = 3 if avail >= (p3 - 300 if cur == 3 else p3 + 300) else 1
        last = self.state.get("phase_switch")
        if want != cur and last and ctx.now.timestamp() - float(last) < PHASE_SWITCH_INTERVAL.total_seconds():
            return cur
        return want

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        if not self.connected:
            self.status = "nicht_verbunden"
            self._deficit_since = None
            return Decision(False, 0, "Auto nicht angesteckt")
        soc = self.soc
        if soc is not None and soc >= float(self.p("max_soc")):
            self.status = "voll"
            return Decision(False, 0, f"Max-SoC erreicht ({soc:.0f} %)")

        on = self.is_on()
        goal = self.p("goal")
        max_ph = 3 if self.cfg.get(CONF_PHASE_ENTITY) else self.max_phases

        if goal == EV_GOAL_NOW:
            self.status = "laedt_sofort"
            return self._charge(self.max_a, max_ph, "Sofort laden", forced=True)

        if self._latest_start and ctx.now >= self._latest_start and self._need_wh > 0:
            self.status = "laedt_pflicht"
            return self._charge(self.max_a, max_ph,
                                f"Ziel {self._target_km:.0f} km bis {self._deadline:%H:%M} – Netzladung",
                                forced=True)

        # Follow instantaneous grid power for modulation; longer averages are
        # only start gates, not a throttle on a running charge.
        avail = ctx.now_left(budget_left)
        avail_avg = ctx.short_left(budget_left) if ctx.history_ready else avail
        share = float(self.p("pv_share")) / 100
        phases = self._phases_for(avail, ctx)
        p_min = self.min_a * self.voltage * phases
        threshold = p_min * share

        if on:
            if avail >= threshold:
                self._deficit_since = None
            else:
                self._deficit_since = self._deficit_since or ctx.now
                if ctx.now - self._deficit_since >= timedelta(minutes=float(self.p("stop_delay"))):
                    self._deficit_since = None
                    self.status = "wartet"
                    return Decision(False, 0, f"Überschuss fehlt ({avail:.0f} W < {threshold:.0f} W)")
            # Reduce current immediately, even while stop_delay is counting.
            # The minimum 6 A remains necessary while charging is enabled.
            amps = clamp(math.floor(max(avail, p_min) / (self.voltage * phases)), self.min_a, self.max_a)
            self.status = "laedt_pv"
            return self._charge(amps, phases, f"PV-Laden {amps:.0f} A × {phases}")

        if avail >= threshold and avail_avg >= threshold:
            amps = clamp(math.floor(avail / (self.voltage * phases)), self.min_a, self.max_a)
            self.status = "laedt_pv"
            return self._charge(amps, phases, f"PV-Start {amps:.0f} A × {phases}")
        self.status = "wartet"
        extra = f" · Netzladung ab {self._latest_start:%H:%M}" if self._latest_start else ""
        return Decision(False, 0, f"Warte auf Überschuss ({avail:.0f} W < {threshold:.0f} W){extra}")

    def _charge(self, amps: float, phases: int, reason: str, forced: bool = False) -> Decision:
        amps = int(clamp(amps, self.min_a, self.max_a))
        return Decision(True, amps * self.voltage * phases, reason, forced=forced,
                        setpoint={"current": amps, "phases": phases})

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        if decision.on:
            await self._set_phases(decision.setpoint.get("phases"), ctx)
            await self._set_current(decision.setpoint.get("current"))
        if decision.on != self.is_on():
            await self._set_control(decision.on)

    async def async_disabled(self, ctx: Context) -> None:
        if self.p("mode") == "off" and self.is_on():
            await self._set_control(False)

    async def _set_current(self, amps: int | None) -> None:
        ent = self.cfg.get(CONF_CURRENT_ENTITY)
        if not ent or amps is None:
            return
        if state_float(self.hass, ent) == float(amps):
            return
        domain = ent.split(".")[0]
        await self.hass.services.async_call(domain, "set_value", {"entity_id": ent, "value": amps}, blocking=True)

    async def _set_phases(self, phases: int | None, ctx: Context) -> None:
        ent = self.cfg.get(CONF_PHASE_ENTITY)
        if not ent or phases is None:
            return
        option = self.cfg.get(CONF_PHASE_1 if phases == 1 else CONF_PHASE_3)
        if not option or state_str(self.hass, ent) == option:
            return
        await self.hass.services.async_call(ent.split(".")[0], "select_option",
                                            {"entity_id": ent, "option": option}, blocking=True)
        self.state["phase_switch"] = ctx.now.timestamp()
        self.state["phases"] = phases

    async def _set_control(self, on: bool) -> None:
        ent = self.cfg.get(CONF_CONTROL_ENTITY)
        if not ent:
            if not on:
                await self._set_current(int(self.min_a))
            return
        domain = ent.split(".")[0]
        if domain in ("select", "input_select"):
            option = self.cfg.get(CONF_CONTROL_ON if on else CONF_CONTROL_OFF)
            if option:
                await self.hass.services.async_call(domain, "select_option",
                                                    {"entity_id": ent, "option": option}, blocking=True)
        elif domain in ("button", "input_button"):
            if on:
                await self.hass.services.async_call(domain, "press", {"entity_id": ent}, blocking=True)
        else:
            await self._switch(ent, on)
        _LOGGER.info("[%s] Laden %s (%s)", self.name, "EIN" if on else "AUS", self.reason)

    def plan_demand(self, now: datetime) -> PlanDemand | None:
        if not self.connected:
            return None
        if self._need_wh > 0 and self._deadline:
            return PlanDemand(self.min_a * self.voltage * 3, self._need_wh, self._deadline)
        if self.p("goal") == EV_GOAL_PV:
            cap = self._c(CONF_CAPACITY, 0) * 1000
            soc = self.soc
            if cap and soc is not None:
                wh = max(0.0, (float(self.p("max_soc")) - soc) / 100 * cap / self.efficiency)
                if wh > 0:
                    return PlanDemand(self.min_a * self.voltage, wh, now.replace(hour=23, minute=0))
        return None
