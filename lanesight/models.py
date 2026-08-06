"""SQLModel ORM definitions for LaneSight fleet assets."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Vehicle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vin: str = Field(index=True, unique=True)
    unit_number: str = Field(index=True, unique=True)
    make_model: str
    fuel_type: str
    fuel_capacity_gallons: float
    avg_mpg: float
    max_payload_lbs: float
    height_feet: float
    gross_weight_lbs: float


class Driver(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    cdl_number: str = Field(index=True, unique=True)
    cdl_state: str
    is_active: bool = True
    drive_hours_remaining: float
    shift_hours_remaining: float
    cycle_hours_remaining: float
    last_rest_break_end: Optional[datetime] = None


class SavedRoute(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    origin_address: str
    destination_address: str
    distance_miles: float
    duration_hours: float
    polyline_geometry: str
    waypoints_json: str
    estimated_fuel_cost: Optional[float] = None
    created_at: datetime = Field(default_factory=_utcnow)


class DispatchLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    route_id: int = Field(foreign_key="savedroute.id")
    vehicle_id: int = Field(foreign_key="vehicle.id")
    driver_id: int = Field(foreign_key="driver.id")
    status: str
    departure_time: Optional[datetime] = None
    estimated_arrival_time: Optional[datetime] = None
    actual_arrival_time: Optional[datetime] = None
    notes: Optional[str] = None
