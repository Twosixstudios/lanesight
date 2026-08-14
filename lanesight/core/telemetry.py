"""LaneSight live telemetry & GPS route matching engine.

Ingests GPS samples (lat, lon, timestamp) and matches them against an
active OSRM route polyline to report on-route status, remaining distance
to the destination, and (via :class:`Router`) an updated ETA. Kept pure
and dependency-light so it can run on the vehicle side without the full
routing stack.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from geopy.distance import geodesic

logger = logging.getLogger("lanesight")

# GPS drift tolerance (meters). Samples within this distance of the route
# polyline are treated as on-route and snapped to the line.
GPS_DRIFT_TOLERANCE_METERS = 50.0

MILES_PER_METER = 1.0 / 1609.34


@dataclass(frozen=True)
class TelemetryPoint:
    """A single incoming GPS sample (lat, lon, timestamp)."""

    lat: float
    lon: float
    timestamp: datetime


@dataclass(frozen=True)
class MatchResult:
    """Outcome of matching a GPS sample against a route polyline."""

    matched_coords: tuple  # (lat, lon) snapped onto the route
    distance_off_route_meters: float  # GPS drift / deviation distance
    remaining_distance_meters: float
    remaining_distance_miles: float
    on_route: bool  # False when drift exceeds GPS_DRIFT_TOLERANCE_METERS
    nearest_index: int  # index of the closest polyline segment start

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-friendly)."""
        return asdict(self)


def _project_point_to_segment(
    point: Sequence[float], a: Sequence[float], b: Sequence[float]
) -> tuple:
    """Project ``point`` (lat, lon) onto segment ``a``-``b``.

    Uses a local equirectangular approximation centered on the segment's
    midpoint latitude, then reports the geodesic distance from the raw
    point to its projected location. Returns ``(matched_latlon, meters)``.
    """
    lat, lon = point[0], point[1]
    mid_lat = math.radians((a[0] + b[0]) / 2.0)
    cos_mid = math.cos(mid_lat) or 1e-9

    ax, ay = a[1] * cos_mid, a[0]
    bx, by = b[1] * cos_mid, b[0]
    px, py = lon * cos_mid, lat

    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        t = 0.0
    else:
        t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0.0, min(1.0, t))

    matched = (ay + t * dy, (ax + t * dx) / cos_mid)
    meters = geodesic((lat, lon), matched).meters
    return matched, meters


def match_to_route(
    current_coords: Sequence[float], route_polyline: Sequence[Sequence[float]]
) -> MatchResult:
    """Match the vehicle's current GPS position against the route polyline.

    Identifies the nearest point on the route (allowing for GPS drift up
    to :data:`GPS_DRIFT_TOLERANCE_METERS`) and computes the remaining
    distance from that snapped point to the destination.

    Args:
        current_coords: ``(lat, lon)`` tuple of the live GPS position.
        route_polyline: ``[lat, lng]`` pairs exactly as produced by
            :attr:`RouteResult.geometry`.

    Returns:
        A :class:`MatchResult` with on-route status and remaining distance.

    Raises:
        ValueError: if the polyline contains fewer than two points.
    """
    if len(route_polyline) < 2:
        raise ValueError("route_polyline must contain at least two points")

    # Cumulative distance (meters) from the start of the route to each vertex.
    cumulative = [0.0]
    for index in range(len(route_polyline) - 1):
        cumulative.append(
            cumulative[-1]
            + geodesic(
                route_polyline[index], route_polyline[index + 1]
            ).meters
        )
    total_meters = cumulative[-1]

    best = None
    for index in range(len(route_polyline) - 1):
        matched, offset = _project_point_to_segment(
            current_coords, route_polyline[index], route_polyline[index + 1]
        )
        remaining = (
            geodesic(matched, route_polyline[index + 1]).meters
            + (total_meters - cumulative[index + 1])
        )
        if best is None or offset < best[0]:
            best = (offset, matched, remaining, index)

    offset_meters, matched, remaining_meters, nearest_index = best
    return MatchResult(
        matched_coords=(round(matched[0], 6), round(matched[1], 6)),
        distance_off_route_meters=round(offset_meters, 2),
        remaining_distance_meters=round(remaining_meters, 2),
        remaining_distance_miles=round(remaining_meters * MILES_PER_METER, 2),
        on_route=offset_meters <= GPS_DRIFT_TOLERANCE_METERS,
        nearest_index=nearest_index,
    )


class TelemetrySession:
    """Accumulates live GPS samples and reports route progress per sample."""

    def __init__(self, route_polyline: Sequence[Sequence[float]]):
        self.route_polyline = route_polyline
        self.points: list[TelemetryPoint] = []

    def ingest(
        self,
        lat: float,
        lon: float,
        timestamp: Optional[datetime] = None,
    ) -> MatchResult:
        """Record a GPS sample and return its route match.

        Defaults the timestamp to the current UTC time when omitted.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        point = TelemetryPoint(lat=lat, lon=lon, timestamp=timestamp)
        self.points.append(point)
        return match_to_route((lat, lon), self.route_polyline)

    @property
    def latest(self) -> Optional[TelemetryPoint]:
        """Most recently ingested GPS sample, if any."""
        return self.points[-1] if self.points else None
