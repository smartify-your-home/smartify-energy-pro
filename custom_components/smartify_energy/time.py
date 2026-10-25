"""Uhrzeit-Parameter."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import add_entities_per_owner
from .helpers import time_from_str, time_to_str
from .params import ParamEntity, param_specs


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifyTime(manager, owner, s) for s in param_specs(owner, "time")],
    )


class SmartifyTime(ParamEntity, TimeEntity):
    @property
    def native_value(self) -> time:
        return time_from_str(self.value, time_from_str(self.spec.default, time(0)))

    async def async_set_value(self, value: time) -> None:
        self.set_value(time_to_str(value))
