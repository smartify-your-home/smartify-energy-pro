"""Simulated priority dispatch for two or more household heaters.

The present NOW AND the mature average must EACH accommodate all earlier
still-unmet heater reservations before a later device gets PV approval.
"""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace as NS

from test_load_budget import LoadDevice, Context

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "smartify_energy"
spec = importlib.util.spec_from_file_location("sep_budget_parallel", ROOT / "budget.py")
math = importlib.util.module_from_spec(spec)
spec.loader.exec_module(math)


class ParallelHeatingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.values = {}

        def get(entity):
            val = self.values.get(entity)
            return (NS(state=val, attributes={"unit_of_measurement": "W"})
                    if val is not None else None)

        self.manager = NS(hass=NS(states=NS(get=get)),
                          hub_mode="auto", async_param_changed=lambda: None)

    def appliance(self, name, state, measured, nominal=2000, heater_done=False):
        self.values[f"switch.{name}"] = "on" if state == "laeuft" else "off"
        self.values[f"sensor.{name}"] = str(measured)
        d = LoadDevice(self.manager, name, name, {
            "switch": f"switch.{name}", "power_sensor": f"sensor.{name}",
        })
        d.params.update(mode="auto", nominal_power=nominal, min_surplus=1500,
                        latest_start="23:59")
        d.state.update(sm=state, approved=state == "laeuft",
                       hp_done=heater_done, hp_active=not heater_done and state == "laeuft")
        return d

    def dispatch(self, devices, current, average):
        ctx = Context(self.now, 30, current, average, average,
                      True, False, average)
        left = ctx.alloc_base
        decisions = []
        reservations = []
        for d in devices:
            decision = d.decide(ctx, left)
            extra = (math.additional_reservation(
                decision.power, d.power_accounted_in_grid(), 0
            ) if decision.on else 0.0)
            reservations.append(extra)
            left -= extra
            decisions.append(decision)
        return decisions, reservations, left

    def test_large_old_average_cannot_hide_low_instantaneous_power(self):
        first = self.appliance("first", "laeuft", 50)
        second = self.appliance("second", "wartet", 0)
        decisions, reservations, _ = self.dispatch([first, second], 3000, 6000)
        self.assertEqual(reservations[0], 1950)
        self.assertFalse(decisions[1].on)
        self.assertIn("aktuell 1050 W", decisions[1].reason)
        self.assertIn("Ø 4050 W", decisions[1].reason)

    def test_high_current_sun_cannot_hide_insufficient_average(self):
        first = self.appliance("first", "laeuft", 50)
        second = self.appliance("second", "wartet", 0)
        decisions, _, _ = self.dispatch([first, second], 6000, 3000)
        self.assertFalse(decisions[1].on)
        self.assertIn("aktuell 4050 W", decisions[1].reason)
        self.assertIn("Ø 1050 W", decisions[1].reason)

    def test_two_heaters_may_overlap_when_both_budgets_are_sufficient(self):
        first = self.appliance("first", "laeuft", 50)
        second = self.appliance("second", "wartet", 0)
        third = self.appliance("third", "wartet", 0)
        decisions, reservations, left = self.dispatch([first, second, third], 4300, 4300)
        self.assertTrue(decisions[0].on)
        self.assertTrue(decisions[1].on)
        self.assertFalse(decisions[2].on)
        self.assertEqual(reservations, [1950, 2000, 0])
        self.assertEqual(left, 350)
        self.assertIn("aktuell 350 W", decisions[2].reason)

    def test_running_heater_already_measured_is_not_reserved_twice(self):
        first = self.appliance("first", "laeuft", 2000)
        second = self.appliance("second", "wartet", 0)
        decisions, reservations, left = self.dispatch([first, second], 2100, 2100)
        self.assertEqual(reservations, [0, 2000])
        self.assertTrue(decisions[1].on)
        self.assertEqual(left, 100)

    def test_completed_heater_releases_only_unmet_reservation(self):
        first = self.appliance("first", "laeuft", 50, heater_done=True)
        second = self.appliance("second", "wartet", 0)
        # Default full reserve blocks a later 2 kW device.
        decisions, reservations, _ = self.dispatch([first, second], 2500, 2500)
        self.assertEqual(reservations[0], 1950)
        self.assertFalse(decisions[1].on)
        # Explicit 0 % restores the previous release-on-heating-pause behavior.
        first.params["pause_reservation_pct"] = 0
        decisions, reservations, _ = self.dispatch([first, second], 2500, 2500)
        self.assertEqual(reservations[0], 0)
        self.assertTrue(decisions[1].on)
        # 50 % retains 1 kW, of which the 50 W meter already accounts for.
        first.params["pause_reservation_pct"] = 50
        decisions, reservations, _ = self.dispatch([first, second], 2500, 2500)
        self.assertEqual(reservations[0], 950)
        self.assertFalse(decisions[1].on)

    def test_two_2000w_heaters_at_3500w_are_not_both_approved(self):
        first = self.appliance("first", "laeuft", 100)
        second = self.appliance("second", "wartet", 0)
        decisions, reservations, _ = self.dispatch([first, second], 3500, 3500)
        self.assertEqual(reservations[0], 1900)
        self.assertFalse(decisions[1].on)

    def test_pre_start_headroom_reclaims_only_own_metered_load(self):
        second = self.appliance("second", "erkannt", 1000)
        self.values["switch.second"] = "on"
        ctx = Context(self.now, 30, 1300, 2300, 2300,
                      True, False, 2300)
        current, average, upstream = second._pv_start_headroom(ctx, 2300, True)
        self.assertEqual((current, average, upstream), (2300, 2300, 0))
        self.assertTrue(second.decide(ctx, 2300).on)


if __name__ == "__main__":
    unittest.main()
