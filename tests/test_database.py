"""Tests for lanesight.database and lanesight.models."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from lanesight import database
from lanesight.models import DispatchLog, Driver, SavedRoute, Vehicle


@pytest.fixture()
def db_engine(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", engine)
    return engine


def test_init_db_creates_tables(db_engine):
    database.init_db()
    tables = SQLModel.metadata.tables
    assert set(tables) >= {
        "vehicle",
        "driver",
        "savedroute",
        "dispatchlog",
    }


def test_crud_all_models(db_engine):
    database.init_db()

    vehicle = Vehicle(
        vin="1HGCM82633A004352",
        unit_number="UNIT-001",
        make_model="Freightliner Cascadia",
        fuel_type="diesel",
        fuel_capacity_gallons=150.0,
        avg_mpg=6.5,
        max_payload_lbs=38000.0,
        height_feet=13.5,
        gross_weight_lbs=80000.0,
    )
    driver = Driver(
        name="Erik Villa",
        cdl_number="DL123456",
        cdl_state="CA",
        is_active=True,
        drive_hours_remaining=8.0,
        shift_hours_remaining=11.0,
        cycle_hours_remaining=60.0,
        last_rest_break_end=datetime.now(timezone.utc),
    )
    route = SavedRoute(
        origin_address="San Bernardino, CA",
        destination_address="Oakland, CA",
        distance_miles=410.5,
        duration_hours=7.4,
        polyline_geometry="a~b~c",
        waypoints_json='[{"lat": 34.1, "lng": -117.3}]',
        estimated_fuel_cost=512.40,
    )
    dispatch = DispatchLog(
        route_id=1,
        vehicle_id=1,
        driver_id=1,
        status="in_transit",
        departure_time=datetime.now(timezone.utc),
        estimated_arrival_time=datetime.now(timezone.utc) + timedelta(hours=7, minutes=24),
        actual_arrival_time=None,
        notes="Loaded freight at warehouse",
    )

    with Session(database.engine) as session:
        session.add(vehicle)
        session.add(driver)
        session.add(route)
        session.add(dispatch)
        session.commit()
        session.refresh(vehicle)
        session.refresh(driver)
        session.refresh(route)
        session.refresh(dispatch)

        assert vehicle.id == 1
        assert driver.id == 1
        assert route.id == 1
        assert dispatch.id == 1

        fetched_vehicle = session.get(Vehicle, 1)
        assert fetched_vehicle.vin == "1HGCM82633A004352"
        assert fetched_vehicle.unit_number == "UNIT-001"
        assert fetched_vehicle.fuel_type == "diesel"
        assert fetched_vehicle.fuel_capacity_gallons == 150.0
        assert fetched_vehicle.avg_mpg == 6.5
        assert fetched_vehicle.max_payload_lbs == 38000.0
        assert fetched_vehicle.height_feet == 13.5
        assert fetched_vehicle.gross_weight_lbs == 80000.0

        fetched_driver = session.get(Driver, 1)
        assert fetched_driver.name == "Erik Villa"
        assert fetched_driver.cdl_number == "DL123456"
        assert fetched_driver.cdl_state == "CA"
        assert fetched_driver.is_active is True
        assert fetched_driver.drive_hours_remaining == 8.0
        assert fetched_driver.shift_hours_remaining == 11.0
        assert fetched_driver.cycle_hours_remaining == 60.0
        assert fetched_driver.last_rest_break_end is not None

        fetched_route = session.get(SavedRoute, 1)
        assert fetched_route.origin_address == "San Bernardino, CA"
        assert fetched_route.destination_address == "Oakland, CA"
        assert fetched_route.distance_miles == 410.5
        assert fetched_route.duration_hours == 7.4
        assert fetched_route.polyline_geometry == "a~b~c"
        assert fetched_route.waypoints_json
        assert fetched_route.estimated_fuel_cost == 512.40
        assert fetched_route.created_at is not None

        fetched_dispatch = session.get(DispatchLog, 1)
        assert fetched_dispatch.status == "in_transit"
        assert fetched_dispatch.route_id == 1
        assert fetched_dispatch.vehicle_id == 1
        assert fetched_dispatch.driver_id == 1
        assert fetched_dispatch.departure_time is not None
        assert fetched_dispatch.estimated_arrival_time is not None
        assert fetched_dispatch.actual_arrival_time is None
        assert fetched_dispatch.notes == "Loaded freight at warehouse"


def test_get_session_yields_sessions(db_engine):
    database.init_db()
    gen = database.get_session()
    session = next(gen)
    assert isinstance(session, Session)
    gen.close()
