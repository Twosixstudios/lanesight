"""Tests for the FastAPI headless wrapper (lanesight.api)."""

import pytest
from fastapi.testclient import TestClient

from lanesight.api.main import app
from lanesight.core.router import GeoPoint, Router

client = TestClient(app)

ORIGIN = GeoPoint(lat=34.1083, lng=-117.2898, address="San Bernardino, CA, USA")
DEST = GeoPoint(lat=37.8044, lng=-122.2712, address="Oakland, CA, USA")


def _geocode_ok(self, loc):
    return ORIGIN if "San" in loc else DEST


# ---------------------------------------------------------------------- #
# health / OpenAPI docs
# ---------------------------------------------------------------------- #
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_exposes_endpoints():
    paths = app.openapi()["paths"]
    assert "/api/v1/route" in paths
    assert "/api/v1/geocode" in paths
    assert app.openapi()["info"]["title"] == "LaneSight API"


# ---------------------------------------------------------------------- #
# geocode
# ---------------------------------------------------------------------- #
def test_geocode_success(monkeypatch):
    monkeypatch.setattr(
        Router,
        "geocode",
        lambda self, loc: GeoPoint(40.0, -75.0, "Philadelphia, PA, USA"),
    )
    resp = client.post("/api/v1/geocode", json={"location": "Philadelphia, PA"})
    assert resp.status_code == 200
    assert resp.json() == {
        "lat": 40.0,
        "lng": -75.0,
        "address": "Philadelphia, PA, USA",
    }


def test_geocode_unresolvable(monkeypatch):
    monkeypatch.setattr(Router, "geocode", lambda self, loc: None)
    resp = client.post("/api/v1/geocode", json={"location": "Nowhere, ZZ"})
    assert resp.status_code == 404
    assert "Could not resolve" in resp.json()["detail"]


def test_geocode_validation_error():
    resp = client.post("/api/v1/geocode", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------- #
# route
# ---------------------------------------------------------------------- #
def test_route_success(monkeypatch):
    monkeypatch.setattr(Router, "geocode", _geocode_ok)
    resp = client.post(
        "/api/v1/route",
        json={"origin": "San Bernardino, CA", "destination": "Oakland, CA"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["origin"]["address"] == ORIGIN.address
    assert data["destination"]["address"] == DEST.address
    assert data["distance_miles"] > 0
    assert data["duration_hours"] > 0
    assert data["source"] in {"osrm", "geodesic"}
    assert data["compliance"] is None
    assert len(data["waypoints"]) == 2


def test_route_with_waypoints(monkeypatch):
    mid = GeoPoint(lat=36.3069, lng=-119.7838, address="Fresno, CA, USA")
    monkeypatch.setattr(
        Router, "geocode", lambda self, loc: ORIGIN if "San" in loc else (mid if "Fresno" in loc else DEST)
    )
    resp = client.post(
        "/api/v1/route",
        json={
            "origin": "San Bernardino, CA",
            "destination": "Oakland, CA",
            "waypoints": ["Fresno, CA"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert [wp["address"] for wp in data["waypoints"]] == [
        ORIGIN.address,
        mid.address,
        DEST.address,
    ]
    assert len(data["legs"]) == 2


def test_route_with_vehicle_compliance(monkeypatch):
    monkeypatch.setattr(Router, "geocode", _geocode_ok)
    resp = client.post(
        "/api/v1/route",
        json={
            "origin": "San Bernardino, CA",
            "destination": "Oakland, CA",
            "vehicle": {"height_feet": 14.0, "gross_weight_lbs": 82000.0},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["compliance"]["is_compliant"] is False
    assert len(data["compliance"]["violations"]) == 2


def test_route_unresolvable(monkeypatch):
    monkeypatch.setattr(Router, "geocode", lambda self, loc: None)
    resp = client.post(
        "/api/v1/route",
        json={"origin": "Nowhere, ZZ", "destination": "Also Nowhere"},
    )
    assert resp.status_code == 404
    assert "Could not resolve" in resp.json()["detail"]


def test_route_validation_error():
    resp = client.post(
        "/api/v1/route", json={"origin": "San Bernardino, CA"}
    )
    assert resp.status_code == 422
