"""FBH setpoint boost integration: safety, time, standby completion, reservation."""
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartify_energy.devices.base import Context
from custom_components.smartify_energy.devices.heatpump_fbh import FBHBoostDevice
from custom_components.smartify_energy.manager import EnergyManager


def make_fbh(hass):
    entry = MockConfigEntry(domain="smartify_energy", data={"grid_sensor": "sensor.grid"})
    entry.add_to_hass(hass)
    manager = EnergyManager(hass, entry)
    manager.params["mode"] = "auto"
    manager.async_save_now = AsyncMock()
    conf = {
        "fbh_setpoint_entity": "input_number.fbh_setpoint",
        "power_sensor": "sensor.wp",
        "nominal_power": 2500,
        "ww_active_entity": "binary_sensor.ww",
        "fbh_heating_active_entity": "binary_sensor.fbh_heating",
    }
    dev = FBHBoostDevice(manager, "fbh", "WP FBH", conf)
    dev.params.update(mode="auto", fbh_start_1="10:00", fbh_end_1="15:00",
                      fbh_reserve_before=30, fbh_finish_runtime=180,
                      fbh_idle_power=50, fbh_idle_minutes=20)
    manager.devices[dev.id] = dev
    hass.states.async_set("input_number.fbh_setpoint", "26", {"min": 16, "max": 45})
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("binary_sensor.ww", "off")
    hass.states.async_set("binary_sensor.fbh_heating", "on")

    async def update(call):
        hass.states.async_set("input_number.fbh_setpoint", str(call.data["value"]),
                              {"min": 16, "max": 45})
    hass.services.async_register("input_number", "set_value", update)
    return manager, dev


def make_ctx(local_time, watts=5000):
    return Context(now=local_time, dt=60, budget_now=watts,
                   budget_avg=watts, budget_short=watts,
                   history_ready=True, night_window=False, alloc_base=watts)


def today_at(hour, minute=0):
    return dt_util.as_local(dt_util.now()).replace(hour=hour, minute=minute,
                                                    second=0, microsecond=0)


async def test_time_mode_saves_original_and_restores_after_window(hass):
    manager, dev = make_fbh(hass)
    start = today_at(10, 15)
    await dev.async_run(make_ctx(start, 0), 0)
    assert dev.state["active"]
    assert dev.state["original"] == 26
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28
    assert manager.async_save_now.await_count >= 1  # Saved BEFORE writing
    await dev.async_run(make_ctx(today_at(15), 0), 0)
    assert not dev.state["active"]
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26


async def test_pv_control_requires_budget_and_manual_change_is_not_overwritten(hass):
    manager, dev = make_fbh(hass)
    dev.params["fbh_control"] = "pv"
    ctx = make_ctx(today_at(10), 100)
    assert not dev.decide(ctx, 100).on
    await dev.async_run(make_ctx(today_at(10), 5000), 5000)
    assert dev.state["active"]
    hass.states.async_set("input_number.fbh_setpoint", "25.5")
    await dev.async_run(make_ctx(today_at(15), 0), 0)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 25.5
    assert not dev.state["active"]


async def test_advance_reservation_only_in_configured_lead_and_remaining_power(hass):
    _, dev = make_fbh(hass)
    assert dev.advance_reservation(today_at(9, 20)) == 0
    assert dev.advance_reservation(today_at(9, 30)) == 2500
    hass.states.async_set("sensor.wp", "1000", {"unit_of_measurement": "W"})
    assert dev.advance_reservation(today_at(9, 40)) == 1500
    hass.states.async_set("binary_sensor.ww", "on")
    assert dev.advance_reservation(today_at(9, 40)) == 0
    hass.states.async_set("binary_sensor.ww", "off")
    dev.params["fbh_reserve_before"] = 0
    assert dev.advance_reservation(today_at(9, 59)) == 0


