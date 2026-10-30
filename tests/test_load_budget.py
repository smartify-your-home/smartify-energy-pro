"""Household PV start must check both current and averaged power.

Run: python -m unittest discover -s tests
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "smartify_energy"


def load_device():
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    dt = types.ModuleType("homeassistant.util.dt")
    dt.now = lambda: datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    util = types.ModuleType("homeassistant.util")
    util.dt = dt
    package = types.ModuleType("sep_load_test")
    package.__path__ = [str(ROOT)]
    devices = types.ModuleType("sep_load_test.devices")
    devices.__path__ = [str(ROOT / "devices")]
    with patch.dict(sys.modules, {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.core": core,
        "homeassistant.util": util,
        "homeassistant.util.dt": dt,
        "sep_load_test": package,
        "sep_load_test.devices": devices,
    }):
        loaded = {}
        for name, file in [
            ("const", "const.py"),
            ("helpers", "helpers.py"),
            ("devices.base", "devices/base.py"),
            ("devices.load", "devices/load.py"),
            ("devices.dryer", "devices/dryer.py"),
        ]:
            fullname = "sep_load_test." + name
            spec = importlib.util.spec_from_file_location(fullname, ROOT / file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            loaded[name] = module
        return loaded["devices.load"].LoadDevice, loaded["devices.base"].Context, loaded["devices.dryer"].DryerDevice


LoadDevice, Context, DryerDevice = load_device()


class HouseholdBudgetStartTests(unittest.TestCase):
    def setUp(self):
        self.values = {"switch.washer": "off", "sensor.washer": "0"}

        def get(entity):
            value = self.values.get(entity)
            return NS(state=value, attributes={"unit_of_measurement": "W"}) if value is not None else None

        hass = NS(states=NS(get=get))
        manager = NS(hass=hass, hub_mode="auto", async_param_changed=lambda: None)
        self.load = LoadDevice(manager, "washer", "Waschmaschine", {
            "switch": "switch.washer", "power_sensor": "sensor.washer",
        })
        self.load.params.update(mode="auto", min_surplus=1500, latest_start="23:59")
        self.load.state["sm"] = "wartet"
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def run_check(self, current, average):
        ctx = Context(
            self.now, 30, current, average, average, True, False,
            average, [],
        )
        return self.load.decide(ctx, average)


    def test_falling_trend_blocks_automatic_pv_start(self):
        ctx = Context(self.now, 30, 2900, 2900, 2900, True, False, 2900,
                      trend_delta=-600, trend_ready=True)
        decision = self.load.decide(ctx, 2900)
        self.assertFalse(decision.on)
        self.assertIn("PV-Trend", decision.reason)

    def test_stable_trend_allows_automatic_pv_start(self):
        ctx = Context(self.now, 30, 2900, 2900, 2900, True, False, 2900,
                      trend_delta=-60, trend_ready=True)
        self.assertTrue(self.load.decide(ctx, 2900).on)

    def test_missing_trend_history_blocks_automatic_pv_start(self):
        ctx = Context(self.now, 30, 2900, 2900, 2900, True, False, 2900,
                      trend_delta=0, trend_ready=False)
        decision = self.load.decide(ctx, 2900)
        self.assertFalse(decision.on)
        self.assertIn("Messhistorie", decision.reason)

    def test_old_positive_average_cannot_start_at_grid_import(self):
        d = self.run_check(-1000, 3000)
        self.assertFalse(d.on)
        self.assertEqual(self.load.state["sm"], "wartet")

    def test_start_requires_current_as_well_as_average(self):
        self.assertTrue(self.run_check(2500, 3000).on)

    def test_average_alone_is_insufficient(self):
        d = self.run_check(1100, 3000)
        self.assertFalse(d.on)

    def test_nominal_heater_power_sets_minimum_pv_threshold(self):
        # 1500 W configuration may not approve a 2200 W heater on PV.
        self.load.params["min_surplus"] = 1500
        self.assertEqual(self.load.pv_start_need, 2200)
        self.assertFalse(self.run_check(2000, 3000).on)
        self.assertTrue(self.run_check(2400, 3000).on)

    def test_higher_configured_threshold_wins(self):
        self.load.params["min_surplus"] = 3000
        self.assertEqual(self.load.pv_start_need, 3000)
        self.assertFalse(self.run_check(2400, 3500).on)
        self.assertTrue(self.run_check(3100, 3500).on)

    def test_active_other_heater_is_not_hard_lock(self):
        # Another appliance is heating, but additional true PV is enough.
        ctx = Context(self.now, 30, 2500, 2500, 2500,
                      True, False, 2500, ["Geschirrspueler"])
        d = self.load.decide(ctx, 2500)
        self.assertTrue(d.on)

    def test_first_detection_reclaims_only_own_measured_consumption(self):
        self.load.state["sm"] = "erkannt"
        self.values.update({"switch.washer": "on", "sensor.washer": "1800"})
        # Because washer is ALREADY drawing 1800 W, only the remaining
        # prospective 400 W can affect grid import after approval.
        ctx = Context(self.now, 30, 500, 2500, 2500, True, False, 2500)
        self.assertTrue(self.load.decide(ctx, 2500).on)

    def test_first_detection_rejects_if_own_draw_still_insufficient(self):
        self.load.state["sm"] = "erkannt"
        self.values.update({"switch.washer": "on", "sensor.washer": "1800"})
        ctx = Context(self.now, 30, 200, 2500, 2500, True, False, 2500)
        self.assertFalse(self.load.decide(ctx, 2500).on)

    def test_first_detection_requires_mature_average(self):
        self.load.state["sm"] = "erkannt"
        self.values.update({"switch.washer": "on", "sensor.washer": "1800"})
        ctx = Context(self.now, 30, 500, 2500, 2500, False, False, 2500)
        self.assertFalse(self.load.decide(ctx, 2500).on)

    def test_missing_meter_never_cancels_its_own_reservation(self):
        self.load.cfg.pop("power_sensor")
        self.values["switch.washer"] = "on"
        self.assertEqual(self.load._p(), self.load.nominal)
        self.assertEqual(self.load.power_accounted_in_grid(), 0)

    def test_first_heater_reservation_and_second_start_after_heating(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sep_load_budget_math", ROOT / "budget.py"
        )
        math = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(math)

        first_values = {"switch.first": "on", "sensor.first": "50"}

        def get_first(entity):
            value = first_values.get(entity)
            return NS(state=value, attributes={"unit_of_measurement": "W"}) if value is not None else None

        first_manager = NS(hass=NS(states=NS(get=get_first)),
                           hub_mode="auto", async_param_changed=lambda: None)
        first = LoadDevice(first_manager, "first", "Trockner", {
            "switch": "switch.first", "power_sensor": "sensor.first",
        })
        first.params.update(mode="auto", nominal_power=2200)
        first.state.update(sm="laeuft", approved=True, hp_active=False, hp_done=False)

        # Before first heater has run, 50 W already flows at the meter,
        # but another 2150 W must stay reserved for the future heater.
        current = first.power_accounted_in_grid()
        reserved = math.additional_reservation(
            first.reserved_power, current, 0
        )
        self.assertEqual(reserved, 2150)
        self.assertFalse(self.run_check(4300 - reserved, 4300 - reserved).on)
        self.load.state["sm"] = "wartet"
        self.assertTrue(self.run_check(4500 - reserved, 4500 - reserved).on)

        # Once the first heating phase ends, no future heater capacity
        # remains reserved. Its small measured running draw still stays
        # included in the real grid balance.
        # Legacy zero-reserve behavior is now opt-in; default 100 % retains the heater.\n        first.params["pause_reservation_pct"] = 0\n        first.state["hp_active"] = True\n        first._check_heating(50, self.now)
        self.assertTrue(first.state["hp_done"])
        current = first.power_accounted_in_grid()
        reserved = math.additional_reservation(first.reserved_power, current, 0)
        self.assertEqual(reserved, 0)
        first.params["pause_reservation_pct"] = 50
        self.assertEqual(math.additional_reservation(first.reserved_power, current, 0), 1050)
        first.params["pause_reservation_pct"] = 100
        self.assertEqual(math.additional_reservation(first.reserved_power, current, 0), 2150)

        # Even then the second machine only starts once the mean recovers.
        self.load.state["sm"] = "wartet"
        self.assertFalse(self.run_check(3000, 2100).on)
        self.assertTrue(self.run_check(3000, 2300).on)

    def test_unmetered_running_load_conservatively_reserves_full_power(self):
        self.load.cfg.pop("power_sensor")
        self.values["switch.washer"] = "on"
        self.load.state.update(sm="laeuft", approved=True, hp_done=False)
        accounted = self.load.power_accounted_in_grid()
        self.assertEqual(accounted, 0)
        self.assertEqual(self.load.reserved_power, self.load.nominal)


if __name__ == "__main__":
    unittest.main()
