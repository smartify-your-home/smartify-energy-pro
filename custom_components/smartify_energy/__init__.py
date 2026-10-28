"""smartify Energiemanager – PV-Überschuss mit Prioritäten, Prognose und Speicherlogik."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN, PLATFORMS
from .manager import EnergyManager

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SERVICE_PRIORITY_ORDER = "set_priority_order"
CARD_FILE = "smartify-energy-plan-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"
LOGO_URL = f"/{DOMAIN}/sep-logo.png"

type SmartifyEnergyConfigEntry = ConfigEntry[EnergyManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Dashboard-Card bereitstellen und Prioritäten-Dienst registrieren."""
    async def set_priority_order(call: ServiceCall) -> None:
        device_ids = call.data["device_ids"]
        registry = dr.async_get(hass)
        if len(set(device_ids)) != len(device_ids):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="duplicate_device")
        # The battery is a virtual, drag-sortable item (no HA device).
        # Its rank is persisted in the hub; all other IDs remain HA devices.
        battery_token = "__battery__"
        has_battery_item = battery_token in device_ids
        devices = [registry.async_get(device_id) if device_id != battery_token else None
                   for device_id in device_ids]
        if any(device is None for token, device in zip(device_ids, devices, strict=True)
               if token != battery_token):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unknown_device")
        for entry in hass.config_entries.async_entries(DOMAIN):
            manager = getattr(entry, "runtime_data", None)
            if manager is None:
                continue
            by_identifier = {(DOMAIN, sub_id): dev for sub_id, dev in manager.devices.items()}
            matches = [
                next((by_identifier[key] for key in device.identifiers if key in by_identifier), None)
                if device is not None else None
                for device in devices
            ]
            non_battery = [dev for dev in matches if dev is not None]
            if not non_battery and not (has_battery_item and manager.has_battery
                                        and len(manager.devices) == 0):
                continue
            if (len(non_battery) != len(by_identifier)
                    or len(set(dev.id for dev in non_battery)) != len(by_identifier)
                    or (has_battery_item != manager.has_battery)):
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="incomplete_order")
            for rank, (token, dev) in enumerate(zip(device_ids, matches, strict=True), start=1):
                if token == battery_token:
                    manager.set_param("battery_rank", rank)
                else:
                    dev.set_param("priority", rank)
            return
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="order_not_found")

    if not hass.services.has_service(DOMAIN, SERVICE_PRIORITY_ORDER):
        hass.services.async_register(
            DOMAIN, SERVICE_PRIORITY_ORDER, set_priority_order,
            schema=vol.Schema({
                vol.Required("device_ids"): vol.All([cv.string], vol.Length(min=1, max=100)),
            }),
        )
    if getattr(hass, "http", None) is None or "frontend" not in hass.config.components:
        return True
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        path = Path(__file__).parent / "www" / CARD_FILE
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_URL, str(path), False),
            StaticPathConfig(LOGO_URL, str(path.parent / "sep-logo.png"), False),
        ])
        add_extra_js_url(hass, f"{CARD_URL}?v={(await async_get_integration(hass, DOMAIN)).version}")
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Dashboard-Card konnte nicht registriert werden", exc_info=True)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SmartifyEnergyConfigEntry) -> bool:
    manager = EnergyManager(hass, entry)
    manager.integration_version = str((await async_get_integration(hass, DOMAIN)).version)
    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _link_devices(hass, entry)
    await manager.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartifyEnergyConfigEntry) -> bool:
    await entry.runtime_data.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SmartifyEnergyConfigEntry) -> None:
    """Optionen oder Geräte geändert → neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)


def _link_devices(hass: HomeAssistant, entry: SmartifyEnergyConfigEntry) -> None:
    """Geräte dem Hub-Gerät unterordnen (via_device_id statt veraltetem via_device)."""
    reg = dr.async_get(hass)
    hub = reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    if hub is None:
        return
    for sub_id in entry.subentries:
        dev = reg.async_get_device(identifiers={(DOMAIN, sub_id)})
        if dev and dev.via_device_id != hub.id:
            reg.async_update_device(dev.id, via_device_id=hub.id)
