"""Sensoren."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartifyEntity, add_entities_per_owner
from .helpers import SensorSpec


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifySensor(manager, owner, s) for s in owner.sensor_specs()],
    )


class SmartifySensor(SmartifyEntity, SensorEntity):
    def __init__(self, manager, owner, spec: SensorSpec) -> None:
        super().__init__(manager, owner, spec.key)
        self.spec = spec
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = SensorDeviceClass(spec.device_class) if spec.device_class else None
        self._attr_state_class = SensorStateClass(spec.state_class) if spec.state_class else None
        self._attr_icon = spec.icon
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self.spec.value()

    @property
    def extra_state_attributes(self) -> dict | None:
        return self.spec.attrs() if self.spec.attrs else None
