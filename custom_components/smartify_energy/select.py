"""Auswahlen (Modus, Strategie, Ziel …)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import add_entities_per_owner
from .params import ParamEntity, param_specs


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    manager = entry.runtime_data
    add_entities_per_owner(
        manager, async_add_entities,
        lambda owner: [SmartifySelect(manager, owner, s) for s in param_specs(owner, "select")],
    )


class SmartifySelect(ParamEntity, SelectEntity):
    def __init__(self, manager, owner, spec) -> None:
        super().__init__(manager, owner, spec)
        self._attr_options = list(spec.options)

    @property
    def current_option(self) -> str | None:
        val = self.value
        return val if val in self._attr_options else self.spec.default

    async def async_select_option(self, option: str) -> None:
        self.set_value(option)
