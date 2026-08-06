"""DOT / FMCSA Hours of Service (HOS) regulatory engine for LaneSight.

Implements the core HOS rules:
- 11-hour daily driving limit
- 14-hour daily duty window
- Mandatory 30-minute rest break after 8 cumulative hours of driving
- 70-hour / 8-day cycle limit
"""

from lanesight.models import Driver

DAILY_DRIVE_LIMIT_HOURS = 11.0
DAILY_DUTY_WINDOW_HOURS = 14.0
BREAK_THRESHOLD_HOURS = 8.0
BREAK_DURATION_HOURS = 0.5
CYCLE_LIMIT_HOURS = 70.0
CYCLE_DAYS = 8


def calculate_required_breaks(drive_hours: float) -> int:
    """Number of mandatory 30-minute rest breaks for a given driving time."""
    if drive_hours <= 0:
        return 0
    return int(drive_hours // BREAK_THRESHOLD_HOURS)


def calculate_route_hos(route_duration_hours: float, driver: Driver) -> dict:
    """Evaluate whether a route fits within a driver's remaining HOS clocks.

    Args:
        route_duration_hours: Estimated driving time for the trip.
        driver: The Driver whose remaining drive, shift, and cycle hours
            are checked against the route.

    Returns:
        dict with:
            is_legal: True if the trip fits the driver's available hours.
            required_breaks: Number of mandatory 30-minute rest breaks.
            total_elapsed_hours: Driving time plus mandatory break durations.
            updated_driver_clocks: Remaining drive, shift, and cycle hours
                after the trip.
    """
    required_breaks = calculate_required_breaks(route_duration_hours)
    total_elapsed_hours = route_duration_hours + required_breaks * BREAK_DURATION_HOURS

    is_legal = (
        route_duration_hours <= driver.drive_hours_remaining
        and total_elapsed_hours <= driver.shift_hours_remaining
        and route_duration_hours <= driver.cycle_hours_remaining
    )

    updated_driver_clocks = {
        "drive_hours_remaining": driver.drive_hours_remaining - route_duration_hours,
        "shift_hours_remaining": driver.shift_hours_remaining - total_elapsed_hours,
        "cycle_hours_remaining": driver.cycle_hours_remaining - route_duration_hours,
    }

    return {
        "is_legal": is_legal,
        "required_breaks": required_breaks,
        "total_elapsed_hours": total_elapsed_hours,
        "updated_driver_clocks": updated_driver_clocks,
    }
