import requests
from geopy.distance import geodesic
from geopy.geocoders import Nominatim, Photon


def geocode_location(location_name: str):
    """Converts location string into (lat, lng, address) with multi-geocoder fallback."""
    # Strategy 1: Nominatim
    try:
        geo_nom = Nominatim(user_agent="lanesight_app_twosix_studios_v1")
        loc = geo_nom.geocode(location_name, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception as e:
        print(f"Nominatim lookup failed: {e}")

    # Strategy 2: Photon (OpenStreetMap data via Komoot, bypasses cloud IP bans)
    try:
        geo_photon = Photon(user_agent="lanesight_app_twosix_studios_v1")
        loc = geo_photon.geocode(location_name, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception as e:
        print(f"Photon lookup failed: {e}")

    return None, None, None


def get_route_and_metrics(origin_str: str, destination_str: str):
    """Fetches coordinates, driving route geometry, distance, and transit time."""
    orig_lat, orig_lng, orig_full = geocode_location(origin_str)
    dest_lat, dest_lng, dest_full = geocode_location(destination_str)

    if not orig_lat or not dest_lat:
        return None

    # Default baseline calculation using geodesic distance (~1.2x road curvature factor)
    direct_miles = round(
        geodesic((orig_lat, orig_lng), (dest_lat, dest_lng)).miles * 1.2, 1
    )
    est_hours = round(direct_miles / 55.0, 1)
    geometry_coords = [[orig_lat, orig_lng], [dest_lat, dest_lng]]

    # OSRM API Request
    osrm_url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{orig_lng},{orig_lat};{dest_lng},{dest_lat}"
        f"?overview=full&geometries=geojson"
    )
    headers = {"User-Agent": "LaneSight-App/1.0 (twosixstudios.dev@gmail.com)"}

    try:
        response = requests.get(osrm_url, headers=headers, timeout=8)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and data["routes"]:
                route = data["routes"][0]
                direct_miles = round(route["distance"] / 1609.34, 1)
                est_hours = round(route["duration"] / 3600, 1)
                geometry_coords = [
                    [lat, lng] for lng, lat in route["geometry"]["coordinates"]
                ]
    except Exception as e:
        print(f"OSRM routing failed, using geodesic fallback: {e}")

    return {
        "origin": {"lat": orig_lat, "lng": orig_lng, "address": orig_full},
        "destination": {
            "lat": dest_lat,
            "lng": dest_lng,
            "address": dest_full,
        },
        "distance_miles": direct_miles,
        "duration_hours": est_hours,
        "geometry": geometry_coords,
    }