"""Offline tests for the opt-in adaptive PV forecast algorithm."""
import importlib.util
import sys
import types
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy"
pkg = types.ModuleType("sep_live_testpkg")
pkg.__path__ = [str(root)]
sys.modules[pkg.__name__] = pkg
spec = importlib.util.spec_from_file_location("sep_live_testpkg.live_pv", root / "live_pv.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class AdaptivePVTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
        self.surfaces = [{"kwp": 10, "tilt": 20, "azimuth": 180}]
        self.estimator = module.LivePVEstimator(48, 13, self.surfaces)
        self.hours = {self.now + timedelta(hours=i): 1200.0 for i in range(5)}

    def feed(self, ratios):
        for i, ratio in enumerate(ratios):
            t = self.now + timedelta(minutes=i)
            self.assertTrue(self.estimator.observe(t, self.estimator.clear_power(t) * ratio))
        return self.now + timedelta(minutes=len(ratios) - 1)

    def test_no_data_keeps_original_forecast(self):
        self.assertEqual(self.estimator.corrected(self.now, self.hours), self.hours)
        self.assertEqual(self.estimator.diagnostics(self.now)["state"], "insufficient_data")

    def test_stably_sunny_morning_boosts_only_short_horizon(self):
        t = self.feed([0.85] * 7)
        out = self.estimator.corrected(t, self.hours)
        self.assertGreater(out[self.now], self.hours[self.now])
        self.assertEqual(out[self.now + timedelta(hours=3)], self.hours[self.now + timedelta(hours=3)])
        self.assertEqual(self.estimator.state, "clear")
        self.assertLessEqual(out[self.now], self.hours[self.now] * 1.8)

    def test_stably_cloudy_day_reduces_overoptimistic_forecast(self):
        self.hours = {h: 5500.0 for h in self.hours}
        t = self.feed([0.20] * 7)
        out = self.estimator.corrected(t, self.hours)
        self.assertEqual(self.estimator.state, "low_irradiance")
        self.assertLess(out[self.now], self.hours[self.now])

    def test_variable_weather_reduces_confidence(self):
        t = self.feed([0.2, 0.9, 0.3, 0.85, 0.25, 0.8, 0.35])
        self.assertEqual(self.estimator.state, "variable")
        out = self.estimator.corrected(t, self.hours)
        self.assertGreaterEqual(out[self.now], 0)
        self.assertLessEqual(out[self.now], self.hours[self.now] * 1.8)

    def test_clearing_classification(self):
        self.feed([0.2, 0.21, 0.2, 0.35, 0.48, 0.62, 0.75])
        self.assertEqual(self.estimator.state, "clearing")

    def test_stale_measurements_do_not_override(self):
        t = self.feed([0.8] * 7)
        self.assertNotEqual(self.estimator.corrected(t, self.hours), self.hours)
        self.assertEqual(self.estimator.corrected(t + timedelta(minutes=5), self.hours), self.hours)

    def test_reject_invalid_meters_and_clipping(self):
        self.assertFalse(self.estimator.observe(self.now, float("nan")))
        self.assertFalse(self.estimator.observe(self.now, -1))
        self.assertFalse(self.estimator.observe(self.now, self.estimator.capacity))
        self.assertFalse(self.estimator.observe(self.now.replace(hour=0), 0))
        self.assertIsNone(self.estimator.index)

    def test_north_facing_azimuth_zero_is_not_south(self):
        north = module.LivePVEstimator(48, 13, [{"kwp": 5, "tilt": 80, "azimuth": 0}])
        south = module.LivePVEstimator(48, 13, [{"kwp": 5, "tilt": 80, "azimuth": 180}])
        self.assertLess(north.clear_power(self.now), south.clear_power(self.now))

    def test_out_of_order_and_duplicate_samples_ignored(self):
        t = self.now
        self.assertTrue(self.estimator.observe(t, 1500))
        self.assertFalse(self.estimator.observe(t, 1500))
        self.assertFalse(self.estimator.observe(t - timedelta(minutes=1), 1500))


if __name__ == "__main__":
    unittest.main()
