"""Instantaneous heater sink: PV-only, thermal safety, and optional debounce."""
import importlib.util
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
import unittest
import sys
import types
from unittest.mock import patch

from test_load_budget import Context, ROOT, load_device

# Isolated modules, with no real Home Assistant installation required.
fake_ha = types.ModuleType("homeassistant")
fake_core = types.ModuleType("homeassistant.core")
fake_core.HomeAssistant = object
fake_ha_util = types.ModuleType("homeassistant.util")
fake_dt = types.ModuleType("homeassistant.util.dt")
fake_dt.now = lambda: datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
fake_ha_util.dt = fake_dt
package = types.ModuleType("sep_heater_test")
package.__path__ = [str(ROOT)]
devices_package = types.ModuleType("sep_heater_test.devices")
devices_package.__path__ = [str(ROOT / "devices")]
with patch.dict(sys.modules, {
    "homeassistant": fake_ha,
    "homeassistant.core": fake_core,
    "homeassistant.util": fake_ha_util,
    "homeassistant.util.dt": fake_dt,
    "sep_heater_test": package,
    "sep_heater_test.devices": devices_package,
}):
    modules = {}
    for name, filename in [
        ("const", "const.py"),
        ("helpers", "helpers.py"),
        ("devices.base", "devices/base.py"),
        ("devices.heater", "devices/heater.py"),
    ]:
        fullname = "sep_heater_test." + name
        spec = importlib.util.spec_from_file_location(fullname, ROOT / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        spec.loader.exec_module(module)
        modules[name] = module
HeaterDevice = modules["devices.heater"].HeaterDevice


class HeaterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.states = {
            "switch.heater": "off",
            "input_boolean.heater": "off",
            "sensor.temp": "45",
            "sensor.heater_power": "0",
        }
        self.calls = []
        self.saves = []
        def get(name):
            s = self.states.get(name)
            return NS(state=s, attributes={"unit_of_measurement": "W"}) if s is not None else None

        async def async_call(domain, service, data, blocking):
            self.calls.append((domain, service, dict(data)))
            self.states[data["entity_id"]] = "on" if service == "turn_on" else "off"

        async def async_save_now():
            self.saves.append(True)

        self.manager = NS(
            hass=NS(states=NS(get=get), services=NS(async_call=async_call)),
            hub_mode="auto", device_budgets={},
            async_param_changed=lambda: None,
            async_save_now=async_save_now,
        )
        self.heater = HeaterDevice(
            self.manager, "heater", "Elektroheizstab",
            {"switch": "switch.heater", "power_sensor": "sensor.heater_power",
             "temperature_sensor": "sensor.temp", "nominal_power": 2000}
        )
        self.heater.params.update(mode="auto")
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def context(self, current, mean=-2000, *, upstream=0, ready=False):
        # The heap manager has already reserved upstream new demand.
        return Context(self.now, 30, current, mean, mean,
                       ready, False, mean, [])

    def decide(self, current, mean=-5000, upstream=0):
        ctx = self.context(current, mean)
        # Pass allocation base minus upstream extra heater reservations.
        return self.heater.decide(ctx, ctx.alloc_base - upstream)

    async def test_priority_stop_overrides_minimum_on_and_retry_pause(self):
        self.states["switch.heater"] = "on"
        self.heater.params["heater_min_on"] = 120
        self.heater.state["last_switch"] = self.now.timestamp()
        self.heater._actuator_retry_at = self.now.timestamp() + 30
        self.assertTrue(await self.heater.async_priority_stop(self.context(-1200)))
        self.assertFalse(self.heater.is_on())

    async def test_priority_stop_preserves_manual_observe_and_positive_credit(self):
        self.states["switch.heater"] = "on"
        for mode, budget in [("manual", -1200), ("observe", -1200), ("auto", 1000)]:
            self.heater.params["mode"] = mode
            self.assertFalse(await self.heater.async_priority_stop(self.context(budget)))
            self.assertTrue(self.heater.is_on())
        self.assertEqual(self.calls, [])

    async def test_invalid_grid_stops_despite_minimum_on_and_positive_credit(self):
        self.states["switch.heater"] = "on"
        self.heater.params["heater_min_on"] = 120
        self.heater.state["last_switch"] = self.now.timestamp()
        ctx = self.context(5000)
        ctx.grid_valid = False
        decision = await self.heater.async_run(ctx, ctx.alloc_base)
        self.assertFalse(decision.on)
        self.assertFalse(self.heater.is_on())
        self.assertIn("Netzsensor", decision.reason)
        self.assertEqual(self.calls[-1][:2], ("switch", "turn_off"))

    async def test_invalid_grid_blocks_start_then_recovers(self):
        ctx = self.context(5000)
        ctx.grid_valid = False
        self.assertFalse((await self.heater.async_run(ctx, ctx.alloc_base)).on)
        self.assertEqual(self.calls, [])
        ctx.grid_valid = True
        self.assertTrue((await self.heater.async_run(ctx, ctx.alloc_base)).on)

    async def test_manual_thermostat_does_not_require_grid_sensor(self):
        self.heater.params["mode"] = "manual"
        ctx = self.context(0)
        ctx.grid_valid = False
        self.assertTrue((await self.heater.async_run(ctx, ctx.alloc_base)).on)

    async def test_manual_thermostat_with_grid_import_and_hysteresis(self):
        self.heater.params.update(mode="manual", heater_max_temp=50, heater_hysteresis=1)
        self.now = self.now.replace(hour=8)
        self.heater.state["preempt_until"] = self.now.timestamp() + 3600
        ctx = self.context(-5000)
        decision = await self.heater.async_run(ctx, -5000)
        self.assertTrue(decision.on)
        self.assertTrue(decision.forced)
        self.assertTrue(self.heater.is_on())
        self.assertFalse(self.heater.can_preempt(self.now))
        self.states["sensor.temp"] = "49.5"
        self.assertTrue((await self.heater.async_run(ctx, -5000)).on)
        self.states["sensor.temp"] = "50"
        self.assertFalse((await self.heater.async_run(ctx, -5000)).on)
        self.assertFalse(self.heater.is_on())
        self.states["sensor.temp"] = "49"
        self.assertFalse((await self.heater.async_run(ctx, -5000)).on)
        self.states["sensor.temp"] = "48.9"
        self.assertTrue((await self.heater.async_run(ctx, -5000)).on)

    async def test_manual_sensor_failure_and_hub_off_stop_immediately(self):
        self.heater.params.update(mode="manual", heater_min_on=120)
        ctx = self.context(-5000)
        await self.heater.async_run(ctx, -5000)
        self.states["sensor.temp"] = "unavailable"
        await self.heater.async_run(ctx, -5000)
        self.assertFalse(self.heater.is_on())
        self.states["sensor.temp"] = "45"
        await self.heater.async_run(ctx, -5000)
        self.manager.hub_mode = "off"
        await self.heater.async_run(ctx, -5000)
        self.assertFalse(self.heater.is_on())

    async def test_manual_minimum_pause_and_return_to_automatic(self):
        self.heater.params.update(mode="manual", heater_min_off=5)
        self.heater.state["last_switch"] = self.now.timestamp()
        self.assertFalse((await self.heater.async_run(self.context(-5000), -5000)).on)
        self.now += timedelta(minutes=5)
        self.assertTrue((await self.heater.async_run(self.context(-5000), -5000)).on)
        self.heater.params["mode"] = "auto"
        self.assertFalse((await self.heater.async_run(self.context(-5000), -5000)).on)
        self.assertFalse(self.heater.is_on())

    async def test_observe_does_not_actuate(self):
        self.heater.params["mode"] = "observe"
        await self.heater.async_run(self.context(5000), 5000)
        self.assertEqual(self.calls, [])

    def test_no_average_gate_even_if_average_very_negative(self):
        self.assertTrue(self.decide(2500, mean=-9000).on)
        self.assertFalse(self.decide(2100, mean=9000).on)

    def test_priority_reservations_always_count_in_current_budget(self):
        self.assertFalse(self.decide(3000, mean=4000, upstream=1300).on)
        self.assertTrue(self.decide(3600, mean=4000, upstream=1300).on)

    def test_heater_load_already_embedded_in_grid(self):
        self.states["switch.heater"] = "on"
        self.states["sensor.heater_power"] = "2000"
        self.assertEqual(self.heater.power_accounted_in_grid(), 2000)
        self.assertTrue(self.decide(100, mean=-6000).on)
        self.assertFalse(self.decide(-20, mean=6000).on)

    def test_on_no_sensor_never_claims_nominal_watts_are_metered(self):
        self.heater.cfg.pop("power_sensor")
        self.states["switch.heater"] = "on"
        self.assertEqual(self.heater.power_accounted_in_grid(), 0)

    def test_temperature_limits_and_hysteresis(self):
        self.states["sensor.temp"] = "52"
        self.assertFalse(self.decide(4000).on)  # restart strictly below 52
        self.states["sensor.temp"] = "51.5"
        self.assertTrue(self.decide(4000).on)
        self.states["switch.heater"] = "on"
        self.states["sensor.temp"] = "54.5"
        self.assertTrue(self.decide(50).on)  # may continue through hysteresis
        self.states["sensor.temp"] = "55"
        self.assertFalse(self.decide(4000).on)

    def test_invalid_temperature_is_safety_stop_even_in_minimum_on_time(self):
        self.states["switch.heater"] = "on"
        self.states["sensor.temp"] = "unavailable"
        self.heater.params["heater_min_on"] = 60
        self.heater.state["last_switch"] = self.now.timestamp()
        self.assertFalse(self.decide(4000).on)

    def test_missing_switch_readback_blocks_new_start(self):
        self.states["switch.heater"] = "unavailable"
        self.assertFalse(self.decide(4000).on)

    def test_start_allowed_from_ten_am_only(self):
        self.now = self.now.replace(hour=9, minute=59)
        self.assertFalse(self.decide(4000).on)
        self.now = self.now.replace(hour=10)
        self.assertTrue(self.decide(4000).on)

    def test_optional_minimum_off_time_survives_restart(self):
        self.heater.params["heater_min_off"] = 10
        self.heater.state.update(last_switch=self.now.timestamp(), last_switch_state=False)
        self.assertFalse(self.decide(4000).on)
        self.now += timedelta(minutes=10)
        self.assertTrue(self.decide(4000).on)
        other = HeaterDevice(self.manager, "heater2", "Other", self.heater.cfg)
        other.params.update(self.heater.params)
        other.load(self.heater.dump())
        self.assertEqual(other.state["last_switch"], self.heater.state["last_switch"])

    def test_optional_minimum_on_time_and_urgent_overtemperature(self):
        self.states["switch.heater"] = "on"
        self.heater.params["heater_min_on"] = 5
        self.heater.state["last_switch"] = self.now.timestamp()
        self.assertTrue(self.decide(-800).on)
        self.states["sensor.temp"] = "55"
        self.assertFalse(self.decide(6000).on)
        self.states["sensor.temp"] = "45"
        self.now += timedelta(minutes=5)
        self.assertFalse(self.decide(-800).on)

    async def test_switch_actuation_and_durable_pause_state(self):
        d = self.decide(2500)
        ctx = self.context(2500)
        await self.heater.async_apply(d, ctx)
        self.assertEqual(self.calls[-1][:2], ("switch", "turn_on"))
        self.assertTrue(self.saves)
        self.assertTrue(self.heater.is_on())
        d = self.decide(-100)
        await self.heater.async_apply(d, ctx)
        self.assertEqual(self.calls[-1][:2], ("switch", "turn_off"))
        self.assertEqual(len(self.saves), 2)

    async def test_input_boolean_actuation(self):
        self.heater.cfg["switch"] = "input_boolean.heater"
        await self.heater.async_apply(self.decide(2500), self.context(2500))
        self.assertEqual(self.calls[-1][:2], ("input_boolean", "turn_on"))

    async def test_hub_off_always_disables_heater(self):
        self.states["switch.heater"] = "on"
        self.heater.params["heater_min_on"] = 120
        self.heater.state["last_switch"] = self.now.timestamp()
        await self.heater.async_disabled(self.context(10000))
        self.assertEqual(self.calls[-1][:2], ("switch", "turn_off"))


if __name__ == "__main__":
    unittest.main()


