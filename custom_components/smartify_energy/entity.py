"""Gemeinsame Entity-Basis."""
from __future__ import annotations

from typing import Any, Callable, Iterable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, MANUFACTURER, NAME, SIGNAL_UPDATE, VERSION
from .devices import BaseDevice
from .manager import EnergyManager


class SmartifyEntity(Entity):
    """Entity eines Hubs oder Geräts."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: EnergyManager, owner: EnergyManager | BaseDevice, key: str) -> None:
        self.manager = manager
        self.owner = owner
        self._key = key
        self._attr_translation_key = key
        if isinstance(owner, BaseDevice):
            self._attr_unique_id = f"{manager.entry.entry_id}_{owner.id}_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, owner.id)},
                name=owner.name,
                manufacturer=MANUFACTURER,
                model=f"Energiemanager – {owner.TYPE}",
            )
        else:
            self._attr_unique_id = f"{manager.entry.entry_id}_hub_{key}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, manager.entry.entry_id)},
                name=manager.entry.title,
                manufacturer=MANUFACTURER,
                model=NAME,
                sw_version=VERSION,
                entry_type=DeviceEntryType.SERVICE,
            )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE.format(self.manager.entry.entry_id), self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


def add_entities_per_owner(
    manager: EnergyManager,
    async_add_entities: AddConfigEntryEntitiesCallback,
    build: Callable[[EnergyManager | BaseDevice], Iterable[Any]],
) -> None:
    """Hub-Entities ohne, Geräte-Entities mit Subentry-Zuordnung anlegen."""
    async_add_entities(list(build(manager)))
    for sub_id, dev in manager.devices.items():
        ents = list(build(dev))
        if ents:
            async_add_entities(ents, config_subentry_id=sub_id)
