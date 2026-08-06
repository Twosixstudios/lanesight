import logging

import folium
import streamlit as st
from streamlit_folium import st_folium

from lanesight.core.router import Router
from lanesight.hubs import MAJOR_FREIGHT_HUBS

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
