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
        waypoints=[ORIGIN, DEST],
        legs=[
            {
                "origin": ORIGIN.address,
                "destination": DEST.address,
                "distance_miles": 410.5,
                "duration_hours": 7.4,
            }
        ],
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
# multi-stop waypoints
# ---------------------------------------------------------------------- #
MID = GeoPoint(lat=36.3069, lng=-119.7838, address="Fresno, CA, USA")
THREE_STOP_URL = (
    f"{Config().osrm_base_url}/route/v1/driving/"
    f"{ORIGIN.lng},{ORIGIN.lat};{MID.lng},{MID.lat};{DEST.lng},{DEST.lat}"
    f"?overview=full&geometries=geojson"
)


def _three_stop_geocode(self, loc):
    if "San" in loc:
        return ORIGIN
    if "Fresno" in loc:
        return MID
    return DEST


@responses.activate
def test_route_multi_stop_osrm(monkeypatch):
    monkeypatch.setattr(Router, "geocode", _three_stop_geocode)
    payload = {
        "routes": [
            {
                "distance": 763000.0,  # ~474 miles total
                "duration": 30600.0,  # 8.5 hours total
                "geometry": {
                    "coordinates": [
                        [ORIGIN.lng, ORIGIN.lat],
                        [-119.7, 36.3],
                        [MID.lng, MID.lat],
                        [-121.0, 37.3],
                        [DEST.lng, DEST.lat],
                    ]
                },
                "legs": [
                    {"distance": 412800.0, "duration": 16500.0},  # ~256.5 mi
                    {"distance": 350200.0, "duration": 14100.0},  # ~217.6 mi
                ],
            }
        ]
    }
    responses.add(responses.GET, THREE_STOP_URL, json=payload, status=200)

    result = Router().route(
        "San Bernardino, CA", "Oakland, CA", waypoints=["Fresno, CA"]
    )

    assert result.distance_miles == 474.1
    assert result.duration_hours == 8.5
    assert result.source == SRC_OSRM
    assert result.origin == ORIGIN
    assert result.destination == DEST
    assert result.waypoints == [ORIGIN, MID, DEST]
    assert len(result.legs) == 2
    assert result.legs[0] == {
        "origin": ORIGIN.address,
        "destination": MID.address,
        "distance_miles": 256.5,
        "duration_hours": 4.6,
    }
    assert result.legs[1] == {
        "origin": MID.address,
        "destination": DEST.address,
        "distance_miles": 217.6,
        "duration_hours": 3.9,
    }
    assert [DEST.lat, DEST.lng] in result.geometry


@responses.activate
def test_route_multi_stop_geodesic_fallback(monkeypatch):
    monkeypatch.setattr(Router, "geocode", _three_stop_geocode)
    responses.add(responses.GET, THREE_STOP_URL, status=500)

    result = Router().route(
        "San Bernardino, CA", "Oakland, CA", waypoints=["Fresno, CA"]
    )

    assert result.source == SRC_GEODESIC
    assert result.waypoints == [ORIGIN, MID, DEST]
    assert len(result.legs) == 2
    assert result.geometry == [
        [ORIGIN.lat, ORIGIN.lng],
        [MID.lat, MID.lng],
        [DEST.lat, DEST.lng],
    ]
    assert sum(leg["distance_miles"] for leg in result.legs) == pytest.approx(
        result.distance_miles
    )
    assert result.distance_miles > 0
    assert result.duration_hours > 0


def test_route_multi_stop_unresolvable_waypoint(monkeypatch):
    def flaky_geocode(self, loc):
        if "Fresno" in loc:
            return None
        return ORIGIN

    monkeypatch.setattr(Router, "geocode", flaky_geocode)
    with pytest.raises(ValueError) as excinfo:
        Router().route("San Bernardino, CA", "Oakland, CA", waypoints=["Fresno, CA"])
    assert "Fresno, CA" in str(excinfo.value)


def test_route_multi_stop_no_waypoints_single_leg(monkeypatch):
    monkeypatch.setattr(Router, "geocode", _three_stop_geocode)

    result = Router().route("San Bernardino, CA", "Oakland, CA")

    assert result.waypoints == [ORIGIN, DEST]
    assert len(result.legs) == 1
    assert result.legs[0]["origin"] == ORIGIN.address
    assert result.legs[0]["destination"] == DEST.address


# ---------------------------------------------------------------------- #
# save_route persistence
# ---------------------------------------------------------------------- #
def test_save_route_persists(tmp_path, monkeypatch):
    from sqlmodel import Session, SQLModel, create_engine

    from lanesight import database
    from lanesight.models import SavedRoute

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", engine)
    database.init_db()

    router = Router()
    result = make_route(source=SRC_OSRM)
    with Session(database.engine) as session:
        saved = router.save_route(result, session)

    assert saved.id is not None
    assert saved.origin_address == ORIGIN.address
    assert saved.destination_address == DEST.address
    assert saved.distance_miles == 410.5
    assert saved.duration_hours == 7.4
    assert saved.polyline_geometry == json.dumps(result.geometry)

    waypoints = json.loads(saved.waypoints_json)
    assert waypoints == [
        {"lat": ORIGIN.lat, "lng": ORIGIN.lng, "address": ORIGIN.address},
        {"lat": DEST.lat, "lng": DEST.lng, "address": DEST.address},
    ]


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
        "waypoints",
        "legs",
    }
    assert set(payload["origin"]) == {"lat", "lng", "address"}
    assert len(payload["waypoints"]) == 2
    assert payload["legs"][0]["distance_miles"] == 410.5

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