---
kanban-plugin: list
---

## kanban-plugin: board



## 🚚 LaneSight - Architecture & Rules

- [x] **Agent Instructions & Guidelines**
	- Always check this file before starting work on a task.
	- Only work on tasks marked as `[ ]` under the **Active Phase**.
	- Once a task is completed and verified, update its status to `[x]` and commit `Tasks.md` alongside code changes.


## 🎯 Current Status

- [ ] **Active Phase**: Phase 3 - Interactive UI & Dispatch Dashboard
- [ ] **Target Deliverable**: Interactive Streamlit UI featuring multi-stop route visualizer, HOS duty clock status, route financial cost breakdown, and persistent dispatch log views.
- [x] **Overall Progress**: 13 / 15 Tasks Completed (86.7%)


## 📌 Phase 1: Core Engine & Foundation

- [x] **Task 1.1: Core Routing & Geocoding Engine** #priority/high
	- **Description**: Implement OSRM routing with geodesic fallback and US location normalization.
	- **Prerequisites**: None
- [x] **Task 1.2: Pytest Suite & Streamlit Visualizer** #priority/high
	- **Description**: Build Folium map visualizer in Streamlit frontend and mock API test suite.
	- **Prerequisites**: Task 1.1
- [x] **Task 1.3: Repo Housekeeping & Cleanup** #priority/high
	- **Description**: Delete legacy Express bridge files (`bridge.mjs`, `server.mjs`, `package.json`) and update `.gitignore`.
	- **Prerequisites**: Task 1.2
- [x] **Task 1.4: Database Layer & Fleet Schema** #priority/high
	- **Description**: Integrate SQLite database layer using SQLAlchemy/SQLModel for routes, vehicles, and logs.
	- **Prerequisites**: Task 1.3


## 🚛 Phase 2: Commercial Trucking Engine

- [x] **Task 2.1: Multi-Stop Waypoint Engine** #priority/high
	- **Description**: Extend `Router.route()` to handle multiple waypoint stops and map polyline rendering.
	- **Prerequisites**: Task 1.4
- [x] **Task 2.2: HOS & Rest Break Estimator** #priority/high
	- **Description**: Calculate DOT 30-min break and 10-hr sleeper berth pauses based on driving hours.
	- **Prerequisites**: Task 2.1
- [x] **Task 2.3: Operating Costs & Toll Engine** #priority/low
	- **Description**: Compute fuel consumption and cost estimates from vehicle MPG, driver/operational per-mile rates, and tolls via `lanesight/core/costs.py`.
	- **Prerequisites**: Task 2.1
- [x] **Task 2.4: Commercial Route Controls & Constraints** #priority/high
	- **Description**: Evaluate route compliance against vehicle height, gross weight, and hazmat limits via `lanesight/core/constraints.py`.
	- **Prerequisites**: Task 2.1


## 📊 Phase 3: Operating Cost Analytics

- [x] **Task 3.1: Streamlit Dashboard Refactor & Multi-Stop UI** #priority/medium
	- **Description**: Add dynamic add/remove multi-stop waypoint inputs to the Streamlit sidebar, wire locations into `lanesight.core.router.route()`, and render total distance/duration metrics, per-leg breakdowns, and the route overview map with graceful error alerts.
	- **Prerequisites**: Task 2.1
- [x] **Task 3.2: HOS & Driver Duty Status Dashboard** #priority/medium
	- **Description**: Integrate `lanesight.core.hos` into the Streamlit dashboard with driver clock presets/custom inputs, HOS compliance status badges, mandatory rest break metrics, total elapsed trip time, and post-trip remaining-clock progress bars. Verified via Streamlit `AppTest` UI tests.
	- **Prerequisites**: Task 3.1
- [x] **Task 3.3: Cost Efficiency Analytics** #priority/low
	- **Description**: Display cost-per-mile and efficiency metrics directly in the Streamlit dashboard.
	- **Prerequisites**: Task 3.1


## 🔌 Phase 4: SDK & REST Microservice

- [x] **Task 4.1: Core SDK Packaging** #priority/high
	- **Description**: Configure `pyproject.toml` to build `lanesight.core` as a standalone pip package.
	- **Prerequisites**: Task 2.1
- [ ] **Task 4.2: FastAPI Headless Wrapper** #priority/high
	- **Description**: Expose `/api/v1/route` and `/api/v1/geocode` REST endpoints for external apps.
	- **Prerequisites**: Task 4.1
- [ ] **Task 4.3: Test Suite Expansion** #priority/medium
	- **Description**: Expand pytest suite for multi-stop routing and HOS calculation logic.
	- **Prerequisites**: Task 4.1


## 📡 Phase 5: Fleet Scout Live Integration

- [ ] **Task 5.1: Live Telemetry & GPS Matching** #priority/high
	- **Description**: Recalculate remaining distance and ETA in real time using active GPS coordinates.
	- **Prerequisites**: Task 4.2
- [ ] **Task 5.2: Route Deviation Alerts** #priority/medium
	- **Description**: Detect when a vehicle strays from the calculated OSRM route polyline.
	- **Prerequisites**: Task 5.1




%% kanban:settings
```
{"kanban-plugin":"list","show-checkboxes":true,"full-list-lane-width":true,"show-relative-date":true,"link-date-to-daily-note":true}
```
%%