async def test_completed_after_three_hours_heating_and_twenty_minutes_standby(hass):
    _, dev = make_fbh(hass)
    await dev.async_run(make_ctx(today_at(10), 3000), 3000)
    assert dev.state["active"]
    hass.states.async_set("sensor.wp", "900", {"unit_of_measurement": "W"})
    for minute in range(181):
        dev.pre_update(make_ctx(today_at(10) + timedelta(minutes=minute)))
    assert dev.state["runtime_seconds"] >= 180 * 60
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("binary_sensor.fbh_heating", "off")  # Common after compressor reaches target.
    dev.pre_update(make_ctx(today_at(13, 1)))
    dev.pre_update(make_ctx(today_at(13, 20)))
    assert dev.state["completed_window"] is None
    dev.pre_update(make_ctx(today_at(13, 21)))
    assert dev.state["completed_window"] is not None
    assert dev.advance_reservation(today_at(13, 21)) == 0
    await dev.async_run(make_ctx(today_at(13, 21)), 0)
    assert not dev.state["active"]
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26
    assert not dev.decide(make_ctx(today_at(13, 22)), 5000).on


async def test_ww_charge_never_counts_as_fbh_heating_or_standby(hass):
    _, dev = make_fbh(hass)
    await dev.async_run(make_ctx(today_at(10), 3000), 3000)
    hass.states.async_set("sensor.wp", "1600", {"unit_of_measurement": "W"})
    hass.states.async_set("binary_sensor.ww", "on")
    dev.pre_update(make_ctx(today_at(11)))
    dev.pre_update(make_ctx(today_at(12)))
    assert dev.state["runtime_seconds"] == 0
    assert dev.state["idle_since"] is None


async def test_no_restart_after_mode_off_restore(hass):
    _, dev = make_fbh(hass)
    await dev.async_run(make_ctx(today_at(10), 3000), 3000)
    assert dev.state["active"]
    dev.params["mode"] = "off"
    await dev.async_run(make_ctx(today_at(10, 5)), 0)
    assert not dev.state["active"]
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26


@pytest.mark.parametrize("invalid", ["unavailable", "unknown"])
async def test_invalid_setpoint_blocks_unsafe_start(hass, invalid):
    _, dev = make_fbh(hass)
    hass.states.async_set("input_number.fbh_setpoint", invalid)
    assert not dev.decide(make_ctx(today_at(10), 5000), 5000).on

async def test_advance_reservation_delays_lower_priority_appliance(hass):
    """A future FBH rise wins a PV budget slot before a new appliance start."""
    from unittest.mock import patch
    from custom_components.smartify_energy.devices.base import BaseDevice, Decision

    manager, fbh = make_fbh(hass)
    hass.states.async_set("sensor.grid", "3000", {"unit_of_measurement": "W"})
    class Appliance(BaseDevice):
        def is_on(self): return False
        def decide(self, ctx, left):
            return Decision(ctx.now_left(left) >= 2000, 2000 if ctx.now_left(left) >= 2000 else 0)
        async def async_apply(self, decision, ctx): pass
    appliance = Appliance(manager, "load", "Waschmaschine", {"nominal_power": 2000})
    appliance.params.update(mode="auto", priority=5)
    manager.devices[appliance.id] = appliance
    fake_now = today_at(9, 40)
    with patch("custom_components.smartify_energy.manager.dt_util.now", return_value=fake_now):
        await manager._async_run()
    assert fbh.advance_reservation(fake_now) == 2500
    assert manager.device_budgets["fbh"]["fbh_vorreservierung_w"] == 2500
    assert not appliance.last_decision.on
    assert manager.device_budgets["load"]["aktuell_w"] <= 500
    await manager.async_stop()

