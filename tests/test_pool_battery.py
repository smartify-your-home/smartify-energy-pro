"""Pool x passive-battery priority regression tests (no HA installation)."""
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import patch
from test_load_budget import ROOT

def build():
    fake_core = types.ModuleType("homeassistant.core")
    fake_core.HomeAssistant = object
    dt = types.ModuleType("homeassistant.util.dt")
    dt.now = lambda: datetime(2026, 10, 26, 14, tzinfo=timezone.utc)
    dt.parse_datetime = datetime.fromisoformat
    dt.as_local = lambda value: value
    util = types.ModuleType("homeassistant.util")
    util.dt = dt
    pkg = types.ModuleType("sep_pool_test")
    pkg.__path__ = [str(ROOT)]
    devices = types.ModuleType("sep_pool_test.devices")
    devices.__path__ = [str(ROOT / "devices")]
    with patch.dict(sys.modules, {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.core": fake_core,
        "homeassistant.util": util,
        "homeassistant.util.dt": dt,
        "sep_pool_test": pkg,
        "sep_pool_test.devices": devices,
    }):
        modules = {}
        for name, filename in [
            ("const", "const.py"), ("helpers", "helpers.py"),
            ("devices.base", "devices/base.py"),
            ("devices.pool", "devices/pool.py"),
            ("budget", "budget.py"),
        ]:
            full = "sep_pool_test." + name
            spec = importlib.util.spec_from_file_location(full, ROOT / filename)
            module = importlib.util.module_from_spec(spec)
            sys.modules[full] = module
            spec.loader.exec_module(module)
            modules[name] = module
    return modules["devices.pool"].PoolDevice, modules["devices.base"].Context, modules["budget"]

PoolDevice, Context, budget_math = build()


class PoolBatteryTests(unittest.TestCase):
    def setUp(self):
        self.values = {"switch.pool": "off", "sensor.pool": "0", "sensor.temp": "24"}
        def get(ent):
            state = self.values.get(ent)
            return NS(state=state, attributes={"unit_of_measurement": "W"}) if state is not None else None
        self.manager = NS(hass=NS(states=NS(get=get)), hub_mode="auto",
                          async_param_changed=lambda: None, device_budgets={})
        self.pump = PoolDevice(self.manager, "pool", "Poolpumpe", {
            "switch": "switch.pool", "power_sensor": "sensor.pool",
            "temperature_sensor": "sensor.temp", "nominal_power": 700,
        })
        self.pump.params.update(mode="auto", season="summer", lock_enabled=False,
                                min_on=0, min_off=0)
        self.when = datetime(2026, 10, 26, 14, tzinfo=timezone.utc)
        self.pump.state.update(runtime=200, runtime_vm=200)
        self.pump._pflicht = lambda now, ist, vm: None

    def check(self, grid_w, battery_charge_w=0, battery_rank=10, pool_rank=1,
              averaged_grid=None, upstream=0):
        avg = grid_w if averaged_grid is None else averaged_grid
        credit = budget_math.battery_priority_credit(battery_charge_w, battery_rank, pool_rank)
        avg_credit = credit
        ctx = Context(self.when, 30, grid_w + credit, avg + avg_credit,
                      avg + avg_credit, True, False, avg + avg_credit, [])
        metered = self.pump.power_accounted_in_grid()
        own_credit = self.pump.own_budget_power(metered, 0)
        return self.pump.decide(ctx, ctx.alloc_base - upstream + own_credit)

    def test_pool_before_battery_may_start_from_battery_charge(self):
        # Grid export 0 W, battery absorbs 1200 W. Pump gets 700 W ahead
        # of storage only, even if grid meter sees zero.
        self.assertTrue(self.check(0, 1200, battery_rank=2, pool_rank=1).on)

    def test_pool_after_battery_cannot_take_existing_battery_charge(self):
        self.assertFalse(self.check(0, 1200, battery_rank=1, pool_rank=2).on)

    def test_no_double_count_own_running_pool(self):
        self.values["switch.pool"] = "on"
        self.values["sensor.pool"] = "700"
        # Grid export 100W while pool already runs; own 700W draw is
        # embedded in grid. This also meets the 50W safety margin.
        self.assertTrue(self.check(100).on)
        self.assertIsNone(self.pump._low_since)

    def test_running_pool_cannot_hog_other_priority_reservations(self):
        self.values["switch.pool"] = "on"
        self.values["sensor.pool"] = "700"
        # Higher-priority reservation of 1000 W produces a deficit.
        self.assertTrue(self.check(0, upstream=1000).on)
        self.assertEqual(self.pump._low_since, self.when)

    def test_15_min_pv_shortage_can_stop_after_target(self):
        self.values["switch.pool"] = "on"
        self.values["sensor.pool"] = "700"
        self.pump.state["runtime"] = self.pump.target_min
         # Once target is met, the currently coded pool policy stops
        # immediately when its averaged headroom is insufficient.
        self.assertFalse(self.check(-100).on)

    def test_15_min_pv_shortage_below_target(self):
        self.values["switch.pool"] = "on"
        self.values["sensor.pool"] = "700"
        self.pump.state["runtime"] = 20
        self.assertTrue(self.check(-100).on)
        self.when += timedelta(minutes=14)
        self.assertTrue(self.check(-100).on)
        self.when += timedelta(minutes=2)
        self.assertFalse(self.check(-100).on)

    def test_minimum_on_overrides_pv_shortage(self):
        self.values["switch.pool"] = "on"
        self.values["sensor.pool"] = "700"
        self.pump.params["min_on"] = 20
        self.pump.state["last_switch"] = self.when.timestamp()
        self.pump.state["runtime"] = 20
        self.assertTrue(self.check(-1500).on)
        self.assertIn("Mindestlaufzeit", self.pump.decide(
            Context(self.when, 30, -1500, -1500, -1500, True, False, -1500, []),
            -1500 + 700).reason)

    def test_lock_and_season_override_budget(self):
        self.pump.params["season"] = "winter"
        self.assertFalse(self.check(2000).on)
        self.pump.params["season"] = "summer"
        self.pump.params.update(lock_enabled=True, lock_start="13:00", lock_end="15:00")
        self.assertFalse(self.check(2000).on)

    def test_battery_discharge_is_never_pv_credit(self):
        self.assertFalse(self.check(0, battery_charge_w=-2000,
                                    battery_rank=2, pool_rank=1).on)


if __name__ == "__main__":
    unittest.main()
