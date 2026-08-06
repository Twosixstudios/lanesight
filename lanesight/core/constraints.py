"""LaneSight commercial route compliance engine.

Evaluates a vehicle/route combination against common commercial-vehicle
constraints (low clearance, gross weight, hazmat) and reports warnings or
violations to the dispatcher before a load is released.
"""

from dataclasses import asdict, dataclass

from lanesight.models import Vehicle

LOW_CLEARANCE_THRESHOLD_FEET = 13.5
MAX_GROSS_WEIGHT_LBS = 80000


@dataclass
class RouteCompliance:
    """Result of a route/vehicle compliance evaluation (JSON-serializable).

    Attributes:
        is_compliant: True when no hard violations were found.
        warnings: Advisory messages that do not block dispatch
            (e.g. hazmat handling notes).
        violations: Blocking messages that make the route non-compliant
            (e.g. over-height or over-gross-weight loads).
    """

    is_compliant: bool
    warnings: list
    violations: list

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-friendly)."""
        return asdict(self)


def evaluate_route_compliance(
    vehicle: Vehicle,
    is_hazmat: bool = False,
    low_clearance_threshold_feet: float = LOW_CLEARANCE_THRESHOLD_FEET,
    max_gross_weight_lbs: float = MAX_GROSS_WEIGHT_LBS,
) -> RouteCompliance:
    """Evaluate a :class:`Vehicle` against route constraint limits.

    Args:
        vehicle: The truck being dispatched.
        is_hazmat: True if the load is hazmat (triggers an advisory warning).
        low_clearance_threshold_feet: Max vehicle height in feet before the
            route is flagged for low-clearance/overpass concerns.
        max_gross_weight_lbs: Max gross vehicle weight before the route is
            flagged against bridge/road limits.

    Returns:
        A :class:`RouteCompliance` describing whether the route can be
        dispatched, plus any warnings or blocking violations.
    """
    warnings: list[str] = []
    violations: list[str] = []

    if vehicle.height_feet > low_clearance_threshold_feet:
        violations.append(
            f"Vehicle height {vehicle.height_feet} ft exceeds "
            f"low-clearance threshold {low_clearance_threshold_feet} ft"
        )

    if vehicle.gross_weight_lbs > max_gross_weight_lbs:
        violations.append(
            f"Gross weight {vehicle.gross_weight_lbs} lbs exceeds "
            f"bridge/road limit {max_gross_weight_lbs} lbs"
        )

    if is_hazmat:
        warnings.append(
            "Hazmat load requires placarding, permits, and "
            "hazmat-approved routing"
        )

    return RouteCompliance(
        is_compliant=not violations,
        warnings=warnings,
        violations=violations,
    )
