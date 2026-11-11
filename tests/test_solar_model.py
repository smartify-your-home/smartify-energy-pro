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


    def test_extended_48h_forecast_is_accepted_but_stale_missing_is_not(self):
        rows = [
            {"datetime": (self.t + timedelta(hours=i)).isoformat(),
             "cloud_coverage": (i * 7) % 101}
            for i in range(48)
        ]
        rows.extend([
            {"datetime": (self.t - timedelta(hours=3)).isoformat(), "cloud_coverage": 0},
            {"datetime": (self.t + timedelta(hours=60)).isoformat(), "cloud_coverage": 0},
            {"datetime": (self.t + timedelta(hours=2)).isoformat(), "cloud_coverage": None},
        ])
        clouds = solar.hourly_clouds({"forecast": rows}, self.t)
        self.assertEqual(len(clouds), 48)
        self.assertIn(self.t + timedelta(hours=47), clouds)
        self.assertNotIn(self.t + timedelta(hours=60), clouds)
        self.assertNotIn(self.t - timedelta(hours=3), clouds)
        self.assertEqual(len(solar.pv_hours(self.t, 48, 13, self.south, clouds)), 48)

    def test_rejects_invalid_clouds(self):
        self.assertEqual(solar.hourly_clouds({"forecast": [
            {"datetime": self.t.isoformat(), "cloud_coverage": -1},
            {"datetime": self.t.isoformat(), "cloud_coverage": 140}
        ]}, self.t), {})



class BifacialTests(unittest.TestCase):
    """0.3.69: bifacial modules add their rear side (opposite normal × bifaciality)."""
    LAT, LON = 47.98, 13.29

    def day(self, surfaces, date):
        start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
        clouds = {start + timedelta(hours=h): 0 for h in range(24)}
        return solar.pv_hours(start, self.LAT, self.LON, surfaces, clouds)

    def test_west_fence_gets_morning_sun_on_rear(self):
        mono = [{"kwp": 1.14, "tilt": 90, "azimuth": 280}]
        bi = [{**mono[0], "bifaciality": 0.7}]
        d = datetime(2026, 3, 21)
        m, b = self.day(mono, d), self.day(bi, d)
        morning = datetime(2026, 3, 21, 7, tzinfo=timezone.utc)  # 08:00 local, sun in the east
        self.assertGreater(b[morning], 3 * max(m[morning], 1))
        self.assertGreater(sum(b.values()), 1.5 * sum(m.values()))

    def test_south_fence_gain_is_small_in_winter(self):
        mono = [{"kwp": 3.04, "tilt": 90, "azimuth": 193}]
        bi = [{**mono[0], "bifaciality": 0.7}]
        d = datetime(2026, 11, 11)
        ratio = sum(self.day(bi, d).values()) / sum(self.day(mono, d).values())
        self.assertTrue(1.0 < ratio < 1.15, ratio)

    def test_monofacial_unchanged(self):
        surfaces = [{"kwp": 10, "tilt": 20, "azimuth": 180}]
        d = datetime(2026, 6, 21)
        self.assertEqual(self.day(surfaces, d), self.day([{**surfaces[0], "bifaciality": 0}], d))

if __name__ == "__main__":
    unittest.main()
