"""PV-Stopp-Zeitpunkt der Wallbox während der Stopp-Verzögerung.

Run: python -m unittest discover -s tests
"""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace as NS

from test_ev_budget import EvDevice

T0 = datetime(2026, 11, 5, 12, 0)


class Ctx:
    history_ready = True

    def __init__(self, now, avail):
        self.now, self.avail = now, avail

    def now_left(self, _budget):
        return self.avail

    def short_left(self, _budget):
        return self.avail


class EVStopDelayTests(unittest.TestCase):
    def setUp(self):
        self.values = {"sensor.ev": "1380", "switch.charge": "on", "number.current": "6"}

        def get(entity):
            val = self.values.get(entity)
            return NS(state=val, attributes={}) if val is not None else None

        manager = NS(hass=NS(states=NS(get=get)), hub_mode="auto", async_param_changed=lambda: None,
                     p=lambda key: None, device_budgets={})
        self.ev = EvDevice(manager, "ev", "Wallbox", {
            "power_sensor": "sensor.ev", "control_entity": "switch.charge",
            "current_entity": "number.current", "min_current": 6, "max_current": 16,
            "phases": 1, "voltage": 230,
        })
        self.ev.params.update(mode="auto", stop_delay=30, pv_share=100, phase_mode="1")

    def decide(self, minutes, avail):
        return self.ev.decide(Ctx(T0 + timedelta(minutes=minutes), avail), avail)

    def test_stop_time_shown_while_delay_counts_and_cleared_on_recovery(self):
        self.decide(0, 2000)
        self.assertIsNone(self.ev.status_attrs()["pv_stopp_um"])
        d = self.decide(1, 200)  # cloud
        self.assertTrue(d.on)
        self.assertEqual(self.ev.status_attrs()["pv_stopp_um"], (T0 + timedelta(minutes=31)).isoformat())
        self.decide(10, 300)  # still short: deadline unchanged
        self.assertEqual(self.ev.status_attrs()["pv_stopp_um"], (T0 + timedelta(minutes=31)).isoformat())
        self.decide(12, 2000)  # sun is back
        self.assertIsNone(self.ev.status_attrs()["pv_stopp_um"])

    def test_charge_stops_at_shown_time_and_value_is_cleared(self):
        self.decide(0, 200)
        self.assertTrue(self.decide(29, 200).on)
        d = self.decide(30, 200)
        self.assertFalse(d.on)
        self.assertIsNone(self.ev.status_attrs()["pv_stopp_um"])

    def test_stale_timer_cleared_while_not_charging(self):
        self.decide(0, 200)
        self.values["switch.charge"] = "off"  # stopped externally / Max-SoC
        self.decide(5, 200)
        self.values["switch.charge"] = "on"
        self.assertTrue(self.decide(40, 200).on, "neuer Ladevorgang darf nicht sofort stoppen")
        self.assertEqual(self.ev.status_attrs()["pv_stopp_um"], (T0 + timedelta(minutes=70)).isoformat())

    def test_unplugging_clears_timer(self):
        self.ev.cfg["connected_entity"] = "binary_sensor.plug"
        self.values["binary_sensor.plug"] = "on"
        self.decide(0, 200)
        self.values["binary_sensor.plug"] = "off"
        self.decide(1, 200)
        self.assertIsNone(self.ev.status_attrs()["pv_stopp_um"])


    def _km_goal(self, km):
        self.ev.params.update(goal="km_until", target_km=km, deadline="18:00", consumption=18)
        self.ev.state["charged_wh"] = 0.0

    def test_km_goal_open_never_pv_stops(self):
        self._km_goal(20)
        for minute in (0, 1, 31, 120):
            self.ev._update_need(T0 + timedelta(minutes=minute))
            d = self.decide(minute, 200)
            self.assertTrue(d.on, f"km-Ziel offen: kein PV-Stopp (min {minute})")
            self.assertEqual(d.setpoint["current"], 6)
            self.assertIsNone(self.ev.status_attrs()["pv_stopp_um"])

    def test_km_goal_reached_uses_normal_stop_delay(self):
        self._km_goal(0)
        self.ev._update_need(T0)
        self.decide(0, 200)
        self.assertEqual(self.ev.status_attrs()["pv_stopp_um"], (T0 + timedelta(minutes=30)).isoformat())
        self.assertFalse(self.decide(30, 200).on)

    def test_km_goal_does_not_start_without_surplus_before_forced_start(self):
        self._km_goal(20)
        self.values["switch.charge"] = "off"
        self.ev._update_need(T0)
        self.assertFalse(self.decide(0, 200).on)


if __name__ == "__main__":
    unittest.main()
