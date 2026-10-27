"""WW one-shot and persistent cooldown regression tests."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

from test_heatpump_weather import HeatPumpDevice, Context


class WarmWaterOnceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
        self.values = {
            "binary_sensor.ww": "off",
            "sensor.power": "0",
            "sensor.temp": "40",
            "input_boolean.trigger": "off",
        }
        self.saved = []
        self.calls = []
        self.fail_service = False

        def get(entity):
            value = self.values.get(entity)
            return NS(state=value, attributes={}, last_changed=self.now) if value is not None else None

        async def save():
            self.saved.append(self.dev.dump())

        async def call(domain, service, data, blocking=False):
            # The date MUST have been persisted before the external command.
            self.assertTrue(self.saved)
            self.calls.append((domain, service, data))
            if self.fail_service:
                raise RuntimeError("uncertain actuator result")
            if domain == "input_boolean":
                self.values["input_boolean.trigger"] = (
                    "on" if service == "turn_on" else "off"
                )

        self.manager = NS(
            hass=NS(states=NS(get=get), services=NS(async_call=call)),
            hub_mode="auto", async_param_changed=lambda: None,
            async_save_now=save,
        )
        self.cfg = {
            "boost_type": "switch",
            "boost_entity": "input_boolean.trigger",
            "ww_active_entity": "binary_sensor.ww",
            "power_sensor": "sensor.power",
            "temperature_sensor": "sensor.temp",
            "nominal_power": 2000,
        }
        self.dev = self.device()
    
    def device(self):
        dev = HeatPumpDevice(self.manager, "ww", "WW", dict(self.cfg))
        dev.params["mode"] = "auto"
        dev._idle_since = self.now - timedelta(minutes=20)
        return dev

    def ctx(self, now=None, power=3000):
        return Context(now or self.now, 30, power, power, power, True, False, power)

    async def run_cycle(self, now=None, budget=3000):
        return await self.dev.async_run(self.ctx(now, budget), budget)

    async def test_persist_before_start_and_never_send_off(self):
        decision = await self.run_cycle()
        self.assertTrue(decision.on)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1], "turn_on")
        self.assertEqual(self.saved[-1]["state"]["last_trigger"], self.now.timestamp())
        # Power drops/sky clouds: SEP must never send an OFF to cancel WW.
        self.values["binary_sensor.ww"] = "on"
        d = await self.run_cycle(self.now + timedelta(minutes=10), -1000)
        self.assertFalse(d.on)
        self.assertEqual(len(self.calls), 1)
        await self.dev.async_disabled(self.ctx())
        self.assertEqual(len(self.calls), 1)

    async def test_restart_keeps_one_hour_interval(self):
        await self.run_cycle()
        state_before_restart = self.saved[-1]
        self.values["input_boolean.trigger"] = "off"
        self.dev = self.device()
        self.dev.load(state_before_restart)
        self.dev._idle_since = self.now - timedelta(minutes=20)
        d = await self.run_cycle(self.now + timedelta(minutes=59))
        self.assertFalse(d.on)
        self.assertEqual(len(self.calls), 1)
        self.dev._idle_since = self.now - timedelta(minutes=20)
        d = await self.run_cycle(self.now + timedelta(minutes=60))
        self.assertTrue(d.on)
        self.assertEqual(len(self.calls), 2)

    async def test_longer_configured_cooldown(self):
        self.dev.params["trigger_cooldown"] = 125
        await self.run_cycle()
        self.values["input_boolean.trigger"] = "off"
        self.dev._idle_since = self.now - timedelta(minutes=20)
        self.assertFalse((await self.run_cycle(self.now + timedelta(minutes=124))).on)
        self.assertTrue((await self.run_cycle(self.now + timedelta(minutes=125))).on)
        self.assertEqual(len(self.calls), 2)

    async def test_cooldown_cannot_go_below_hour(self):
        self.dev.params["trigger_cooldown"] = 30
        await self.run_cycle()
        self.assertGreater(self.dev._cooldown_remaining(self.now + timedelta(minutes=59)), 0)
        self.assertEqual(self.dev._cooldown_remaining(self.now + timedelta(minutes=60)), 0)

    async def test_running_ww_blocks_first_start(self):
        self.values["binary_sensor.ww"] = "on"
        d = await self.run_cycle()
        self.assertFalse(d.on)
        self.assertEqual(len(self.calls), 0)
        self.assertTrue(self.dev.is_on())

    async def test_missing_ww_state_blocks_start(self):
        self.values.pop("binary_sensor.ww")
        d = await self.run_cycle()
        self.assertFalse(d.on)
        self.assertIn("nicht verfügbar", d.reason)
        self.assertEqual(len(self.calls), 0)

    async def test_trigger_still_on_blocks_new_start(self):
        self.values["input_boolean.trigger"] = "on"
        d = await self.run_cycle()
        self.assertFalse(d.on)
        self.assertEqual(len(self.calls), 0)

    async def test_actuator_failure_is_fail_closed(self):
        self.fail_service = True
        with self.assertRaises(RuntimeError):
            await self.run_cycle()
        self.assertEqual(len(self.saved), 1)
        self.assertGreater(self.dev._cooldown_remaining(self.now + timedelta(minutes=1)), 0)

    async def test_button_sends_only_press(self):
        self.cfg.update(boost_type="button", boost_entity="button.trigger")
        self.values["button.trigger"] = "unknown"
        self.dev = self.device()
        await self.run_cycle()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][:2], ("button", "press"))

    def test_legacy_start_timestamp_restored(self):
        start = (self.now - timedelta(minutes=15)).timestamp()
        self.dev.load({"params": {}, "state": {"started": start},
                       "cfg": self.cfg})
        self.assertEqual(self.dev.state["last_trigger"], start)
        self.assertGreater(self.dev._cooldown_remaining(self.now), 0)

    async def test_configured_wait_boundaries_and_zero_budget(self):
        self.values["binary_sensor.ww"] = "on"
        self.dev._idle_since = None
        for minutes in (1, 10, 25, 180):
            self.dev.params["ww_active_minutes"] = minutes
            before = self.now + timedelta(minutes=minutes, seconds=-1)
            at = self.now + timedelta(minutes=minutes)
            self.assertFalse(self.dev.decide(self.ctx(before, 0), 0).on)
            self.assertTrue(self.dev.decide(self.ctx(at, 0), 0).on)
            self.assertFalse(self.dev.decide(self.ctx(at, -1), -1).on)

    async def test_zero_disables_running_permission_only(self):
        self.dev.params["ww_active_minutes"] = 0
        self.values["binary_sensor.ww"] = "on"
        self.assertFalse(self.dev.decide(self.ctx(self.now + timedelta(hours=5)), 3000).on)
        self.values["binary_sensor.ww"] = "off"
        self.assertTrue(self.dev.decide(self.ctx(), 3000).on)

    async def test_running_cycle_only_once_after_cooldown(self):
        self.values["binary_sensor.ww"] = "on"
        self.assertTrue((await self.run_cycle(self.now + timedelta(minutes=10), 0)).on)
        self.values["input_boolean.trigger"] = "off"
        self.assertFalse((await self.run_cycle(self.now + timedelta(minutes=90), 3000)).on)
        self.assertEqual(len(self.calls), 1)

    def test_wait_default_and_restart(self):
        self.assertEqual(self.dev.p("ww_active_minutes"), 10)
        self.dev.params["ww_active_minutes"] = 0
        saved = self.dev.dump()
        self.dev = self.device()
        self.dev.load(saved)
        self.assertEqual(self.dev.p("ww_active_minutes"), 0)
        self.cfg["ww_active_minutes"] = 25
        self.dev = self.device()
        self.dev.load(saved)
        self.assertEqual(self.dev.p("ww_active_minutes"), 25)

    def test_running_ww_ignores_clouds_but_keeps_temperature_and_budget(self):
        self.dev.cfg.update(cloud_now_entity="sensor.cloud_now", cloud_next_entity="sensor.cloud_next")
        self.dev.params.update(boost_start_filter="cloud", cloud_now_max=75, cloud_next_max=50)
        self.values["binary_sensor.ww"] = "on"
        at = self.now + timedelta(minutes=10)
        for cloud in ("100", "unavailable", "unknown"):
            self.values.update({"sensor.cloud_now": cloud, "sensor.cloud_next": cloud})
            self.assertTrue(self.dev.decide(self.ctx(at, 0), 0).on)
            self.assertFalse(self.dev.decide(self.ctx(at, -1), -1).on)
        self.values["sensor.temp"] = "51"  # 55 target - 4 hysteresis: strict boundary
        self.assertFalse(self.dev.decide(self.ctx(at, 0), 0).on)
        self.values["sensor.temp"] = "50.9"
        self.assertTrue(self.dev.decide(self.ctx(at, 0), 0).on)
        self.values["binary_sensor.ww"] = "off"
        self.assertFalse(self.dev.decide(self.ctx(at, 3000), 3000).on)

    def test_running_ww_keeps_optional_sun_filter(self):
        self.dev.cfg["sun_angle_entity"] = "sensor.sun"
        self.dev.params.update(sun_filter_active=True, sun_angle_min=12)
        self.values.update({"binary_sensor.ww": "on", "sensor.sun": "11"})
        self.assertFalse(self.dev.decide(self.ctx(self.now + timedelta(minutes=10), 0), 0).on)


if __name__ == "__main__":
    unittest.main()