async def test_post_ww_restart_only_if_fbh_was_heating_before_ww(hass):
    _, dev = make_fbh(hass)
    dev.params.update(fbh_restart_after_ww=True, fbh_restart_wait=5,
                      fbh_restart_delta=3.0, fbh_restart_duration=15)
    await dev.async_run(make_ctx(today_at(10)), 4000)
    # A positively identified heating run must precede the WW transition.
    hass.states.async_set("sensor.wp", "900", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 1)))
    hass.states.async_set("binary_sensor.ww", "on")
    hass.states.async_set("binary_sensor.fbh_heating", "off")
    hass.states.async_set("sensor.wp", "1800", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 2)))
    assert dev.state["fbh_was_running_before_ww"]
    # WW has finished but the FBH did not resume.
    hass.states.async_set("binary_sensor.ww", "off")
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 15)))
    assert dev.state["ww_recovery_eligible"]
    await dev.async_run(make_ctx(today_at(10, 19)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28
    await dev.async_run(make_ctx(today_at(10, 20)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 31
    assert dev.state["restart_used_window"] == dev.state["window"]
    # Without feedback of a heating restart the 15-minute cap must prevail.
    await dev.async_run(make_ctx(today_at(10, 34)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 31
    await dev.async_run(make_ctx(today_at(10, 35)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28
    # The same WW interruption must never cause a second pulse.
    await dev.async_run(make_ctx(today_at(10, 42)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28
    await dev.async_run(make_ctx(today_at(15)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26


async def test_ww_without_prior_fbh_heating_does_not_trigger_pulse(hass):
    _, dev = make_fbh(hass)
    dev.params.update(fbh_restart_after_ww=True, fbh_restart_wait=5)
    await dev.async_run(make_ctx(today_at(10)), 4000)
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("binary_sensor.fbh_heating", "off")
    dev.pre_update(make_ctx(today_at(10, 1)))
    hass.states.async_set("binary_sensor.ww", "on")
    hass.states.async_set("sensor.wp", "1800", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 2)))
    assert not dev.state["fbh_was_running_before_ww"]
    hass.states.async_set("binary_sensor.ww", "off")
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 15)))
    await dev.async_run(make_ctx(today_at(10, 30)), 4000)
    assert not dev.state["ww_recovery_eligible"]
    assert dev.state["restart_pulse_target"] is None
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28


async def test_post_ww_spontaneous_fbh_restart_prevents_extra_setpoint(hass):
    _, dev = make_fbh(hass)
    dev.params["fbh_restart_after_ww"] = True
    await dev.async_run(make_ctx(today_at(10)), 4000)
    hass.states.async_set("sensor.wp", "900", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 1)))
    hass.states.async_set("binary_sensor.ww", "on")
    hass.states.async_set("binary_sensor.fbh_heating", "off")
    dev.pre_update(make_ctx(today_at(10, 2)))
    hass.states.async_set("binary_sensor.ww", "off")
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 15)))
    hass.states.async_set("binary_sensor.fbh_heating", "on")
    hass.states.async_set("sensor.wp", "900", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 18)))
    await dev.async_run(make_ctx(today_at(10, 28)), 4000)
    assert dev.state["restart_pulse_target"] is None
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28


async def test_post_ww_restart_requires_both_status_signals_and_max_temp_limit(hass):
    _, dev = make_fbh(hass)
    dev.params.update(fbh_restart_after_ww=True, fbh_restart_wait=5,
                      fbh_restart_delta=6.0)
    await dev.async_run(make_ctx(today_at(10)), 4000)
    hass.states.async_set("sensor.wp", "900", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 1)))
    hass.states.async_set("binary_sensor.ww", "on")
    hass.states.async_set("binary_sensor.fbh_heating", "off")
    dev.pre_update(make_ctx(today_at(10, 2)))
    hass.states.async_set("binary_sensor.ww", "off")
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 15)))
    dev.cfg.pop("fbh_heating_active_entity")
    await dev.async_run(make_ctx(today_at(10, 21)), 4000)
    assert dev.state["restart_pulse_target"] is None
    dev.cfg["fbh_heating_active_entity"] = "binary_sensor.fbh_heating"
    dev.params["fbh_max_temp"] = 30
    await dev.async_run(make_ctx(today_at(10, 22)), 4000)
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 30
    assert dev.state["restart_pulse_target"] == 30


