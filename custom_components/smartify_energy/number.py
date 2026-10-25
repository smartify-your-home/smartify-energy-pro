"""Einstellwerte."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import add_entities_per_owner
from .params import ParamEntity, param_specs


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifyNumber(manager, owner, s) for s in param_specs(owner, "number")],
    )


class SmartifyNumber(ParamEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, manager, owner, spec) -> None:
        super().__init__(manager, owner, spec)
        self._attr_native_min_value = spec.min
        self._attr_native_max_value = spec.max
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit

    @property
    def native_value(self) -> float | None:
        val = self.value
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        self.set_value(value)
