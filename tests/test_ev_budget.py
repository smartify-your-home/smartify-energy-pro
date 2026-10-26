"""The EV may credit only metered PV charging above its current minimum.

Run: python -m unittest discover -s tests
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "smartify_energy"


def load_ev():
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    package = types.ModuleType("sep_ev_test")
    package.__path__ = [str(ROOT)]
    devices = types.ModuleType("sep_ev_test.devices")
    devices.__path__ = [str(ROOT / "devices")]
    with patch.dict(sys.modules, {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.core": core,
        "sep_ev_test": package,
        "sep_ev_test.devices": devices,
    }):
        loaded = {}
        for name, file in [
            ("const", "const.py"),
            ("helpers", "helpers.py"),
            ("devices.base", "devices/base.py"),
            ("devices.ev", "devices/ev.py"),
        ]:
            fullname = "sep_ev_test." + name
            spec = importlib.util.spec_from_file_location(fullname, ROOT / file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            loaded[name] = module
        return loaded["devices.ev"].EvDevice


EvDevice = load_ev()


class EVReclaimableTests(unittest.TestCase):
    def setUp(self):
        self.values = {
            "sensor.ev": "3000",
            "switch.charge": "on",
            "number.current": "13",
        }

        def get(entity):
            val = self.values.get(entity)
            return NS(state=val, attributes={"unit_of_measurement": "W"} if entity == "sensor.ev" else {}) if val is not None else None

        hass = NS(states=NS(get=get))
        manager = NS(hass=hass, hub_mode="auto", async_param_changed=lambda: None)
        self.ev = EvDevice(manager, "ev", "Wallbox", {
            "power_sensor": "sensor.ev",
            "control_entity": "switch.charge",
            "current_entity": "number.current",
            "min_current": 6,
            "max_current": 16,
            "phases": 1,
            "voltage": 230,
        })
        self.ev.params["mode"] = "auto"

    def test_only_variable_power_is_reclaimable(self):
        self.assertEqual(self.ev.power_now(), 3000)
        self.assertEqual(self.ev.reclaimable_power(), 1620)
        self.assertEqual(self.ev.own_budget_power(3000, 1620), 1380)

    def test_minimum_current_is_never_offered_to_other_loads(self):
        self.values["sensor.ev"] = "1380"
        self.assertEqual(self.ev.reclaimable_power(), 0)
        self.assertEqual(self.ev.own_budget_power(1380, 0), 1380)

    def test_observing_and_forced_charging_are_not_reclaimable(self):
        self.ev.params["mode"] = "observe"
        self.assertEqual(self.ev.reclaimable_power(), 0)
        self.ev.params.update(mode="auto", goal="now")
        self.assertEqual(self.ev.reclaimable_power(), 0)

    def test_no_valid_meter_no_power_credit(self):
        self.values["sensor.ev"] = "unknown"
        self.assertEqual(self.ev.reclaimable_power(), 0)
        self.values.pop("sensor.ev")
        self.assertEqual(self.ev.reclaimable_power(), 0)

    def test_no_charge_current_control_no_power_credit(self):
        self.ev.cfg.pop("current_entity")
        self.assertEqual(self.ev.reclaimable_power(), 0)


if __name__ == "__main__":
    unittest.main()
