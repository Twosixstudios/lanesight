"""Tests for lanesight.core.constraints (route compliance engine)."""

import pytest

from lanesight.core.constraints import (
    LOW_CLEARANCE_THRESHOLD_FEET,
    MAX_GROSS_WEIGHT_LBS,
    RouteCompliance,
    evaluate_route_compliance,
)
from lanesight.models import Vehicle


def make_vehicle(height_feet=13.5, gross_weight_lbs=80000.0):
    return Vehicle(
        vin="1HGCM82633A004352",
        unit_number="UNIT-001",
        make_model="Freightliner Cascadia",
        fuel_type="diesel",
        fuel_capacity_gallons=150.0,
        avg_mpg=6.5,
        max_payload_lbs=38000.0,
        height_feet=height_feet,
        gross_weight_lbs=gross_weight_lbs,
    )


# ---------------------------------------------------------------------- #
# height compliance
# ---------------------------------------------------------------------- #
def test_height_within_limit_is_compliant():
    compliance = evaluate_route_compliance(
        make_vehicle(height_feet=LOW_CLEARANCE_THRESHOLD_FEET - 1.0)
    )

    assert compliance.is_compliant is True
    assert compliance.warnings == []
    assert compliance.violations == []


def test_height_at_threshold_is_compliant():
    compliance = evaluate_route_compliance(
        make_vehicle(height_feet=LOW_CLEARANCE_THRESHOLD_FEET)
    )

    assert compliance.is_compliant is True
    assert compliance.violations == []


def test_height_over_threshold_warns():
    compliance = evaluate_route_compliance(
        make_vehicle(height_feet=LOW_CLEARANCE_THRESHOLD_FEET + 1.0)
    )

    assert compliance.is_compliant is False
    assert any("height" in message.lower() for message in compliance.violations)


# ---------------------------------------------------------------------- #
# gross weight compliance
# ---------------------------------------------------------------------- #
def test_weight_within_limit_is_compliant():
    compliance = evaluate_route_compliance(
        make_vehicle(gross_weight_lbs=MAX_GROSS_WEIGHT_LBS - 1000.0)
    )

    assert compliance.is_compliant is True
    assert compliance.violations == []


def test_weight_at_limit_is_compliant():
    compliance = evaluate_route_compliance(
        make_vehicle(gross_weight_lbs=MAX_GROSS_WEIGHT_LBS)
    )

    assert compliance.is_compliant is True


def test_weight_over_limit_warns():
    compliance = evaluate_route_compliance(
        make_vehicle(gross_weight_lbs=MAX_GROSS_WEIGHT_LBS + 1000.0)
    )

    assert compliance.is_compliant is False
    assert any("weight" in message.lower() for message in compliance.violations)


# ---------------------------------------------------------------------- #
# hazmat compliance
# ---------------------------------------------------------------------- #
def test_hazmat_produces_warning_but_remains_compliant():
    compliance = evaluate_route_compliance(make_vehicle(), is_hazmat=True)

    assert compliance.is_compliant is True
    assert compliance.violations == []
    assert any("hazmat" in message.lower() for message in compliance.warnings)


def test_non_hazmat_has_no_hazmat_warning():
    compliance = evaluate_route_compliance(make_vehicle(), is_hazmat=False)

    assert compliance.warnings == []


# ---------------------------------------------------------------------- #
# combined & custom limits
# ---------------------------------------------------------------------- #
def test_over_height_and_weight_yields_multiple_violations():
    compliance = evaluate_route_compliance(
        make_vehicle(
            height_feet=LOW_CLEARANCE_THRESHOLD_FEET + 2.0,
            gross_weight_lbs=MAX_GROSS_WEIGHT_LBS + 5000.0,
        )
    )

    assert compliance.is_compliant is False
    assert len(compliance.violations) == 2


def test_custom_thresholds_relax_compliance():
    compliance = evaluate_route_compliance(
        make_vehicle(height_feet=14.0, gross_weight_lbs=85000.0),
        low_clearance_threshold_feet=14.5,
        max_gross_weight_lbs=90000.0,
    )

    assert compliance.is_compliant is True
    assert compliance.violations == []


# ---------------------------------------------------------------------- #
# serialization
# ---------------------------------------------------------------------- #
def test_route_compliance_to_dict():
    compliance = evaluate_route_compliance(make_vehicle(height_feet=14.0))
    data = compliance.to_dict()

    assert data["is_compliant"] is False
    assert isinstance(data["warnings"], list)
    assert isinstance(data["violations"], list)
    assert data["violations"]


def test_route_compliance_is_dataclass():
    compliance = evaluate_route_compliance(make_vehicle())
    assert isinstance(compliance, RouteCompliance)
