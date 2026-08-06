"""LaneSight route operating cost engine.

Computes fuel consumption and driver/operating costs for a route using a
vehicle's fuel economy (MPG) and configurable per-mile operating rates.
"""

from dataclasses import asdict, dataclass

from lanesight.models import Vehicle

DEFAULT_FUEL_PRICE_PER_GALLON = 4.25
DEFAULT_OPERATING_COST_PER_MILE = 0.65
DEFAULT_ESTIMATED_TOLLS = 0.0


@dataclass
class CostBreakdown:
    """Estimated operating costs for a route (JSON-serializable)."""

    distance_miles: float
    fuel_gallons: float
    fuel_cost: float
    driver_cost: float
    estimated_tolls: float
    total_cost: float

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-friendly)."""
        return asdict(self)


def calculate_fuel_gallons(distance_miles: float, avg_mpg: float) -> float:
    """Gallons of fuel consumed over a route at a given average MPG."""
    return distance_miles / avg_mpg


def calculate_fuel_cost(
    distance_miles: float,
    avg_mpg: float,
    fuel_price_per_gallon: float = DEFAULT_FUEL_PRICE_PER_GALLON,
) -> float:
    """Total fuel spend for a route."""
    return calculate_fuel_gallons(distance_miles, avg_mpg) * fuel_price_per_gallon


def calculate_driver_cost(
    distance_miles: float,
    operating_cost_per_mile: float = DEFAULT_OPERATING_COST_PER_MILE,
) -> float:
    """Driver pay / operational cost for a route."""
    return distance_miles * operating_cost_per_mile


def calculate_route_costs(
    distance_miles: float,
    avg_mpg: float,
    fuel_price_per_gallon: float = DEFAULT_FUEL_PRICE_PER_GALLON,
    operating_cost_per_mile: float = DEFAULT_OPERATING_COST_PER_MILE,
    estimated_tolls: float = DEFAULT_ESTIMATED_TOLLS,
) -> CostBreakdown:
    """Compute a full :class:`CostBreakdown` for a route.

    Args:
        distance_miles: Route length in miles.
        avg_mpg: Vehicle average miles-per-gallon.
        fuel_price_per_gallon: Price per gallon of fuel.
        operating_cost_per_mile: Driver/operational rate per mile.
        estimated_tolls: Estimated toll charges for the route.

    Returns:
        A :class:`CostBreakdown` with fuel, driver, toll, and total costs.
    """
    fuel_gallons = calculate_fuel_gallons(distance_miles, avg_mpg)
    fuel_cost = fuel_gallons * fuel_price_per_gallon
    driver_cost = calculate_driver_cost(distance_miles, operating_cost_per_mile)
    total_cost = fuel_cost + driver_cost + estimated_tolls
    return CostBreakdown(
        distance_miles=distance_miles,
        fuel_gallons=fuel_gallons,
        fuel_cost=fuel_cost,
        driver_cost=driver_cost,
        estimated_tolls=estimated_tolls,
        total_cost=total_cost,
    )


def calculate_route_costs_for_vehicle(
    distance_miles: float,
    vehicle: Vehicle,
    fuel_price_per_gallon: float = DEFAULT_FUEL_PRICE_PER_GALLON,
    operating_cost_per_mile: float = DEFAULT_OPERATING_COST_PER_MILE,
    estimated_tolls: float = DEFAULT_ESTIMATED_TOLLS,
) -> CostBreakdown:
    """Route economics driven by a :class:`Vehicle`'s ``avg_mpg``.

    Wrapper around :func:`calculate_route_costs` that reads fuel economy
    directly from a :class:`lanesight.models.Vehicle`.
    """
    return calculate_route_costs(
        distance_miles=distance_miles,
        avg_mpg=vehicle.avg_mpg,
        fuel_price_per_gallon=fuel_price_per_gallon,
        operating_cost_per_mile=operating_cost_per_mile,
        estimated_tolls=estimated_tolls,
    )
