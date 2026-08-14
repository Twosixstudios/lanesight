"""Tests for lanesight.core.telemetry and Router.update_eta."""

from datetime import datetime

import pytest
from geopy.distance import geodesic

from lanesight.core.router import Router
from lanesight.core.telemetry import (
    GPS_DRIFT_TOLERANCE_METERS,
    MatchResult,
    TelemetryPoint,
    TelemetrySession,
    match_to_route,
)

M_PER_DEG_LAT = 110574.0  # meters per degree of latitude at the equator

# A straight 2,200m route running west-to-east along the equator.
ORIGIN = (0.0, 0.0)
MID = (0.0, 0.01)
DEST = (0.0, 0.02)
POLYLINE = [[ORIGIN[0], ORIGIN[1]], [MID[0], MID[1]], [DEST[0], DEST[1]]]


def _offset_lat(meters):
    """Latitude shift (degrees) equal to ``meters`` of northward drift."""
    return meters / M_PER_DEG_LAT


# ---------------------------------------------------------------------- #
# match_to_route - basic route matching
# ---------------------------------------------------------------------- #
def test_match_exactly_on_route_origin():
    result = match_to_route(ORIGIN, POLYLINE)
    assert isinstance(result, MatchResult)
    assert result.on_route is True
    assert result.distance_off_route_meters == pytest.approx(0.0, abs=0.1)
    assert result.remaining_distance_meters == pytest.approx(
        geodesic(ORIGIN, DEST).meters, rel=0.01
    )
    assert result.nearest_index == 0


def test_match_remaining_distance_at_midpoint():
    result = match_to_route(MID, POLYLINE)
    expected = geodesic(MID, DEST).meters
    assert result.on_route is True
    assert result.remaining_distance_meters == pytest.approx(
        expected, rel=0.01
    )
    assert result.remaining_distance_miles == pytest.approx(
        expected / 1609.34, rel=0.01
    )


def test_match_snaps_onto_segment_between_vertices():
    # Halfway along the first leg; should match itself and leave ~1.1km.
    point = (0.0, 0.005)
    result = match_to_route(point, POLYLINE)
    assert result.on_route is True
    assert result.remaining_distance_meters == pytest.approx(
        geodesic(point, DEST).meters, rel=0.01
    )
    assert result.matched_coords[0] == pytest.approx(point[0], abs=1e-6)
    assert result.matched_coords[1] == pytest.approx(point[1], abs=1e-6)


def test_match_accepts_route_result_geometry_style():
    # RouteResult.geometry uses [lat, lng] lists; same format as POLYLINE.
    geometry = [[MID[0], MID[1]], [DEST[0], DEST[1]]]
    result = match_to_route(MID, geometry)
    assert result.remaining_distance_meters == pytest.approx(
        geodesic(MID, DEST).meters, rel=0.01
    )


def test_match_raises_on_single_point_polyline():
    with pytest.raises(ValueError):
        match_to_route((0.0, 0.0), [[0.0, 0.0]])


def test_match_raises_on_empty_polyline():
    with pytest.raises(ValueError):
        match_to_route((0.0, 0.0), [])


# ---------------------------------------------------------------------- #
# GPS drift tolerance (50 meters)
# ---------------------------------------------------------------------- #
def test_match_within_drift_tolerance_is_on_route():
    point = (_offset_lat(30.0), 0.01)
    result = match_to_route(point, POLYLINE)
    assert result.on_route is True
    assert result.distance_off_route_meters == pytest.approx(30.0, rel=0.05)
    # Snapped back onto the route, so remaining distance is ~that of MID.
    assert result.remaining_distance_meters == pytest.approx(
        geodesic(MID, DEST).meters, rel=0.02
    )


def test_match_at_tolerance_boundary_is_on_route():
    point = (_offset_lat(GPS_DRIFT_TOLERANCE_METERS - 1.0), 0.01)
    result = match_to_route(point, POLYLINE)
    assert result.on_route is True
    assert result.distance_off_route_meters <= GPS_DRIFT_TOLERANCE_METERS
    assert result.distance_off_route_meters == pytest.approx(
        GPS_DRIFT_TOLERANCE_METERS - 1.0, rel=0.05
    )


def test_match_beyond_drift_tolerance_is_off_route():
    point = (_offset_lat(100.0), 0.01)
    result = match_to_route(point, POLYLINE)
    assert result.on_route is False
    assert result.distance_off_route_meters == pytest.approx(100.0, rel=0.05)


def test_match_clearly_off_route_still_reports_remaining():
    point = (_offset_lat(500.0), 0.005)
    result = match_to_route(point, POLYLINE)
    assert result.on_route is False
    assert result.distance_off_route_meters > GPS_DRIFT_TOLERANCE_METERS
    assert result.remaining_distance_miles > 0
    assert result.remaining_distance_miles < 1.5


# ---------------------------------------------------------------------- #
# telemetry ingestion
# ---------------------------------------------------------------------- #
def test_telemetry_session_ingest_tracks_latest_point():
    session = TelemetrySession(POLYLINE)
    ts = datetime(2026, 8, 13, 12, 0, 0)
    result = session.ingest(0.0, 0.0, ts)

    assert result.on_route is True
    assert len(session.points) == 1
    assert session.latest == TelemetryPoint(
        lat=0.0, lon=0.0, timestamp=ts
    )
    assert session.latest.timestamp == ts


def test_telemetry_session_default_timestamp():
    session = TelemetrySession(POLYLINE)
    session.ingest(0.0, 0.01)
    assert session.latest is not None
    assert session.latest.lat == 0.0
    assert session.latest.timestamp is not None


def test_telemetry_session_reports_progress_after_multiple_samples():
    session = TelemetrySession(POLYLINE)
    session.ingest(*ORIGIN)
    mid_match = session.ingest(*MID)

    assert len(session.points) == 2
    assert mid_match.remaining_distance_meters == pytest.approx(
        geodesic(MID, DEST).meters, rel=0.01
    )
    assert mid_match.remaining_distance_miles == pytest.approx(
        geodesic(MID, DEST).miles, rel=0.02
    )


def test_match_result_to_dict_contract():
    result = match_to_route(MID, POLYLINE)
    payload = result.to_dict()
    assert set(payload) == {
        "matched_coords",
        "distance_off_route_meters",
        "remaining_distance_meters",
        "remaining_distance_miles",
        "on_route",
        "nearest_index",
    }


# ---------------------------------------------------------------------- #
# Router.update_eta
# ---------------------------------------------------------------------- #
def test_update_eta_remaining_hours():
    router = Router()
    assert router.update_eta(
        remaining_distance=410.5, average_speed=55.0
    ) == pytest.approx(7.46, abs=0.01)


def test_update_eta_zero_distance_is_zero():
    assert Router().update_eta(0.0, 55.0) == 0.0


def test_update_eta_negative_distance_raises():
    with pytest.raises(ValueError, match="remaining_distance"):
        Router().update_eta(-5.0, 55.0)


def test_update_eta_nonpositive_speed_raises():
    with pytest.raises(ValueError, match="average_speed"):
        Router().update_eta(100.0, 0.0)
    with pytest.raises(ValueError, match="average_speed"):
        Router().update_eta(100.0, -10.0)