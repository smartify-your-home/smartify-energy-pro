"""Binärsensoren."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartifyEntity, add_entities_per_owner
from .helpers import BinarySpec


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifyBinary(manager, owner, s) for s in getattr(owner, "binary_specs", lambda: [])()],
    )


class SmartifyBinary(SmartifyEntity, BinarySensorEntity):
    def __init__(self, manager, owner, spec: BinarySpec) -> None:
        super().__init__(manager, owner, spec.key)
        self.spec = spec
        self._attr_icon = spec.icon
        self._attr_device_class = BinarySensorDeviceClass(spec.device_class) if spec.device_class else None

    @property
    def is_on(self) -> bool:
        return bool(self.spec.value())
