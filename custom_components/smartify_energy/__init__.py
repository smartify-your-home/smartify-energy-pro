"""smartify Energiemanager – PV-Überschuss mit Prioritäten, Prognose und Speicherlogik."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS, VERSION
from .manager import EnergyManager

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_FILE = "smartify-energy-plan-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"

type SmartifyEnergyConfigEntry = ConfigEntry[EnergyManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Dashboard-Card automatisch bereitstellen (keine Ressource nötig)."""
    if getattr(hass, "http", None) is None or "frontend" not in hass.config.components:
        return True
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        path = Path(__file__).parent / "www" / CARD_FILE
        await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(path), False)])
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Dashboard-Card konnte nicht registriert werden", exc_info=True)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SmartifyEnergyConfigEntry) -> bool:
    manager = EnergyManager(hass, entry)
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
