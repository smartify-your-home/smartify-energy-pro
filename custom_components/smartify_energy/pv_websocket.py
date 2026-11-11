"""WebSocket API for the PV surface editor card.

* ``smartify_energy/pv_layout``      – read surfaces and the stored aerial photo
* ``smartify_energy/pv_layout/save`` – save surfaces (admin), reloads the entry
* ``smartify_energy/pv_map/reload``  – download the aerial photo once (admin)

The aerial photo (basemap.at orthophoto tiles) is downloaded only on explicit
request and stored below ``.storage``; reading the layout never contacts the
tile server.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import shutil
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .pv_layout import (
    CONF_SOLAR_SURFACES,
    MAP_ATTRIBUTION,
    MAP_GRID,
    MAP_TILE_URLS,
    MAP_ZOOM_DEFAULT,
    MAP_ZOOM_MAX,
    MAP_ZOOM_MIN,
    MAX_SURFACES,
    effective_kwp,
    legacy_mirror,
    normalize_surfaces,
    surfaces_from_config,
    tile_grid,
)

_LOGGER = logging.getLogger(__name__)
MAX_TILE_BYTES = 600_000
TILE_TIMEOUT = 15
# Be polite to the public tile server: a few requests at a time, short pause.
TILE_PARALLEL = 4
TILE_PAUSE = 0.05


def _map_dir(hass: HomeAssistant, entry_id: str) -> Path:
    return Path(hass.config.path(".storage", f"{DOMAIN}_map", entry_id))


def _read_map(folder: Path) -> dict[str, Any] | None:
    meta_file = folder / "meta.json"
    if not meta_file.is_file():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        tiles = []
        for tile in meta["tiles"]:
            data = (folder / f"{int(tile['x'])}_{int(tile['y'])}.jpg").read_bytes()
            tiles.append({"x": int(tile["x"]), "y": int(tile["y"]),
                          "data": base64.b64encode(data).decode("ascii")})
    except (OSError, ValueError, KeyError, TypeError):
        _LOGGER.warning("Gespeichertes Luftbild ist unvollständig: %s", folder)
        return None
    return {**{k: meta[k] for k in ("lat", "lon", "zoom", "fetched", "attribution")}, "tiles": tiles}


def _write_map(folder: Path, meta: dict[str, Any], images: dict[tuple[int, int], bytes]) -> None:
    """Write into a temporary folder first so a failed download keeps the old photo."""
    tmp = folder.with_name(folder.name + ".new")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for (x, y), data in images.items():
        (tmp / f"{x}_{y}.jpg").write_bytes(data)
    (tmp / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    shutil.rmtree(folder, ignore_errors=True)
    tmp.rename(folder)


async def _download_tile(session, zoom: int, x: int, y: int) -> bytes:
    last_error = "keine Antwort"
    for template in MAP_TILE_URLS:
        url = template.format(z=zoom, x=x, y=y)
        try:
            async with asyncio.timeout(TILE_TIMEOUT):
                async with session.get(url, headers={"User-Agent": "smartify-energy-pro (Home Assistant)"}) as resp:
                    if resp.status != 200:
                        last_error = f"HTTP {resp.status}"
                        continue
                    length = resp.headers.get("Content-Length")
                    if length and length.isdigit() and int(length) > MAX_TILE_BYTES:
                        last_error = "Kachel zu groß"
                        continue
                    # resp.read() reads the WHOLE body. content.read(n) returns only what is
                    # buffered and truncated tiles in 0.3.64–0.3.66 (grey patches in the photo).
                    data = await resp.read()
        except (TimeoutError, OSError) as err:
            last_error = type(err).__name__
            continue
        except Exception as err:  # noqa: BLE001 - aiohttp client errors
            last_error = type(err).__name__
            continue
        if (len(data) > MAX_TILE_BYTES or not data.startswith(b"\xff\xd8")
                or not data.rstrip(b"\x00").endswith(b"\xff\xd9")):
            last_error = "keine vollständige Bilddatei"
            continue
        return data
    raise ValueError(last_error)


def _entry(hass: HomeAssistant, entry_id: str | None):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if getattr(entry, "runtime_data", None) is None:
            continue
        if entry_id in (None, "", entry.entry_id):
            return entry
    return None


def _layout_payload(hass: HomeAssistant, entry) -> dict[str, Any]:
    cfg = {**entry.data, **entry.options}
    surfaces = surfaces_from_config(cfg)
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "solar_mode": cfg.get("solar_mode", "external"),
        "surfaces": surfaces,
        "total_kwp": round(sum(effective_kwp(s) for s in surfaces), 3),
        "max_surfaces": MAX_SURFACES,
        "home": {"lat": hass.config.latitude, "lon": hass.config.longitude},
        "zoom": {"default": MAP_ZOOM_DEFAULT, "min": MAP_ZOOM_MIN, "max": MAP_ZOOM_MAX},
        "attribution": MAP_ATTRIBUTION,
    }


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/pv_layout",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_get_layout(hass: HomeAssistant, connection, msg: dict) -> None:
    entry = _entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Kein geladener smartify Energiemanager gefunden")
        return
    payload = _layout_payload(hass, entry)
    payload["map"] = await hass.async_add_executor_job(_read_map, _map_dir(hass, entry.entry_id))
    connection.send_result(msg["id"], payload)


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/pv_layout/save",
    vol.Optional("entry_id"): str,
    vol.Required("surfaces"): list,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save_layout(hass: HomeAssistant, connection, msg: dict) -> None:
    entry = _entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Kein geladener smartify Energiemanager gefunden")
        return
    try:
        surfaces = normalize_surfaces(msg["surfaces"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    options = {**entry.options, CONF_SOLAR_SURFACES: surfaces, **legacy_mirror(surfaces)}
    # The options update listener reloads the entry → new forecast geometry.
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], {"surfaces": surfaces,
                                       "total_kwp": round(sum(effective_kwp(s) for s in surfaces), 3)})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/pv_map/reload",
    vol.Optional("entry_id"): str,
    vol.Optional("lat"): vol.All(vol.Coerce(float), vol.Range(min=-85, max=85)),
    vol.Optional("lon"): vol.All(vol.Coerce(float), vol.Range(min=-180, max=180)),
    vol.Optional("zoom"): vol.All(vol.Coerce(int), vol.Range(min=MAP_ZOOM_MIN, max=MAP_ZOOM_MAX)),
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_reload_map(hass: HomeAssistant, connection, msg: dict) -> None:
    entry = _entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Kein geladener smartify Energiemanager gefunden")
        return
    lat = msg.get("lat", hass.config.latitude)
    lon = msg.get("lon", hass.config.longitude)
    zoom = msg.get("zoom", MAP_ZOOM_DEFAULT)
    session = async_get_clientsession(hass)
    grid = tile_grid(lat, lon, zoom, MAP_GRID)
    limit = asyncio.Semaphore(TILE_PARALLEL)

    async def _limited(x: int, y: int) -> bytes:
        async with limit:
            data = await _download_tile(session, zoom, x, y)
            await asyncio.sleep(TILE_PAUSE)
            return data

    results = await asyncio.gather(*(_limited(x, y) for x, y in grid), return_exceptions=True)
    failed = [r for r in results if isinstance(r, Exception)]
    if failed:
        _LOGGER.warning("Luftbild: %s von %s Kacheln nicht geladen (%s)", len(failed), len(grid), failed[0])
        connection.send_error(
            msg["id"], "home_assistant_error",
            f"Luftbild konnte nicht geladen werden ({failed[0]}). basemap.at deckt nur Österreich ab; "
            "das bisher gespeicherte Luftbild bleibt erhalten.")
        return
    meta = {"lat": lat, "lon": lon, "zoom": zoom, "fetched": dt_util.utcnow().isoformat(),
            "attribution": MAP_ATTRIBUTION, "tiles": [{"x": x, "y": y} for x, y in grid]}
    folder = _map_dir(hass, entry.entry_id)
    await hass.async_add_executor_job(_write_map, folder, meta, dict(zip(grid, results, strict=True)))
    connection.send_result(msg["id"], {"map": await hass.async_add_executor_job(_read_map, folder)})


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register once per Home Assistant instance."""
    key = f"{DOMAIN}_pv_ws_registered"
    if hass.data.get(key):
        return
    hass.data[key] = True
    websocket_api.async_register_command(hass, ws_get_layout)
    websocket_api.async_register_command(hass, ws_save_layout)
    websocket_api.async_register_command(hass, ws_reload_map)


def remove_map(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the stored aerial photo when the entry is removed (executor)."""
    shutil.rmtree(_map_dir(hass, entry_id), ignore_errors=True)
