import requests
from geopy.distance import geodesic
from geopy.geocoders import ArcGIS, Nominatim

# 50 US State Abbreviation Mapping
STATE_ABBREVS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def normalize_us_location(location_name: str) -> str:
    """Expands state abbreviations (e.g. 'Ontario, CA' -> 'Ontario, California, USA')

    to prevent Canada/international geocoding mix-ups.
    """
    clean = location_name.strip()
    parts = [p.strip() for p in clean.split(",")]

    if len(parts) >= 2:
        state_part = parts[1].upper()
        if state_part in STATE_ABBREVS:
            parts[1] = STATE_ABBREVS[state_part]
            if len(parts) == 2:
                parts.append("USA")
            return ", ".join(parts)

    if "usa" not in clean.lower() and "united states" not in clean.lower():
        clean += ", USA"

    return clean


def geocode_location(location_name: str):
    """Converts location string into (lat, lng, address)."""
    normalized_query = normalize_us_location(location_name)
    print(
        f"[LaneSight Log] Geocoding query: '{normalized_query}' (Raw input: '{location_name}')"
    )

    # Strategy 1: ArcGIS (Zero API key required, cloud friendly)
    try:
        geo_arcgis = ArcGIS(user_agent="lanesight_twosix_studios_v1")
        loc = geo_arcgis.geocode(normalized_query, timeout=10)
        if loc:
            print(
                f"[LaneSight Log] ArcGIS Success -> {loc.address} ({loc.latitude}, {loc.longitude})"
            )
            return loc.latitude, loc.longitude, loc.address
    except Exception as e:
        print(f"[LaneSight Log] ArcGIS geocoding failed: {e}")

    # Strategy 2: Nominatim (Fallback)
    try:
        geo_nom = Nominatim(user_agent="lanesight_twosix_studios_v1")
        loc = geo_nom.geocode(normalized_query, timeout=10)
        if loc:
            print(
                f"[LaneSight Log] Nominatim Success -> {loc.address} ({loc.latitude}, {loc.longitude})"
            )
            return loc.latitude, loc.longitude, loc.address
    except Exception as e:
        print(f"[LaneSight Log] Nominatim geocoding failed: {e}")

    return None, None, None


def get_route_and_metrics(origin_str: str, destination_str: str):
    """Fetches coordinates, driving route geometry, distance, and transit time."""
    orig_lat, orig_lng, orig_full = geocode_location(origin_str)
    dest_lat, dest_lng, dest_full = geocode_location(destination_str)

    if not orig_lat or not dest_lat:
        return None

    # Geodesic baseline fallback (~1.2x road factor)
    direct_miles = round(
        geodesic((orig_lat, orig_lng), (dest_lat, dest_lng)).miles * 1.2, 1
    )
    est_hours = round(direct_miles / 55.0, 1)
    geometry_coords = [[orig_lat, orig_lng], [dest_lat, dest_lng]]

    # OSRM Driving Route Request
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
                print(
                    f"[LaneSight Log] OSRM Route Fetched: {direct_miles} miles, {est_hours} hrs"
                )
    except Exception as e:
        print(
            f"[LaneSight Log] OSRM routing failed, using geodesic fallback: {e}"
        )

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