# LaneSight

LaneSight is an open-source freight route visualizer and transit time engine designed to give dispatchers, brokers, and fleet managers macro route visibility, driving mile calculations, and baseline transit metrics without requiring proprietary mapping API keys or paid billing setups.

Built by Two Six Studios.

---

## Features

* Instant Geocoding: Converts address and city inputs into precise latitude/longitude coordinates using OpenStreetMap's Nominatim engine.
* OSRM Routing Integration: Pulls real road network geometry, driving mileage, and estimated transit hours.
* Interactive Dark-Mode Map: Embedded Folium rendering with customizable pickup (origin) and dropoff (destination) markers alongside a highlighted route polyline.
* Zero Billing / No-Key Architecture: Runs 100% on open-source GIS tools.

---

## Tech Stack

* Framework: Python 3, Streamlit
* Geospatial & Mapping: Folium, streamlit-folium
* Geocoding & Routing: geopy, OSRM (Open Source Routing Machine)
* Version Control: Git, GitHub

---

## Quick Start

1. Clone the repository:
   git clone https://github.com/YOUR_GITHUB_USERNAME/lanesight.git
   cd lanesight

2. Set up a virtual environment:
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Run the Streamlit app:
   streamlit run app.py