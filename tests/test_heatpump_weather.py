"""Start-gate regression tests with minimal HA state/service doubles.

Run: python -m unittest discover -s tests
These tests execute the integration's device code, not a live HA installation.
"""
import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/smartify_energy'

def load_device():
    core = types.ModuleType('homeassistant.core')
    core.HomeAssistant = object
    package = types.ModuleType('sep_weather_test')
    package.__path__ = [str(ROOT)]
    devices = types.ModuleType('sep_weather_test.devices')
    devices.__path__ = [str(ROOT / 'devices')]
    with patch.dict(sys.modules, {'homeassistant': types.ModuleType('homeassistant'),
                                 'homeassistant.core': core,
                                 'sep_weather_test': package,
                                 'sep_weather_test.devices': devices}):
        loaded = {}
        for name, file in [('const', 'const.py'), ('helpers', 'helpers.py'),
                           ('devices.base', 'devices/base.py'),
                           ('devices.heatpump', 'devices/heatpump.py')]:
            fullname = 'sep_weather_test.' + name
            spec = importlib.util.spec_from_file_location(fullname, ROOT / file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            loaded[name] = module
        return loaded['devices.heatpump'].HeatPumpDevice, loaded['devices.base'].Context

HeatPumpDevice, Context = load_device()

class WeatherStartTests(unittest.TestCase):
    def setUp(self):
        self.values = {'sensor.sun': '12', 'sensor.now': '74.9', 'sensor.next': '49.9',
                       'sensor.power': '0', 'sensor.temp': '40'}
        def get(entity):
            value = self.values.get(entity)
            return NS(state=value, attributes={}) if value is not None else None
        hass = NS(states=NS(get=get))
        self.manager = NS(hass=hass, hub_mode='auto', async_param_changed=lambda: None)
        self.cfg = {'boost_type': 'button', 'boost_entity': 'button.boost',
                    'power_sensor': 'sensor.power', 'temperature_sensor': 'sensor.temp',
                    'sun_angle_entity': 'sensor.sun', 'sun_angle_min': 12,
                    'cloud_now_entity': 'sensor.now', 'cloud_now_max': 75,
                    'cloud_next_entity': 'sensor.next', 'cloud_next_max': 50}
        self.dev = HeatPumpDevice(self.manager, 'hp', 'Warmwasser', dict(self.cfg))
        self.dev.params.update(sun_filter_active=True, cloud_filter_active=True)
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.dev._idle_since = self.now - timedelta(minutes=20)
        self.ctx = Context(self.now, 30, 3000, 3000, 3000, True, False, 3000)

    def allowed(self):
        return self.dev.decide(self.ctx, 3000).on

    def test_defaults_disabled_and_limits_unset(self):
        dev = HeatPumpDevice(self.manager, 'new', 'New', {})
        self.assertFalse(dev.p('sun_filter_active'))
        self.assertFalse(dev.p('cloud_filter_active'))
        self.assertIsNone(dev.p('sun_angle_min'))
        self.assertIsNone(dev.p('cloud_now_max'))
        self.assertIsNone(dev.p('cloud_next_max'))

    def test_boundary_values(self):
        self.assertTrue(self.allowed())  # Sun exactly 12 allowed.
        for entity, bad in [('sensor.sun', '11.99'), ('sensor.now', '75'), ('sensor.next', '50')]:
            with self.subTest(entity=entity):
                saved = self.values[entity]
                self.values[entity] = bad
                self.assertFalse(self.allowed())
                self.values[entity] = saved

    def test_disabled_checks_ignore_bad_values(self):
        self.dev.params.update(sun_filter_active=False, cloud_filter_active=False)
        self.values.update({'sensor.sun': 'unavailable', 'sensor.now': '100', 'sensor.next': '100'})
        self.assertTrue(self.allowed())

    def test_each_missing_cloud_field_ignores_whole_cloud_check(self):
        self.values['sensor.now'] = '100'
        for key in ('cloud_now_entity', 'cloud_next_entity', 'cloud_now_max', 'cloud_next_max'):
            with self.subTest(key=key):
                target = self.dev.cfg if key.endswith('entity') else self.dev.params
                old = target.pop(key)
                self.assertTrue(self.allowed())
                self.assertFalse(self.dev._weather_checks()['cloud']['wirksam'])
                target[key] = old

    def test_missing_sun_fields_ignore_sun_check(self):
        self.values['sensor.sun'] = '-5'
        for key in ('sun_angle_entity', 'sun_angle_min'):
            target = self.dev.cfg if key.endswith('entity') else self.dev.params
            old = target.pop(key)
            self.assertTrue(self.allowed())
            target[key] = old

    def test_missing_invalid_or_out_of_range_readings_block(self):
        for value in (None, 'unavailable', 'unknown', 'nan', 'inf', '-1', '101'):
            with self.subTest(value=value):
                self.values['sensor.next'] = value
                self.assertFalse(self.allowed())

    def test_zero_threshold_is_configured(self):
        self.dev.params['cloud_now_max'] = 0
        self.values['sensor.now'] = '0'
        self.assertFalse(self.allowed())
        self.assertTrue(self.dev._weather_checks()['cloud']['wirksam'])

    def test_invalid_threshold_blocks(self):
        for value in (math.nan, math.inf, 'bad', 101):
            self.dev.params['cloud_now_max'] = value
            self.assertFalse(self.allowed())

    def test_checks_are_independent(self):
        self.dev.params['cloud_filter_active'] = False
        self.values['sensor.sun'] = '5'
        self.assertFalse(self.allowed())
        self.dev.params.update(cloud_filter_active=True, sun_filter_active=False)
        self.values['sensor.next'] = '100'
        self.assertFalse(self.allowed())

    def test_ww_power_is_never_reclaimable(self):
        # A triggered WW cycle is controlled by the heat pump itself.
        self.dev.params["mode"] = "auto"
        self.dev.state["active"] = True
        self.values["sensor.power"] = "2000"
        self.assertEqual(self.dev.power_now(), 2000)
        self.assertEqual(self.dev.reclaimable_power(), 0)
        self.assertEqual(self.dev.own_budget_power(2000, 0), 0)

    def test_running_boost_not_stopped_by_weather(self):
        self.dev.state.update(active=True, started=self.now.timestamp())
        self.values.update({'sensor.sun': '-10', 'sensor.next': '100'})
        self.assertTrue(self.allowed())

    def test_existing_temperature_idle_and_power_gates_remain(self):
        self.dev.params['target_temp'] = 50
        self.values['sensor.temp'] = '46'
        self.assertFalse(self.allowed())
        self.values['sensor.temp'] = '45.9'
        self.dev._idle_since = self.now - timedelta(minutes=14)
        self.assertFalse(self.allowed())
        self.dev._idle_since = self.now - timedelta(minutes=20)
        self.assertFalse(self.dev.decide(self.ctx, 0).on)

    def test_store_and_config_removal(self):
        data = self.dev.dump()
        restored = HeatPumpDevice(self.manager, 'hp', 'Warmwasser', dict(self.cfg))
        restored.load(data)
        self.assertTrue(restored.p('sun_filter_active'))
        self.assertEqual(restored.p('sun_angle_min'), 12)
        cfg = dict(self.cfg)
        cfg.pop('sun_angle_min')
        changed = HeatPumpDevice(self.manager, 'hp', 'Warmwasser', cfg)
        changed.load(data)
        self.assertIsNone(changed.p('sun_angle_min'))
        self.assertFalse(changed._weather_checks()['sun']['wirksam'])

if __name__ == '__main__':
    unittest.main()
