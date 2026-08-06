"""Tests for lanesight.core.hos (DOT / FMCSA HOS engine)."""

import pytest

from lanesight.core.hos import (
    BREAK_DURATION_HOURS,
    BREAK_THRESHOLD_HOURS,
    CYCLE_LIMIT_HOURS,
    DAILY_DRIVE_LIMIT_HOURS,
    DAILY_DUTY_WINDOW_HOURS,
    calculate_required_breaks,
    calculate_route_hos,
)
from lanesight.models import Driver


def make_driver(
    drive=DAILY_DRIVE_LIMIT_HOURS,
    shift=DAILY_DUTY_WINDOW_HOURS,
    cycle=CYCLE_LIMIT_HOURS,
):
    return Driver(
        name="Test Driver",
        cdl_number="DL000001",
        cdl_state="CA",
        is_active=True,
        drive_hours_remaining=drive,
        shift_hours_remaining=shift,
        cycle_hours_remaining=cycle,
    )


# ---------------------------------------------------------------------- #
# required breaks
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "drive_hours,expected",
    [
        (0.0, 0),
        (5.0, 0),
        (7.99, 0),
        (8.0, 1),
        (8.5, 1),
        (15.99, 1),
        (16.0, 2),
        (16.5, 2),
    ],
)
def test_calculate_required_breaks(drive_hours, expected):
    assert calculate_required_breaks(drive_hours) == expected


# ---------------------------------------------------------------------- #
# compliant runs
# ---------------------------------------------------------------------- #
def test_compliant_run_without_breaks():
    driver = make_driver(drive=11.0, shift=14.0, cycle=70.0)
    result = calculate_route_hos(7.4, driver)

    assert result["is_legal"] is True
    assert result["required_breaks"] == 0
    assert result["total_elapsed_hours"] == pytest.approx(7.4)
    assert result["updated_driver_clocks"]["drive_hours_remaining"] == pytest.approx(3.6)
    assert result["updated_driver_clocks"]["shift_hours_remaining"] == pytest.approx(6.6)
    assert result["updated_driver_clocks"]["cycle_hours_remaining"] == pytest.approx(62.6)


def test_compliant_run_at_full_11_hour_limit():
    driver = make_driver(drive=11.0, shift=14.0, cycle=70.0)
    result = calculate_route_hos(11.0, driver)

    assert result["is_legal"] is True
    assert result["required_breaks"] == 1
    assert result["total_elapsed_hours"] == pytest.approx(11.5)
    assert result["updated_driver_clocks"]["drive_hours_remaining"] == pytest.approx(0.0)
    assert result["updated_driver_clocks"]["shift_hours_remaining"] == pytest.approx(2.5)


# ---------------------------------------------------------------------- #
# runs requiring 30-minute rest breaks
# ---------------------------------------------------------------------- #
def test_route_requiring_single_break():
    driver = make_driver()
    result = calculate_route_hos(BREAK_THRESHOLD_HOURS + 0.5, driver)

    assert result["is_legal"] is True
    assert result["required_breaks"] == 1
    assert result["total_elapsed_hours"] == pytest.approx(
        BREAK_THRESHOLD_HOURS + 0.5 + BREAK_DURATION_HOURS
    )
    assert result["updated_driver_clocks"]["shift_hours_remaining"] == pytest.approx(
        14.0 - (BREAK_THRESHOLD_HOURS + 1.0)
    )
    assert result["updated_driver_clocks"]["cycle_hours_remaining"] == pytest.approx(
        70.0 - 8.5
    )


def test_route_requiring_two_breaks_is_out_of_service():
    driver = make_driver()
    result = calculate_route_hos(16.5, driver)

    assert result["required_breaks"] == 2
    assert result["total_elapsed_hours"] == pytest.approx(17.5)
    assert result["is_legal"] is False
    assert result["updated_driver_clocks"]["drive_hours_remaining"] == pytest.approx(
        11.0 - 16.5
    )


# ---------------------------------------------------------------------- #
# out-of-service violations
# ---------------------------------------------------------------------- #
def test_violation_daily_drive_limit():
    driver = make_driver(drive=5.0, shift=14.0, cycle=70.0)
    result = calculate_route_hos(7.4, driver)

    assert result["is_legal"] is False
    assert result["required_breaks"] == 0


def test_violation_14_hour_duty_window():
    driver = make_driver(drive=11.0, shift=8.0, cycle=70.0)
    result = calculate_route_hos(9.0, driver)

    assert result["is_legal"] is False
    assert result["required_breaks"] == 1
    assert result["total_elapsed_hours"] == pytest.approx(9.5)


def test_violation_70_hour_cycle_limit():
    driver = make_driver(drive=11.0, shift=14.0, cycle=6.0)
    result = calculate_route_hos(6.5, driver)

    assert result["is_legal"] is False
    assert result["required_breaks"] == 0
    assert result["updated_driver_clocks"]["cycle_hours_remaining"] == pytest.approx(-0.5)
