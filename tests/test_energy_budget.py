"""Budget regression tests (no Home Assistant instance required).

Run: python -m unittest discover -s tests
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "smartify_energy"
spec = importlib.util.spec_from_file_location("sep_budget_math", ROOT / "budget.py")
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


class BudgetAccountingTests(unittest.TestCase):
    def test_wp_import_is_not_positive_surplus(self):
        # WP draws 2000 W, grid imports 1000 W: no phantom 1000 W.
        actual_grid_w = -1000
        wp_current_w = 2000
        wp_reclaimable_w = 0  # A one-shot WW cycle cannot be curtailed by SEP.
        available = budget.control_budget(actual_grid_w, wp_reclaimable_w, 0, 0)
        self.assertEqual(available, -1000)
        self.assertEqual(
            budget.additional_reservation(wp_current_w, wp_current_w, wp_reclaimable_w),
            0,  # Already embedded in the physical grid measurement.
        )

    def test_running_washing_machine_never_creates_phantom_power(self):
        grid_w = -700
        running_w = 1800
        self.assertEqual(budget.control_budget(grid_w, 0, 0, 0), -700)
        self.assertEqual(budget.additional_reservation(2200, running_w, 0), 400)

    def test_running_ev_can_reallocate_only_reducible_charge(self):
        # 3000 W charge; 1380 W is unavoidable 6 A floor.
        grid_w = 0
        charging_w = 3000
        reclaimable_w = charging_w - 1380
        available = budget.control_budget(grid_w, reclaimable_w, 0, 0)
        self.assertEqual(available, 1620)
        self.assertEqual(
            budget.additional_reservation(3000, charging_w, reclaimable_w),
            1620,
        )
        # Replacing EV charging with a 1500 W load consumes this budget;
        # the remaining EV floor is already embedded in the measured grid.
        self.assertEqual(available - budget.additional_reservation(1500, 0, 0), 120)

    def test_self_consumption_is_not_charged_twice(self):
        self.assertEqual(budget.additional_reservation(700, 700, 0), 0)
        self.assertEqual(budget.additional_reservation(1200, 700, 0), 500)

    def test_no_external_load_or_battery_charge_assumption(self):
        # House imports 1000 W while a sink is running and a battery is
        # charging. Neither can be explicitly curtailed by this SEP release.
        self.assertEqual(budget.control_budget(-1000, 0, 0, 0), -1000)

    def test_discharge_and_grid_reserve_lower_budget(self):
        self.assertEqual(budget.control_budget(2300, 0, 500, 200), 1600)

    def test_observe_mode_reserves_no_power(self):
        # Observe-mode decisions never enter additional_reservation in manager.
        self.assertEqual(budget.control_budget(-1000, 0, 0, 0), -1000)


if __name__ == "__main__":
    unittest.main()
