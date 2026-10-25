"""Tasten."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartifyEntity, add_entities_per_owner
from .helpers import ButtonSpec


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifyButton(manager, owner, s) for s in getattr(owner, "button_specs", lambda: [])()],
    )


class SmartifyButton(SmartifyEntity, ButtonEntity):
    def __init__(self, manager, owner, spec: ButtonSpec) -> None:
        super().__init__(manager, owner, spec.key)
        self.spec = spec
        self._attr_icon = spec.icon

    async def async_press(self) -> None:
        await self.spec.press()
        self.async_write_ha_state()