async def test_post_ww_pulse_only_once_and_respects_disabled_default(hass):
    _, dev = make_fbh(hass)
    assert dev.p("fbh_restart_after_ww") is False
    await dev.async_run(make_ctx(today_at(10)), 4000)
    hass.states.async_set("sensor.wp", "900", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 1)))
    hass.states.async_set("binary_sensor.ww", "on")
    hass.states.async_set("binary_sensor.fbh_heating", "off")
    dev.pre_update(make_ctx(today_at(10, 2)))
    hass.states.async_set("binary_sensor.ww", "off")
    hass.states.async_set("sensor.wp", "0", {"unit_of_measurement": "W"})
    dev.pre_update(make_ctx(today_at(10, 15)))
    await dev.async_run(make_ctx(today_at(10, 30)), 4000)
    assert dev.state["restart_pulse_target"] is None
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28


async def test_demand_sensor_blocks_automatic_start_and_advance_reservation(hass):
    _, dev = make_fbh(hass)
    dev.cfg["fbh_demand_entity"] = "input_boolean.heizbedarf"
    hass.states.async_set("input_boolean.heizbedarf", "off")
    ctx = make_ctx(today_at(10, 15))
    assert not dev.decide(ctx, 5000).on
    assert "Standby" in dev.reason or "Standby" in dev.decide(ctx, 5000).reason
    assert dev.advance_reservation(today_at(9, 40)) == 0
    assert not dev._manual_can_raise(today_at(10, 15))
    hass.states.async_set("input_boolean.heizbedarf", "on")
    assert dev.decide(ctx, 5000).on
    assert dev.advance_reservation(today_at(9, 40)) == 2500


async def test_demand_unknown_fails_closed_and_active_boost_restores(hass):
    _, dev = make_fbh(hass)
    dev.cfg["fbh_demand_entity"] = "binary_sensor.heizbedarf"
    hass.states.async_set("binary_sensor.heizbedarf", "on")
    await dev.async_run(make_ctx(today_at(10, 20)), 5000)
    assert dev.state["active"]
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 28
    hass.states.async_set("binary_sensor.heizbedarf", "unavailable")
    await dev.async_run(make_ctx(today_at(10, 21)), 5000)
    assert not dev.state["active"]
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26
    assert dev.advance_reservation(today_at(10, 22)) == 0


async def test_manual_lower_pauses_automatic_restart_but_explicit_raise_is_possible(hass):
    from unittest.mock import patch

    manager, dev = make_fbh(hass)
    manager.async_request_run = AsyncMock()
    with patch("custom_components.smartify_energy.devices.heatpump_fbh.dt_util.now",
               return_value=today_at(10, 30)):
        before = dev.status_attrs()
        assert before["fbh_erhoehung_aktiv"] is False
        assert before["sollwert_aktuell"] == 26
        assert before["fbh_manuell_anheben_moeglich"]
        assert not before["fbh_manuell_absenken_moeglich"]
        await dev.async_raise_now()
        raised = dev.status_attrs()
        assert raised["fbh_erhoehung_aktiv"]
        assert raised["sollwert_original"] == 26
        assert raised["sollwert_boost"] == 28
        assert raised["sollwert_aktuell"] == 28
        assert not raised["fbh_manuell_anheben_moeglich"]
        assert raised["fbh_manuell_absenken_moeglich"]

        await dev.async_lower_now()
        lowered = dev.status_attrs()
        assert not lowered["fbh_erhoehung_aktiv"]
        assert lowered["sollwert_aktuell"] == 26
        assert lowered["fbh_automatik_nach_absenken_pausiert"]
        assert lowered["fbh_manuell_anheben_moeglich"]
        assert not lowered["fbh_manuell_absenken_moeglich"]
        # No automatic restart immediately following a user lowering.
        assert not dev.decide(make_ctx(today_at(10, 35)), 5000).on

        # Explicit user request may raise again in the same eligible window.
        await dev.async_raise_now()
        assert dev.state["active"]
        assert dev.state["manual_lock_window"] is None
        assert dev.state["completed_window"] is None
        assert float(hass.states.get("input_number.fbh_setpoint").state) == 28
        await dev.async_lower_now()
        assert float(hass.states.get("input_number.fbh_setpoint").state) == 26


