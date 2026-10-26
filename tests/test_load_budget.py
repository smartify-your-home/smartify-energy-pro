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
        ]:
            fullname = "sep_load_test." + name
            spec = importlib.util.spec_from_file_location(fullname, ROOT / file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            loaded[name] = module
        return loaded["devices.load"].LoadDevice, loaded["devices.base"].Context


LoadDevice, Context = load_device()


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

    def test_old_positive_average_cannot_start_at_grid_import(self):
        d = self.run_check(-1000, 3000)
        self.assertFalse(d.on)
        self.assertEqual(self.load.state["sm"], "wartet")

    def test_start_requires_current_as_well_as_average(self):
        self.assertTrue(self.run_check(2500, 3000).on)

    def test_average_alone_is_insufficient(self):
        d = self.run_check(1100, 3000)
        self.assertFalse(d.on)


if __name__ == "__main__":
    unittest.main()
