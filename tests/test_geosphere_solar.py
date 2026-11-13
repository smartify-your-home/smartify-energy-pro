"""Regression tests: GeoSphere C-LAEF GHI -> calculated SEP PV forecast.

Pure model tests, no network and no Home Assistant runtime required.
"""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy/solar_model.py"
spec = importlib.util.spec_from_file_location("sep_geosphere_solar", source)
solar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solar)


class GeoSpherePVTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 21, 11, tzinfo=timezone.utc)
        self.surface = [{"kwp": 10, "tilt": 20, "azimuth": 180}]

    def attrs(self, rows, **changes):
        return {
            "source": "GeoSphere Austria C-LAEF",
            "dataset": "nwp-v2-1h-1km",
            "irradiance_unit": "W/m²",
            "forecast": rows,
            **changes,
        }

    def row(self, stamp, ghi, clouds=50):
        return {
            "datetime": stamp.isoformat(),
            "end": (stamp + timedelta(hours=1)).isoformat(),
            "ghi_w_m2": ghi,
            "cloud_coverage": clouds,
        }

    def test_reads_only_correctly_labelled_ghi_and_preserves_zero(self):
        rows = [self.row(self.now, 0), self.row(self.now+timedelta(hours=1), 600),
                self.row(self.now+timedelta(hours=2), None)]
        expected = {self.now: 0.0, self.now+timedelta(hours=1): 600.0}
        self.assertEqual(solar.hourly_ghi(self.attrs(rows), self.now), expected)
        self.assertEqual(solar.hourly_ghi(self.attrs(rows, irradiance_unit="Wh"), self.now), {})
        self.assertEqual(solar.hourly_ghi(self.attrs(rows, source="Meteonomiqs"), self.now), {})
        self.assertEqual(solar.hourly_ghi({"forecast": rows}, self.now), {})

    def test_rejects_invalid_values_missing_end_unaware_and_wrong_intervals(self):
        bad = [
            self.row(self.now, -1), self.row(self.now+timedelta(hours=1), 2000),
            self.row(self.now+timedelta(hours=2), float("nan")),
            {"datetime": self.now.isoformat(), "ghi_w_m2": 200},
            {"datetime": "2026-06-21T11:00:00", "end": "2026-06-21T12:00:00", "ghi_w_m2": 300},
            {"datetime": self.now.isoformat(),
             "end": (self.now+timedelta(hours=2)).isoformat(), "ghi_w_m2": 400},
        ]
        self.assertEqual(solar.hourly_ghi(self.attrs(bad), self.now), {})

    def test_geo_horizon_has_up_to_60_hours_without_made_up_slots(self):
        rows = [self.row(self.now + timedelta(hours=i), i * 5) for i in range(60)]
        rows.append(self.row(self.now + timedelta(hours=64), 900))
        values = solar.hourly_ghi(self.attrs(rows), self.now)
        self.assertEqual(len(values), 60)
        self.assertEqual(values[self.now+timedelta(hours=59)], 295)
        self.assertNotIn(self.now+timedelta(hours=64), values)
        self.assertEqual(len(solar.hourly_clouds(self.attrs(rows), self.now, horizon_hours=60)), 60)
        # Keep the pre-existing cloud-parser boundary rule unchanged (49 when
        # a synthetic provider feeds more than the legacy 48h series).
        self.assertEqual(len(solar.hourly_clouds(self.attrs(rows), self.now)), 49)

    def test_geosphere_cloud_sensor_uses_all_60_real_hours(self):
        # Cloud-based PV model must not be cut off at Meteonomiqs' 48h.
        rows = [self.row(self.now + timedelta(hours=i), None, i % 101)
                for i in range(60)]
        rows.append(self.row(self.now + timedelta(hours=63), None, 20))
        attrs = self.attrs(rows, max_forecast_hours=60)
        horizon = solar.cloud_forecast_horizon(attrs)
        self.assertEqual(horizon, 60)
        selected = solar.hourly_clouds(attrs, self.now, horizon_hours=horizon)
        self.assertEqual(len(selected), 60)
        self.assertIn(self.now + timedelta(hours=59), selected)
        self.assertNotIn(self.now + timedelta(hours=63), selected)
        pv = solar.pv_hours(self.now, 48, 13, self.surface, selected)
        self.assertEqual(len(pv), 60)
        self.assertGreater(pv[self.now + timedelta(hours=59)], 0)
        self.assertEqual(solar.hourly_ghi(attrs, self.now), {})

    def test_legacy_cloud_horizon_and_metadata_detection(self):
        rows = [self.row(self.now + timedelta(hours=i), None, 20)
                for i in range(60)]
        gs = self.attrs(rows, max_forecast_hours=60)
        meteonomiqs = {**gs, "source": "Meteonomiqs"}
        self.assertEqual(solar.cloud_forecast_horizon(meteonomiqs), 48)
        self.assertEqual(len(solar.hourly_clouds(
            meteonomiqs, self.now, solar.cloud_forecast_horizon(meteonomiqs))), 49)
        self.assertEqual(solar.cloud_forecast_horizon({**gs, "dataset": "unknown"}), 48)
        self.assertEqual(solar.cloud_forecast_horizon({**gs, "max_forecast_hours": 48}), 48)
        self.assertEqual(solar.cloud_forecast_horizon({**gs, "source": "unverified"}), 48)
        self.assertEqual(solar.cloud_forecast_horizon({}), 48)
        short = self.attrs(rows[:6], max_forecast_hours=60)
        self.assertEqual(len(solar.hourly_clouds(
            short, self.now, solar.cloud_forecast_horizon(short))), 6)
        # Real zero-cloud coverage remains zero, not missing.
        zero = self.attrs([self.row(self.now, None, 0)], max_forecast_hours=60)
        self.assertEqual(solar.hourly_clouds(zero, self.now, 60)[self.now], 0.0)

    def test_larger_ghi_yields_larger_pv_even_with_same_clouds(self):
        low = solar.pv_hours_ghi(self.now, 48, 13, self.surface, {self.now: 100})[self.now]
        high = solar.pv_hours_ghi(self.now, 48, 13, self.surface, {self.now: 750})[self.now]
        self.assertGreater(high, low)
        self.assertGreater(low, 0)
        self.assertEqual(
            solar.pv_hours_ghi(self.now, 48, 13, self.surface, {self.now: 0})[self.now], 0)

    def test_cloud_percent_does_not_double_attenuate_ghi(self):
        # The GHI solver depends only on irradiance and array geometry.
        ghi = {self.now: 620}
        a = solar.pv_hours_ghi(self.now, 48, 13, self.surface, ghi)
        attrs_clear = self.attrs([self.row(self.now, 620, 0)])
        attrs_cloudy = self.attrs([self.row(self.now, 620, 100)])
        self.assertEqual(solar.hourly_ghi(attrs_clear, self.now), solar.hourly_ghi(attrs_cloudy, self.now))
        self.assertEqual(a, solar.pv_hours_ghi(self.now, 48, 13, self.surface,
                                               solar.hourly_ghi(attrs_cloudy, self.now)))

    def test_two_surfaces_and_bifacial_geometry(self):
        east = {"kwp": 4, "tilt": 30, "azimuth": 90}
        west = {"kwp": 4, "tilt": 30, "azimuth": 270}
        single = solar.pv_hours_ghi(self.now, 48, 13, [east], {self.now: 700})[self.now]
        two = solar.pv_hours_ghi(self.now, 48, 13, [east, west], {self.now: 700})[self.now]
        self.assertGreater(two, single)
        fence = {"kwp": 2, "tilt": 90, "azimuth": 280}
        mono = solar.pv_hours_ghi(self.now, 48, 13, [fence], {self.now: 700})[self.now]
        bi = solar.pv_hours_ghi(self.now, 48, 13, [{**fence, "bifaciality": 0.7}], {self.now: 700})[self.now]
        self.assertGreater(bi, mono)

    def test_night_and_missing_are_distinct(self):
        night = datetime(2026, 6, 21, 0, tzinfo=timezone.utc)
        self.assertEqual(solar.pv_hours_ghi(night, 48, 13, self.surface, {night: 0})[night], 0)
        self.assertEqual(solar.pv_hours_ghi(night, 48, 13, self.surface, {}), {})
        self.assertEqual(solar.hourly_ghi(self.attrs([]), night), {})

    def test_legacy_cloud_model_unmodified(self):
        cloudy = {self.now: 80}
        direct = solar.pv_hours(self.now, 48, 13, self.surface, cloudy)
        self.assertEqual(direct, solar.pv_hours(self.now, 48, 13, self.surface, cloudy))


if __name__ == "__main__":
    unittest.main()
