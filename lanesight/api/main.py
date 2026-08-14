"""LaneSight FastAPI headless wrapper.

Exposes routing and geocoding as documented REST endpoints backed by the
``lanesight.core`` engine. OpenAPI/Swagger docs are available at ``/docs``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from lanesight.api.schemas import (
    GeocodeRequest,
    GeocodeResponse,
    RouteRequest,
    RouteResponse,
)
from lanesight.core.constraints import evaluate_route_compliance
from lanesight.core.router import Router
from lanesight.models import Vehicle

logger = logging.getLogger("lanesight")

app = FastAPI(
    title="LaneSight API",
    description=(
        "Headless REST wrapper for the LaneSight routing engine. "
        "Resolves locations and computes driving routes with optional "
        "commercial vehicle compliance checks."
    ),
    version="0.1.0",
)

router = Router()


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe for orchestrators and load balancers."""
    return {"status": "ok"}


@app.post(
    "/api/v1/route",
    response_model=RouteResponse,
    tags=["routing"],
    summary="Compute a driving route",
)
def compute_route(payload: RouteRequest) -> RouteResponse:
    """Resolve an ordered set of stops and return route metrics.

    ``origin`` and ``destination`` are required; intermediate ``waypoints``
    are geocoded and visited in order. Optional ``vehicle`` specs trigger a
    commercial route compliance evaluation.
    """
    try:
        result = router.route(
            payload.origin,
            payload.destination,
            waypoints=payload.waypoints,
        )
    except ValueError as exc:
        logger.warning("Route request rejected: %s", exc)
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve one or more locations: {exc}",
        ) from exc

    data = result.to_dict()
    if payload.vehicle:
        data["compliance"] = evaluate_route_compliance(
            _build_vehicle(payload.vehicle),
            is_hazmat=payload.vehicle.is_hazmat,
        ).to_dict()
    return RouteResponse.model_validate(data)


@app.post(
    "/api/v1/geocode",
    response_model=GeocodeResponse,
    tags=["geocoding"],
    summary="Resolve a location string to coordinates",
)
def geocode(payload: GeocodeRequest) -> GeocodeResponse:
    """Convert a location string (e.g. ``\"Oakland, CA\"``) into coordinates."""
    point = router.geocode(payload.location)
    if point is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve location: {payload.location!r}",
        )
    return GeocodeResponse(lat=point.lat, lng=point.lng, address=point.address)


def _build_vehicle(specs) -> Vehicle:
    """Build an internal :class:`Vehicle` from API-level vehicle specs."""
    return Vehicle(
        vin="api-generated",
        unit_number="api-generated",
        make_model="api-generated",
        fuel_type="diesel",
        fuel_capacity_gallons=200.0,
        avg_mpg=6.5,
        max_payload_lbs=40000.0,
        height_feet=specs.height_feet,
        gross_weight_lbs=specs.gross_weight_lbs,
    )