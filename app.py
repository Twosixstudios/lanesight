import logging

import folium
import streamlit as st
from streamlit_folium import st_folium

from lanesight.core.costs import (
    DEFAULT_ESTIMATED_TOLLS,
    DEFAULT_FUEL_PRICE_PER_GALLON,
    DEFAULT_OPERATING_COST_PER_MILE,
    calculate_route_costs,
)
from lanesight.core.hos import (
    BREAK_DURATION_HOURS,
    CYCLE_LIMIT_HOURS,
    DAILY_DRIVE_LIMIT_HOURS,
    DAILY_DUTY_WINDOW_HOURS,
    calculate_route_hos,
)
from lanesight.core.router import Router
from lanesight.hubs import MAJOR_FREIGHT_HUBS
from lanesight.models import Driver

logging.basicConfig(
    level=logging.INFO,
    format="[LaneSight] %(levelname)s: %(message)s",
)

st.set_page_config(
    page_title="LaneSight | Dispatch & Transit Engine",
    page_icon=":world_map:",
    layout="wide",
)

st.title(":world_map: LaneSight")
st.caption(
    "Open-source freight route visualizer & transit time engine by Two Six Studios"
)
st.markdown("---")


@st.cache_resource
def get_router() -> Router:
    return Router()


# Preset driver clock states used to populate the sidebar HOS inputs.
DRIVER_PRESETS: dict[str, tuple[float, float, float] | None] = {
    "Fresh Driver (11h / 14h / 70h)": (
        DAILY_DRIVE_LIMIT_HOURS,
        DAILY_DUTY_WINDOW_HOURS,
        CYCLE_LIMIT_HOURS,
    ),
    "Fatigued Driver (5h / 8h / 45h)": (5.0, 8.0, 45.0),
    "Custom Clocks": None,
}


# ------------------------------------------------------------------ #
# Sidebar: route planner with dynamic multi-stop waypoints
# ------------------------------------------------------------------ #
with st.sidebar:
    st.header("Route Planner")

    origin_select = st.selectbox(
        "Origin Location",
        options=MAJOR_FREIGHT_HUBS + ["Custom Location..."],
        index=0,  # San Bernardino, CA
    )
    if origin_select == "Custom Location...":
        origin_input = st.text_input(
            "Enter Custom Origin", value="San Bernardino, California"
        )
    else:
        origin_input = origin_select

    dest_select = st.selectbox(
        "Destination Location",
        options=MAJOR_FREIGHT_HUBS + ["Custom Location..."],
        index=4,  # Oakland, CA
    )
    if dest_select == "Custom Location...":
        dest_input = st.text_input(
            "Enter Custom Destination", value="Oakland, California"
        )
    else:
        dest_input = dest_select

    st.markdown("---")
    st.subheader("Intermediate Stops")

    if "num_stops" not in st.session_state:
        st.session_state.num_stops = 0

    add_col, remove_col = st.columns(2)
    if add_col.button("+ Add Stop", width="stretch"):
        st.session_state.num_stops += 1
    if (
        remove_col.button("- Remove Stop", width="stretch")
        and st.session_state.num_stops > 0
    ):
        st.session_state.num_stops -= 1

    waypoints: list[str] = []
    for index in range(st.session_state.num_stops):
        stop_select = st.selectbox(
            f"Stop {index + 1}",
            options=MAJOR_FREIGHT_HUBS + ["Custom Location..."],
            key=f"stop_select_{index}",
        )
        if stop_select == "Custom Location...":
            stop_input = st.text_input(
                f"Custom Stop {index + 1}", key=f"stop_input_{index}"
            )
        else:
            stop_input = stop_select
        waypoints.append(stop_input)

    st.markdown("---")
    st.subheader("Driver Hours of Service (HOS)")


    def _apply_driver_preset() -> None:
        """Load the selected preset's clocks into the HOS number inputs."""
        values = DRIVER_PRESETS[st.session_state["hos_preset"]]
        if values is None:
            return
        (
            st.session_state["hos_drive_in"],
            st.session_state["hos_shift_in"],
            st.session_state["hos_cycle_in"],
        ) = values


    st.selectbox(
        "Driver Clock State",
        options=list(DRIVER_PRESETS),
        index=0,
        key="hos_preset",
        on_change=_apply_driver_preset,
    )

    st.session_state.setdefault("hos_drive_in", DAILY_DRIVE_LIMIT_HOURS)
    st.session_state.setdefault("hos_shift_in", DAILY_DUTY_WINDOW_HOURS)
    st.session_state.setdefault("hos_cycle_in", CYCLE_LIMIT_HOURS)

    drive_remaining = st.number_input(
        "Drive Hours Remaining",
        min_value=0.0,
        max_value=CYCLE_LIMIT_HOURS,
        step=0.5,
        key="hos_drive_in",
    )
    shift_remaining = st.number_input(
        "Shift Hours Remaining",
        min_value=0.0,
        max_value=CYCLE_LIMIT_HOURS,
        step=0.5,
        key="hos_shift_in",
    )
    cycle_remaining = st.number_input(
        "Cycle Hours Remaining",
        min_value=0.0,
        max_value=CYCLE_LIMIT_HOURS,
        step=0.5,
        key="hos_cycle_in",
    )

    st.markdown("---")
    st.subheader("Cost Assumptions")

    st.session_state.setdefault("cost_mpg", 6.5)
    st.session_state.setdefault("cost_fuel_price", DEFAULT_FUEL_PRICE_PER_GALLON)
    st.session_state.setdefault("cost_operating_cost", DEFAULT_OPERATING_COST_PER_MILE)
    st.session_state.setdefault("cost_tolls", DEFAULT_ESTIMATED_TOLLS)

    avg_mpg = st.number_input("Avg MPG", min_value=1.0, step=0.5, key="cost_mpg")
    fuel_price = st.number_input(
        "Fuel Price ($/gal)", step=0.05, key="cost_fuel_price"
    )
    operating_cost = st.number_input(
        "Operating Cost ($/mi)", step=0.05, key="cost_operating_cost"
    )
    estimated_tolls = st.number_input(
        "Estimated Tolls ($)", min_value=0.0, step=5.0, key="cost_tolls"
    )

    st.markdown("---")
    calculate_btn = st.button("Calculate Route", type="primary", width="stretch")
