"""Tests for lanesight.core.router."""

import json

import pytest
import responses

from lanesight.core.router import (
    Config,
    GeoPoint,
    RouteResult,
    Router,
    SRC_GEODESIC,
    SRC_OSRM,
)

ORIGIN = GeoPoint(lat=34.1083, lng=-117.2898, address="San Bernardino, CA, USA")
DEST = GeoPoint(lat=37.8044, lng=-122.2712, address="Oakland, CA, USA")

OSRM_URL = (
    f"{Config().osrm_base_url}/route/v1/driving/"
    f"{ORIGIN.lng},{ORIGIN.lat};{DEST.lng},{DEST.lat}"
    f"?overview=full&geometries=geojson"
)


def make_route(use_gear=False, source=SRC_GEODESIC):
    return RouteResult(
        origin=ORIGIN,
        destination=DEST,
        distance_miles=410.5,
        duration_hours=7.4,
        geometry=[[ORIGIN.lat, ORIGIN.lng], [DEST.lat, DEST.lng]],
        source=source,
    )


# ---------------------------------------------------------------------- #
# normalize_us_location
# ---------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Ontario, CA", "Ontario, California, USA"),
        ("San Bernardino, CA, 92410", "San Bernardino, California, 92410"),
        ("Oakland, California", "Oakland, California, USA"),
        ("Toronto", "Toronto, USA"),
        ("New York, NY", "New York, New York, USA"),
    ],
)
def test_normalize_us_location(raw, expected):
    assert Router._normalize_us_location(raw) == expected


# ---------------------------------------------------------------------- #
# geocode fallback order
# ---------------------------------------------------------------------- #
def test_geocode_fallback_to_nominatim(monkeypatch):
    router = Router()
    monkeypatch.setattr(
        router, "_arcgis_point", lambda query: None
    )
    monkeypatch.setattr(
        router, "_nominatim_point", lambda query: GeoPoint(40.0, -75.0, "PH")
    )
    assert router.geocode("Philly, PA") == GeoPoint(40.0, -75.0, "PH")


def test_geocode_returns_none_when_all_fail(monkeypatch):
    router = Router()
    monkeypatch.setattr(router, "_arcgis_point", lambda query: None)
    monkeypatch.setattr(router, "_nominatim_point", lambda query: None)
    assert router.geocode("Nowhere, ZZ") is None


# ---------------------------------------------------------------------- #
# routing
# ---------------------------------------------------------------------- #
@responses.activate
def test_route_osrm_success(monkeypatch):
    monkeypatch.setattr(
        Router, "geocode", lambda self, loc: ORIGIN if "San" in loc else DEST
    )
    geometry = [[ORIGIN.lat, ORIGIN.lng], [34.5, -118.0], [DEST.lat, DEST.lng]]
    payload = {
        "routes": [
            {
                "distance": 660556.0,  # ~410.5 miles
                "duration": 26640.0,  # 7.4 hours
                "geometry": {
                    "coordinates": [
                        [ORIGIN.lng, ORIGIN.lat],
                        [-118.0, 34.5],
                        [DEST.lng, DEST.lat],
                    ]
                },
            }
        ]
    }
    responses.add(responses.GET, OSRM_URL, json=payload, status=200)

    result = Router().route("San Bernardino, CA", "Oakland, CA")

    assert result.distance_miles == 410.5
    assert result.duration_hours == 7.4
    assert result.source == SRC_OSRM
    assert result.geometry == geometry


@responses.activate
def test_route_geodesic_fallback(monkeypatch):
    monkeypatch.setattr(
        Router, "geocode", lambda self, loc: ORIGIN if "San" in loc else DEST
    )
    responses.add(responses.GET, OSRM_URL, status=500)

    result = Router().route("San Bernardino, CA", "Oakland, CA")

    assert result.source == SRC_GEODESIC
    assert result.geometry == [[ORIGIN.lat, ORIGIN.lng], [DEST.lat, DEST.lng]]
    assert result.distance_miles > 0
    assert result.duration_hours > 0


def test_route_raises_on_unresolvable(monkeypatch):
    monkeypatch.setattr(Router, "geocode", lambda self, loc: None)
    with pytest.raises(ValueError):
        Router().route("Nowhere, ZZ", "Also Nowhere")


# ---------------------------------------------------------------------- #
# JSON contract
# ---------------------------------------------------------------------- #
def test_route_result_to_json_contract():
    result = make_route()
    payload = result.to_dict()
    assert set(payload) == {
        "origin",
        "destination",
        "distance_miles",
        "duration_hours",
        "geometry",
        "source",
    }
    assert set(payload["origin"]) == {"lat", "lng", "address"}

    reparsed = json.loads(result.to_json())
    assert reparsed == payload


# ---------------------------------------------------------------------- #
# CLI
# ---------------------------------------------------------------------- #
def test_cli_main(monkeypatch, capsys):
    from lanesight.cli import main

    monkeypatch.setattr(
        Router, "route", lambda self, o, d: make_route(source=SRC_OSRM)
    )
    assert main(["route", "San Bernardino, CA", "Oakland, CA"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["source"] == SRC_OSRM


def test_cli_failure_exit_code(monkeypatch, capsys):
    from lanesight.cli import main

    monkeypatch.setattr(Router, "route", lambda self, o, d: (_ for _ in ()).throw(ValueError("x")))
    assert main(["route", "X", "Y"]) == 1
    assert "Error" in capsys.readouterr().err