"""Conservative power accounting for SEP.

Positive grid power means export, negative means import. Only power that SEP
can actually reduce may be reclaimed for another consumer.
"""


def control_budget(grid_export_w: float, reclaimable_w: float,
                   battery_discharge_w: float, reserve_w: float) -> float:
    """Power available for allocation, without crediting fixed or external loads."""
    return grid_export_w + max(0.0, reclaimable_w) - max(0.0, battery_discharge_w) - reserve_w


def additional_reservation(decision_w: float, current_w: float,
                           reclaimable_w: float) -> float:
    """Charge only new demand against the budget.

    Existing non-reclaimable consumption is already included in the grid
    measurement; reclaimable consumption was explicitly credited above.
    """
    embedded_w = max(0.0, current_w - min(current_w, max(0.0, reclaimable_w)))
    return max(0.0, decision_w - embedded_w)


def pv_start_remaining(
    budget_now_w: float,
    budget_avg_w: float,
    allocation_base_w: float,
    left_w: float,
    own_metered_w: float = 0.0,
) -> tuple[float, float, float]:
    """Compute independent instantaneous and averaged headroom for a PV start.

    left_w already reflects the additional reservations of all previous
    devices in this dispatch cycle. Their metered consumption is ALREADY part
    of both grid balances, so only their unmet heater demand is reserved.

    Own metered power can be credited to the instantaneous start check of an
    already-detected appliance, never to another device or to the historic
    ten-minute average. This prevents two 2000 W heaters from being approved
    based on an old average when the current PV power has dropped.
    """
    previous_reservations = max(0.0, allocation_base_w - left_w)
    now_left = budget_now_w - previous_reservations + max(0.0, own_metered_w)
    avg_left = budget_avg_w - previous_reservations
    return now_left, avg_left, previous_reservations


def battery_priority_credit(charge_w: float, battery_rank: int, device_rank: int) -> float:
    """Self-regulating battery's measured charge is reclaimable only upstream.

    It is already embedded in net export. Return this extra headroom exactly
    once when a higher-priority device is being evaluated.
    """
    if device_rank >= battery_rank:
        return 0.0
    return max(0.0, charge_w)
