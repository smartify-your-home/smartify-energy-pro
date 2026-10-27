"""Hilfsfunktionen und Entity-Spezifikationen."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from homeassistant.core import HomeAssistant

UNAVAILABLE = ("unknown", "unavailable", "", None)


def state_float(hass: HomeAssistant, entity_id: str | None, default: float | None = None) -> float | None:
    """Liest einen numerischen Zustand."""
    if not entity_id:
        return default
    st = hass.states.get(entity_id)
    if st is None or st.state in UNAVAILABLE:
        return default
    try:
        return float(st.state)
    except (TypeError, ValueError):
        return default


def power_w(hass: HomeAssistant, entity_id: str | None, default: float | None = None) -> float | None:
    """Liest eine Leistung und rechnet kW/MW in W um."""
    val = state_float(hass, entity_id, None)
    if val is None:
        return default
    unit = (hass.states.get(entity_id).attributes.get("unit_of_measurement") or "W").strip()
    if unit == "kW":
        return val * 1000.0
    if unit == "MW":
        return val * 1_000_000.0
    return val


def is_on(hass: HomeAssistant, entity_id: str | None) -> bool:
    if not entity_id:
        return False
    st = hass.states.get(entity_id)
    return bool(st and st.state == "on")


def state_str(hass: HomeAssistant, entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    st = hass.states.get(entity_id)
    if st is None or st.state in UNAVAILABLE:
        return None
    return st.state


def time_from_str(value: Any, default: time) -> time:
    if isinstance(value, time):
        return value
    try:
        parts = [int(p) for p in str(value).split(":")[:2]]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return default


def time_to_str(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def in_window(now: datetime, start: time, end: time) -> bool:
    """Liegt now im Zeitfenster (auch über Mitternacht)."""
    t = now.time()
    if start == end:
        return False
    if start < end:
        return start <= t < end
    return t >= start or t < end


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ── Spezifikationen für dynamisch erzeugte Entities ──────────────────────────
@dataclass
class ParamSpec:
    """Einstellbarer Parameter (number/select/switch/time)."""

    key: str
    platform: str
    default: Any
    icon: str | None = None
    min: float = 0
    max: float = 100
    step: float = 1
    unit: str | None = None
    options: list[str] = field(default_factory=list)
    config: bool = True  # EntityCategory.CONFIG


@dataclass
class SensorSpec:
    key: str
    value: Callable[[], Any]
    attrs: Callable[[], dict] | None = None
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    icon: str | None = None
    diagnostic: bool = False


@dataclass
class BinarySpec:
    key: str
    value: Callable[[], bool]
    icon: str | None = None
    device_class: str | None = None


@dataclass
class ButtonSpec:
    key: str
    press: Callable[[], Any]
    icon: str | None = None