# ------------------------------------------------------------------ #
# Route computation (wired directly into lanesight.core.router.route)
# ------------------------------------------------------------------ #
if calculate_btn or ("route_result" not in st.session_state):
    with st.spinner("Fetching route geometry & calculating transit metrics..."):
        try:
            st.session_state["route_result"] = get_router().route(
                origin_input, dest_input, waypoints=waypoints
            )
            st.session_state.pop("route_error", None)
        except ValueError as exc:
            st.session_state["route_result"] = None
            st.session_state["route_error"] = str(exc)

result = st.session_state.get("route_result")

if result is None:
    error_msg = st.session_state.get("route_error")
    if error_msg:
        st.error(f"Route calculation failed: {error_msg}")
    else:
        st.info(
            "Set your origin, destination, and any stops in the sidebar, "
            "then press 'Calculate Route'."
        )
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Distance", f"{result.distance_miles:,.1f} miles")
    m2.metric("Total Duration", f"{result.duration_hours:,.1f} hours")
    m3.metric("Dispatch Status", "Route Active")

    st.markdown("---")

    # ------------------------------------------------------------------ #
    # Hours of Service (HOS) compliance
    # ------------------------------------------------------------------ #
    driver = Driver(
        name="Assigned Driver",
        cdl_number="ASSIGNED-0001",
        cdl_state="CA",
        is_active=True,
        drive_hours_remaining=drive_remaining,
        shift_hours_remaining=shift_remaining,
        cycle_hours_remaining=cycle_remaining,
    )
    hos = calculate_route_hos(result.duration_hours, driver)

    st.subheader("Hours of Service (HOS) Compliance")

    if hos["is_legal"]:
        st.success(
            f"HOS Compliant - trip fits within remaining driver clocks "
            f"(estimated drive {result.duration_hours:,.1f} hrs)."
        )
    else:
        st.error("HOS Violation / Out of Service - trip exceeds available driver hours.")

    h1, h2 = st.columns(2)
    h1.metric("Mandatory Rest Breaks", int(hos["required_breaks"]))
    h2.metric(
        "Total Elapsed Trip Time",
        f"{hos['total_elapsed_hours']:,.1f} hrs",
        delta=f"+{hos['required_breaks'] * BREAK_DURATION_HOURS:,.1f} breaks",
        delta_color="off",
        help="Estimated driving hours plus mandatory 30-minute rest breaks.",
    )

    c1, c2, c3 = st.columns(3)
    drive_after = hos["updated_driver_clocks"]["drive_hours_remaining"]
    shift_after = hos["updated_driver_clocks"]["shift_hours_remaining"]
    cycle_after = hos["updated_driver_clocks"]["cycle_hours_remaining"]

    c1.metric(
        "Drive Hrs Remaining",
        f"{drive_after:,.1f}",
        delta=f"{drive_after - drive_remaining:+,.1f}",
        delta_color="inverse",
    )
    c1.progress(
        min(max(drive_after, 0.0) / DAILY_DRIVE_LIMIT_HOURS, 1.0),
        text=f"{drive_remaining:,.1f}h → {drive_after:,.1f}h post-trip",
    )

    c2.metric(
        "Shift Hrs Remaining",
        f"{shift_after:,.1f}",
        delta=f"{shift_after - shift_remaining:+,.1f}",
        delta_color="inverse",
    )
    c2.progress(
        min(max(shift_after, 0.0) / DAILY_DUTY_WINDOW_HOURS, 1.0),
        text=f"{shift_remaining:,.1f}h → {shift_after:,.1f}h post-trip",
    )

    c3.metric(
        "Cycle Hrs Remaining",
        f"{cycle_after:,.1f}",
        delta=f"{cycle_after - cycle_remaining:+,.1f}",
        delta_color="inverse",
    )
    c3.progress(
        min(max(cycle_after, 0.0) / CYCLE_LIMIT_HOURS, 1.0),
        text=f"{cycle_remaining:,.1f}h → {cycle_after:,.1f}h post-trip",
    )

    st.markdown("---")

    st.subheader("Cost Efficiency")
    cost_breakdown = calculate_route_costs(
        result.distance_miles,
        avg_mpg,
        fuel_price,
        operating_cost,
        estimated_tolls,
    )
    cost_per_mile = (
        cost_breakdown.total_cost / result.distance_miles
        if result.distance_miles > 0
        else 0.0
    )
    delta_per_mile = cost_per_mile - DEFAULT_OPERATING_COST_PER_MILE

    e1, e2, e3 = st.columns(3)
    e1.metric(
        "Cost per Mile",
        f"${cost_per_mile:,.2f}",
        delta=f"{delta_per_mile:+,.2f}",
        delta_color="inverse",
        help="Total trip cost divided by route miles, relative to the per-mile operating baseline.",
    )
    e2.metric("Total Cost", f"${cost_breakdown.total_cost:,.2f}")
    e3.metric("Fuel Gallons", f"{cost_breakdown.fuel_gallons:,.1f}")

    e4, e5, e6 = st.columns(3)
    e4.metric("Fuel Cost", f"${cost_breakdown.fuel_cost:,.2f}")
    e5.metric("Driver Cost", f"${cost_breakdown.driver_cost:,.2f}")
    e6.metric("Tolls", f"${cost_breakdown.estimated_tolls:,.2f}")

    st.markdown("---")

    with st.expander(
        f"Leg Breakdown ({len(result.waypoints)} stops)", expanded=True
    ):
        leg_rows = [
            {
                "Leg": f"Leg {index + 1}",
                "From": leg["origin"],
                "To": leg["destination"],
                "Distance (mi)": f'{leg["distance_miles"]:,.1f}',
                "Duration (hrs)": f'{leg["duration_hours"]:,.1f}',
            }
            for index, leg in enumerate(result.legs)
        ]
        st.dataframe(leg_rows, width="stretch", hide_index=True)

    st.markdown("---")

    orig = result.origin
    dest = result.destination

    center_lat = (orig.lat + dest.lat) / 2
    center_lng = (orig.lng + dest.lng) / 2

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=6,
        tiles="CartoDB dark_matter",
    )

    folium.Marker(
        [orig.lat, orig.lng],
        popup=f"Pickup: {orig.address}",
        tooltip="Origin (Pickup)",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    for index, stop_point in enumerate(result.waypoints[1:-1], start=1):
        folium.Marker(
            [stop_point.lat, stop_point.lng],
            popup=f"Stop {index}: {stop_point.address}",
            tooltip=f"Stop {index}",
            icon=folium.Icon(color="orange", icon="info-sign"),
        ).add_to(m)

    folium.Marker(
        [dest.lat, dest.lng],
        popup=f"Dropoff: {dest.address}",
        tooltip="Destination (Dropoff)",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(m)

    folium.PolyLine(
        locations=result.geometry,
        color="#00D2FF",
        weight=4,
        opacity=0.8,
    ).add_to(m)

    st_folium(m, width="100%", height=500)
