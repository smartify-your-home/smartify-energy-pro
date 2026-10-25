"""Schalter für Ja/Nein-Parameter."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import add_entities_per_owner
from .params import ParamEntity, param_specs


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifySwitch(manager, owner, s) for s in param_specs(owner, "switch")],
    )


class SmartifySwitch(ParamEntity, SwitchEntity):
    @property
    def is_on(self) -> bool:
        return bool(self.value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.set_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.set_value(False)
