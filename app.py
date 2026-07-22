import folium
import streamlit as st
from streamlit_folium import st_folium

from engine import get_route_and_metrics

# Major US Freight Markets
MAJOR_FREIGHT_HUBS = [
    "San Bernardino, CA",
    "Ontario, CA",
    "Los Angeles, CA",
    "Fresno, CA",
    "Oakland, CA",
    "Phoenix, AZ",
    "Las Vegas, NV",
    "Salt Lake City, UT",
    "Seattle, WA",
    "Portland, OR",
    "Dallas, TX",
    "Houston, TX",
    "San Antonio, TX",
    "El Paso, TX",
    "Laredo, TX",
    "Chicago, IL",
    "Indianapolis, IN",
    "Columbus, OH",
    "Memphis, TN",
    "Nashville, TN",
    "Atlanta, GA",
    "Charlotte, NC",
    "Jacksonville, FL",
    "Miami, FL",
    "Kansas City, MO",
    "St. Louis, MO",
    "Minneapolis, MN",
    "Denver, CO",
    "Newark, NJ",
    "Harrisburg, PA",
]

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

col1, col2, col3 = st.columns([3, 3, 2])

with col1:
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

with col2:
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

with col3:
    st.write("##")
    calculate_btn = st.button(
        "Calculate Route", type="primary", use_container_width=True
    )

# Force recalculation when button is clicked or state is uninitialized
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
    m1, m2, m3 = st.columns(3)
    m1.metric("Driving Distance", f"{data['distance_miles']} miles")
    m2.metric("Est. Driving Time", f"{data['duration_hours']} hours")
    m3.metric("Dispatch Status", "Route Active")

    st.markdown("---")

    orig = data["origin"]
    dest = data["destination"]

    center_lat = (orig["lat"] + dest["lat"]) / 2
    center_lng = (orig["lng"] + dest["lng"]) / 2

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=6,
        tiles="CartoDB dark_matter",
    )

    folium.Marker(
        [orig["lat"], orig["lng"]],
        popup=f"Pickup: {orig['address']}",
        tooltip="Origin (Pickup)",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    folium.Marker(
        [dest["lat"], dest["lng"]],
        popup=f"Dropoff: {dest['address']}",
        tooltip="Destination (Dropoff)",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(m)

    folium.PolyLine(
        locations=data["geometry"],
        color="#00D2FF",
        weight=4,
        opacity=0.8,
    ).add_to(m)

    st_folium(m, width="100%", height=500)