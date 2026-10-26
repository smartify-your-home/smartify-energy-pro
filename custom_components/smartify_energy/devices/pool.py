"""Poolpumpe – Logik aus pool_control, Soll-Laufzeit aus Wassertemperatur.

Soll-Laufzeit = Wassertemperatur × Faktor (Standard 0,5 → Faustregel T/2),
begrenzt auf Minimum/Maximum. Ohne Temperatursensor gilt die feste Soll-Laufzeit.
Einschalten: PV-Überschuss (aktuell UND Mittelwert) – auch über Soll bis Max-Laufzeit,
             Pflichtlaufzeit Vormittag (VM-Anteil bis VM-Zeit), Pflichtlaufzeit Tag
             (Rest bis Sonnenuntergang − 30 min).
Ausschalten: Sperrzeit, Max-Laufzeit (hart), Überschuss fehlt 15 min und Ziel erreicht.
Anti-Toggle: Mindestlaufzeit / Mindestpause.
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from homeassistant.util import dt as dt_util

from ..const import (
    CONF_SWITCH,
    CONF_TEMP_SENSOR,
    POOL_SEASON_AUTO,
    POOL_SEASON_SUMMER,
    POOL_SEASON_WINTER,
    POOL_SEASONS,
)
from ..helpers import ParamSpec, SensorSpec, clamp, in_window, is_on, state_float, time_from_str
from .base import BaseDevice, Context, Decision, PlanDemand

_LOGGER = logging.getLogger(__name__)
LOW_MINUTES = 15


class PoolDevice(BaseDevice):
    TYPE = "pool"
    ICON = "mdi:pool"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state.setdefault("day", None)
        self.state.setdefault("runtime", 0.0)     # Minuten heute
        self.state.setdefault("runtime_vm", 0.0)  # Minuten bis VM-Zeit
        self.state.setdefault("last_switch", None)
        self._low_since: datetime | None = None

    def param_specs(self) -> list[ParamSpec]:
        return [
            ParamSpec("season", "select", POOL_SEASON_AUTO, "mdi:sun-snowflake-variant", options=POOL_SEASONS, config=False),
            ParamSpec("nominal_power", "number", float(self.cfg.get("nominal_power", 700)),
                      "mdi:flash", 50, 3000, 10, "W"),
            ParamSpec("fixed_runtime", "number", 6.0, "mdi:timer-outline", 0, 24, 0.5, "h"),
            ParamSpec("temp_factor", "number", 0.5, "mdi:thermometer-lines", 0.1, 1.0, 0.05, "h/°C"),
            ParamSpec("runtime_min", "number", 3.0, "mdi:timer-minus-outline", 0, 24, 0.5, "h"),
            ParamSpec("runtime_max", "number", 10.0, "mdi:timer-plus-outline", 0, 24, 0.5, "h"),
            ParamSpec("max_runtime", "number", 12.0, "mdi:timer-alert-outline", 0, 24, 0.5, "h"),
            ParamSpec("winter_temp", "number", 12.0, "mdi:snowflake-thermometer", 0, 25, 0.5, "°C"),
            ParamSpec("vm_share", "number", 40, "mdi:weather-sunset-up", 0, 100, 5, "%"),
            ParamSpec("vm_deadline", "time", "11:45", "mdi:clock-time-eleven-outline"),
            ParamSpec("lock_enabled", "switch", True, "mdi:pot-steam"),
            ParamSpec("lock_start", "time", "12:00", "mdi:clock-start"),
            ParamSpec("lock_end", "time", "13:00", "mdi:clock-end"),
            ParamSpec("min_on", "number", 20, "mdi:timer-lock-outline", 0, 120, 1, "min"),
            ParamSpec("min_off", "number", 20, "mdi:timer-lock-open-outline", 0, 120, 1, "min"),
        ]

    def sensor_specs(self) -> list[SensorSpec]:
        return super().sensor_specs() + [
            SensorSpec("runtime_today", lambda: round(self.state["runtime"]), unit="min",
                       icon="mdi:timer-check-outline", state_class="measurement"),
            SensorSpec("runtime_target", lambda: round(self.target_min), unit="min",
                       icon="mdi:target", attrs=lambda: {
                           "vormittag_ziel_min": round(self.target_vm_min),
                           "vormittag_ist_min": round(self.state["runtime_vm"]),
                           "max_min": round(self.max_min),
                           "wassertemperatur": self.water_temp,
                           "saison_aktiv": self.season_active,
                       }),
        ]

    # ── Hilfswerte ───────────────────────────────────────────────────────────
    @property
    def switch(self) -> str:
        return self.cfg[CONF_SWITCH]

    def is_on(self) -> bool:
        return is_on(self.hass, self.switch)

    def own_budget_power(self, measured_w: float, reclaimed_w: float) -> float:
        # Existing pool draw is already reflected in the grid. It can count
        # toward maintaining its own run, never toward another device's start.
        return measured_w if self.mode == "auto" and self.is_on() else 0.0

    @property
    def water_temp(self) -> float | None:
        return state_float(self.hass, self.cfg.get(CONF_TEMP_SENSOR))

    @property
    def season_active(self) -> bool:
        season = self.p("season")
        if season == POOL_SEASON_SUMMER:
            return True
        if season == POOL_SEASON_WINTER:
            return False
        temp = self.water_temp
        return temp is None or temp >= float(self.p("winter_temp"))

    @property
    def target_min(self) -> float:
        if not self.season_active:
            return 0.0
        temp = self.water_temp
        if temp is None:
            hours = float(self.p("fixed_runtime"))
        else:
            hours = clamp(temp * float(self.p("temp_factor")),
                          float(self.p("runtime_min")), float(self.p("runtime_max")))
        return hours * 60

    @property
    def target_vm_min(self) -> float:
        return self.target_min * float(self.p("vm_share")) / 100

    @property
    def max_min(self) -> float:
        return max(float(self.p("max_runtime")) * 60, self.target_min) if self.season_active else 0.0

    def _vm_deadline(self) -> time:
        return time_from_str(self.p("vm_deadline"), time(11, 45))

    def _locked(self, now: datetime) -> bool:
        if not self.p("lock_enabled"):
            return False
        return in_window(now, time_from_str(self.p("lock_start"), time(12)),
                         time_from_str(self.p("lock_end"), time(13)))

    def _sunset(self, now: datetime) -> datetime | None:
        sun = self.hass.states.get("sun.sun")
        if sun is None:
            return None
        ns = sun.attributes.get("next_setting")
        dt = dt_util.parse_datetime(str(ns)) if ns else None
        if dt is None:
            return None
        dt = dt_util.as_local(dt)
        if dt.date() != now.date():
            # nach Sonnenuntergang zeigt next_setting auf morgen
            return dt - timedelta(days=1)
        return dt

    def _can_switch(self, now: datetime) -> bool:
        last = self.state.get("last_switch")
        if last is None:
            return True
        elapsed = now.timestamp() - float(last)
        limit = float(self.p("min_on" if self.is_on() else "min_off")) * 60
        return elapsed >= limit

    # ── Messung ──────────────────────────────────────────────────────────────
    def pre_update(self, ctx: Context) -> None:
        today = ctx.now.date().isoformat()
        if self.state.get("day") != today:
            self.state.update(day=today, runtime=0.0, runtime_vm=0.0)
            self._low_since = None
        if self.is_on():
            minutes = ctx.dt / 60
            self.state["runtime"] = min(self.state["runtime"] + minutes, 1440)
            if ctx.now.time() < self._vm_deadline():
                self.state["runtime_vm"] = min(self.state["runtime_vm"] + minutes, 720)
            if self.state.get("since") is None:
                self.state["since"] = ctx.now.timestamp()
        else:
            self.state["since"] = None

    # ── Entscheidung ─────────────────────────────────────────────────────────
    def decide(self, ctx: Context, budget_left: float) -> Decision:
        now = ctx.now
        on = self.is_on()
        own = self.power_now() if on else 0.0
        need = self.nominal
        left_now = ctx.now_left(budget_left)
        covered_now = left_now >= (own if on else need)
        covered_avg = (budget_left >= (own if on else need)) if ctx.history_ready else covered_now
        ist, vm = self.state["runtime"], self.state["runtime_vm"]
        reserve = own if on else need

        if not self.season_active:
            self.status = "inaktiv"
            return Decision(False, 0, "Saison inaktiv (Winter/zu kalt)")
        if self._locked(now):
            self.status = "sperrzeit"
            return Decision(False, 0, "Sperrzeit")
        if ist >= self.max_min:
            self.status = "max_erreicht"
            return Decision(False, 0, "Max-Laufzeit erreicht")

        # Überschuss-Unterdeckung tracken (laufend)
        if on and left_now - own < 50:
            self._low_since = self._low_since or now
        else:
            self._low_since = None

        before_vm = now.time() < self._vm_deadline()
        pflicht = self._pflicht(now, ist, vm)

        if on:
            self.status = "laeuft"
            if not self._can_switch(now):
                return Decision(True, reserve, "Mindestlaufzeit läuft", forced=pflicht is not None)
            if pflicht:
                return Decision(True, reserve, pflicht, forced=True)
            low_long = self._low_since and now - self._low_since >= timedelta(minutes=LOW_MINUTES)
            if before_vm:
                if vm >= self.target_vm_min and (low_long or not covered_now):
                    return Decision(False, 0, "VM-Ziel erreicht, kein Überschuss")
                if not covered_avg and vm >= self.target_vm_min:
                    return Decision(False, 0, "VM-Ziel erreicht, kein Überschuss")
                return Decision(True, reserve, "PV-Überschuss" if covered_avg else "läuft weiter")
            if ist >= self.target_min:
                if covered_avg:
                    return Decision(True, reserve, f"PV-Bonus ({ist:.0f}/{self.max_min:.0f} min)")
                return Decision(False, 0, "Tagesziel erreicht")
            if low_long:
                return Decision(False, 0, "Überschuss fehlt seit 15 min")
            return Decision(True, reserve, "PV-Überschuss" if covered_avg else "läuft – Pflicht später")

        self.status = "aus"
        if not self._can_switch(now):
            return Decision(False, 0, "Mindestpause läuft")
        if pflicht:
            return Decision(True, need, pflicht, forced=True)
        if covered_now and covered_avg:
            return Decision(True, need, "PV-Überschuss")
        if covered_now:
            return Decision(False, 0, f"Mittelwert zu niedrig ({budget_left:.0f} W)")
        return Decision(False, 0, f"Überschuss zu niedrig ({left_now:.0f} W < {need:.0f} W)")

    def _pflicht(self, now: datetime, ist: float, vm: float) -> str | None:
        minutes = now.hour * 60 + now.minute
        dl = self._vm_deadline()
        if now.time() < dl and vm < self.target_vm_min:
            rest = self.target_vm_min - vm
            if minutes >= dl.hour * 60 + dl.minute - rest:
                return "Pflichtlaufzeit Vormittag"
        if now.time() >= dl and ist < self.target_min:
            sunset = self._sunset(now)
            if sunset:
                end = sunset.hour * 60 + sunset.minute - 30
                if minutes >= end - (self.target_min - ist):
                    return "Pflichtlaufzeit Tag"
        return None

    async def async_apply(self, decision: Decision, ctx: Context) -> None:
        if decision.on != self.is_on():
            await self._switch(self.switch, decision.on)
            self.state["last_switch"] = ctx.now.timestamp()
            self._low_since = None

    async def async_disabled(self, ctx: Context) -> None:
        if self.is_on() and self.p("mode") == "off":
            await self._switch(self.switch, False)
            self.state["last_switch"] = ctx.now.timestamp()

    def plan_demand(self, now: datetime) -> PlanDemand | None:
        rest = self.target_min - self.state["runtime"]
        if rest <= 0:
            return None
        sunset = self._sunset(now) or now.replace(hour=19, minute=0)
        return PlanDemand(self.nominal, self.nominal * rest / 60, sunset - timedelta(minutes=30))
