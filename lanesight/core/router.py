"""LaneSight routing & geocoding engine.

Provides a standalone :class:`Router` that resolves origin/destination
locations (plus optional intermediate waypoint stops), fetches an OSRM
driving route, and returns a structured :class:`RouteResult` serializable
to JSON. Intended to be imported by other projects (e.g. Fleet Scout)
without pulling in the Streamlit UI.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Optional

import requests
from geopy.distance import geodesic
from geopy.geocoders import ArcGIS, Nominatim
from sqlmodel import Session

from lanesight.core.constraints import RouteCompliance, evaluate_route_compliance
from lanesight.models import SavedRoute, Vehicle

logger = logging.getLogger("lanesight")

# 50 US State Abbreviation Mapping
STATE_ABBREVS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

SRC_OSRM = "osrm"
SRC_GEODESIC = "geodesic"


@dataclass(frozen=True)
class Config:
    """Tunable settings for :class:`Router`."""

    osrm_base_url: str = "https://router.project-osrm.org"
    osrm_timeout: float = 8.0
    geocode_timeout: float = 10.0
    geodesic_road_factor: float = 1.2
    fallback_speed_mph: float = 55.0
    osrm_user_agent: str = "LaneSight-App/1.0 (twosixstudios.dev@gmail.com)"
    geocode_user_agent: str = "lanesight_twosix_studios_v1"


@dataclass(frozen=True)
class GeoPoint:
    """A resolved point of interest with its address."""

    lat: float
    lng: float
    address: str


@dataclass
class RouteResult:
    """Structured output of a routing request (JSON-serializable)."""

    origin: GeoPoint
    destination: GeoPoint
    distance_miles: float
    duration_hours: float
    geometry: list = field(default_factory=list)  # list of [lat, lng]
    source: str = SRC_GEODESIC  # "osrm" | "geodesic"
    waypoints: list = field(default_factory=list)  # list[GeoPoint], all ordered stops
    legs: list = field(default_factory=list)  # list[dict] per-stop breakdown
    compliance: Optional[RouteCompliance] = None  # dispatch compliance result

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-friendly)."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to an indented JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class Router:
    """Resolves locations and computes driving routes/transit metrics."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def geocode(self, location_name: str) -> Optional[GeoPoint]:
        """Convert a location string into a :class:`GeoPoint` or ``None``."""
        normalized = self._normalize_us_location(location_name)
        logger.info(
            "Geocoding query: %r (raw input: %r)", normalized, location_name
        )

        for geocoder_factory in (self._arcgis_point, self._nominatim_point):
            point = geocoder_factory(normalized)
            if point is not None:
                logger.info(
                    "Geocode success -> %s (%s, %s)",
                    point.address,
                    point.lat,
                    point.lng,
                )
                return point
        return None

    def route(
        self,
        origin_str: str,
        destination_str: str,
        waypoints: Optional[list[str]] = None,
        vehicle: Optional[Vehicle] = None,
    ) -> RouteResult:
        """Compute a driving route across one or more ordered stops.

        ``waypoints`` are intermediate stops geocoded between origin and
        destination. Each stop is resolved to a :class:`GeoPoint`, an OSRM
        request is built over the full ordered sequence of coordinates, and
        the response is parsed into total distance/duration plus per-leg
        breakdowns. Falls back to sequential geodesic estimates if OSRM is
        unavailable.

        When a ``vehicle`` is supplied, the route is evaluated against
        commercial constraint limits and the resulting
        :class:`RouteCompliance` is attached to the returned result.

        Raises ``ValueError`` if any location cannot be resolved.
        """
        stops = [origin_str, *(waypoints or []), destination_str]
        resolved: list[GeoPoint] = []
        unresolved: list[str] = []
        for stop in stops:
            point = self.geocode(stop)
            if point is None:
                unresolved.append(stop)
            else:
                resolved.append(point)

        if unresolved:
            raise ValueError(f"Could not resolve location(s): {unresolved}")

        result = self._route_geopoints(resolved)
        if vehicle is not None:
            result.compliance = evaluate_route_compliance(vehicle)
        return result

    def update_eta(
        self, remaining_distance: float, average_speed: float
    ) -> float:
        """Estimate hours remaining given remaining distance (miles) and
        average speed (mph).

        Raises ``ValueError`` for negative distances or non-positive speeds.
        """
        if remaining_distance < 0:
            raise ValueError("remaining_distance must be non-negative")
        if average_speed <= 0:
            raise ValueError("average_speed must be positive")
        return round(remaining_distance / average_speed, 2)

    def save_route(self, result: RouteResult, session: Session) -> SavedRoute:
        """Persist a computed route into the SQLite database.

        Stores origin/destination addresses, totals, the overview geometry
        (as JSON), and the full ordered stop list into a :class:`SavedRoute`.
        """
        saved = SavedRoute(
            origin_address=result.origin.address,
            destination_address=result.destination.address,
            distance_miles=result.distance_miles,
            duration_hours=result.duration_hours,
            polyline_geometry=json.dumps(result.geometry),
            waypoints_json=json.dumps(
                [asdict(point) for point in result.waypoints]
            ),
        )
        session.add(saved)
        session.commit()
        session.refresh(saved)
        return saved

    # ------------------------------------------------------------------ #
    # Fallback geocoders
    # ------------------------------------------------------------------ #
    def _arcgis_point(self, query: str) -> Optional[GeoPoint]:
        try:
            location = ArcGIS(
                user_agent=self.config.geocode_user_agent
            ).geocode(query, timeout=self.config.geocode_timeout)
            if location:
                return GeoPoint(
                    lat=location.latitude,
                    lng=location.longitude,
                    address=location.address,
                )
        except Exception as exc:  # noqa: BLE001 - tolerate provider failures
            logger.warning("ArcGIS geocoding failed: %s", exc)
        return None

    def _nominatim_point(self, query: str) -> Optional[GeoPoint]:
        try:
            location = Nominatim(
                user_agent=self.config.geocode_user_agent
            ).geocode(query, timeout=self.config.geocode_timeout)
            if location:
                return GeoPoint(
                    lat=location.latitude,
                    lng=location.longitude,
                    address=location.address,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nominatim geocoding failed: %s", exc)
        return None

    # ------------------------------------------------------------------ #
    # Routing
    # ------------------------------------------------------------------ #
    def _route_geopoints(self, points: list[GeoPoint]) -> RouteResult:
        origin, destination = points[0], points[-1]

        # Geodesic fallback: sequential straight-line legs between stops.
        legs = []
        total_miles = 0.0
        for index in range(len(points) - 1):
            a, b = points[index], points[index + 1]
            miles = round(
                geodesic((a.lat, a.lng), (b.lat, b.lng)).miles
                * self.config.geodesic_road_factor,
                1,
            )
            total_miles += miles
            legs.append(
                {
                    "origin": a.address,
                    "destination": b.address,
                    "distance_miles": miles,
                    "duration_hours": round(
                        miles / self.config.fallback_speed_mph, 1
                    ),
                }
            )

        direct_miles = round(total_miles, 1)
        est_hours = round(direct_miles / self.config.fallback_speed_mph, 1)
        geometry = [[point.lat, point.lng] for point in points]
        source = SRC_GEODESIC

        try:
            route = self._fetch_osrm_route(points)
            if route:
                direct_miles = round(route["distance"] / 1609.34, 1)
                est_hours = round(route["duration"] / 3600, 1)
                geometry = [
                    [lat, lng] for lng, lat in route["geometry"]["coordinates"]
                ]
                legs = [
                    {
                        "origin": points[index].address,
                        "destination": points[index + 1].address,
                        "distance_miles": round(leg["distance"] / 1609.34, 1),
                        "duration_hours": round(leg["duration"] / 3600, 1),
                    }
                    for index, leg in enumerate(route.get("legs", []))
                    if index + 1 < len(points)
                ]
                source = SRC_OSRM
                logger.info(
                    "OSRM route fetched: %s miles, %s hrs across %s stops",
                    direct_miles,
                    est_hours,
                    len(points),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "OSRM routing failed, using geodesic fallback: %s", exc
            )

        return RouteResult(
            origin=origin,
            destination=destination,
            distance_miles=direct_miles,
            duration_hours=est_hours,
            geometry=geometry,
            source=source,
            waypoints=points,
            legs=legs,
        )

    def _fetch_osrm_route(self, points: list[GeoPoint]) -> Optional[dict]:
        coords = ";".join(f"{p.lng},{p.lat}" for p in points)
        url = (
            f"{self.config.osrm_base_url}/route/v1/driving/{coords}"
            f"?overview=full&geometries=geojson"
        )
        headers = {"User-Agent": self.config.osrm_user_agent}
        response = requests.get(url, headers=headers, timeout=self.config.osrm_timeout)
        response.raise_for_status()
        data = response.json()
        if data.get("routes"):
            return data["routes"][0]
        return None

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_us_location(location_name: str) -> str:
        """Expand state abbreviations (e.g. 'Ontario, CA' -> 'Ontario, California, USA').

        Prevents Canada/international geocoding mix-ups.
        """
        clean = location_name.strip()
        parts = [p.strip() for p in clean.split(",")]

        if len(parts) >= 2:
            state_part = parts[1].upper()
            if state_part in STATE_ABBREVS:
                parts[1] = STATE_ABBREVS[state_part]
                if len(parts) == 2:
                    parts.append("USA")
                return ", ".join(parts)

        if "usa" not in clean.lower() and "united states" not in clean.lower():
            clean += ", USA"

        return clean