"""Route deviation alerting for live telemetry streams.

Watches a vehicle's GPS samples as they flow through a
:class:`~lanesight.core.telemetry.TelemetrySession` and flags a
``ROUTE_DEVIATION`` alert only when the vehicle has been off-route for a
*sustained* run of consecutive samples. The threshold-based design ignores
single-sample GPS jitter while still catching a vehicle that has genuinely
left the calculated route.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

logger = logging.getLogger("lanesight")

# Consecutive off-route samples required before an alert is raised. The
# alert fires when the off-route run exceeds this value (e.g. >3 samples).
DEVIATION_ALERT_THRESHOLD = 3

ALERT_TYPE_ROUTE_DEVIATION = "ROUTE_DEVIATION"


@dataclass(frozen=True)
class Alert:
    """A single route-deviation alert raised by a :class:`DeviationMonitor`."""

    alert_type: str
    timestamp: datetime
    distance_off_route_meters: float
    consecutive_off_route_samples: int
    matched_coords: tuple

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-friendly)."""
        return asdict(self)


class DeviationMonitor:
    """Tracks consecutive off-route telemetry samples and fires alerts.

    The monitor keeps a running count of consecutive off-route samples. An
    alert is emitted the first time the run exceeds ``threshold`` (default
    :data:`DEVIATION_ALERT_THRESHOLD`) and is not re-raised until the
    vehicle returns on-route and deviates again.
    """

    def __init__(self, threshold: int = DEVIATION_ALERT_THRESHOLD):
        if threshold < 1:
            raise ValueError("threshold must be a positive integer")
        self.threshold = threshold
        self.consecutive_off_route = 0
        self.alerts: list[Alert] = []
        self._armed = True

    def update(
        self,
        on_route: bool,
        distance_off_route_meters: float = 0.0,
        timestamp: Optional[datetime] = None,
        matched_coords: Optional[Sequence[float]] = None,
    ) -> Optional[Alert]:
        """Consume one telemetry sample and return a fired alert, if any.

        Args:
            on_route: whether the sample matched the active route polyline.
            distance_off_route_meters: GPS drift of the sample in meters.
            timestamp: sample timestamp; defaults to current UTC time.
            matched_coords: snapped ``(lat, lon)`` position on the route.

        Returns:
            A :class:`Alert` the first time the sustained off-route run
            exceeds ``threshold``, otherwise ``None``.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if not on_route:
            self.consecutive_off_route += 1
            if self._armed and self.consecutive_off_route > self.threshold:
                self._armed = False
                return self._fire(
                    timestamp,
                    distance_off_route_meters,
                    matched_coords,
                )
        else:
            self.consecutive_off_route = 0
            self._armed = True

        return None

    def _fire(
        self,
        timestamp: datetime,
        distance_off_route_meters: float,
        matched_coords: Optional[Sequence[float]],
    ) -> Alert:
        alert = Alert(
            alert_type=ALERT_TYPE_ROUTE_DEVIATION,
            timestamp=timestamp,
            distance_off_route_meters=round(distance_off_route_meters, 2),
            consecutive_off_route_samples=self.consecutive_off_route,
            matched_coords=tuple(matched_coords) if matched_coords else (),
        )
        self.alerts.append(alert)
        logger.warning(
            "ROUTE_DEVIATION alert raised after %s off-route samples "
            "(drift %.2fm)",
            self.consecutive_off_route,
            alert.distance_off_route_meters,
        )
        return alert
