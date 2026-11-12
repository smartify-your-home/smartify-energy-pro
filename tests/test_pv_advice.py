"""Offline regression tests for SEP's read-only PV everyday adviser."""
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy/pv_advice.py"
spec = importlib.util.spec_from_file_location("sep_pv_advice", SOURCE)
advice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(advice)


class PVAdviceTests(unittest.TestCase):
    def setUp(self):
        self.zone = ZoneInfo("Europe/Vienna")
        self.now = datetime(2026, 11, 12, 6, 0, tzinfo=self.zone)
        self.washer = [{"kind": "washing_machine", "mode": "auto", "power": 1800, "duration": 2.0}]

    def hours(self, values):
        out = {}
        for offset, day_kwh in enumerate(values):
            if day_kwh is None:
                continue
            date = (self.now + timedelta(days=offset)).date()
            for h in range(8, 16):
                out[datetime(date.year, date.month, date.day, h, tzinfo=self.zone)] = day_kwh / 8 * 1000
        return out

    def run_advice(self, vals, devices=None, **kw):
        return advice.build_advice(self.hours(vals), self.now,
                                   self.washer if devices is None else devices, **kw)

    def test_tomorrow_advised_only_when_both_thresholds_met(self):
        result = self.run_advice([10, 16, 12])
        self.assertEqual(result["waschtipp"]["empfehlung"], "morgen")
        self.assertEqual(result["waschtipp"]["mehrertrag_kwh"], 6)
        self.assertEqual(result["tage"][1]["kwh"], 16)
        self.assertEqual(result["state"], result["tips"][0]["text"])

    def test_overmorgen_requires_clear_gain_over_tomorrow(self):
        result = self.run_advice([10, 15, 20])
        self.assertEqual(result["waschtipp"]["empfehlung"], "uebermorgen")
        self.assertIn("übermorgen", result["waschtipp"]["text"])
        self.assertEqual(self.run_advice([10, 15, 17])["waschtipp"]["empfehlung"], "morgen")

    def test_small_relative_or_absolute_gain_does_not_postpone(self):
        self.assertEqual(self.run_advice([20, 24, 22])["waschtipp"]["empfehlung"], "heute")
        self.assertEqual(self.run_advice([1, 2, 1.8])["waschtipp"]["empfehlung"], "heute")

    def test_missing_day_hours_are_not_assumed_zero(self):
        vals = self.hours([10, 16, 20])
        vals.pop(next(k for k in vals if k.day == 13 and k.hour == 9))
        res = advice.build_advice(vals, self.now, self.washer)
        self.assertFalse(res["tage"][1]["vollstaendig"])
        self.assertIsNone(res["tage"][1]["kwh"])
        self.assertEqual(res["waschtipp"]["empfehlung"], "uebermorgen")

    def test_no_whole_day_has_no_fabricated_tip(self):
        res = self.run_advice([None, None, None])
        self.assertEqual(res["waschtipp"]["empfehlung"], "unbekannt")
        self.assertIsNone(res["tage"][0]["kwh"])
        self.assertEqual(res["tips"], [])

    def test_tips_only_for_installed_devices(self):
        res = self.run_advice([10, 16, 12], devices=[])
        self.assertIsNone(res["waschtipp"])
        self.assertFalse(any(t["typ"] == "waschen" for t in res["tips"]))
        dryer = [{"kind": "dryer", "mode": "auto", "power": 1500, "duration": 2}]
        res = self.run_advice([10, 16, 12], devices=dryer)
        self.assertIsNone(res["waschtipp"])
        self.assertEqual(res["tips"][0]["typ"], "dryer")

    def test_disabled_devices_never_generate_tips(self):
        off = [{"kind": "washing_machine", "mode": "off"}]
        self.assertEqual(self.run_advice([10, 20, 12], devices=off)["tips"], [])

    def test_wait_until_06_local(self):
        self.now = self.now.replace(hour=5, minute=59)
        res = self.run_advice([10, 16, 12])
        self.assertEqual(res["state"], "ab_06_uhr")
        self.assertEqual(res["tips"], [])

    def test_live_clouds_short_tip_only_if_available(self):
        res = self.run_advice([10, 15, 12], devices=[], live_state="clearing")
        self.assertEqual(res["tips"][0]["typ"], "pv_wetter")
        self.assertIn("Sonne", res["state"])
        self.assertEqual(self.run_advice([10, 15, 12], devices=[], live_state="learning")["tips"], [])

    def test_no_double_during_dst_day_window(self):
        self.now = datetime(2026, 10, 24, 6, tzinfo=self.zone)
        res = self.run_advice([10, 16, 12])
        self.assertEqual(len(res["tage"]), 3)
        self.assertEqual(res["tage"][1]["kwh"], 16)


if __name__ == "__main__":
    unittest.main()
