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
