"""Rolling energy and mutually exclusive WW start-filter regression checks."""
import importlib.util
from datetime import timedelta, timezone
from types import SimpleNamespace as NS
import unittest
import test_heatpump_weather as weather
from test_heatpump_weather import ROOT, HeatPumpDevice

spec = importlib.util.spec_from_file_location('forecast_window_test', ROOT / 'forecast_window.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ForecastStartTests(unittest.TestCase):
    def setUp(self):
        weather.WeatherStartTests.setUp(self)
        self.now += timedelta(minutes=30)
        self.ctx.now = self.now
        self.dev.params.update(boost_start_filter='pv_forecast', boost_forecast_hours='2',
                               boost_forecast_min_kwh=2)
        hour = self.now.replace(minute=0)
        self.fc = NS(configured=True, error=None, last_update=self.now,
                     hours={hour: 1000, hour+timedelta(hours=1): 1000,
                            hour+timedelta(hours=2): 1000})
        self.manager.forecast = self.fc

    def allowed(self):
        return self.dev.decide(self.ctx, 3000).on

    def test_rolling_partial_hours(self):
        h = self.now.replace(minute=0)
        self.fc.hours = {h:1000, h+timedelta(hours=1):2000, h+timedelta(hours=2):3000}
        self.assertEqual(module.rolling_energy(self.fc,self.now,1), (1500,None))
        self.assertEqual(module.rolling_energy(self.fc,self.now,2), (4000,None))

    def test_threshold_and_budget(self):
        self.assertTrue(self.allowed())
        self.dev.params['boost_forecast_min_kwh'] = 2.1
        self.assertFalse(self.allowed())
        self.dev.params['boost_forecast_min_kwh'] = 2
        self.assertFalse(self.dev.decide(self.ctx,0).on)

    def test_alternative_filters(self):
        self.values['sensor.next']='100'
        self.assertTrue(self.allowed())  # clouds ignored in forecast mode
        self.dev.params['boost_start_filter']='cloud'
        self.assertFalse(self.allowed())
        self.dev.params['boost_start_filter']='none'
        self.manager.forecast=None
        self.assertTrue(self.allowed())

    def test_missing_invalid_stale_forecast(self):
        for changes in ({'configured':False}, {'error':'failed'}, {'last_update':None},
                        {'last_update':self.now-timedelta(minutes=61)}, {'hours':{}},
                        {'hours':{self.now.replace(minute=0):1000}}):
            with self.subTest(changes=changes):
                self.manager.forecast=NS(**(vars(self.fc)|changes))
                self.assertFalse(self.allowed())
        for value in (float('nan'), float('inf'), -1, 'bad'):
            bad=dict(self.fc.hours);bad[next(iter(bad))]=value
            self.manager.forecast=NS(**(vars(self.fc)|{'hours':bad}))
            self.assertFalse(self.allowed())

    def test_zero_forecast_is_valid_but_below_threshold(self):
        self.fc.hours=dict.fromkeys(self.fc.hours,0)
        self.assertEqual(module.rolling_energy(self.fc,self.now,2), (0,None))
        self.assertFalse(self.allowed())

    def test_running_ww_bypasses_forecast_not_temperature(self):
        self.dev.cfg['ww_active_entity']='binary_sensor.ww'
        self.values['binary_sensor.ww']='on'
        self.ctx.now=self.now+timedelta(minutes=10)
        self.manager.forecast=None
        self.ctx.budget_now=self.ctx.budget_avg=self.ctx.alloc_base=0
        self.assertTrue(self.dev.decide(self.ctx,0).on)
        self.values['sensor.temp']='51'
        self.assertFalse(self.dev.decide(self.ctx,0).on)

    def test_number_start_uses_forecast(self):
        self.dev.cfg.update(boost_type='number',boost_entity='number.target')
        self.dev=HeatPumpDevice(self.manager,'hp','WW',dict(self.dev.cfg))
        self.dev.params.update(boost_start_filter='pv_forecast',boost_forecast_min_kwh=2)
        self.dev._idle_since=self.now-timedelta(minutes=20)
        self.assertTrue(self.allowed())
        self.fc.error='broken'
        self.assertFalse(self.allowed())

    def test_migration_and_saved_selection(self):
        for active in (True,False):
            self.dev.load({'params':{'cloud_filter_active':active},'cfg':self.cfg})
            self.assertEqual(self.dev.p('boost_start_filter'),'cloud' if active else 'none')
        self.dev.params['boost_start_filter']='pv_forecast'
        saved=self.dev.dump()
        restored=HeatPumpDevice(self.manager,'hp','WW',self.cfg)
        restored.load(saved)
        self.assertEqual(restored.p('boost_start_filter'),'pv_forecast')

