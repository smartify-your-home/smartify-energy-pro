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


    def test_48h_history_has_missing_gaps_and_only_completed_comparisons(self):
        model = PVComparison()
        model.capture(self.hour-timedelta(minutes=5), {
            self.hour: 2000, self.hour+timedelta(hours=1): 1800,
        })
        for i in range(61):
            model.observe(self.hour+timedelta(minutes=i), 1000)
        report = model.recent(self.hour+timedelta(hours=2), 48)
        self.assertEqual(report["zeitraum_stunden"], 48)
        self.assertEqual(len(report["stunden"]), 48)
        self.assertEqual(report["stunden"][-3]["zeit"], self.hour.isoformat())
        self.assertEqual(report["stunden"][-3]["ist_wh"], 1000)
        self.assertIsNone(report["stunden"][0]["prognose_wh"])
        self.assertIsNone(report["stunden"][0]["ist_wh"])
        self.assertEqual(report["verglichene_stunden"], 1)
        self.assertEqual(report["prognose_kwh"], 2)
        self.assertEqual(report["ist_kwh"], 1)
        self.assertEqual(report["abweichung_pct"], -50)

    def test_fourteen_day_history_retained_persisted_and_older_pruned(self):
        model = PVComparison()
        current = self.hour + timedelta(days=15)
        within = current - timedelta(days=13)
        obsolete = current - timedelta(days=17)
        model.capture(obsolete-timedelta(hours=1), {obsolete: 1000})
        model.capture(within-timedelta(hours=1), {within: 1200})
        model._prune(current)
        self.assertNotIn(obsolete.isoformat(), model.forecasts)
        self.assertIn(within.isoformat(), model.forecasts)
        report = model.recent(current, 336)
        self.assertEqual(report["zeitraum_stunden"], 336)
        self.assertEqual(len(report["stunden"]), 336)
        self.assertIn(within.isoformat(), {row["zeit"] for row in report["stunden"]})
        restored = PVComparison()
        restored.restore(model.dump(), current)
        self.assertIn(within.isoformat(), restored.forecasts)

    def test_48h_history_distinguishes_two_dst_hours(self):
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Vienna")
        model = PVComparison()
        result = model.recent(datetime(2026, 10, 25, 6, tzinfo=UTC), 48)
        local = [datetime.fromisoformat(x["zeit"]).astimezone(tz)
                 for x in result["stunden"]]
        repeated = [t for t in local if t.date().isoformat()=="2026-10-25" and t.hour==2]
        self.assertEqual(len(repeated), 2)
        self.assertNotEqual(repeated[0].utcoffset(),repeated[1].utcoffset())

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



class DayForecastTests(unittest.TestCase):
    """0.3.63: "PV-Prognose heute" covers the whole day, not only the rest."""
    VIENNA = timezone(timedelta(hours=1))

    def test_elapsed_hours_come_from_frozen_forecast(self):
        model = PVComparison()
        day = datetime(2026, 11, 11, 6, tzinfo=UTC)  # 07:00 local
        model.capture(day - timedelta(hours=1), {day + timedelta(hours=h): w for h, w in
                                                 enumerate([66.5, 308.1, 471.6, 1030.6, 1174.5])})
        now = day + timedelta(hours=4, minutes=22)  # 11:22 local, current hour 10 UTC
        # Live (calculated) forecast only from the current hour onwards, already lowered.
        live = {day + timedelta(hours=4): 473.0, day + timedelta(hours=5): 499.0,
                day + timedelta(days=1): 300.0}  # tomorrow must not count
        total = model.day_forecast_wh(live, now, self.VIENNA)
        self.assertAlmostEqual(total, 66.5 + 308.1 + 471.6 + 1030.6 + 473.0 + 499.0)

    def test_live_hours_win_and_nothing_is_counted_twice(self):
        model = PVComparison()
        h = datetime(2026, 11, 11, 8, tzinfo=UTC)
        model.capture(h - timedelta(hours=1), {h: 900.0})
        # External providers deliver elapsed hours themselves: keep their value.
        total = model.day_forecast_wh({h: 500.0}, h + timedelta(hours=2), self.VIENNA)
        self.assertEqual(total, 500.0)

    def test_frozen_hours_of_other_days_and_future_are_ignored(self):
        model = PVComparison()
        y = datetime(2026, 11, 10, 10, tzinfo=UTC)
        model.capture(y - timedelta(hours=1), {y: 700.0})
        now = datetime(2026, 11, 11, 9, 30, tzinfo=UTC)
        model.capture(now - timedelta(minutes=40), {now.replace(minute=0) + timedelta(hours=1): 50.0})
        self.assertEqual(model.day_forecast_wh({now.replace(minute=0): 10.0}, now, self.VIENNA), 10.0)

    def test_no_live_forecast_returns_none(self):
        self.assertIsNone(PVComparison().day_forecast_wh({}, datetime(2026, 11, 11, tzinfo=UTC), self.VIENNA))

if __name__=="__main__":
    unittest.main()
