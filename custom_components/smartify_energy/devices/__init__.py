"""Gerätetypen."""
from __future__ import annotations

from ..const import TYPE_EV, TYPE_HEATPUMP, TYPE_HEATER, TYPE_LOAD, TYPE_POOL
from .base import BaseDevice, Context, Decision, PlanDemand
from .ev import EvDevice
from .heatpump import HeatPumpDevice
from .heater import HeaterDevice
from .load import LoadDevice
from .pool import PoolDevice

DEVICE_CLASSES: dict[str, type[BaseDevice]] = {
    TYPE_LOAD: LoadDevice,
    TYPE_POOL: PoolDevice,
    TYPE_EV: EvDevice,
    TYPE_HEATPUMP: HeatPumpDevice,
    TYPE_HEATER: HeaterDevice,
}

__all__ = ["DEVICE_CLASSES", "BaseDevice", "Context", "Decision", "PlanDemand"]
