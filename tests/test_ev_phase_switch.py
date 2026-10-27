"""Configurable 1/3-phase switch hysteresis and minimum interval."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

from test_ev_budget import EvDevice


class PhaseSwitchTests(unittest.TestCase):
    def setUp(self):
        self.values = {"select.phase": "3"}

        def get(entity):
            val = self.values.get(entity)
            return NS(state=val, attributes={}) if val is not None else None

        manager = NS(hass=NS(states=NS(get=get)), hub_mode="auto", async_param_changed=lambda: None)
        self.ev = EvDevice(manager, "ev", "Wallbox", {
            "control_entity": "switch.charge", "current_entity": "number.current",
            "min_current": 6, "max_current": 16, "phases": 3, "voltage": 230,
            "phase_entity": "select.phase", "phase_1": "1", "phase_3": "3",
        })
        self.ev.params.update(mode="auto", phase_mode="auto")
        self.now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)

    def phases(self, avail, minutes=0):
        return self.ev._phases_for(avail, NS(now=self.now + timedelta(minutes=minutes)))

    def test_defaults(self):
        self.assertEqual(self.ev.p("phase_switch_minutes"), 20)
        self.assertEqual(self.ev.p("phase_hysteresis"), 500)

    def test_hysteresis_on_three_phase(self):
        # p3 = 6 A * 230 V * 3 = 4140 W → stay on 3 phases down to 3640 W
        self.assertEqual(self.phases(3700), 3)
        self.assertEqual(self.phases(3600), 1)

    def test_hysteresis_on_single_phase(self):
        self.values["select.phase"] = "1"
        self.assertEqual(self.phases(4600), 1)
        self.assertEqual(self.phases(4700), 3)

    def test_minimum_interval(self):
        self.ev.state["phase_switch"] = self.now.timestamp()
        self.assertEqual(self.phases(1000, minutes=19), 3)
        self.assertEqual(self.phases(1000, minutes=21), 1)
        self.ev.params["phase_switch_minutes"] = 30
        self.assertEqual(self.phases(1000, minutes=21), 3)


if __name__ == "__main__":
    unittest.main()
