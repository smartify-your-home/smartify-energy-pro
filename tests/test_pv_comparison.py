"""Offline regression tests for PV plan actual vs frozen forecast comparison."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy/pv_comparison.py"
spec = importlib.util.spec_from_file_location("pv_comparison_test", file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
PVComparison = mod.PVComparison
UTC = timezone.utc


class PVComparisonTests(unittest.TestCase):
    def setUp(self):
        self.hour = datetime(2026, 11, 8, 8, tzinfo=UTC)

    def test_original_forecast_is_not_replaced(self):
        model = PVComparison()
        model.capture(self.hour - timedelta(minutes=15), {self.hour: 1000})
        model.capture(self.hour - timedelta(minutes=10), {self.hour: 4000})
        self.assertEqual(model.forecasts[self.hour.isoformat()], 1000)

    def test_integrates_complete_hours_and_survives_restart(self):
        model = PVComparison()
        model.capture(self.hour - timedelta(minutes=15), {self.hour: 1000})
        for i in range(61):
            model.observe(self.hour + timedelta(minutes=i), 800.0)
        result = model.today(self.hour + timedelta(hours=1,minutes=1), UTC)
        self.assertEqual(result["verglichene_stunden"], 1)
        self.assertEqual(result["prognose_kwh"], 1)
        self.assertEqual(result["ist_kwh"], 0.8)
        self.assertEqual(result["abweichung_pct"], -20.0)
        restored = PVComparison()
        restored.restore(model.dump(), self.hour + timedelta(hours=1))
        self.assertEqual(restored.today(self.hour+timedelta(hours=1,minutes=1), UTC)["ist_kwh"], 0.8)
        self.assertIsNone(restored.previous)
        restored.observe(self.hour+timedelta(hours=1,minutes=2), 900)
        self.assertEqual(restored.today(self.hour+timedelta(hours=1,minutes=2),UTC)["ist_kwh"], 0.8)

    def test_missing_meter_and_large_gaps_are_not_filled_with_zero(self):
        model = PVComparison()
        model.capture(self.hour-timedelta(minutes=1),{self.hour:2000})
        model.observe(self.hour, 1000)
        model.observe(self.hour+timedelta(minutes=10), 1000) # Gap > 180 seconds.
        model.observe(self.hour+timedelta(minutes=11), None)
        model.observe(self.hour+timedelta(hours=1), 1000)
        report=model.today(self.hour+timedelta(hours=1,minutes=1),UTC)
        self.assertEqual(report["verglichene_stunden"],0)
        self.assertIsNone(report["ist_kwh"])
        self.assertIsNone(report["stunden"][0]["ist_wh"])

    def test_missing_forecast_does_not_count_as_zero(self):
        model = PVComparison()
        for i in range(61):
            model.observe(self.hour+timedelta(minutes=i), 500)
        report = model.today(self.hour+timedelta(hours=1), UTC)
        self.assertEqual(report["stunden"], [])
        self.assertIsNone(report["prognose_kwh"])

    def test_hourly_buckets_split_at_utc_boundary(self):
        model = PVComparison()
        model.capture(self.hour-timedelta(minutes=15),{self.hour:1000})
        model.observe(self.hour+timedelta(minutes=59), 1000)
        model.observe(self.hour+timedelta(hours=1,minutes=1), 1000)
        self.assertAlmostEqual(model.actual_wh[self.hour.isoformat()], 1000/60,places=2)
        self.assertAlmostEqual(model.actual_wh[(self.hour+timedelta(hours=1)).isoformat()],1000/60,places=2)

    def test_no_retroactive_capture_and_invalid_meter(self):
        model = PVComparison()
        model.capture(self.hour+timedelta(minutes=20), {self.hour:1000,
                       self.hour+timedelta(hours=1):900})
        self.assertNotIn(self.hour.isoformat(), model.forecasts)
        model.observe(self.hour, float("nan"))
        model.observe(self.hour+timedelta(minutes=1), -1)
        self.assertEqual(model.actual_wh, {})
        self.assertIsNone(model.previous)

    def test_duplicate_dst_hour_uses_distinct_utc_keys(self):
        from zoneinfo import ZoneInfo
        tz=ZoneInfo("Europe/Vienna")
        first=datetime(2026,10,25,0,tzinfo=UTC)
        second=first+timedelta(hours=1)
        model=PVComparison()
        model.capture(first-timedelta(hours=1),{first:100,second:200})
        self.assertEqual(len(model.today(second+timedelta(hours=1),tz)["stunden"]),2)


if __name__=="__main__":
    unittest.main()
