"""Timed or PV-triggered floor-heating setpoint boost for a shared heat pump.

Read/modify/restore ONLY the configured writable setpoint. A durable snapshot
precedes every modification. No compressor control or WW scheduling is added.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

from ..const import MODE_AUTO
from ..helpers import (
    BinarySpec,
    ButtonSpec,
    ParamSpec,
    SensorSpec,
    power_w,
    state_float,
    state_str,
    time_from_str,
)
from .base import BaseDevice, Context, Decision

_LOGGER = logging.getLogger(__name__)
EPSILON = 0.2


class FBHBoostDevice(BaseDevice):
    TYPE = "heatpump_fbh"
    ICON = "mdi:heat-pump"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Place the upcoming WP heating commitment ahead of ordinary loads by
        # default. The user can change priority via normal SEP drag & drop.
        self.params["priority"] = 2
        self.state.setdefault("active", False)
        self.state.setdefault("completed_window", None)
        self.state.setdefault("window", None)
        self.state.setdefault("original", None)
        self.state.setdefault("target", None)
        self.state.setdefault("setpoint_entity", None)
        self.state.setdefault("runtime_seconds", 0.0)
        self.state.setdefault("idle_since", None)
        self.state.setdefault("reservation_released", False)
        self.state.setdefault("manual_hold_window", None)
        self.state.setdefault("manual_override", False)
        self.state.setdefault("last_sample", None)
        self.state.setdefault("externally_changed", False)
        self.state.setdefault("restore_pending", False)
        # Optional one-shot recovery after WW preempts an ACTIVE FBH cycle.
        # Scalar values are retained in HA's durable manager storage.
        self.state.setdefault("ww_seen", None)
        self.state.setdefault("last_fbh_running_at", None)
        self.state.setdefault("fbh_was_running_before_ww", False)
        self.state.setdefault("ww_ended_at", None)
        self.state.setdefault("ww_recovery_eligible", False)
        self.state.setdefault("restart_used_window", None)
        self.state.setdefault("restart_pulse_target", None)
        self.state.setdefault("restart_pulse_until", None)
        self.state.setdefault("restart_return_pending", False)

    def param_specs(self) -> list[ParamSpec]:
        return [
            ParamSpec("nominal_power", "number", float(self.cfg.get("nominal_power", 2500)),
                      "mdi:flash", 100, 12000, 50, "W"),
            ParamSpec("fbh_control", "select", "time", "mdi:calendar-clock",
                      options=["time", "pv"]),
            ParamSpec("fbh_delta", "number", 2.0, "mdi:thermometer-chevron-up",
                      0.5, 10, 0.5, "K"),
            ParamSpec("fbh_max_temp", "number", 45.0, "mdi:thermometer-alert",
                      15, 80, 0.5, "°C"),
            ParamSpec("fbh_start_1", "time", "10:00", "mdi:clock-start"),
            ParamSpec("fbh_end_1", "time", "13:00", "mdi:clock-end"),
            ParamSpec("fbh_start_2", "time", "00:00", "mdi:clock-start"),
            ParamSpec("fbh_end_2", "time", "00:00", "mdi:clock-end"),
            ParamSpec("fbh_reserve_before", "number", 30, "mdi:clock-fast",
                      0, 120, 5, "min"),
            ParamSpec("fbh_finish_runtime", "number", 180, "mdi:timer-check",
                      30, 600, 10, "min"),
            ParamSpec("fbh_idle_power", "number", 50, "mdi:flash-outline",
                      0, 1000, 5, "W"),
            ParamSpec("fbh_idle_minutes", "number", 20, "mdi:timer-sand",
                      20, 120, 5, "min"),
            ParamSpec("fbh_restart_after_ww", "switch", False, "mdi:heat-pump-outline"),
            ParamSpec("fbh_restart_wait", "number", 5, "mdi:clock-check",
                      1, 30, 1, "min"),
            ParamSpec("fbh_restart_delta", "number", 3.0, "mdi:thermometer-plus",
                      0.5, 8, 0.5, "K"),
            ParamSpec("fbh_restart_duration", "number", 15, "mdi:timer-play-outline",
                      5, 30, 1, "min"),
        ]

    def _windows(self, now: datetime) -> list[tuple[datetime, datetime, str]]:
        """Two optional same-day windows; equal/invalid start and end disables one."""
        local = dt_util.as_local(now)
        result = []
        for offset in (0, 1):
            date = (local + timedelta(days=offset)).date()
            for index in (1, 2):
                start = time_from_str(self.p(f"fbh_start_{index}"), local.time().replace(hour=0, minute=0))
                end = time_from_str(self.p(f"fbh_end_{index}"), local.time().replace(hour=0, minute=0))
                if start >= end:
                    continue  # No implicit midnight crossover; use local daytime windows.
                beginning = datetime.combine(date, start, tzinfo=local.tzinfo)
                finish = datetime.combine(date, end, tzinfo=local.tzinfo)
                result.append((beginning, finish, f"{date.isoformat()}:{index}"))
        return sorted(result)

    def _window_now(self, now: datetime) -> tuple[datetime, datetime, str] | None:
        local = dt_util.as_local(now)
        return next((w for w in self._windows(local) if w[0] <= local < w[1]), None)

    def _next_window(self, now: datetime) -> tuple[datetime, datetime, str] | None:
        local = dt_util.as_local(now)
        return next((w for w in self._windows(local)
                     if w[1] > local and w[2] != self.state.get("completed_window")), None)

    def _ww_active(self) -> bool | None:
        source = self.cfg.get("ww_active_entity")
        if not source:
            return False
        value = state_str(self.hass, source)
        return {"on": True, "off": False}.get(value)

    def _heating_active(self) -> bool | None:
        source = self.cfg.get("fbh_heating_active_entity")
        if not source:
            return None
        value = state_str(self.hass, source)
        return {"on": True, "off": False}.get(value)

    def _power(self) -> float | None:
        val = power_w(self.hass, self.cfg.get("power_sensor"))
        return val if val is not None and math.isfinite(val) and val >= 0 else None

    def _setpoint(self, entity: str | None = None) -> float | None:
        entity = entity or self.cfg.get("fbh_setpoint_entity")
        if not entity:
            return None
        st = self.hass.states.get(entity)
        if st is None or st.state in ("unavailable", "unknown"):
            return None
        if entity.startswith("climate."):
            try:
                value = float(st.attributes.get("temperature"))
            except (ValueError, TypeError):
                return None
            return value if math.isfinite(value) else None
        val = state_float(self.hass, entity)
        return val if val is not None and math.isfinite(val) else None

    async def _write_setpoint(self, entity: str, value: float) -> None:
        domain = entity.split(".", 1)[0]
        if domain == "climate":
            await self._call_actor("climate", "set_temperature",
                                   {"entity_id": entity, "temperature": value}, blocking=True)
        elif domain in ("number", "input_number"):
            await self._call_actor(domain, "set_value",
                                   {"entity_id": entity, "value": value}, blocking=True)
        else:
            raise ValueError("FBH-Sollwert muss eine schreibbare number/input_number/climate-Entität sein")

    def observed_entities(self) -> set[str]:
        return (super().observed_entities()
                | {entity for key in ("fbh_setpoint_entity", "fbh_heating_active_entity")
                   if (entity := self.cfg.get(key))})

    def _unavailable_actor(self) -> str | None:
        entity = self.state.get("setpoint_entity") if self.state.get("active") else self.cfg.get("fbh_setpoint_entity")
        if not entity:
            return "Sollwert-Entität fehlt"
        return entity if self._actor_unavailable(entity) else None

    def is_on(self) -> bool:
        return bool(self.state.get("active"))

    def power_accounted_in_grid(self) -> float:
        # The grid meter already measures the same compressor as WW boost.
        # Never credit/claim that measured power as reclaimable.
        return max(0.0, self._power() or 0.0)

    def status_attrs(self) -> dict:
        return {**super().status_attrs(),
                "regelung": self.p("fbh_control"),
                "sollwert_original": self.state.get("original"),
                "sollwert_boost": self.state.get("target"),
                "sollwert_entitaet": self.cfg.get("fbh_setpoint_entity"),
                "ww_aktiv": self._ww_active(),
                "heizbetrieb_aktiv": self._heating_active(),
                "laufzeit_heizen_min": round(float(self.state.get("runtime_seconds") or 0) / 60, 1),
                "fertig_im_zeitfenster": self.state.get("completed_window"),
                "temperatur_angehoben": bool(self.state.get("active") and not self.state.get("externally_changed")),
                "leistungsreservierung_freigegeben": bool(self.state.get("reservation_released")),
                "vorreservierung_w": round(self.advance_reservation(dt_util.now())),
                "manuell_geaendert": bool(self.state.get("externally_changed")),
                "ww_unterbrechung_fbh_vorher_aktiv": bool(self.state.get("fbh_was_running_before_ww")),
                "ww_wiederanlauf_freigegeben": bool(self.state.get("ww_recovery_eligible")),
                "ww_wiederanlauf_verwendet": self.state.get("restart_used_window"),
                "ww_wiederanlauf_impuls_bis": self.state.get("restart_pulse_until"),
                "ww_wiederanlauf_impuls_sollwert": self.state.get("restart_pulse_target")}


    def _temperature_raised(self) -> bool:
        if not self.state.get("active") or self.state.get("externally_changed"):
            return False
        actual = self._setpoint(self.state.get("setpoint_entity"))
        if actual is None:
            return False
        targets = [self.state.get("target"), self.state.get("restart_pulse_target")]
        return any(abs(actual - float(t)) <= EPSILON for t in targets if t is not None)

    def binary_specs(self) -> list[BinarySpec]:
        return super().binary_specs() + [
            BinarySpec("temperature_raised", self._temperature_raised,
                       icon="mdi:thermometer-chevron-up"),
        ]

    def button_specs(self) -> list[ButtonSpec]:
        return [
            ButtonSpec("raise_now", self._manual_raise, icon="mdi:arrow-up-bold"),
            ButtonSpec("lower_now", self._manual_lower, icon="mdi:arrow-down-bold"),
        ]

    async def _manual_raise(self) -> None:
        if self.mode != MODE_AUTO:
            raise ValueError("Jetzt anheben erfordert FBH-Automatikmodus")
        now = dt_util.now()
        window = self._window_now(now)
        if window is None or window[1] - dt_util.as_local(now) < timedelta(hours=1):
            raise ValueError("Jetzt anheben nur im Zeitfenster und mindestens 60 Minuten vor Ende")
        if self.state.get("active"):
            return
        original = self._setpoint()
        entity = self.cfg.get("fbh_setpoint_entity")
        if original is None or not entity:
            raise ValueError("FBH-Sollwert nicht verfügbar")
        target = original + float(self.p("fbh_delta"))
        st = self.hass.states.get(entity)
        maximum = float(self.p("fbh_max_temp"))
        if st and st.attributes.get("max") is not None:
            maximum = min(maximum, float(st.attributes["max"]))
        if target > maximum:
            raise ValueError("FBH-Sollwertmaximum überschritten")
        self.state.update(active=True, manual_override=False, manual_hold_window=None,
                          window=window[2],
                          setpoint_entity=entity, original=original, target=target,
                          started=dt_util.now().timestamp(), runtime_seconds=0.0,
                          idle_since=None, reservation_released=False,
                          last_sample=dt_util.now().timestamp(),
                          externally_changed=False, restore_pending=False)
        await self.manager.async_save_now()
        await self._write_setpoint(entity, target)

    async def _manual_lower(self) -> None:
        window = self._window_now(dt_util.now())
        if self.state.get("active"):
            await self._restore()
            if self.state.get("active"):
                raise RuntimeError("FBH-Rückstellung noch nicht bestätigt")
        self.state["manual_hold_window"] = window[2] if window else None
        self.state["manual_override"] = False
        await self.manager.async_save_now()

    def sensor_specs(self) -> list[SensorSpec]:
        return super().sensor_specs() + [
            SensorSpec("fbh_runtime", lambda: round(float(self.state.get("runtime_seconds") or 0) / 60),
                       unit="min", icon="mdi:timer-check-outline"),
        ]

    def _shared_ww_running(self) -> bool:
        if self._ww_active() is not False:
            return True  # Incomplete WW signal means wait rather than misattribute power.
        for device in self.manager.devices.values():
            if device is self or device.TYPE != "heatpump":
                continue
            if device.cfg.get("power_sensor") == self.cfg.get("power_sensor"):
                active = getattr(device, "ww_active", False)
                if active is not False or device.is_on():
                    return True
        return False

    def _pv_window_plausible(self, when: datetime) -> bool:
        forecast = getattr(self.manager, "forecast", None)
        if forecast is None:
            return False
        at = when.replace(minute=0, second=0, microsecond=0)
        value = forecast.hours.get(at)
        base = float(self.manager.p("base_load") or 0)
        return value is not None and math.isfinite(value) and value >= self.nominal + base

    def advance_reservation(self, now: datetime) -> float:
        """W above the *real* compressor metering; do not reserve it twice."""
        if self.mode != MODE_AUTO or self.state.get("externally_changed"):
            return 0
        if self._shared_ww_running():
            return 0
        window = self._next_window(now)
        if self.state.get("active"):
            if self.state.get("reservation_released"):
                return 0
            return max(0.0, self.nominal - (self._power() or 0.0))
        if not window:
            return 0
        start, end, key = window
        if self.state.get("completed_window") == key:
            return 0
        lead = timedelta(minutes=max(0.0, float(self.p("fbh_reserve_before") or 0)))
        local = dt_util.as_local(now)
        if not start - lead <= local < end:
            return 0
        if self.p("fbh_control") == "pv" and not self._pv_window_plausible(max(start, local)):
            return 0
        return max(0.0, self.nominal - (self._power() or 0.0))

    def _watch_ww_interruption(self, now: datetime, power: float | None,
                               ww: bool | None, heating: bool | None) -> None:
        """Observe WW edges; require proof FBH was running BEFORE WW started.

        A power reading without a positive FBH-mode sensor is insufficient;
        the compressor may have been heating water or doing another task.
        """
        t = now.timestamp()
        previous = self.state.get("ww_seen")
        has_feedback = bool(self.cfg.get("ww_active_entity") and
                            self.cfg.get("fbh_heating_active_entity"))
        if not self.p("fbh_restart_after_ww") or not has_feedback or not self.state.get("active"):
            self.state["ww_seen"] = ww
            self.state["ww_recovery_eligible"] = False
            return
        if ww is None or heating is None or power is None:
            # Unknown feedback must not trigger a speculative heat-pump restart.
            self.state["ww_seen"] = None
            self.state["ww_recovery_eligible"] = False
            return
        is_heating = heating is True and power > float(self.p("fbh_idle_power"))
        if ww is False and is_heating:
            self.state["last_fbh_running_at"] = t
            # Heating has already resumed on its own: a pulse is unnecessary.
            if self.state.get("ww_ended_at") is not None:
                self.state["ww_recovery_eligible"] = False
        if ww is True and previous is False:
            seen = self.state.get("last_fbh_running_at")
            was_running = bool(seen is not None and
                               0 <= t - float(seen) <= 180)
            self.state["fbh_was_running_before_ww"] = was_running
            self.state["ww_recovery_eligible"] = False
            self.state["ww_ended_at"] = None
        elif ww is False and previous is True:
            # Only this confirmed transition can authorize a future pulse.
            eligible = bool(self.state.get("fbh_was_running_before_ww") and
                            self.state.get("restart_used_window") != self.state.get("window") and
                            self._window_now(now) is not None)
            self.state["ww_ended_at"] = t
            self.state["ww_recovery_eligible"] = eligible
            self.state["fbh_was_running_before_ww"] = False
        self.state["ww_seen"] = ww

    def _restart_ready(self, ctx: Context) -> bool:
        if not self.state.get("active") or not self.state.get("ww_recovery_eligible"):
            return False
        if not self.p("fbh_restart_after_ww") or self.state.get("externally_changed"):
            return False
        if not self.cfg.get("fbh_heating_active_entity") or not self.cfg.get("ww_active_entity"):
            return False
        if self.state.get("restart_used_window") == self.state.get("window"):
            return False
        window = self._window_now(ctx.now)
        if not window or window[2] != self.state.get("window"):
            return False
        if (self._ww_active() is not False or self._heating_active() is not False or
                self._shared_ww_running()):
            return False
        power = self._power()
        if power is None or power >= float(self.p("fbh_idle_power")):
            return False
        ended = self.state.get("ww_ended_at")
        if ended is None or ctx.now.timestamp() - float(ended) < (
                float(self.p("fbh_restart_wait")) * 60):
            return False
        # In PV-gated mode do not force extra heating without surplus.
        if self.p("fbh_control") == "pv" and (
                not ctx.grid_valid or ctx.budget_now < self.nominal):
            return False
        return True

    async def _restart_pulse(self, ctx: Context) -> None:
        """Temporarily raise the ALREADY boosted target, not the stored original."""
        if not self._restart_ready(ctx):
            return
        entity = self.state.get("setpoint_entity")
        baseline = self.state.get("target")
        actual = self._setpoint(entity)
        if entity is None or baseline is None or actual is None or (
                abs(actual - float(baseline)) > EPSILON):
            return
        maximum = float(self.p("fbh_max_temp"))
        st = self.hass.states.get(entity)
        if st and st.attributes.get("max") is not None:
            try:
                maximum = min(maximum, float(st.attributes["max"]))
            except (TypeError, ValueError):
                return
        pulse_target = min(maximum, float(baseline) + float(self.p("fbh_restart_delta")))
        if pulse_target <= float(baseline) + EPSILON:
            return  # Temperature limit reached; never exceed it to force a start.
        # If near the end, the existing window-end restore takes precedence.
        self.state["restart_used_window"] = self.state.get("window")
        self.state["ww_recovery_eligible"] = False
        self.state["restart_pulse_target"] = pulse_target
        self.state["restart_pulse_until"] = (
            ctx.now.timestamp() + 60 * float(self.p("fbh_restart_duration")))
        self.state["restart_return_pending"] = False
        await self.manager.async_save_now()  # Crash-safe before extra setpoint write.
        await self._write_setpoint(entity, pulse_target)

    async def _settle_restart_pulse(self, ctx: Context) -> None:
        """Revert the temporary impulse to the normal FBH boost setpoint."""
        pulse_target = self.state.get("restart_pulse_target")
        if pulse_target is None:
            return
        baseline = self.state.get("target")
        entity = self.state.get("setpoint_entity")
        actual = self._setpoint(entity)
        if actual is None or baseline is None or entity is None:
            return  # A missing sensor never justifies clearing rollback data.
        until = self.state.get("restart_pulse_until")
        running_again = (self._ww_active() is False and self._heating_active() is True
                         and (self._power() or 0) > float(self.p("fbh_idle_power")))
        must_end = bool(self._ww_active() is not False or running_again or
                        (until is not None and ctx.now.timestamp() >= float(until)) or
                        self._window_now(ctx.now) is None)
        if not must_end and not self.state.get("restart_return_pending"):
            return
        if abs(actual - float(baseline)) <= EPSILON:
            self.state.update(restart_pulse_target=None, restart_pulse_until=None,
                              restart_return_pending=False)
            await self.manager.async_save_now()
            return
        if abs(actual - float(pulse_target)) > EPSILON:
            # External intervention: do not overwrite a user-adjusted setpoint.
            self.state["externally_changed"] = True
            self.state["ww_recovery_eligible"] = False
            return
        self.state["restart_return_pending"] = True
        await self.manager.async_save_now()
        await self._write_setpoint(entity, float(baseline))
        confirmed = self._setpoint(entity)
        if confirmed is not None and abs(confirmed - float(baseline)) <= EPSILON:
            self.state.update(restart_pulse_target=None, restart_pulse_until=None,
                              restart_return_pending=False)
            await self.manager.async_save_now()

    def pre_update(self, ctx: Context) -> None:
        if not self.state.get("active"):
            return
        # Require uninterrupted power measurements; a restart/offline gap does
        # not mean hours of actual compressor operation.
        power = self._power()
        ww = self._ww_active()
        heating = self._heating_active()
        previous = self.state.get("last_sample")
        self.state["last_sample"] = ctx.now.timestamp()
        self._watch_ww_interruption(ctx.now, power, ww, heating)
        if power is None or ww is not False:
            self.state["idle_since"] = None
            return
        # Do not count hours of an unrelated compressor mode. Without at
        # least one mode signal, standby alone cannot prove FBH completion.
        if not (self.cfg.get("ww_active_entity") or
                self.cfg.get("fbh_heating_active_entity")):
            self.state["idle_since"] = None
            return
        idle_limit = float(self.p("fbh_idle_power"))
        if power >= idle_limit:
            self.state["idle_since"] = None
            self.state["reservation_released"] = False
            if heating is False:
                return
            elapsed = min(max(0.0, ctx.now.timestamp() - float(previous or ctx.now.timestamp())), 90.0)
            self.state["runtime_seconds"] = float(self.state.get("runtime_seconds") or 0) + elapsed
            return
        # Once genuine heating ran for long enough, the heating-status
        # binary may legitimately turn OFF in standby; that is completion,
        # not a reason to reset the idle timer.
        if self.state.get("restart_pulse_target") is not None:
            return  # A running restart pulse is not a finished FBH cycle.
        if self.state.get("runtime_seconds", 0) < float(self.p("fbh_finish_runtime")) * 60:
            return
        if self.state.get("idle_since") is None:
            self.state["idle_since"] = ctx.now.timestamp()
        if ctx.now.timestamp() - float(self.state["idle_since"]) >= 60 * float(self.p("fbh_idle_minutes")):
            self.state["reservation_released"] = True
            self.status = "boost"
            self.reason = "FBH-Heizzyklus beendet: Leistung freigegeben, Sollwert bleibt angehoben"

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        now = ctx.now
        if self.state.get("restore_pending"):
            return Decision(False, 0, "Wiederherstellung des FBH-Sollwerts läuft")
        if self.state.get("active"):
            key = self.state.get("window")
            window = self._window_now(now)
            if key is not None and (window is None or window[2] != key):
                self.status = "fertig"
                return Decision(False, 0, "FBH-Zeitfenster beendet – Sollwert wiederherstellen")
            if self._shared_ww_running():
                self.status = "wartet"
                return Decision(True, 0, "Warmwasserbetrieb hat Vorrang – keine zusätzliche FBH-Reservierung")
            self.status = "boost"
            if self.state.get("reservation_released"):
                return Decision(True, 0, "Temperatur angehoben – Leistungsreservierung freigegeben")
            return Decision(True, self.nominal, "FBH-Sollwerterhöhung läuft")
        window = self._window_now(now)
        if window and self.state.get("manual_hold_window") == window[2]:
            return Decision(False, 0, "Manuell abgesenkt – bis zum nächsten Zeitfenster gesperrt")
        if window and self.state.get("completed_window") == window[2]:
            self.status = "fertig"
            return Decision(False, 0, "FBH-Boost in diesem Zeitfenster erledigt")
        if not window:
            self.status = "bereit"
            return Decision(False, 0, "Kein offenes FBH-Zeitfenster")
        if self._shared_ww_running():
            self.status = "wartet"
            return Decision(False, 0, "Warmwasser hat Vorrang")
        original = self._setpoint()
        if original is None:
            self.status = "wartet"
            return Decision(False, 0, "FBH-Sollwert nicht lesbar")
        target = original + float(self.p("fbh_delta"))
        max_value = float(self.p("fbh_max_temp"))
        st = self.hass.states.get(self.cfg.get("fbh_setpoint_entity"))
        if st and st.attributes.get("max") is not None:
            try:
                max_value = min(max_value, float(st.attributes["max"]))
            except (TypeError, ValueError):
                return Decision(False, 0, "FBH-Gerätegrenze ungültig")
        if target > max_value:
            self.status = "wartet"
            return Decision(False, 0, f"Max. FBH-Sollwert {max_value:g} °C überschritten")
        if self.p("fbh_control") == "pv" and (
                not ctx.grid_valid or min(ctx.now_left(budget_left), budget_left) < self.nominal):
            self.status = "wartet"
            return Decision(False, 0, "PV-Überschuss für FBH-Boost zu niedrig")
        self.status = "boost"
        return Decision(True, self.nominal, "FBH-Sollwerterhöhung starten")

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        if self.state.get("active"):
            # A manually edited target cannot be overwritten on automatic restore.
            actual = self._setpoint(self.state.get("setpoint_entity"))
            target = self.state.get("target")
            ts = self.state.get("started")
            if (actual is not None and target is not None and ts is not None
                    and ctx.now.timestamp() - float(ts) > 120
                    and abs(actual - float(target)) > EPSILON
                    and (self.state.get("restart_pulse_target") is None or
                         abs(actual - float(self.state["restart_pulse_target"])) > EPSILON)):
                self.state["externally_changed"] = True
                self.state["completed_window"] = self.state.get("window")
                decision = Decision(False, 0, "FBH-Sollwert extern verändert")
            if not decision.on:
                await self._restore()
            else:
                await self._settle_restart_pulse(ctx)
                if self.state.get("restart_pulse_target") is None:
                    await self._restart_pulse(ctx)
            return
        if not decision.on:
            return
        window = self._window_now(ctx.now)
        if window is None:
            return
        original = self._setpoint()
        if original is None:
            return
        target = original + float(self.p("fbh_delta"))
        self.state.update(active=True, window=window[2], setpoint_entity=self.cfg["fbh_setpoint_entity"],
                          original=original, target=target, started=ctx.now.timestamp(),
                          runtime_seconds=0.0, idle_since=None, reservation_released=False,
                          manual_override=False, last_sample=ctx.now.timestamp(),
                          externally_changed=False, restore_pending=False,
                          ww_seen=self._ww_active(), last_fbh_running_at=None,
                          fbh_was_running_before_ww=False, ww_ended_at=None,
                          ww_recovery_eligible=False, restart_pulse_target=None,
                          restart_pulse_until=None, restart_return_pending=False)
        # Persist BEFORE changing the external actuator: restart must restore.
        await self.manager.async_save_now()
        await self._write_setpoint(self.state["setpoint_entity"], target)

    async def _restore(self) -> None:
        """Confirm actual HA setpoint before clearing durable rollback state."""
        if not self.state.get("active"):
            return
        entity = self.state.get("setpoint_entity")
        original = self.state.get("original")
        current = self._setpoint(entity)
        target = self.state.get("target")
        if current is None:
            raise RuntimeError("FBH-Sollwert nicht verfügbar; Wiederherstellung später versuchen")
        if not entity or original is None or target is None:
            raise RuntimeError("FBH-Rückstellwert fehlt; Zustand zur Diagnose erhalten")
        if not self.state.get("externally_changed"):
            pulse_target = self.state.get("restart_pulse_target")
            if abs(current - float(original)) <= EPSILON:
                pass  # Already restored (or the boost write never took effect).
            elif (abs(current - float(target)) <= EPSILON or
                  (pulse_target is not None and
                   abs(current - float(pulse_target)) <= EPSILON)):
                self.state["restore_pending"] = True
                await self.manager.async_save_now()
                await self._write_setpoint(entity, float(original))
                actual = self._setpoint(entity)
                if actual is None or abs(actual - float(original)) > EPSILON:
                    return  # Keep rollback state until HA confirms the change.
            elif self.state.get("restore_pending"):
                return  # Delayed write/HA state update: retry on the next cycle.
            else:
                # Do not overwrite an externally adjusted temperature target.
                self.state["externally_changed"] = True
        self.state.update(active=False, original=None, target=None, setpoint_entity=None,
                          idle_since=None, last_sample=None, reservation_released=False,
                          manual_override=False, restore_pending=False,
                          ww_recovery_eligible=False, fbh_was_running_before_ww=False,
                          restart_pulse_target=None, restart_pulse_until=None,
                          restart_return_pending=False, ww_ended_at=None)
        await self.manager.async_save_now()

    async def async_run(self, ctx: Context, budget_left: float) -> Decision:
        if self.state.get("active") and self.mode != MODE_AUTO:
            # Avoid leaving a raised setpoint behind when the hub/FBH mode
            # switches to Observe, Manual or Off.
            await self._restore()
            return Decision(False, 0, "FBH-Moduswechsel – Sollwert zurückstellen")
        return await super().async_run(ctx, budget_left)

    async def async_disabled(self, ctx: Context) -> None:
        await self._restore()
