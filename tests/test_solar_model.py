"""Offline regression tests for cloud-driven four-plane solar projection."""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

source = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy/solar_model.py"
spec = importlib.util.spec_from_file_location("sep_solar_model", source)
solar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solar)


class SolarModelTests(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026, 6, 21, 11, 0, tzinfo=timezone.utc)
        self.south = [{"kwp": 10, "tilt": 20, "azimuth": 180}]

    def test_cloud_values_percent_not_wh(self):
        attributes = {"forecast": [
            {"datetime": self.t.isoformat(), "cloud_coverage": 50},
            {"datetime": (self.t + timedelta(hours=1)).isoformat(), "cloud_coverage": None},
        ]}
        self.assertEqual(solar.hourly_clouds(attributes, self.t), {self.t: 50.0})

    def test_cloudier_means_lower_generation(self):
        clear = solar.pv_hours(self.t, 48, 13, self.south, {self.t: 0})[self.t]
        cloudy = solar.pv_hours(self.t, 48, 13, self.south, {self.t: 100})[self.t]
        self.assertGreater(clear, cloudy)
        self.assertGreater(cloudy, 0)

    def test_two_planes_sum_independently(self):
        east = {"kwp": 4, "tilt": 30, "azimuth": 90}
        west = {"kwp": 4, "tilt": 30, "azimuth": 270}
        single = solar.pv_hours(self.t, 48, 13, [east], {self.t: 20})[self.t]
        both = solar.pv_hours(self.t, 48, 13, [east, west], {self.t: 20})[self.t]
        self.assertGreater(both, single)

    def test_night_is_zero(self):
        night = datetime(2026, 6, 21, 0, tzinfo=timezone.utc)
        self.assertEqual(solar.pv_hours(night, 48, 13, self.south, {night: 0})[night], 0)

    def test_absent_cloud_forecast_is_not_assumed_clear(self):
        self.assertEqual(solar.pv_hours(self.t, 48, 13, self.south, {}), {})

    def test_rejects_invalid_clouds(self):
        self.assertEqual(solar.hourly_clouds({"forecast": [
            {"datetime": self.t.isoformat(), "cloud_coverage": -1},
            {"datetime": self.t.isoformat(), "cloud_coverage": 140}
        ]}, self.t), {})


if __name__ == "__main__":
    unittest.main()
