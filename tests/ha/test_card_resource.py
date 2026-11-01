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
