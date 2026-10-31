"""PV-controlled resistive heater (Heizstab), switch or input_boolean.

The *instantaneous* per-device budget is used for start and stop, never a
rolling mean. Positive budget = PV export, negative = real grid import.
The physical grid meter already includes ON heater consumption; it must
not be subtracted a second time. Higher-priority *unmeasured* allocations
are still reserved by the EnergyManager before this device decides.

Minimum on/off times are OPTIONAL (zero disables them). Invalid temperature,
maximum temperature, and integration/device OFF always stop immediately.
"""
from __future__ import annotations

import math
from datetime import datetime, time, timedelta

from ..const import CONF_POWER_SENSOR, CONF_SWITCH, CONF_TEMP_SENSOR
from ..helpers import ParamSpec, is_on, power_w, state_float, state_str, time_from_str
from .base import BaseDevice, Context, Decision


class HeaterDevice(BaseDevice):
    TYPE = "heater"
    ICON = "mdi:water-boiler"
    CONTROLS_MANUAL = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state.setdefault("last_switch", None)
        self.state.setdefault("last_switch_state", None)

    def param_specs(self) -> list[ParamSpec]:
        return [
            ParamSpec("nominal_power", "number",
                      float(self.cfg.get("nominal_power", 2000)),
                      "mdi:flash", 100, 10000, 50, "W"),
            ParamSpec("heater_max_temp", "number", 55,
                      "mdi:thermometer-high", 30, 85, 0.5, "°C"),
            ParamSpec("heater_hysteresis", "number", 3,
                      "mdi:thermometer-chevron-down", 0, 30, 0.5, "K"),
            ParamSpec("heater_start_surplus", "number", 2200,
                      "mdi:solar-power", 100, 12000, 50, "W"),
            ParamSpec("heater_stop_surplus", "number", 0,
                      "mdi:transmission-tower-import", -2000, 2000, 50, "W"),
            ParamSpec("heater_earliest_start", "time", "10:00",
                      "mdi:clock-start"),
            ParamSpec("heater_min_on", "number", 0,
                      "mdi:timer-lock-outline", 0, 120, 1, "min"),
            ParamSpec("heater_min_off", "number", 0,
                      "mdi:timer-lock-open-outline", 0, 120, 1, "min"),
        ]

    @property
    def switch(self) -> str:
        return self.cfg[CONF_SWITCH]

    def is_on(self) -> bool:
        return is_on(self.hass, self.switch)

    @property
    def temperature(self) -> float | None:
        temp = state_float(self.hass, self.cfg.get(CONF_TEMP_SENSOR))
        return temp if temp is not None and math.isfinite(temp) else None

    @property
    def start_need(self) -> float:
        # Even an accidentally low start threshold must cover the full heater.
        return max(self.nominal, float(self.p("heater_start_surplus")))

    def can_preempt(self, now: datetime) -> bool:
        """An ON heater may yield to a higher-ranked device after minimum-on."""
        return (self.mode == "auto" and self.is_on()
                and not self._unavailable_actor()
                and now.timestamp() >= self._actuator_retry_at
                and self._remaining(now, True) == 0)

    async def async_preempt(self, ctx: Context) -> None:
        """Shed and hold off while the upstream device obtains a stable budget."""
        await self._switch(self.switch, False)
        self.state["last_switch"] = ctx.now.timestamp()
        self.state["last_switch_state"] = False
        self.state["preempt_until"] = (ctx.now + timedelta(
            minutes=max(2, float(self.manager.p("avg_window") or 20)
                        + 2 * float(self.manager.p("trend_window") or 10)))).timestamp()
        await self.manager.async_save_now()

    def power_accounted_in_grid(self) -> float:
        # Only an ACTUAL measurement can cancel nominal reservation; never
        # mistake BaseDevice's nominal fallback for a metered observation.
        p = power_w(self.hass, self.cfg.get(CONF_POWER_SENSOR))
        return max(0.0, p) if p is not None and math.isfinite(p) else 0.0

    def pre_update(self, ctx: Context) -> None:
        raw = state_str(self.hass, self.switch)
        if raw not in ("on", "off"):
            return
        observed = raw == "on"
        previous = self.state.get("last_switch_state")
        if previous is not None and bool(previous) != observed:
            # Manual/external changes must also honour optional anti-cycling.
            self.state["last_switch"] = ctx.now.timestamp()
        self.state["last_switch_state"] = observed

    def _remaining(self, now: datetime, on: bool) -> float:
        ts = self.state.get("last_switch")
        if ts is None:
            return 0.0
        try:
            duration = float(self.p("heater_min_on" if on else "heater_min_off"))
            return max(0.0, duration * 60 - (now.timestamp() - float(ts)))
        except (TypeError, ValueError, OverflowError):
            # Corrupt switch timestamps must not allow rapid switching.
            return 60.0

    def status_attrs(self) -> dict:
        return {
            **super().status_attrs(),
            "temperatur_ist_c": self.temperature,
            "temperatur_max_c": float(self.p("heater_max_temp")),
            "einschalten_unter_c": float(self.p("heater_max_temp")) - float(self.p("heater_hysteresis")),
            "pv_start_noetig_w": round(self.start_need),
            "pv_stop_schwelle_w": float(self.p("heater_stop_surplus")),
            "budgetregelung": "nur Momentanwert, kein Mittelwert",
            "schaltpause_rest_s": round(self._remaining(datetime.now().astimezone(), self.is_on())),
        }

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        raw = state_str(self.hass, self.switch)
        on = raw == "on"
        temp = self.temperature
        high = float(self.p("heater_max_temp"))
        low = high - float(self.p("heater_hysteresis"))
        # Budget already includes ON draw in grid. Do NOT add the heater's
        # own metered power back for its stop check: import must switch OFF.
        # The manager dispatches its higher-priority reservations first.
        now_budget = ctx.now_left(budget_left)

        if raw not in ("on", "off"):
            self.status = "aus"
            return Decision(False, 0, "Schaltzustand unbekannt – keine Heizfreigabe")

        if temp is None:
            self.status = "aus"
            return Decision(False, 0, "Temperatursensor ungültig – Heizstab AUS (Sicherheit)")

        # Temperature protection ALWAYS outranks minimum-on.
        if temp >= high:
            self.status = "max_erreicht"
            return Decision(False, 0, f"Maximaltemperatur erreicht ({temp:.1f} °C ≥ {high:.1f} °C)")

        if self.mode == "manual":
            self.status = "manuell"
            if not on:
                if temp >= low:
                    return Decision(False, 0,
                                    f"Manuell: Neustart erst unter {low:.1f} °C")
                seconds = self._remaining(ctx.now, False)
                if seconds > 0:
                    return Decision(False, 0, f"Mindestpause noch {seconds:.0f} s")
            return Decision(True, self.nominal,
                            f"Manuell: Heizen bis {high:.1f} °C – Netzbezug erlaubt",
                            forced=True)

        # PV operation requires a trustworthy meter, even during minimum-on.
        # Manual thermostat operation intentionally permits grid consumption.
        if not ctx.grid_valid:
            self.status = "aus"
            return Decision(False, 0, "Netzsensor ungültig – Heizstab AUS; PV-Freigabe gesperrt")

        if on:
            self.status = "laeuft"
            stop_at = float(self.p("heater_stop_surplus"))
            if now_budget < stop_at:
                seconds = self._remaining(ctx.now, True)
                if seconds > 0:
                    return Decision(True, self.nominal,
                                    f"Budget aktuell {now_budget:.0f} W < {stop_at:.0f} W; "
                                    f"Mindestlaufzeit noch {seconds:.0f} s")
                return Decision(False, 0, f"Budget aktuell {now_budget:.0f} W < {stop_at:.0f} W – AUS")
            return Decision(True, self.nominal,
                            f"PV-Restverbrauch aktuell {now_budget:.0f} W; "
                            f"Temperatur {temp:.1f}/{high:.1f} °C")

        self.status = "wartet"
        if ctx.now.timestamp() < float(self.state.get("preempt_until") or 0):
            return Decision(False, 0, "Vorrangiger Verbraucher – Heizstab bleibt aus")
        if ctx.now.time() < time_from_str(self.p("heater_earliest_start"), time(10, 0)):
            return Decision(False, 0, f"Frühester Start {self.p('heater_earliest_start')}")
        if temp >= low:
            return Decision(False, 0, f"Temperatur {temp:.1f} °C; Neustart erst unter {low:.1f} °C")
        seconds = self._remaining(ctx.now, False)
        if seconds > 0:
            return Decision(False, 0, f"Mindestpause noch {seconds:.0f} s")
        if now_budget < self.start_need:
            return Decision(False, 0,
                            f"PV-Restbudget aktuell {now_budget:.0f} W < {self.start_need:.0f} W")
        self.status = "laeuft"
        return Decision(True, self.nominal,
                        f"PV-Restbudget aktuell {now_budget:.0f} W ≥ {self.start_need:.0f} W")

    async def async_priority_stop(self, ctx: Context) -> bool:
        """Only stop: never start, and do not wait behind another consumer."""
        if self.mode == "observe" or not self.is_on():
            return False
        if self.mode == "off":
            decision = Decision(False, 0, "Modus: Aus")
        else:
            decision = self.decide(ctx, ctx.alloc_base)
            if (self.mode == "auto" and ctx.grid_valid
                    and ctx.budget_now < float(self.p("heater_stop_surplus"))):
                decision = Decision(False, 0,
                                    f"Vorrangige Abschaltung: Budget {ctx.budget_now:.0f} W – AUS")
        if decision.on:
            return False
        self.status = "aus"
        self.reason = decision.reason
        self.last_decision = decision
        # An old actuator retry pause must not suppress an urgent OFF attempt.
        await self.async_apply(decision, ctx)
        return True

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        raw = state_str(self.hass, self.switch)
        # Unknown actor: fail closed, never attempt a blind ON command.
        if raw is None or decision.on == (raw == "on"):
            return
        await self._switch(self.switch, decision.on)
        self.state["last_switch"] = ctx.now.timestamp()
        self.state["last_switch_state"] = decision.on
        await self.manager.async_save_now()

    async def async_disabled(self, ctx: Context) -> None:
        # Unlike a washing machine, a resistive heater is stopped on OFF,
        # regardless of configured minimum-on time.
        if self.is_on():
            await self._switch(self.switch, False)
            self.state["last_switch"] = ctx.now.timestamp()
            self.state["last_switch_state"] = False
            await self.manager.async_save_now()


