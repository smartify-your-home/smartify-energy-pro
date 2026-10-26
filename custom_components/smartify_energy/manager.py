"""Kern: Überschuss-Budget, Speicherlogik, Prioritätenmanager, Prognose-Planer."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_interval, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    BAT_SIGN_DISCHARGE_POSITIVE,
    BAT_STRATEGIES,
    BAT_STRATEGY_BATTERY,
    BAT_STRATEGY_DEVICES,
    BAT_STRATEGY_FORECAST,
    CONF_BAT_CAPACITY,
    CONF_BAT_POWER,
    CONF_BAT_SIGN,
    CONF_BAT_SOC,
    CONF_FORECAST_ENTRIES,
    CONF_FORECAST_SENSORS,
    CONF_GRID_EXPORT_SENSOR,
    CONF_GRID_SENSOR,
    CONF_GRID_SIGN,
    CONF_INTERVAL,
    CONF_SINK_SENSORS,
    DOMAIN,
    GRID_SIGN_IMPORT_POSITIVE,
    HUB_MODES,
    MODE_AUTO,
    SIGNAL_UPDATE,
    STORAGE_VERSION,
)
from .budget import additional_reservation, control_budget
from .devices import DEVICE_CLASSES, BaseDevice, Context
from .forecast import ForecastProvider
from .helpers import ParamSpec, SensorSpec, in_window, power_w, state_float, time_from_str

_LOGGER = logging.getLogger(__name__)
SHORT_WINDOW = timedelta(minutes=2)
PLAN_INTERVAL = timedelta(minutes=15)


class EnergyManager:
    """Ein Energiemanager je Config-Entry (Hub)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.cfg: dict[str, Any] = {**entry.data, **entry.options}
        self.has_battery = bool(self.cfg.get(CONF_BAT_SOC) or self.cfg.get(CONF_BAT_POWER))
        self.params: dict[str, Any] = {s.key: s.default for s in self.param_specs()}
        self.devices: dict[str, BaseDevice] = {}
        for sub_id, sub in entry.subentries.items():
            cls = DEVICE_CLASSES.get(sub.subentry_type)
            if cls:
                self.devices[sub_id] = cls(self, sub_id, sub.title, dict(sub.data))
        self.forecast = ForecastProvider(
            hass, self.cfg.get(CONF_FORECAST_ENTRIES) or [], self.cfg.get(CONF_FORECAST_SENSORS) or []
        )
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._history: deque[tuple[datetime, float]] = deque()
        self._grid_history: deque[tuple[datetime, float]] = deque()
        self._lock = asyncio.Lock()
        self._unsubs: list = []
        self._pending_run = None
        self._last_run: datetime | None = None
        self._last_plan: datetime | None = None
        self._plan_dirty = False
        # Messwerte für Sensoren
        self.grid_export = 0.0
        self.grid_avg = 0.0
        self.sinks = 0.0
        self.managed = 0.0  # Only power SEP can actually curtail.
        self._measured_power: dict[str, float] = {}
        self._reclaimable_power: dict[str, float] = {}
        self.battery_power = 0.0
        self.battery_soc: float | None = None
        self.battery_devices_first = True
        self.battery_reason = ""
        self.budget_now = 0.0
        self.budget_avg = 0.0
        self.allocated = 0.0
        self.plan_hours: list[dict] = []
        self.next_action = ""

    # ── Hub-Parameter ────────────────────────────────────────────────────────
    def param_specs(self) -> list[ParamSpec]:
        specs = [
            ParamSpec("mode", "select", MODE_AUTO, "mdi:home-lightning-bolt", options=HUB_MODES, config=False),
            ParamSpec("avg_window", "number", 10, "mdi:chart-bell-curve", 1, 30, 1, "min"),
            ParamSpec("grid_reserve", "number", 0, "mdi:transmission-tower-export", 0, 5000, 50, "W"),
            ParamSpec("base_load", "number", 400, "mdi:home-import-outline", 0, 5000, 50, "W"),
            ParamSpec("night_start", "time", "00:00", "mdi:weather-night"),
            ParamSpec("night_end", "time", "00:00", "mdi:weather-sunset-up"),
        ]
        if self.has_battery:
            specs += [
                ParamSpec("battery_strategy", "select", BAT_STRATEGY_FORECAST, "mdi:home-battery",
                          options=BAT_STRATEGIES, config=False),
                ParamSpec("battery_min_soc", "number", 20, "mdi:battery-low", 0, 100, 5, "%"),
                ParamSpec("battery_target_soc", "number", 100, "mdi:battery-high", 10, 100, 5, "%"),
                ParamSpec("battery_safety", "number", 1.5, "mdi:shield-sun", 1.0, 3.0, 0.1, "×"),
            ]
        return specs

    def p(self, key: str) -> Any:
        return self.params.get(key)

    def set_param(self, key: str, value: Any) -> None:
        if key == "mode" and value != self.params.get(key):
            for dev in self.devices.values():
                if dev.TYPE == "load":
                    dev._hub_released = False
        self.params[key] = value
        if key == "avg_window":
            self._history.clear()
            self._grid_history.clear()
        self.async_param_changed()

    @property
    def hub_mode(self) -> str:
        return self.p("mode")

    def sensor_specs(self) -> list[SensorSpec]:
        specs = [
            SensorSpec("surplus", lambda: round(self.grid_export), unit="W", device_class="power",
                       state_class="measurement", icon="mdi:transmission-tower",
                       attrs=lambda: {
                           "einspeisung_w": round(max(self.grid_export, 0.0)),
                           "netzbezug_w": round(max(-self.grid_export, 0.0)),
                           "vorzeichen": "Einspeisung positiv, Bezug negativ",
                       }),
            SensorSpec("surplus_avg", lambda: round(self.grid_avg), unit="W", device_class="power",
                       state_class="measurement", icon="mdi:chart-bell-curve"),
            SensorSpec("budget", lambda: round(self.budget_now), unit="W", device_class="power",
                       state_class="measurement", icon="mdi:solar-power-variant",
                       attrs=lambda: {
                           "netzsaldo_w": round(self.grid_export),
                           "ruecknehmbar_w": round(self.managed),
                           "senken_nur_information_w": round(self.sinks),
                           "speicher_w": round(self.battery_power),
                           "hinweis": "Nur durch SEP wirklich reduzierbare Lasten werden gutgeschrieben.",
                       }),
            SensorSpec("budget_avg", lambda: round(self.budget_avg), unit="W", device_class="power",
                       state_class="measurement", icon="mdi:chart-bell-curve"),
            SensorSpec("allocated", lambda: round(self.allocated), unit="W", device_class="power",
                       state_class="measurement", icon="mdi:call-split",
                       attrs=self._allocation_attrs),
            SensorSpec("forecast_today", lambda: self._fc_kwh(0), unit="kWh", device_class="energy",
                       icon="mdi:solar-power", attrs=lambda: {
                           "rest_heute_kwh": self._fc_rest(),
                           "morgen_kwh": self._fc_kwh(1),
                           "letzte_aktualisierung": self.forecast.last_update.isoformat()
                           if self.forecast.last_update else None,
                           "fehler": self.forecast.error,
                       }),
            SensorSpec("plan", lambda: self.next_action or "–", icon="mdi:calendar-clock",
                       attrs=lambda: {"stunden": self.plan_hours}),
        ]
        if self.has_battery:
            specs.append(SensorSpec(
                "battery_priority",
                lambda: "geraete" if self.battery_devices_first else "speicher",
                icon="mdi:home-battery-outline",
                attrs=lambda: {"grund": self.battery_reason, "soc": self.battery_soc},
            ))
        return specs

    def _allocation_attrs(self) -> dict:
        out = []
        for dev in self._sorted_devices():
            d = dev.last_decision
            out.append({
                "name": dev.name,
                "prioritaet": dev.priority,
                "modus": dev.mode,
                "ein": bool(d and d.on),
                "reserviert_w": round(d.power) if d and d.on else 0,
                "pflicht": bool(d and d.forced),
                "grund": dev.reason,
            })
        return {"geraete": out}

    def _fc_kwh(self, day_offset: int) -> float | None:
        if not self.forecast.hours:
            return None
        day = (dt_util.now() + timedelta(days=day_offset)).date()
        return round(sum(v for k, v in self.forecast.hours.items() if k.date() == day) / 1000, 2)

    def _fc_rest(self) -> float | None:
        if not self.forecast.hours:
            return None
        now = dt_util.now()
        end = now.replace(hour=23, minute=59, second=59)
        return round(self.forecast.energy_between(now, end) / 1000, 2)

    # ── Lebenszyklus ─────────────────────────────────────────────────────────
    async def async_start(self) -> None:
        data = await self._store.async_load() or {}
        for k, v in (data.get("hub") or {}).items():
            if k in self.params:
                self.params[k] = v
        for sub_id, dev in self.devices.items():
            if sub_id in (data.get("devices") or {}):
                dev.load(data["devices"][sub_id])
        entities = set()
        for cfg in [self.cfg, *(d.cfg for d in self.devices.values())]:
            for value in cfg.values():
                for item in value if isinstance(value, list) else [value]:
                    if isinstance(item, str) and item.split(".")[0] in {
                        "sensor", "binary_sensor", "switch", "input_boolean", "number",
                        "input_number", "select", "input_select", "input_text", "light", "fan",
                    } and "." in item:
                        entities.add(item)
        if entities:
            self._unsubs.append(async_track_state_change_event(self.hass, entities, self._input_changed))
        for dev in self.devices.values():
            if dev.TYPE == "heatpump":
                dev.observe_power(dt_util.now())
        interval = timedelta(seconds=int(self.cfg.get(CONF_INTERVAL, 30)))
        self._unsubs.append(async_track_time_interval(self.hass, self._async_tick, interval))
        self._unsubs.append(async_call_later(self.hass, 10, self._async_first_run))

    @callback
    def _input_changed(self, event) -> None:
        for dev in self.devices.values():
            if dev.TYPE == "heatpump" and event.data.get("entity_id") == dev.cfg.get("power_sensor"):
                dev.observe_power(dt_util.now())
        # Grid / battery metering changes need a shorter control loop than
        # forecast or miscellaneous device state changes.
        entity_id = event.data.get("entity_id")
        fast_inputs = {self.cfg.get(CONF_GRID_SENSOR), self.cfg.get(CONF_GRID_EXPORT_SENSOR),
                       self.cfg.get(CONF_BAT_POWER)}
        for dev in self.devices.values():
            if dev.TYPE == "ev":
                fast_inputs.add(dev.cfg.get("power_sensor"))
                fast_inputs.add(dev.cfg.get("current_entity"))
        self._schedule_run(0.5 if entity_id in fast_inputs else 2.0)

    def _weighted_average(self, now: datetime, window: timedelta, fallback: float,
                          history: deque[tuple[datetime, float]] | None = None) -> float:
        points = list(self._history if history is None else history)
        start = now - window
        total = duration = 0.0
        for (t, value), (end, _) in zip(points, points[1:]):
            seconds = max(0.0, (end - max(t, start)).total_seconds())
            total += value * seconds
            duration += seconds
        return total / duration if duration else fallback

    async def _async_first_run(self, _now=None) -> None:
        await self.forecast.async_refresh()
        await self.async_run()

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._pending_run:
            self._pending_run()
            self._pending_run = None
        await self._store.async_save(self._dump())

    def _dump(self) -> dict:
        return {"hub": self.params, "devices": {sid: d.dump() for sid, d in self.devices.items()}}

    async def async_save_now(self) -> None:
        """Persist a pending one-shot WW trigger before the external command.

        An immediate durable write is necessary: the normal 60 s delayed
        state save could lose the cooldown if Home Assistant restarts.
        """
        await self._store.async_save(self._dump())

    @callback
    def async_param_changed(self) -> None:
        # Changing a device mode/parameter must immediately invalidate the
        # displayed forecast allocation instead of waiting for PLAN_INTERVAL.
        self._plan_dirty = True
        self._store.async_delay_save(self._dump, 5)
        self._schedule_run()

    @callback
    def _schedule_run(self, delay: float = 2.0) -> None:
        if self._pending_run:
            return

        @callback
        def _run(_now) -> None:
            self._pending_run = None
            self.hass.async_create_task(self.async_run())

        self._pending_run = async_call_later(self.hass, delay, _run)

    async def async_request_run(self) -> None:
        self._schedule_run()

    async def _async_tick(self, _now=None) -> None:
        await self.async_run()

    # ── Regelzyklus ──────────────────────────────────────────────────────────
    def _sorted_devices(self, ctx: Context | None = None) -> list[BaseDevice]:
        now = ctx.now if ctx else dt_util.now()

        def key(dev: BaseDevice):
            forced = bool(dev.last_decision and dev.last_decision.forced and dev.last_decision.on)
            since = dev.state.get("since") or now.timestamp()
            return (0 if forced else 1, dev.priority, since)

        return sorted(self.devices.values(), key=key)

    def _read_inputs(self) -> None:
        grid = power_w(self.hass, self.cfg.get(CONF_GRID_SENSOR), 0.0) or 0.0
        if self.cfg.get(CONF_GRID_EXPORT_SENSOR):
            # Getrennte Sensoren: Netzsensor = Bezug, zweiter Sensor = Einspeisung (beide ≥ 0)
            export = power_w(self.hass, self.cfg.get(CONF_GRID_EXPORT_SENSOR), 0.0) or 0.0
            grid = abs(export) - abs(grid)
        elif self.cfg.get(CONF_GRID_SIGN) == GRID_SIGN_IMPORT_POSITIVE:
            grid = -grid
        self.grid_export = grid
        self.sinks = sum(max(power_w(self.hass, s, 0.0) or 0.0, 0.0)
                         for s in self.cfg.get(CONF_SINK_SENSORS) or [])
        bat = power_w(self.hass, self.cfg.get(CONF_BAT_POWER), 0.0) or 0.0
        if self.cfg.get(CONF_BAT_SIGN) == BAT_SIGN_DISCHARGE_POSITIVE:
            bat = -bat
        self.battery_power = bat
        self.battery_soc = state_float(self.hass, self.cfg.get(CONF_BAT_SOC))
        # A normal WW cycle, released household program, forced EV charge or
        # minimum-runtime pool is already part of the measured grid balance.
        # Never add it back as if SEP could stop it to serve another load.
        self._measured_power = {
            key: max(0.0, dev.power_accounted_in_grid())
            for key, dev in self.devices.items()
        }
        self._reclaimable_power = {
            key: min(self._measured_power[key], max(0.0, dev.reclaimable_power()))
            if dev.mode == MODE_AUTO else 0.0
            for key, dev in self.devices.items()
        }
        self.managed = sum(self._reclaimable_power.values())

    def _battery_strategy(self, now: datetime) -> None:
        if not self.has_battery:
            self.battery_devices_first, self.battery_reason = True, "kein Speicher"
            return
        strategy = self.p("battery_strategy")
        soc = self.battery_soc
        if soc is not None and soc < float(self.p("battery_min_soc")):
            self.battery_devices_first, self.battery_reason = False, f"SoC {soc:.0f} % unter Minimum"
            return
        if strategy == BAT_STRATEGY_BATTERY:
            full = soc is not None and soc >= float(self.p("battery_target_soc"))
            self.battery_devices_first = full
            self.battery_reason = "Speicher voll" if full else "Strategie: Speicher zuerst"
            return
        if strategy == BAT_STRATEGY_DEVICES:
            self.battery_devices_first, self.battery_reason = True, "Strategie: Geräte zuerst"
            return
        # Prognose: Geräte zuerst, wenn die Rest-PV des Tages den Speicher sicher noch füllt
        cap = float(self.cfg.get(CONF_BAT_CAPACITY) or 0) * 1000
        if soc is None or cap <= 0 or not self.forecast.hours:
            self.battery_devices_first = soc is not None and soc >= float(self.p("battery_target_soc"))
            self.battery_reason = "keine Prognose/Kapazität – Speicher zuerst"
            return
        need = max(0.0, (float(self.p("battery_target_soc")) - soc) / 100 * cap)
        end = now.replace(hour=21, minute=0, second=0, microsecond=0)
        rest_pv = self.forecast.energy_between(now, end)
        rest_base = float(self.p("base_load")) * max(0.0, (end - now).total_seconds() / 3600)
        free = rest_pv - rest_base
        ok = free >= need * float(self.p("battery_safety"))
        self.battery_devices_first = ok
        self.battery_reason = (
            f"Prognose: frei {free / 1000:.1f} kWh, Speicher braucht {need / 1000:.1f} kWh "
            f"× {float(self.p('battery_safety')):.1f} → {'Geräte' if ok else 'Speicher'} zuerst"
        )

    async def async_run(self) -> None:
        if self._lock.locked():
            return
        async with self._lock:
            try:
                await self._async_run()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Fehler im Regelzyklus")
            async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    async def _async_run(self) -> None:
        now = dt_util.now()
        dt = (now - self._last_run).total_seconds() if self._last_run else 0.0
        dt = min(max(dt, 0.0), 300.0)
        self._last_run = now

        forecast_due = self._last_plan is None or now - self._last_plan >= PLAN_INTERVAL
        plan_due = forecast_due or self._plan_dirty
        if forecast_due:
            if self.forecast.configured:
                await self.forecast.async_refresh()
            self._last_plan = now

        self._read_inputs()
        self._battery_strategy(now)
        bat_discharge = max(-self.battery_power, 0.0)
        # Neither an external surplus diverter nor a battery that SEP cannot
        # command is reliably reclaimable. Keep their measurements for status,
        # but do not offer their power to other devices as fictional PV.
        budget = control_budget(
            self.grid_export, self.managed, bat_discharge,
            float(self.p("grid_reserve"))
        )
        self.budget_now = budget

        window = timedelta(minutes=float(self.p("avg_window")))
        self._history.append((now, budget))
        self._grid_history.append((now, self.grid_export))
        retention = max(window, SHORT_WINDOW)
        for history in (self._history, self._grid_history):
            while len(history) > 1 and now - history[1][0] >= retention:
                history.popleft()
        self.budget_avg = self._weighted_average(now, window, budget)
        self.grid_avg = self._weighted_average(now, window, self.grid_export,
                                               self._grid_history)
        short_avg = self._weighted_average(now, SHORT_WINDOW, budget)
        ready = now - self._history[0][0] >= window * 0.9

        night = in_window(now, time_from_str(self.p("night_start"), time(0)),
                          time_from_str(self.p("night_end"), time(0)))
        ctx = Context(now=now, dt=dt, budget_now=budget, budget_avg=self.budget_avg,
                      budget_short=short_avg, history_ready=ready, night_window=night)
        ctx.alloc_base = self.budget_avg if ready else budget

        for dev in self.devices.values():
            dev.pre_update(ctx)
        ctx.loads_heating = [d.name for d in self.devices.values()
                             if d.TYPE == "load" and d.state.get("hp_active") and d.participates]

        left = ctx.alloc_base
        for dev in self._sorted_devices(ctx):
            current = self._measured_power.get(dev.id, 0.0)
            reclaimed = self._reclaimable_power.get(dev.id, 0.0)
            # A modulating load may use its own already-paid-for minimum
            # power, but must never offer that power to another device.
            own_budget = dev.own_budget_power(current, reclaimed) if dev.mode == MODE_AUTO else 0.0
            try:
                decision = await dev.async_run(ctx, left + own_budget)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("[%s] Fehler", dev.name)
                continue
            # Observe/manual modes do not actually actuate the load.
            if decision.on and dev.mode == MODE_AUTO:
                left -= additional_reservation(decision.power, current, reclaimed)
        self.allocated = ctx.alloc_base - left

        if plan_due:
            self._plan_dirty = False
            self._plan(now)
        self._store.async_delay_save(self._dump, 60)

    # ── Prognose-Planer ──────────────────────────────────────────────────────
    def _plan(self, now: datetime) -> None:
        start = now.replace(minute=0, second=0, microsecond=0)
        # Rest des heutigen Tages und alle 24 Stunden von morgen.
        end = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        hours = []
        hour = start
        while hour < end:
            hours.append(hour)
            hour += timedelta(hours=1)
        base = float(self.p("base_load"))
        rem: dict[datetime, float] = {}
        pv: dict[datetime, float] = {}
        for h in hours:
            frac = 1.0 if h > now else max(0.0, 1 - (now - h).total_seconds() / 3600)
            pv[h] = self.forecast.power_at(h)
            rem[h] = max(0.0, pv[h] - base) * frac
        alloc: dict[datetime, dict[str, float]] = {h: {} for h in hours}

        # Speicher reserviert zuerst, wenn er Vorrang hat
        if self.has_battery and not self.battery_devices_first and self.battery_soc is not None:
            cap = float(self.cfg.get(CONF_BAT_CAPACITY) or 0) * 1000
            need = max(0.0, (float(self.p("battery_target_soc")) - self.battery_soc) / 100 * cap)
            for h in hours:
                if need <= 0:
                    break
                take = min(rem[h], need)
                if take > 0:
                    rem[h] -= take
                    need -= take
                    alloc[h]["Speicher"] = round(take)

        actions: list[tuple[datetime, str]] = []
        for dev in sorted(self.devices.values(), key=lambda d: d.priority):
            demand = dev.plan_demand(now) if dev.mode != "off" else None
            if demand is None or demand.energy <= 0:
                dev.plan = {}
                continue
            deadline = demand.deadline or hours[-1]
            window = [h for h in hours if h + timedelta(hours=1) > now and h < deadline]
            cap_w = max(dev.nominal, demand.power)
            chosen: list[datetime] = []
            pv_wh = 0.0
            if demand.interruptible:
                need = demand.energy
                for h in sorted(window, key=lambda x: (-rem[x], x)):
                    if need <= 0 or rem[h] < demand.power * 0.5:
                        break
                    take = min(rem[h], cap_w, need)
                    rem[h] -= take
                    need -= take
                    pv_wh += take
                    alloc[h][dev.name] = round(take)
                    chosen.append(h)
            else:
                n = max(1, round(demand.energy / max(demand.power, 1)))
                best, best_score = None, -1.0
                for i in range(len(window)):
                    seg = window[i:i + n]
                    if len(seg) < n:
                        break
                    score = sum(min(rem[h], demand.power) for h in seg)
                    if score > best_score + 1:
                        best, best_score = seg, score
                if best:
                    for h in best:
                        take = min(rem[h], demand.power)
                        rem[h] -= take
                        pv_wh += take
                        alloc[h][dev.name] = round(take)
                    chosen = best
            chosen.sort()
            share = round(min(100.0, pv_wh / demand.energy * 100)) if demand.energy else 0
            start_dt = chosen[0] if chosen else None
            if start_dt and start_dt < now:
                start_dt = now
            dev.plan = {
                "start": start_dt,
                "pv_anteil_prozent": share,
                "energie_kwh": round(demand.energy / 1000, 2),
                "faellig": demand.deadline.isoformat() if demand.deadline else None,
                "stunden": [h.strftime("%d.%m. %H:00") for h in chosen],
            }
            if start_dt:
                actions.append((start_dt, f"{dev.name} {start_dt:%H:%M} ({share} % PV)"))

        self.plan_hours = [
            {"zeit": h.isoformat(), "pv_w": round(pv[h]), "frei_w": round(rem[h]), "geraete": alloc[h]}
            for h in hours
        ]
        actions.sort()
        self.next_action = " · ".join(a for _, a in actions[:3])
