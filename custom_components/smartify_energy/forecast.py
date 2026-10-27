"""PV-Prognose: liest stündliche Werte aus Prognose-Integrationen.

Primärquelle ist die Energie-Plattform der Prognose-Integration
(Forecast.Solar, Open-Meteo Solar Forecast, Solcast …) – dieselbe Quelle,
die auch das Energie-Dashboard nutzt. Mehrere Einträge (z. B. mehrere
Dachflächen) werden summiert. Fallback: Sensor-Attribute (wh_period,
watts, detailedForecast).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


async def async_forecast_entry_options(hass: HomeAssistant) -> list[dict[str, str]]:
    """Alle Config-Entries, deren Integration eine Solar-Prognose liefert."""
    result: list[dict[str, str]] = []
    checked: dict[str, bool] = {}
    for entry in hass.config_entries.async_entries():
        if entry.domain not in checked:
            try:
                integ = await async_get_integration(hass, entry.domain)
                checked[entry.domain] = bool(integ.platforms_exists(["energy"]))
            except Exception:  # noqa: BLE001
                checked[entry.domain] = False
        if checked[entry.domain]:
            sources = [{**entry.data, **entry.options}]
            sources += [dict(sub.data) for sub in getattr(entry, "subentries", {}).values()]
            details = []
            for opts in sources:
                parts = [f"{k[:3]} {opts[k]}" for k in ("declination", "azimuth", "modules_power", "kwp")
                         if opts.get(k) not in (None, "")]
                if parts:
                    details.append(" ".join(parts))
            label = entry.title or entry.domain
            extra = " | ".join(details) if details else entry.entry_id[-6:]
            result.append({"value": entry.entry_id, "label": f"{label} ({entry.domain}; {extra})"})
    return result


async def async_default_forecast_entries(hass: HomeAssistant) -> list[str]:
    """Im Energie-Dashboard hinterlegte Prognose-Einträge."""
    try:
        from homeassistant.components.energy.data import async_get_manager

        manager = await async_get_manager(hass)
        ids: list[str] = []
        for src in (manager.data or {}).get("energy_sources", []):
            if src.get("type") == "solar":
                ids.extend(src.get("config_entry_solar_forecast") or [])
        return list(dict.fromkeys(ids))
    except Exception:  # noqa: BLE001
        return []


class ForecastProvider:
    """Liefert {Stundenbeginn (lokal): Wh} für heute und morgen."""

    def __init__(self, hass: HomeAssistant, entry_ids: list[str], sensors: list[str]) -> None:
        self.hass = hass
        self.entry_ids = entry_ids or []
        self.sensors = sensors or []
        self.hours: dict[datetime, float] = {}
        self.last_update: datetime | None = None
        self.error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.entry_ids or self.sensors)

    async def async_refresh(self) -> None:
        hours: dict[datetime, float] = {}
        errors: list[str] = []
        for entry_id in self.entry_ids:
            try:
                data = await self._from_energy_platform(entry_id)
                _merge(hours, data)
            except Exception as err:  # noqa: BLE001
                errors.append(f"{entry_id}: {err}")
        for entity_id in self.sensors:
            try:
                _merge(hours, self._from_sensor(entity_id))
            except Exception as err:  # noqa: BLE001
                errors.append(f"{entity_id}: {err}")
        self.hours = hours
        self.error = "; ".join(errors) or None
        if errors:
            _LOGGER.debug("Prognose-Fehler: %s", self.error)
        self.last_update = dt_util.now()

    async def _from_energy_platform(self, entry_id: str) -> dict[datetime, float]:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            raise ValueError("Eintrag nicht gefunden")
        integ = await async_get_integration(self.hass, entry.domain)
        platform = await integ.async_get_platform("energy")
        data = await platform.async_get_solar_forecast(self.hass, entry_id)
        if not data:
            return {}
        out: dict[datetime, float] = {}
        for ts, wh in (data.get("wh_hours") or {}).items():
            dt = _parse(ts)
            if dt is not None:
                out[_hour(dt)] = out.get(_hour(dt), 0.0) + float(wh or 0)
        return out

    def _from_sensor(self, entity_id: str) -> dict[datetime, float]:
        st = self.hass.states.get(entity_id)
        if st is None:
            return {}
        attrs = st.attributes
        out: dict[datetime, float] = {}
        if isinstance(attrs.get("wh_period"), dict):
            for ts, wh in attrs["wh_period"].items():
                dt = _parse(ts)
                if dt:
                    out[_hour(dt)] = out.get(_hour(dt), 0.0) + float(wh or 0)
        elif isinstance(attrs.get("detailedForecast"), list):  # Solcast (kW je 30 min)
            for item in attrs["detailedForecast"]:
                dt = _parse(item.get("period_start"))
                if dt:
                    out[_hour(dt)] = out.get(_hour(dt), 0.0) + float(item.get("pv_estimate", 0)) * 500
        elif isinstance(attrs.get("watts"), dict):  # Momentanleistung je Zeitstempel
            pts = sorted((d, float(w)) for t, w in attrs["watts"].items() if (d := _parse(t)))
            for (d1, w1), (d2, _w2) in zip(pts, pts[1:], strict=False):
                hours = (d2 - d1).total_seconds() / 3600
                out[_hour(d1)] = out.get(_hour(d1), 0.0) + w1 * hours
        return out

    # ── Auswertung ───────────────────────────────────────────────────────────
    def power_at(self, when: datetime) -> float:
        """Mittlere Prognoseleistung (W) in der Stunde von `when`."""
        return self.hours.get(_hour(dt_util.as_local(when)), 0.0)

    def energy_between(self, start: datetime, end: datetime) -> float:
        """Prognose-Energie (Wh) zwischen start und end, anteilig je Stunde."""
        if end <= start:
            return 0.0
        total = 0.0
        cursor = start
        while cursor < end:
            h = _hour(dt_util.as_local(cursor))
            nxt = min(h + timedelta(hours=1), end)
            total += self.hours.get(h, 0.0) * (nxt - cursor).total_seconds() / 3600
            cursor = nxt
        return total


def _merge(target: dict[datetime, float], src: dict[datetime, float]) -> None:
    for k, v in src.items():
        target[k] = target.get(k, 0.0) + v


def _hour(dt: datetime) -> datetime:
    return dt_util.as_local(dt).replace(minute=0, second=0, microsecond=0)


def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return dt_util.as_local(value)
    if value is None:
        return None
    dt = dt_util.parse_datetime(str(value))
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_local(dt)
