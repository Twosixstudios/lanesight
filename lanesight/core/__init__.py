"""LaneSight core engine.

Exposes the standalone routing, HOS, cost, and constraint engines for
external imports without pulling in the Streamlit UI.
"""

from lanesight.core.constraints import (
    LOW_CLEARANCE_THRESHOLD_FEET,
    MAX_GROSS_WEIGHT_LBS,
    RouteCompliance,
    evaluate_route_compliance,
)
from lanesight.core.costs import (
    CostBreakdown,
    calculate_route_costs,
    calculate_route_costs_for_vehicle,
)
from lanesight.core.hos import (
    BREAK_DURATION_HOURS,
    BREAK_THRESHOLD_HOURS,
    CYCLE_DAYS,
    CYCLE_LIMIT_HOURS,
    DAILY_DRIVE_LIMIT_HOURS,
    DAILY_DUTY_WINDOW_HOURS,
    SLEEPER_BERTH_FULL_RESET_HOURS,
    SLEEPER_BERTH_SPLIT_MIN_HOURS,
    SLEEPER_BERTH_SPLIT_OFF_DUTY_HOURS,
    calculate_required_breaks,
    calculate_route_hos,
    calculate_sleeper_berth_reset,
)
from lanesight.core.router import Config, GeoPoint, RouteResult, Router

__all__ = [
    "Config",
    "GeoPoint",
    "RouteResult",
    "Router",
    "CostBreakdown",
    "calculate_route_costs",
    "calculate_route_costs_for_vehicle",
    "RouteCompliance",
    "evaluate_route_compliance",
    "LOW_CLEARANCE_THRESHOLD_FEET",
    "MAX_GROSS_WEIGHT_LBS",
    "CYCLE_DAYS",
    "CYCLE_LIMIT_HOURS",
    "calculate_required_breaks",
    "calculate_route_hos",
    "calculate_sleeper_berth_reset",
    "SLEEPER_BERTH_FULL_RESET_HOURS",
    "SLEEPER_BERTH_SPLIT_MIN_HOURS",
    "SLEEPER_BERTH_SPLIT_OFF_DUTY_HOURS",
    "DAILY_DRIVE_LIMIT_HOURS",
    "DAILY_DUTY_WINDOW_HOURS",
    "BREAK_DURATION_HOURS",
    "BREAK_THRESHOLD_HOURS",
]
