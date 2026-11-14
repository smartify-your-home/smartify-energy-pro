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
from ..helpers import ParamSpec, SensorSpec, state_float, state_str, power_w, time_from_str
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
        self.state.setdefault("last_sample", None)
        self.state.setdefault("externally_changed", False)
        self.state.setdefault("restore_pending", False)

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
                "vorreservierung_w": round(self.advance_reservation(dt_util.now())),
                "manuell_geaendert": bool(self.state.get("externally_changed"))}

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
            if self.state.get("completed_window") == self.state.get("window"):
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
            if heating is False:
                return
            elapsed = min(max(0.0, ctx.now.timestamp() - float(previous or ctx.now.timestamp())), 90.0)
            self.state["runtime_seconds"] = float(self.state.get("runtime_seconds") or 0) + elapsed
            return
        # Once genuine heating ran for long enough, the heating-status
        # binary may legitimately turn OFF in standby; that is completion,
        # not a reason to reset the idle timer.
        if self.state.get("runtime_seconds", 0) < float(self.p("fbh_finish_runtime")) * 60:
            return
        if self.state.get("idle_since") is None:
            self.state["idle_since"] = ctx.now.timestamp()
        if ctx.now.timestamp() - float(self.state["idle_since"]) >= 60 * float(self.p("fbh_idle_minutes")):
            self.state["completed_window"] = self.state.get("window")
            self.status = "fertig"
            self.reason = "FBH-Boost abgeschlossen: WP länger im Standby"
            # async_apply restores the old setpoint and releases the budget.

    def decide(self, ctx: Context, budget_left: float) -> Decision:
        now = ctx.now
        if self.state.get("restore_pending"):
            return Decision(False, 0, "Wiederherstellung des FBH-Sollwerts läuft")
        if self.state.get("active"):
            if self.state.get("completed_window") == self.state.get("window"):
                self.status = "fertig"
                return Decision(False, 0, "FBH fertig – Standby erkannt")
            key = self.state.get("window")
            window = self._window_now(now)
            if window is None or window[2] != key:
                self.status = "fertig"
                return Decision(False, 0, "FBH-Zeitfenster beendet – Sollwert wiederherstellen")
            if self._shared_ww_running():
                self.status = "wartet"
                return Decision(True, 0, "Warmwasserbetrieb hat Vorrang – keine zusätzliche FBH-Reservierung")
            self.status = "boost"
            return Decision(True, self.nominal, "FBH-Sollwerterhöhung läuft")
        window = self._window_now(now)
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
                    and abs(actual - float(target)) > EPSILON):
                self.state["externally_changed"] = True
                self.state["completed_window"] = self.state.get("window")
                decision = Decision(False, 0, "FBH-Sollwert extern verändert")
            if not decision.on:
                await self._restore()
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
                          runtime_seconds=0.0, idle_since=None, last_sample=ctx.now.timestamp(),
                          externally_changed=False, restore_pending=False)
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
            if abs(current - float(original)) <= EPSILON:
                pass  # Already restored (or the boost write never took effect).
            elif abs(current - float(target)) <= EPSILON:
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
                          idle_since=None, last_sample=None, restore_pending=False)
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
