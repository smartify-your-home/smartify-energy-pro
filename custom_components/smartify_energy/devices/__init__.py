"""Gerätetypen."""
from __future__ import annotations

from ..const import TYPE_DRYER, TYPE_EV, TYPE_HEATER, TYPE_HEATPUMP, TYPE_LOAD, TYPE_POOL
from .base import BaseDevice, Context, Decision, PlanDemand
from .dryer import DryerDevice
from .ev import EvDevice
from .heater import HeaterDevice
from .heatpump import HeatPumpDevice
from .load import LoadDevice
from .pool import PoolDevice

DEVICE_CLASSES: dict[str, type[BaseDevice]] = {
    TYPE_LOAD: LoadDevice,
    TYPE_DRYER: DryerDevice,
    TYPE_POOL: PoolDevice,
    TYPE_EV: EvDevice,
    TYPE_HEATPUMP: HeatPumpDevice,
    TYPE_HEATER: HeaterDevice,
}

__all__ = ["DEVICE_CLASSES", "BaseDevice", "Context", "Decision", "PlanDemand"]
