"""SEP-Card wird zusätzlich als Lovelace-Ressource registriert."""
from homeassistant.setup import async_setup_component

from custom_components.smartify_energy import CARD_URL, _async_ensure_lovelace_resource


async def _resources(hass):
    assert await async_setup_component(hass, "lovelace", {})
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    res = hass.data[LOVELACE_DATA].resources
    await res.async_get_info()
    return res


def _ours(res):
    return [i for i in res.async_items() if i["url"].split("?")[0] == CARD_URL]


async def test_creates_resource_once(hass):
    res = await _resources(hass)
    url = f"{CARD_URL}?v=1.0.0-abc"
    await _async_ensure_lovelace_resource(hass, url)
    await _async_ensure_lovelace_resource(hass, url)
    assert [(i["url"], i["type"]) for i in _ours(res)] == [(url, "module")]


async def test_updates_url_and_removes_duplicates(hass):
    res = await _resources(hass)
    await res.async_create_item({"res_type": "js", "url": f"{CARD_URL}?v=old"})
    await res.async_create_item({"res_type": "module", "url": CARD_URL})
    await res.async_create_item({"res_type": "module", "url": "/local/other.js"})
    url = f"{CARD_URL}?v=2.0.0-def"
    await _async_ensure_lovelace_resource(hass, url)
    assert [(i["url"], i["type"]) for i in _ours(res)] == [(url, "module")]
    assert any(i["url"] == "/local/other.js" for i in res.async_items())


async def test_without_lovelace_is_noop(hass):
    await _async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=x")

async def test_unavailable_lovelace_returns_false_for_retry(hass):
    assert await _async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=retry") is False
    await _resources(hass)
    assert await _async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=retry") is True


async def test_started_event_updates_stale_resource_in_event_loop(hass):
    """Regression 0.3.39–0.3.43: listener ran in a worker thread and crashed."""
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
    from homeassistant.core import CoreState
    from custom_components.smartify_energy import _start_resource_registration

    res = await _resources(hass)
    await res.async_create_item({"res_type": "module", "url": f"{CARD_URL}?v=0.3.38-old"})
    hass.set_state(CoreState.starting)
    from homeassistant.core import callback

    @callback
    def _on_started(_event):
        _start_resource_registration(hass, f"{CARD_URL}?v=new")

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert [i["url"] for i in _ours(res)] == [f"{CARD_URL}?v=new"]


async def test_retry_waits_for_lovelace(hass):
    from custom_components.smartify_energy import _async_register_resource_with_retry
    import asyncio

    task = asyncio.create_task(_async_register_resource_with_retry(hass, f"{CARD_URL}?v=late", delay=0.01))
    await asyncio.sleep(0.02)
    res = await _resources(hass)
    assert await task is True
    assert [i["url"] for i in _ours(res)] == [f"{CARD_URL}?v=late"]


async def test_async_setup_registers_without_thread_errors(hass, caplog):
    """Full async_setup path during startup: stale URL replaced, no thread error."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from homeassistant.core import CoreState
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
    from custom_components.smartify_energy import async_setup

    res = await _resources(hass)
    await res.async_create_item({"res_type": "module", "url": f"{CARD_URL}?v=0.3.38-old"})
    hass.set_state(CoreState.starting)
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    with patch("homeassistant.components.frontend.add_extra_js_url") as extra:
        assert await async_setup(hass, {})
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    urls = [i["url"] for i in _ours(res)]
    assert len(urls) == 1 and urls[0].startswith(f"{CARD_URL}?v=")
    assert "0.3.38-old" not in urls[0]
    # Regression 0.3.38–0.3.61: extra JS in <head> raced with the frontend's
    # scoped-registry polyfill → permanent "Konfigurationsfehler".
    extra.assert_not_called()
    assert "thread other than the event loop" not in caplog.text


async def test_yaml_mode_falls_back_to_extra_js(hass):
    """Without storage-mode resources the card is still made available."""
    from unittest.mock import patch
    from custom_components.smartify_energy import _async_register_resource_with_retry

    url = f"{CARD_URL}?v=yaml"
    with patch("homeassistant.components.frontend.add_extra_js_url") as extra:
        assert await _async_register_resource_with_retry(hass, url, delay=0) is False
    extra.assert_called_once_with(hass, url)
