"""Hub side of the appliance announcements (script call, time window)."""
from datetime import datetime
from types import SimpleNamespace as NS

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smartify_energy.manager import HUB_ENTITY_FIELDS, EnergyManager


def manager(hass, **data):
    entry = MockConfigEntry(domain="smartify_energy", data={"grid_sensor": "sensor.grid", **data})
    entry.add_to_hass(hass)
    return EnergyManager(hass, entry)


def at(hour: int) -> datetime:
    return datetime(2026, 11, 11, hour, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)


DEVICE = NS(id="wm", name="Waschmaschine")


async def test_announce_calls_script_with_message(hass):
    calls = async_mock_service(hass, "script", "turn_on")
    m = manager(hass, announce_script="script.ansage")
    hass.config.language = "de"
    assert m.announce(DEVICE, "finished", at(12)) is True
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data == {"entity_id": "script.ansage",
                             "variables": {"message": "Waschmaschine ist fertig."}}
    assert m.announce(DEVICE, "reminder", at(13)) is True
    await hass.async_block_till_done()
    assert calls[1].data["variables"]["message"] == "Waschmaschine ist fertig – bitte ausräumen."


async def test_no_script_means_no_announcement_and_no_time_entities(hass):
    calls = async_mock_service(hass, "script", "turn_on")
    m = manager(hass)
    assert m.announce(DEVICE, "finished", at(12)) is False
    await hass.async_block_till_done()
    assert calls == []
    keys = [s.key for s in m.param_specs()]
    assert "announce_start" not in keys and "announce_end" not in keys


async def test_time_window_blocks_and_equal_times_mean_always(hass):
    calls = async_mock_service(hass, "script", "turn_on")
    m = manager(hass, announce_script="script.ansage")
    assert {"announce_start", "announce_end"} <= {s.key for s in m.param_specs()}
    assert (m.p("announce_start"), m.p("announce_end")) == ("07:00", "22:00")
    assert m.announce(DEVICE, "finished", at(23)) is False
    assert m.announce(DEVICE, "finished", at(6)) is False
    await hass.async_block_till_done()
    assert calls == []
    m.params.update(announce_start="00:00", announce_end="00:00")
    assert m.announce(DEVICE, "finished", at(3)) is True
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_script_failure_does_not_raise(hass, caplog):
    m = manager(hass, announce_script="script.missing")
    assert m.announce(DEVICE, "finished", at(12)) is True
    await hass.async_block_till_done()
    assert "Ansage über script.missing fehlgeschlagen" in caplog.text


def test_script_is_not_a_tracked_state_entity():
    """The script must never be registered for state-change tracking."""
    assert "announce_script" not in HUB_ENTITY_FIELDS
