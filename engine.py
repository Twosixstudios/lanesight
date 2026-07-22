import requests
from geopy.geocoders import Nominatim

# Unique User-Agent required by OpenStreetMap policy for cloud servers
geolocator = Nominatim(user_agent="lanesight_twosix_studios_v1")


def geocode_location(location_name: str):
    """Converts a city/address string into (latitude, longitude)."""
    try:
        loc = geolocator.geocode(location_name, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception as e:
        print(f"Geocoding error for '{location_name}': {e}")
    return None, None, None


def get_route_and_metrics(origin_str: str, destination_str: str):
    """Fetches geocodes, driving distance, transit hours, and geometry polyline

    from OSRM.
    """
    orig_lat, orig_lng, orig_full = geocode_location(origin_str)
    dest_lat, dest_lng, dest_full = geocode_location(destination_str)

    if not orig_lat or not dest_lat:
        return None

    # Secure HTTPS endpoint
    osrm_url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{orig_lng},{orig_lat};{dest_lng},{dest_lat}"
        f"?overview=full&geometries=geojson"
    )

    # User-Agent header prevents cloud IP blocks on Streamlit Cloud
    headers = {
        "User-Agent": "LaneSight-TwoSixStudios/1.0 (twosixstudios.dev@gmail.com)"
    }

    try:
        response = requests.get(osrm_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        if "routes" not in data or not data["routes"]:
            return None

        route = data["routes"][0]

        # OSRM returns distance in meters and duration in seconds
        distance_miles = round(route["distance"] / 1609.34, 1)
        duration_hours = round(route["duration"] / 3600, 1)

        # Coordinates array for Folium map polyline
        geometry_coords = [
            [lat, lng] for lng, lat in route["geometry"]["coordinates"]
        ]

        return {
            "origin": {"lat": orig_lat, "lng": orig_lng, "address": orig_full},
            "destination": {
                "lat": dest_lat,
                "lng": dest_lng,
                "address": dest_full,
            },
            "distance_miles": distance_miles,
            "duration_hours": duration_hours,
            "geometry": geometry_coords,
        }
    except Exception as e:
        print(f"OSRM request error: {e}")
        return None