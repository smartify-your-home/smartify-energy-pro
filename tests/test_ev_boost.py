"""Zeitlich begrenzter PV-Boost der Wallbox (Faktor × PV, Mindestleistung, Netzbezug).

Run: python -m unittest discover -s tests
"""
import unittest
from datetime import timedelta

from test_ev_stop_delay import T0, Ctx, EVStopDelayTests


class EVBoostTests(unittest.TestCase):
    decide = EVStopDelayTests.decide

    def setUp(self):
        EVStopDelayTests.setUp(self)
        self.ev.params.update(boost=False, boost_factor=2, boost_hours=3, boost_min_power=0, goal="pv_only")

    def start_boost(self, **params):
        self.ev.params.update(params)
        self.ev.set_param("boost", True)

    def amps(self, decision):
        return decision.setpoint.get("current") if decision.on else 0

    def test_factor_doubles_pv_budget(self):
        self.start_boost()
        d = self.decide(0, 1500)  # 3000 W → 13 A × 230 V
        self.assertEqual(self.amps(d), 13)
        self.assertEqual(self.ev.status_attrs()["boost_bis"], (T0 + timedelta(hours=3)).astimezone().isoformat())
        self.assertIn("Boost ×2", d.reason)

    def test_minimum_power_charges_without_pv(self):
        self.start_boost(boost_min_power=2300)
        self.values["switch.charge"] = "off"
        self.assertEqual(self.amps(self.decide(0, -500)), 10)

    def test_without_minimum_low_pv_does_not_start(self):
        self.start_boost()
        self.values["switch.charge"] = "off"
        self.assertFalse(self.decide(0, 400).on)  # 800 W < 6 A minimum

    def test_without_minimum_running_charge_uses_stop_delay(self):
        self.start_boost()
        self.assertTrue(self.decide(0, 400).on)
        self.assertEqual(self.ev.status_attrs()["pv_stopp_um"], (T0 + timedelta(minutes=30)).isoformat())
        self.assertFalse(self.decide(30, 400).on)

    def test_minimum_below_three_phase_wallbox_minimum_keeps_charging(self):
        """Live-Fall 07.11.: ×2 auf ~1058 W PV, Minimum 2000 W, Wallbox 3-phasig
        (6 A × 3 = 4140 W). Kein PV-Stopp, sondern Laden mit Wallbox-Minimum."""
        self.ev.cfg["phases"] = 3
        self.start_boost(boost_min_power=2000)
        for minute in (0, 15, 31, 60):
            d = self.decide(minute, 1058)
            self.assertTrue(d.on, f"Boost darf nach {minute} min nicht stoppen")
            self.assertEqual(self.amps(d), 6)
            self.assertIn("Wallbox-Minimum", d.reason)
        self.assertIsNone(self.ev.status_attrs()["pv_stopp_um"])

    def test_factor_only_on_three_phases_still_uses_stop_delay(self):
        self.ev.cfg["phases"] = 3
        self.start_boost(boost_min_power=0)
        self.assertTrue(self.decide(0, 1058).on)
        self.assertIsNotNone(self.ev.status_attrs()["pv_stopp_um"])
        self.assertFalse(self.decide(30, 1058).on)

    def test_expires_after_duration_and_switches_off(self):
        self.start_boost(boost_min_power=2300)
        self.decide(0, 0)
        self.assertTrue(self.decide(179, 0).on)
        d = self.decide(180, 0)
        self.assertNotIn("Boost", d.reason)
        self.assertFalse(self.ev.p("boost"))
        self.assertIsNone(self.ev.status_attrs()["boost_bis"])

    def test_unplug_ends_boost(self):
        self.ev.cfg["connected_entity"] = "binary_sensor.plug"
        self.values["binary_sensor.plug"] = "on"
        self.start_boost()
        self.decide(0, 1500)
        self.values["binary_sensor.plug"] = "off"
        self.decide(1, 1500)
        self.assertFalse(self.ev.p("boost"))

    def test_switch_off_ends_boost_immediately(self):
        self.start_boost(boost_min_power=2300)
        self.decide(0, 0)
        self.ev.set_param("boost", False)
        self.assertIsNone(self.ev.status_attrs()["boost_bis"])
        self.assertNotIn("Boost", self.decide(1, 2000).reason)

    def test_not_preempted_by_higher_priority_while_boosting(self):
        self.start_boost()
        self.decide(0, 1500)
        self.assertFalse(self.ev.can_preempt(T0 + timedelta(minutes=1)))

    def test_forced_and_immediate_charging_take_precedence(self):
        self.start_boost()
        self.ev.params["goal"] = "now"
        d = self.decide(0, 1500)
        self.assertTrue(d.forced)
        self.assertNotIn("Boost", d.reason)

    def test_own_charge_counts_for_boost_with_km_goal(self):
        self.ev.params["goal"] = "km_until"
        self.assertFalse(self.ev._can_reclaim_pv_power())
        self.start_boost()
        self.assertTrue(self.ev._can_reclaim_pv_power())


if __name__ == "__main__":
    unittest.main()


class EVFullAtTests(unittest.TestCase):
    def setUp(self):
        EVStopDelayTests.setUp(self)
        self.ev.cfg.update(capacity=60, efficiency=100, soc_sensor="sensor.soc")
        self.ev.params["max_soc"] = 80
        self.values["sensor.soc"] = "50"
        self.values["sensor.ev"] = "3600"

    def test_full_time_from_current_power(self):
        # 30 % of 60 kWh = 18 kWh at 3.6 kW = 5 h
        self.assertEqual(self.ev.full_at(T0), T0 + timedelta(hours=5))

    def test_efficiency_extends_time(self):
        self.ev.cfg["efficiency"] = 90
        self.assertEqual(self.ev.full_at(T0), T0 + timedelta(hours=18000 / 0.9 / 3600))

    def test_hidden_when_not_charging_or_data_missing(self):
        self.values["switch.charge"] = "off"
        self.assertIsNone(self.ev.full_at(T0))
        self.values["switch.charge"] = "on"
        self.values["sensor.ev"] = "100"
        self.assertIsNone(self.ev.full_at(T0))
        self.values["sensor.ev"] = "3600"
        self.values["sensor.soc"] = "80"
        self.assertIsNone(self.ev.full_at(T0))
        del self.values["sensor.soc"]
        self.assertIsNone(self.ev.full_at(T0))
