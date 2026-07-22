import folium
import streamlit as st
from streamlit_folium import st_folium

from engine import get_route_and_metrics

# Page setup using fail-safe Streamlit emoji shortcodes
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

# User input controls
col1, col2, col3 = st.columns([3, 3, 2])

with col1:
    origin_input = st.text_input("Origin Location", value="Ontario, CA")
with col2:
    dest_input = st.text_input("Destination Location", value="Fresno, CA")
with col3:
    st.write("##")
    calculate_btn = st.button(
        "Calculate Route", type="primary", use_container_width=True
    )

# Session state management for route data
if calculate_btn or ("route_data" not in st.session_state):
    with st.spinner("Fetching route geometry & calculating transit metrics..."):
        st.session_state["route_data"] = get_route_and_metrics(
            origin_input, dest_input
        )

data = st.session_state.get("route_data")

if not data:
    st.error(
        "Could not resolve locations or calculate route. Please verify city names."
    )
else:
    # Key Metrics Header
    m1, m2, m3 = st.columns(3)
    m1.metric("Driving Distance", f"{data['distance_miles']} miles")
    m2.metric("Est. Driving Time", f"{data['duration_hours']} hours")
    m3.metric("Dispatch Status", "Route Active")

    st.markdown("---")

    # Interactive Dark Mode Map
    orig = data["origin"]
    dest = data["destination"]

    center_lat = (orig["lat"] + dest["lat"]) / 2
    center_lng = (orig["lng"] + dest["lng"]) / 2

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=6,
        tiles="CartoDB dark_matter",
    )

    # Pickup Pin (Green)
    folium.Marker(
        [orig["lat"], orig["lng"]],
        popup=f"Pickup: {orig['address']}",
        tooltip="Origin (Pickup)",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    # Dropoff Pin (Red)
    folium.Marker(
        [dest["lat"], dest["lng"]],
        popup=f"Dropoff: {dest['address']}",
        tooltip="Destination (Dropoff)",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(m)

    # Cyan Route Polyline
    folium.PolyLine(
        locations=data["geometry"],
        color="#00D2FF",
        weight=4,
        opacity=0.8,
    ).add_to(m)

    # Render Map Component
    st_folium(m, width="100%", height=500)