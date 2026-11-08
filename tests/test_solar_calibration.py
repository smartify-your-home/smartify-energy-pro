"""Regression tests for bounded, opt-in PV calibration (no HA dependencies)."""
from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy/solar_calibration.py"
spec = importlib.util.spec_from_file_location("sep_calibration", source)
calib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calib)


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 10, 12, tzinfo=UTC)
        self.model = calib.SolarCalibration()

    def test_opt_in_cold_start_is_neutral(self):
        self.assertEqual(self.model.factor(10, self.now), 1.0)

    def test_learns_gradually_after_six_observations(self):
        for index in range(12):
            time = self.now + timedelta(minutes=11 * index)
            self.assertTrue(self.model.observe(time, 3000, 4000, 15, 10000))
        factor = self.model.factor(15, self.now + timedelta(hours=3))
        self.assertLess(factor, 1.0)
        self.assertGreaterEqual(factor, 0.6)
        self.assertEqual(self.model.factor(90, self.now + timedelta(hours=3)), 1.0)

    def test_reject_night_clipping_invalid_and_duplicate(self):
        self.assertFalse(self.model.observe(self.now, 0, 0, 0, 10000))
        self.assertFalse(self.model.observe(self.now, 10000, 4500, 0, 10000))
        self.assertFalse(self.model.observe(self.now, -3, 4000, 0, 10000))
        self.assertTrue(self.model.observe(self.now, 2000, 4000, 30, 10000))
        self.assertFalse(self.model.observe(self.now + timedelta(minutes=2), 2200, 4000, 30, 10000))
        self.assertEqual(len(self.model.samples), 1)

    def test_persistence_diagnostics_and_reset(self):
        self.model.observe(self.now, 2500, 4000, 50, 10000)
        data = self.model.dump()
        model = calib.SolarCalibration()
        model.restore(data + [{"time": "invalid"}], self.now + timedelta(hours=1))
        self.assertEqual(model.diagnostics(self.now + timedelta(hours=1))["mae_7d_w"], 1500)
        model.reset()
        self.assertEqual(model.diagnostics(self.now + timedelta(hours=1))["samples"], 0)
        self.assertEqual(model.factor(50, self.now + timedelta(hours=1)), 1.0)

    def test_invalid_stale_restored_records_ignored(self):
        ancient = self.now - timedelta(days=70)
        self.model.restore([{"time": ancient.isoformat(), "actual": 1000,
                             "predicted": 3000, "cloud": 20}], self.now)
        self.assertEqual(self.model.dump(), [])


if __name__ == "__main__":
    unittest.main()
