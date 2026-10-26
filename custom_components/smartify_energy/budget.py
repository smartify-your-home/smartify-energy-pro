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
