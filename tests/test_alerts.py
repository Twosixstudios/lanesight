"""Tests for lanesight.core.alerts route deviation monitoring."""

from datetime import datetime

import pytest

from lanesight.core.alerts import (
    ALERT_TYPE_ROUTE_DEVIATION,
    DEVIATION_ALERT_THRESHOLD,
    Alert,
    DeviationMonitor,
)
from lanesight.core.telemetry import TelemetrySession

M_PER_DEG_LAT = 110574.0  # meters per degree of latitude at the equator

# A straight 2,200m route running west-to-east along the equator.
ORIGIN = (0.0, 0.0)
MID = (0.0, 0.01)
DEST = (0.0, 0.02)
POLYLINE = [[ORIGIN[0], ORIGIN[1]], [MID[0], MID[1]], [DEST[0], DEST[1]]]

T0 = datetime(2026, 8, 13, 12, 0, 0)


def _offset_lat(meters):
    """Latitude shift (degrees) equal to ``meters`` of northward drift."""
    return meters / M_PER_DEG_LAT


def _off_route_coords(meters=100.0):
    """A GPS position clearly beyond the 50m drift tolerance."""
    return _offset_lat(meters), MID[1]


def _on_route_coords():
    return MID[0], MID[1]


# ---------------------------------------------------------------------- #
# DeviationMonitor - standalone behaviour
# ---------------------------------------------------------------------- #
def test_monitor_stays_silent_while_on_route():
    monitor = DeviationMonitor()
    for _ in range(10):
        alert = monitor.update(
            on_route=True, distance_off_route_meters=0.0, timestamp=T0
        )
        assert alert is None
    assert monitor.alerts == []
    assert monitor.consecutive_off_route == 0


def test_monitor_ignores_single_sample_gps_jitter():
    monitor = DeviationMonitor()
    # One blip off-route, then immediately back on-route.
    assert monitor.update(
        on_route=False, distance_off_route_meters=80.0, timestamp=T0
    ) is None
    assert monitor.update(
        on_route=True, distance_off_route_meters=0.0, timestamp=T0
    ) is None
    assert monitor.alerts == []
    assert monitor.consecutive_off_route == 0


def test_monitor_does_not_alert_at_exactly_threshold():
    monitor = DeviationMonitor(threshold=DEVIATION_ALERT_THRESHOLD)
    for _ in range(DEVIATION_ALERT_THRESHOLD):
        assert monitor.update(
            on_route=False, distance_off_route_meters=100.0, timestamp=T0
        ) is None
    assert monitor.alerts == []
    assert monitor.consecutive_off_route == DEVIATION_ALERT_THRESHOLD


def test_monitor_fires_alert_after_threshold_exceeded():
    monitor = DeviationMonitor(threshold=DEVIATION_ALERT_THRESHOLD)
    ts = T0
    alert = None
    for _ in range(DEVIATION_ALERT_THRESHOLD + 2):
        alert = monitor.update(
            on_route=False,
            distance_off_route_meters=120.0,
            timestamp=ts,
            matched_coords=(0.0, 0.01),
        )
        if alert is not None:
            break
    assert alert is not None
    assert isinstance(alert, Alert)
    assert alert.alert_type == ALERT_TYPE_ROUTE_DEVIATION
    assert alert.timestamp == ts
    assert alert.distance_off_route_meters == pytest.approx(120.0, rel=0.05)
    assert alert.consecutive_off_route_samples == DEVIATION_ALERT_THRESHOLD + 1
    assert alert.matched_coords == (0.0, 0.01)


def test_monitor_fires_once_until_vehicle_returns_on_route():
    monitor = DeviationMonitor(threshold=3)
    for _ in range(6):
        monitor.update(
            on_route=False, distance_off_route_meters=100.0, timestamp=T0
        )
    assert len(monitor.alerts) == 1  # not re-raised every subsequent sample

    monitor.update(on_route=True, distance_off_route_meters=0.0, timestamp=T0)
    for _ in range(4):
        monitor.update(
            on_route=False, distance_off_route_meters=100.0, timestamp=T0
        )
    assert len(monitor.alerts) == 2  # a new deviation re-arms the monitor


def test_monitor_invalid_threshold_raises():
    with pytest.raises(ValueError, match="threshold"):
        DeviationMonitor(threshold=0)


def test_alert_to_dict_contract():
    alert = Alert(
        alert_type=ALERT_TYPE_ROUTE_DEVIATION,
        timestamp=T0,
        distance_off_route_meters=100.0,
        consecutive_off_route_samples=4,
        matched_coords=(0.0, 0.01),
    )
    payload = alert.to_dict()
    assert set(payload) == {
        "alert_type",
        "timestamp",
        "distance_off_route_meters",
        "consecutive_off_route_samples",
        "matched_coords",
    }
    assert payload["alert_type"] == ALERT_TYPE_ROUTE_DEVIATION


# ---------------------------------------------------------------------- #
# TelemetrySession + DeviationMonitor integration
# ---------------------------------------------------------------------- #
def test_session_with_monitor_no_alerts_on_route_stream():
    monitor = DeviationMonitor()
    session = TelemetrySession(POLYLINE, monitor=monitor)
    for index in range(5):
        session.ingest(*_on_route_coords())
    assert monitor.alerts == []
    assert len(session.points) == 5


def test_session_fires_alert_on_sustained_off_route_stream():
    monitor = DeviationMonitor()
    session = TelemetrySession(POLYLINE, monitor=monitor)
    for index in range(DEVIATION_ALERT_THRESHOLD):
        session.ingest(*_off_route_coords())
    assert monitor.alerts == []

    session.ingest(*_off_route_coords())
    assert len(monitor.alerts) == 1
    alert = monitor.alerts[0]
    assert alert.alert_type == ALERT_TYPE_ROUTE_DEVIATION
    assert alert.consecutive_off_route_samples == DEVIATION_ALERT_THRESHOLD + 1
    assert alert.distance_off_route_meters > 50.0
    # Timestamp matches the sample that crossed the threshold.
    assert alert.timestamp == session.points[-1].timestamp


def test_session_no_alert_when_monitor_absent():
    session = TelemetrySession(POLYLINE)
    for _ in range(5):
        session.ingest(*_off_route_coords())
    assert session.monitor is None


def test_session_returns_to_route_and_deviation_again():
    monitor = DeviationMonitor()
    session = TelemetrySession(POLYLINE, monitor=monitor)
    for _ in range(4):
        session.ingest(*_off_route_coords())
    assert len(monitor.alerts) == 1

    for _ in range(3):
        session.ingest(*_on_route_coords())
    assert monitor.consecutive_off_route == 0

    for _ in range(4):
        session.ingest(*_off_route_coords())
    assert len(monitor.alerts) == 2