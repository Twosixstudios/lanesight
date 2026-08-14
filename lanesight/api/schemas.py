"""Pydantic schemas for the LaneSight REST API.

All request/response payloads are defined here so the API never exposes
database internals directly.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    """A resolved point of interest with its human-readable address."""

    lat: float
    lng: float
    address: str


class VehicleSpecs(BaseModel):
    """Commercial vehicle specifications used for route compliance checks."""

    height_feet: float = Field(default=13.0, ge=0.0)
    gross_weight_lbs: float = Field(default=40000.0, ge=0.0)
    is_hazmat: bool = False


class RouteRequest(BaseModel):
    """Request body for ``POST /api/v1/route``."""

    origin: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    waypoints: list[str] = Field(default_factory=list)
    vehicle: Optional[VehicleSpecs] = None


class RouteResponse(BaseModel):
    """Response body for ``POST /api/v1/route``."""

    origin: GeoPoint
    destination: GeoPoint
    distance_miles: float
    duration_hours: float
    geometry: list[list[float]]
    source: str
    waypoints: list[GeoPoint]
    legs: list[dict]
    compliance: Optional[dict] = None


class GeocodeRequest(BaseModel):
    """Request body for ``POST /api/v1/geocode``."""

    location: str = Field(min_length=1, max_length=200)


class GeocodeResponse(BaseModel):
    """Response body for ``POST /api/v1/geocode``."""

    lat: float
    lng: float
    address: str
