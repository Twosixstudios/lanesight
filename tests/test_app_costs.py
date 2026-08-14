"""Streamlit AppTest UI tests for the Cost Efficiency Analytics dashboard.

These exercise lanesight.app as rendered by Streamlit's AppTest harness.
The network-dependent Router.route is stubbed so the tests are hermetic.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from lanesight.core.costs import calculate_route_costs
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


def _find_number_input(app, label: str):
    return next(w for w in app.sidebar.number_input if w.label == label)


def _metrics(app):
    return {m.label: m.value for m in app.metric}


# ---------------------------------------------------------------------- #
# default assumption rendering
# ---------------------------------------------------------------------- #
def test_cost_efficiency_metrics_render(monkeypatch):
    app = run_app(monkeypatch)  # 410.5 mi @ 6.5 MPG, $4.25/gal, $0.65/mi, $0 tolls

    breakdown = calculate_route_costs(410.5, 6.5)
    cost_per_mile = breakdown.total_cost / 410.5

    labels = _metrics(app)
    assert labels["Cost per Mile"] == f"${cost_per_mile:,.2f}"
    assert labels["Total Cost"] == f"${breakdown.total_cost:,.2f}"
    assert labels["Fuel Gallons"] == f"{breakdown.fuel_gallons:,.1f}"
    assert labels["Fuel Cost"] == f"${breakdown.fuel_cost:,.2f}"
    assert labels["Driver Cost"] == f"${breakdown.driver_cost:,.2f}"
    assert labels["Tolls"] == f"${breakdown.estimated_tolls:,.2f}"
    assert labels["Cost per Mile"] == "$1.30"

    per_mile_metric = next(m for m in app.metric if m.label == "Cost per Mile")
    assert per_mile_metric.delta == f"{cost_per_mile - 0.65:+,.2f}"


def test_cost_efficiency_updates_with_custom_inputs(monkeypatch):
    app = run_app(monkeypatch)

    mpg = _find_number_input(app, "Avg MPG")
    mpg.set_value(8.0)
    op_cost = _find_number_input(app, "Operating Cost ($/mi)")
    op_cost.set_value(0.80)
    app.run()
    assert not app.exception

    breakdown = calculate_route_costs(410.5, 8.0, operating_cost_per_mile=0.80)
    cost_per_mile = breakdown.total_cost / 410.5

    labels = _metrics(app)
    assert labels["Total Cost"] == f"${breakdown.total_cost:,.2f}"
    assert labels["Cost per Mile"] == f"${cost_per_mile:,.2f}"

    default = calculate_route_costs(410.5, 6.5)
    assert labels["Total Cost"] != f"${default.total_cost:,.2f}"
    assert labels["Cost per Mile"] != f"${default.total_cost / 410.5:,.2f}"


def test_cost_breakdown_zero_distance_guarded(monkeypatch):
    app = run_app(monkeypatch, result=make_result(distance_miles=0.0))
    assert not app.exception

    labels = _metrics(app)
    assert labels["Cost per Mile"] == "$0.00"
    assert labels["Total Cost"] == "$0.00"
    assert labels["Fuel Gallons"] == "0.0"