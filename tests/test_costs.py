"""Tests for lanesight.core.costs (route operating cost engine)."""

import pytest

from lanesight.core.costs import (
    DEFAULT_ESTIMATED_TOLLS,
    DEFAULT_FUEL_PRICE_PER_GALLON,
    DEFAULT_OPERATING_COST_PER_MILE,
    CostBreakdown,
    calculate_driver_cost,
    calculate_fuel_cost,
    calculate_fuel_gallons,
    calculate_route_costs,
    calculate_route_costs_for_vehicle,
)
from lanesight.models import Vehicle


def make_vehicle(avg_mpg=6.5):
    return Vehicle(
        vin="1HGCM82633A004352",
        unit_number="UNIT-001",
        make_model="Freightliner Cascadia",
        fuel_type="diesel",
        fuel_capacity_gallons=150.0,
        avg_mpg=avg_mpg,
        max_payload_lbs=38000.0,
        height_feet=13.5,
        gross_weight_lbs=80000.0,
    )


# ---------------------------------------------------------------------- #
# fuel calculations
# ---------------------------------------------------------------------- #
def test_calculate_fuel_gallons():
    assert calculate_fuel_gallons(650.0, 6.5) == pytest.approx(100.0)
    assert calculate_fuel_gallons(410.5, 6.5) == pytest.approx(410.5 / 6.5)


def test_calculate_fuel_cost_default_price():
    assert calculate_fuel_cost(650.0, 6.5) == pytest.approx(425.0)


def test_calculate_fuel_cost_custom_price():
    price = 5.00
    assert calculate_fuel_cost(650.0, 6.5, price) == pytest.approx(
        650.0 / 6.5 * price
    )


# ---------------------------------------------------------------------- #
# driver / operational cost
# ---------------------------------------------------------------------- #
def test_calculate_driver_cost_default_rate():
    assert calculate_driver_cost(650.0) == pytest.approx(422.5)


def test_calculate_driver_cost_custom_rate():
    rate = 0.80
    assert calculate_driver_cost(650.0, rate) == pytest.approx(520.0)


# ---------------------------------------------------------------------- #
# full breakdown
# ---------------------------------------------------------------------- #
def test_calculate_route_costs_breakdown():
    costs = calculate_route_costs(650.0, 6.5)

    assert isinstance(costs, CostBreakdown)
    assert costs.distance_miles == pytest.approx(650.0)
    assert costs.fuel_gallons == pytest.approx(100.0)
    assert costs.fuel_cost == pytest.approx(425.0)
    assert costs.driver_cost == pytest.approx(422.5)
    assert costs.estimated_tolls == DEFAULT_ESTIMATED_TOLLS
    assert costs.total_cost == pytest.approx(425.0 + 422.5)


def test_calculate_route_costs_with_tolls():
    costs = calculate_route_costs(650.0, 6.5, estimated_tolls=88.50)

    assert costs.estimated_tolls == pytest.approx(88.50)
    assert costs.total_cost == pytest.approx(425.0 + 422.5 + 88.50)


def test_calculate_route_costs_custom_rates():
    costs = calculate_route_costs(
        400.0,
        8.0,
        fuel_price_per_gallon=5.10,
        operating_cost_per_mile=0.75,
        estimated_tolls=25.0,
    )

    assert costs.fuel_gallons == pytest.approx(50.0)
    assert costs.fuel_cost == pytest.approx(255.0)
    assert costs.driver_cost == pytest.approx(300.0)
    assert costs.total_cost == pytest.approx(255.0 + 300.0 + 25.0)


def test_calculate_route_costs_defaults_match_constants():
    costs = calculate_route_costs(100.0, 10.0)
    assert costs.fuel_cost == pytest.approx(
        10.0 * DEFAULT_FUEL_PRICE_PER_GALLON
    )
    assert costs.driver_cost == pytest.approx(
        100.0 * DEFAULT_OPERATING_COST_PER_MILE
    )


# ---------------------------------------------------------------------- #
# vehicle wrapper
# ---------------------------------------------------------------------- #
def test_calculate_route_costs_for_vehicle():
    vehicle = make_vehicle(avg_mpg=6.5)
    costs = calculate_route_costs_for_vehicle(650.0, vehicle)

    assert costs.fuel_gallons == pytest.approx(100.0)
    assert costs.fuel_cost == pytest.approx(425.0)
    assert costs.driver_cost == pytest.approx(422.5)
    assert costs.total_cost == pytest.approx(425.0 + 422.5)


def test_calculate_route_costs_for_vehicle_uses_avg_mpg():
    vehicle = make_vehicle(avg_mpg=10.0)
    costs = calculate_route_costs_for_vehicle(1000.0, vehicle)

    assert costs.fuel_gallons == pytest.approx(100.0)
    assert costs.fuel_cost == pytest.approx(425.0)


# ---------------------------------------------------------------------- #
# serialization
# ---------------------------------------------------------------------- #
def test_cost_breakdown_to_dict():
    costs = calculate_route_costs(650.0, 6.5, estimated_tolls=10.0)
    data = costs.to_dict()

    assert data["distance_miles"] == pytest.approx(650.0)
    assert data["fuel_gallons"] == pytest.approx(100.0)
    assert data["fuel_cost"] == pytest.approx(425.0)
    assert data["driver_cost"] == pytest.approx(422.5)
    assert data["estimated_tolls"] == pytest.approx(10.0)
    assert data["total_cost"] == pytest.approx(425.0 + 422.5 + 10.0)
