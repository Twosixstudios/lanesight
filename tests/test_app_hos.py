"""Streamlit AppTest UI tests for the HOS & Driver Duty Status Dashboard.

These exercise lanesight.app as rendered by Streamlit's AppTest harness.
The network-dependent Router.route is stubbed so the tests are hermetic.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from lanesight.core.router import GeoPoint, RouteResult, SRC_GEODESIC

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"

ORIGIN = GeoPoint(lat=34.1083, lng=-117.2898, address="San Bernardino, CA, USA")
DEST = GeoPoint(lat=37.8044, lng=-122.2712, address="Oakland, CA, USA")


def make_result(duration_hours: float = 7.4, distance_miles: float = 410.5) -> RouteResult:
    return RouteResult(
        origin=ORIGIN,
        destination=DEST,
        distance_miles=distance_miles,
        duration_hours=duration_hours,
        geometry=[[ORIGIN.lat, ORIGIN.lng], [DEST.lat, DEST.lng]],
        source=SRC_GEODESIC,
        waypoints=[ORIGIN, DEST],
        legs=[
            {
                "origin": ORIGIN.address,
                "destination": DEST.address,
                "distance_miles": distance_miles,
                "duration_hours": duration_hours,
            }
        ],
    )


def run_app(monkeypatch, result=None):
    """Boot the Streamlit app with Router.route stubbed to a fixed result."""
    from lanesight.core.router import Router

    stub_result = make_result() if result is None else result

    def _stub_route(self, *args, **kwargs):
        return stub_result

    monkeypatch.setattr(Router, "route", _stub_route)
    app = AppTest.from_file(str(APP_PATH), default_timeout=15)
    app.run()
    assert not app.exception
    return app


def _find_selectbox(app, label: str):
    return next(w for w in app.sidebar.selectbox if w.label == label)


# ---------------------------------------------------------------------- #
# compliant rendering
# ---------------------------------------------------------------------- #
def test_hos_compliant_renders_success_and_metrics(monkeypatch):
    app = run_app(monkeypatch)  # fresh 11h / 14h / 70h driver, 7.4h route

    success_msgs = " ".join(e.value for e in app.success)
    assert "HOS Compliant" in success_msgs
    assert not app.error

    labels = {m.label: m.value for m in app.metric}
    assert labels["Mandatory Rest Breaks"] == "0"
    assert "7.4" in labels["Total Elapsed Trip Time"]
    # updated post-trip clocks: 11-7.4=3.6, 14-7.4=6.6, 70-7.4=62.6
    assert labels["Drive Hrs Remaining"] == "3.6"
    assert labels["Shift Hrs Remaining"] == "6.6"
    assert labels["Cycle Hrs Remaining"] == "62.6"


def test_hos_compliant_route_requiring_break_renders_break_metric(monkeypatch):
    app = run_app(monkeypatch, result=make_result(duration_hours=9.5))

    success = " ".join(e.value for e in app.success)
    assert "HOS Compliant" in success

    labels = {m.label: m.value for m in app.metric}
    assert labels["Mandatory Rest Breaks"] == "1"
    assert "10.0" in labels["Total Elapsed Trip Time"]


# ---------------------------------------------------------------------- #
# violation rendering
# ---------------------------------------------------------------------- #
def test_hos_violation_rendered_when_driver_fatigued(monkeypatch):
    app = run_app(monkeypatch)  # fresh driver

    preset = _find_selectbox(app, "Driver Clock State")
    preset.set_value("Fatigued Driver (5h / 8h / 45h)")
    app.run()
    assert not app.exception

    error = " ".join(e.value for e in app.error)
    assert "HOS Violation" in error
    assert not app.success


def test_hos_violation_with_custom_clocks(monkeypatch):
    app = run_app(monkeypatch)  # fresh driver default

    preset = _find_selectbox(app, "Driver Clock State")
    preset.set_value("Custom Clocks")
    app.run()

    drive = next(w for w in app.sidebar.number_input if w.label == "Drive Hours Remaining")
    drive.set_value(5.0)
    app.run()
    assert not app.exception

    error = " ".join(e.value for e in app.error)
    assert "HOS Violation" in error