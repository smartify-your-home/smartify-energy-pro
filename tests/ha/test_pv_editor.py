"""PV surface editor: WebSocket API, saving into options, aerial photo download."""
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

LAT, LON = 47.98, 13.25
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100 + b"\xff\xd9"
RECT = [[LAT, LON], [LAT, LON + 0.000134], [LAT + 0.000054, LON + 0.000134], [LAT + 0.000054, LON]]


async def _setup(hass, options=None):
    hass.config.latitude, hass.config.longitude = LAT, LON
    entry = MockConfigEntry(domain="smartify_energy", data={"grid_sensor": "sensor.grid"},
                            options=options or {})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "smartify_energy", {})
    await hass.async_block_till_done()
    return entry


async def test_legacy_fields_are_shown_as_manual_surfaces(hass, hass_ws_client):
    entry = await _setup(hass, {"solar_mode": "calculated", "solar_1_kwp": 3.04, "solar_1_tilt": 90,
                                "solar_1_azimuth": 190, "solar_3_kwp": 2.66, "solar_3_tilt": 35,
                                "solar_3_azimuth": 265})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "smartify_energy/pv_layout"})
    result = (await client.receive_json())["result"]
    assert result["entry_id"] == entry.entry_id
    assert [(s["kind"], s["kwp"], s["azimuth"]) for s in result["surfaces"]] == [
        ("manual", 3.04, 190), ("manual", 2.66, 265)]
    assert result["map"] is None and result["max_surfaces"] == 4
    assert entry.runtime_data.forecast.solar_config["surfaces"] == [
        {"kwp": 3.04, "tilt": 90.0, "azimuth": 190.0}, {"kwp": 2.66, "tilt": 35.0, "azimuth": 265.0}]


async def test_save_replaces_old_fields_and_reloads_forecast(hass, hass_ws_client):
    entry = await _setup(hass, {"solar_mode": "calculated", "solar_1_kwp": 9, "solar_2_kwp": 1})
    client = await hass_ws_client(hass)
    surfaces = [{"id": "sued", "name": "Süddach", "kind": "area", "points": RECT, "edge": 0,
                 "tilt": 35, "input": "modules", "modules": 8, "module_wp": 380, "azimuth": 1}]
    await client.send_json_auto_id({"type": "smartify_energy/pv_layout/save", "surfaces": surfaces})
    msg = await client.receive_json()
    assert msg["success"], msg
    await hass.async_block_till_done()
    saved = entry.options["solar_surfaces"]
    assert abs(saved[0]["azimuth"] - 180) < 1  # derived from the drawing, client value ignored
    assert entry.options["solar_1_kwp"] == 3.04 and entry.options["solar_2_kwp"] == 0.0
    assert entry.state is ConfigEntryState.LOADED
    model = entry.runtime_data.forecast.solar_config["surfaces"]
    assert len(model) == 1 and model[0]["kwp"] == 3.04 and abs(model[0]["azimuth"] - 180) < 1


async def test_save_rejects_invalid_and_non_admin(hass, hass_ws_client, hass_read_only_access_token):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "smartify_energy/pv_layout/save",
                                    "surfaces": [{"id": "x", "kind": "area", "points": RECT[:2],
                                                  "tilt": 30, "input": "kwp", "kwp": 1}]})
    msg = await client.receive_json()
    assert not msg["success"] and "Fläche 1" in msg["error"]["message"]
    reader = await hass_ws_client(hass, hass_read_only_access_token)
    await reader.send_json_auto_id({"type": "smartify_energy/pv_layout/save", "surfaces": []})
    assert (await reader.receive_json())["error"]["code"] == "unauthorized"
    assert "solar_surfaces" not in entry.options


async def test_map_is_downloaded_once_and_kept_on_failure(hass, hass_ws_client, aioclient_mock):
    entry = await _setup(hass)
    from custom_components.smartify_energy.pv_layout import tile_grid
    for x, y in tile_grid(LAT, LON, 19):
        aioclient_mock.get(f"https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/19/{y}/{x}.jpeg",
                           content=JPEG)
    import asyncio
    from unittest.mock import patch
    from custom_components.smartify_energy import pv_websocket
    active = peak = 0
    real = pv_websocket._download_tile

    async def counting(*args):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        try:
            return await real(*args)
        finally:
            active -= 1

    client = await hass_ws_client(hass)
    with patch.object(pv_websocket, "_download_tile", counting), patch.object(pv_websocket, "TILE_PAUSE", 0):
        await client.send_json_auto_id({"type": "smartify_energy/pv_map/reload"})
        msg = await client.receive_json()
    assert peak <= pv_websocket.TILE_PARALLEL  # no burst of 25 parallel requests
    assert msg["success"], msg
    assert len(msg["result"]["map"]["tiles"]) == 25 and aioclient_mock.call_count == 25
    folder = Path(hass.config.path(".storage", "smartify_energy_map", entry.entry_id))
    assert (folder / "meta.json").is_file()

    # Reading the layout never contacts the tile server.
    await client.send_json_auto_id({"type": "smartify_energy/pv_layout"})
    result = (await client.receive_json())["result"]
    assert len(result["map"]["tiles"]) == 25 and aioclient_mock.call_count == 25

    # Failed reload (outside Austria / offline) keeps the stored photo.
    aioclient_mock._mocks.clear()
    aioclient_mock.get("https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/19/0/0.jpeg",
                       status=404)
    await client.send_json_auto_id({"type": "smartify_energy/pv_map/reload", "lat": 52.5, "lon": 13.4})
    msg = await client.receive_json()
    assert not msg["success"] and "basemap.at" in msg["error"]["message"]
    await client.send_json_auto_id({"type": "smartify_energy/pv_layout"})
    assert (await client.receive_json())["result"]["map"]["lat"] == LAT

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not folder.exists()


async def test_truncated_tile_is_rejected_and_old_photo_kept(hass, hass_ws_client, aioclient_mock):
    """Regression 0.3.64–0.3.66: incomplete tiles were stored and showed as grey patches."""
    from custom_components.smartify_energy.pv_layout import tile_grid
    await _setup(hass)
    for x, y in tile_grid(LAT, LON, 19):
        for host in ("https://mapsneu.wien.gv.at", "https://maps.wien.gv.at"):
            aioclient_mock.get(f"{host}/basemap/bmaporthofoto30cm/normal/google3857/19/{y}/{x}.jpeg",
                               content=JPEG[:60])  # JPEG start but no end marker
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "smartify_energy/pv_map/reload"})
    msg = await client.receive_json()
    assert not msg["success"] and "vollständige" in msg["error"]["message"]