async def test_manual_lower_is_only_offered_during_matching_active_window(hass):
    from unittest.mock import patch

    manager, dev = make_fbh(hass)
    manager.async_request_run = AsyncMock()
    with patch("custom_components.smartify_energy.devices.heatpump_fbh.dt_util.now",
               return_value=today_at(10, 20)):
        await dev.async_raise_now()
        assert dev._manual_can_lower(today_at(10, 21))
        assert not dev._manual_can_lower(today_at(15, 1))
        attrs = dev.status_attrs()
        assert attrs["fbh_erhoehung_aktiv"]
        assert attrs["fbh_zeitfenster_aktiv"]
    with patch("custom_components.smartify_energy.devices.heatpump_fbh.dt_util.now",
               return_value=today_at(15, 1)):
        attrs = dev.status_attrs()
        assert attrs["fbh_erhoehung_aktiv"]  # Until normal safe restore completes.
        assert not attrs["fbh_manuell_absenken_moeglich"]
        assert not attrs["fbh_zeitfenster_aktiv"]
        with pytest.raises(ValueError):
            await dev.async_lower_now()
    # Existing scheduler safely restores outside the configured window.
    await dev.async_run(make_ctx(today_at(15, 2), 0), 0)
    assert not dev.state["active"]
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26



async def test_manual_raise_denied_after_last_hour_of_window(hass):
    from unittest.mock import patch

    _, dev = make_fbh(hass)
    for hour, minute, expected in [(13, 59, True), (14, 0, True), (14, 1, False),
                                    (15, 0, False), (9, 59, False)]:
        with patch("custom_components.smartify_energy.devices.heatpump_fbh.dt_util.now",
                   return_value=today_at(hour, minute)):
            assert dev._manual_can_raise(today_at(hour, minute)) is expected


async def test_manual_raise_does_not_bypass_missing_heat_demand(hass):
    from unittest.mock import patch

    _, dev = make_fbh(hass)
    dev.cfg["fbh_demand_entity"] = "input_boolean.heizbedarf"
    hass.states.async_set("input_boolean.heizbedarf", "off")
    with patch("custom_components.smartify_energy.devices.heatpump_fbh.dt_util.now",
               return_value=today_at(10, 20)):
        with pytest.raises(ValueError):
            await dev.async_raise_now()
    assert dev.state["original"] is None
    assert float(hass.states.get("input_number.fbh_setpoint").state) == 26


async def test_manual_lower_does_not_forget_rollback_if_write_unconfirmed(hass):
    from unittest.mock import patch

    manager, dev = make_fbh(hass)
    manager.async_request_run = AsyncMock()
    with patch("custom_components.smartify_energy.devices.heatpump_fbh.dt_util.now",
               return_value=today_at(10, 20)):
        await dev.async_raise_now()
        hass.services.async_remove("input_number", "set_value")
        async def delayed_write(_call):
            return None
        hass.services.async_register("input_number", "set_value", delayed_write)
        await dev.async_lower_now()
        assert dev.state["active"], "rollback snapshot must survive unconfirmed actor write"
        assert dev.state["original"] == 26
        assert dev.state["restore_pending"]
        assert dev.state["manual_lock_window"] == dev.state["window"]
