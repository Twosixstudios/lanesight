"""Tests for lanesight.core.hos (DOT / FMCSA HOS engine)."""

import pytest

from lanesight.core.hos import (
    BREAK_DURATION_HOURS,
    BREAK_THRESHOLD_HOURS,
    CYCLE_LIMIT_HOURS,
    DAILY_DRIVE_LIMIT_HOURS,
    DAILY_DUTY_WINDOW_HOURS,
    SLEEPER_BERTH_FULL_RESET_HOURS,
    SLEEPER_BERTH_SPLIT_OFF_DUTY_HOURS,
    SLEEPER_BERTH_SPLIT_MIN_HOURS,
    calculate_required_breaks,
    calculate_route_hos,
    calculate_sleeper_berth_reset,
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


# ---------------------------------------------------------------------- #
# 30-minute break trigger edge cases
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "drive_hours,expected_breaks",
    [
        (BREAK_THRESHOLD_HOURS, 1),
        (BREAK_THRESHOLD_HOURS - 0.001, 0),
        (BREAK_THRESHOLD_HOURS + 0.001, 1),
        (BREAK_THRESHOLD_HOURS * 2, 2),
        (BREAK_THRESHOLD_HOURS * 2 - 0.001, 1),
        (BREAK_THRESHOLD_HOURS * 2 + 0.001, 2),
    ],
)
def test_break_trigger_boundaries(drive_hours, expected_breaks):
    assert calculate_required_breaks(drive_hours) == expected_breaks


@pytest.mark.parametrize(
    "drive_hours,expected_elapsed",
    [
        (7.9, 7.9),
        (8.0, 8.5),
        (8.1, 8.6),
        (16.0, 17.0),
        (16.1, 17.1),
    ],
)
def test_total_elapsed_hours_includes_breaks(drive_hours, expected_elapsed):
    driver = make_driver(drive=DAILY_DRIVE_LIMIT_HOURS + 10, shift=40, cycle=40)
    result = calculate_route_hos(drive_hours, driver)
    assert result["total_elapsed_hours"] == pytest.approx(expected_elapsed)
    assert result["required_breaks"] == calculate_required_breaks(drive_hours)


def test_break_trigger_exactly_at_threshold_elapsed():
    driver = make_driver(drive=11.0, shift=14.0, cycle=70.0)
    result = calculate_route_hos(BREAK_THRESHOLD_HOURS, driver)

    assert result["required_breaks"] == 1
    assert result["total_elapsed_hours"] == pytest.approx(8.5)
    assert result["is_legal"] is True
    assert result["updated_driver_clocks"]["drive_hours_remaining"] == pytest.approx(3.0)
    assert result["updated_driver_clocks"]["shift_hours_remaining"] == pytest.approx(5.5)


# ---------------------------------------------------------------------- #
# 10-hour sleeper berth reset
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "sleeper_hours,off_duty_hours,expected",
    [
        (10.0, 0.0, True),
        (10.5, 0.0, True),
        (9.0, 1.0, False),
        (SLEEPER_BERTH_SPLIT_MIN_HOURS, SLEEPER_BERTH_SPLIT_OFF_DUTY_HOURS, True),
        (7.0, 2.5, True),
        (7.5, 2.0, True),
        (6.9, 2.0, False),
        (7.0, 1.9, False),
        (6.9, 1.9, False),
        (0.0, 0.0, False),
    ],
)
def test_sleeper_berth_reset_qualification(sleeper_hours, off_duty_hours, expected):
    assert (
        calculate_sleeper_berth_reset(sleeper_hours, off_duty_hours) == expected
    )


def test_full_ten_hour_sleeper_berth_reset_qualifies():
    assert (
        calculate_sleeper_berth_reset(
            SLEEPER_BERTH_FULL_RESET_HOURS, 0.0
        )
        is True
    )


def test_sleeper_berth_split_requires_both_segments():
    assert (
        calculate_sleeper_berth_reset(
            SLEEPER_BERTH_SPLIT_MIN_HOURS, 0.0
        )
        is False
    )
    assert (
        calculate_sleeper_berth_reset(
            0.0, SLEEPER_BERTH_SPLIT_OFF_DUTY_HOURS
        )
        is False
    )


def test_sleeper_berth_reset_after_full_rest_extends_clocks():
    exhausted = make_driver(drive=8.0, shift=5.0, cycle=60.0)
    before = calculate_route_hos(6.0, exhausted)
    assert before["is_legal"] is False  # 6h drive exceeds remaining 5h shift window

    assert calculate_sleeper_berth_reset(10.0, 0.0) is True

    refreshed = make_driver(drive=11.0, shift=14.0, cycle=60.0)
    after = calculate_route_hos(6.0, refreshed)
    assert after["is_legal"] is True
    assert after["required_breaks"] == 0
