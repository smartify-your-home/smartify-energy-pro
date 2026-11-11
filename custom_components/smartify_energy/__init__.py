"""smartify Energiemanager – PV-Überschuss mit Prioritäten, Prognose und Speicherlogik."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, ServiceCall, callback
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
            # Apply the whole permutation atomically, not one delayed
            # manager run per participant. Update entities in one immediate cycle.
            for rank, (token, dev) in enumerate(zip(device_ids, matches, strict=True), start=1):
                if token == battery_token:
                    manager.params["battery_rank"] = rank
                else:
                    dev.params["priority"] = rank
            manager._plan_dirty = True
            manager._store.async_delay_save(manager._dump, 5)
            await manager.async_request_run(immediate=True)
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
        from homeassistant.components.http import StaticPathConfig

        path = Path(__file__).parent / "www" / CARD_FILE
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_URL, str(path), False),
            StaticPathConfig(LOGO_URL, str(path.parent / "sep-logo.png"), False),
        ])
        version = (await async_get_integration(hass, DOMAIN)).version
        card_hash = await hass.async_add_executor_job(_file_hash, path)
        card_url = f"{CARD_URL}?v={version}-{card_hash}"
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Dashboard-Card konnte nicht registriert werden", exc_info=True)
        return True

    # The card is loaded ONLY as a Lovelace resource. Do not add it via
    # add_extra_js_url as well: extra JS sits in the <head> of index.html and
    # races with the frontend's scoped-custom-element-registry polyfill. If the
    # card defines its elements first, the polyfilled registry never learns
    # about them (customElements.get() is empty, whenDefined() never resolves)
    # and the dashboard permanently shows "Konfigurationsfehler / Custom element
    # doesn't exist" until the page is reloaded. Lovelace resources are loaded
    # by the frontend itself, i.e. always after the polyfill. Extra JS remains
    # only a last-resort fallback for Lovelace YAML mode (see retry function).
    # All of this runs in the event loop: listeners are @callback, retries use
    # asyncio.sleep inside one background task (no executor threads).
    if hass.state is CoreState.running:
        _start_resource_registration(hass, card_url)
    else:
        @callback
        def _on_started(_event) -> None:
            _start_resource_registration(hass, card_url)

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
    return True


RESOURCE_ATTEMPTS = 6


@callback
def _start_resource_registration(hass: HomeAssistant, card_url: str) -> None:
    hass.async_create_background_task(
        _async_register_resource_with_retry(hass, card_url), f"{DOMAIN}_card_resource")


async def _async_register_resource_with_retry(hass: HomeAssistant, card_url: str,
                                              delay: float = 2.0) -> bool:
    """Lovelace can finish later than SEP; retry a few times, then give up."""
    for attempt in range(1, RESOURCE_ATTEMPTS + 1):
        try:
            if await _async_ensure_lovelace_resource(hass, card_url):
                return True
            _LOGGER.debug("SEP-Card-Ressource noch nicht verfügbar (%s/%s)", attempt, RESOURCE_ATTEMPTS)
        except Exception:  # noqa: BLE001
            _LOGGER.warning("SEP-Card-Ressource: Registrierung fehlgeschlagen (%s/%s)",
                            attempt, RESOURCE_ATTEMPTS, exc_info=True)
        if attempt < RESOURCE_ATTEMPTS:
            await asyncio.sleep(delay * attempt)
    _async_extra_js_fallback(hass, card_url)
    return False


@callback
def _async_extra_js_fallback(hass: HomeAssistant, card_url: str) -> None:
    """No storage-mode resources (Lovelace YAML mode): fall back to extra JS.

    Less robust than a resource (see async_setup); the reliable way in YAML mode
    is a manual `lovelace: resources:` entry, which the log message points out.
    """
    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, card_url)
    except Exception:  # noqa: BLE001
        _LOGGER.error("SEP-Card-Ressource nach %s Versuchen nicht registriert: %s",
                      RESOURCE_ATTEMPTS, card_url, exc_info=True)
        return
    _LOGGER.warning(
        "SEP-Card konnte nicht als Lovelace-Ressource registriert werden (YAML-Modus?). "
        "Sie wird ersatzweise über das Frontend eingebunden; für zuverlässiges Laden bitte "
        "manuell als Ressource eintragen: %s (type: module)", card_url)


async def _async_ensure_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Create or update the SEP card resource in storage-mode Lovelace."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        data = hass.data.get(LOVELACE_DATA)
    except ImportError:  # pragma: no cover - very old HA
        data = None
    resources = getattr(data, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        return False  # Lovelace may still be starting; retry from caller.
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    base = CARD_URL
    ours = [item for item in resources.async_items()
            if str(item.get("url", "")).split("?")[0] == base]
    if not ours:
        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info("Lovelace-Ressource für SEP-Card angelegt: %s", url)
        return True
    first, *duplicates = ours
    if first.get("url") != url or first.get("type") != "module":
        await resources.async_update_item(first["id"], {"res_type": "module", "url": url})
    for item in duplicates:
        await resources.async_delete_item(item["id"])
    return True


def _file_hash(path: Path) -> str:
    """Kurzer Inhalts-Hash als Cache-Buster: neue Card-Datei → neue URL, auch ohne Versionssprung."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


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
