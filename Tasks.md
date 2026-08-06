---

kanban-plugin: board

---

## kanban-plugin: board



## 🚚 LaneSight - Architecture & Rules

- [ ] **Agent Instructions & Guidelines**
	- Always check this file before starting work on a task.
	- Only work on tasks marked as `[ ]` under the **Active Phase**.
	- Once a task is completed and verified, update its status to `[x]` and commit `Tasks.md` alongside code changes.


## 🎯 Current Status

- [ ] **Active Phase**: Phase 1 - Foundation, Cleanup & Data Schema
- [ ] **Target Deliverable**: Clean repo root, persistent database schema for fleet assets, and saved route logging.
- [x] **Overall Progress**: 6 / 15 Tasks Completed (40.0%)


## 📌 Phase 1: Core Engine & Foundation

- [x] **Task 1.1: Core Routing & Geocoding Engine** #priority/high
	- **Description**: Implement OSRM routing with geodesic fallback and US location normalization.
	- **Prerequisites**: None
- [x] **Task 1.2: Pytest Suite & Streamlit Visualizer** #priority/high
	- **Description**: Build Folium map visualizer in Streamlit frontend and mock API test suite.
	- **Prerequisites**: Task 1.1
- [ ] **Task 1.3: Repo Housekeeping & Cleanup** #priority/high
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
- [ ] **Task 2.3: Commercial Route Controls** #priority/low
	- **Description**: Add configuration flags for toll avoidance and highway routing preferences.
	- **Prerequisites**: Task 2.1


## 📊 Phase 3: Operating Cost Analytics

- [ ] **Task 3.1: Fuel Cost & MPG Engine** #priority/medium
	- **Description**: Calculate diesel fuel consumption and cost estimates based on truck MPG settings.
	- **Prerequisites**: Task 2.1
- [ ] **Task 3.2: Dispatch Summary PDF Export** #priority/medium
	- **Description**: Generate printable/downloadable dispatch summary sheets for driver hand-offs.
	- **Prerequisites**: Task 3.1
- [ ] **Task 3.3: Cost Efficiency Analytics** #priority/low
	- **Description**: Display cost-per-mile and efficiency metrics directly in the Streamlit dashboard.
	- **Prerequisites**: Task 3.1


## 🔌 Phase 4: SDK & REST Microservice

- [ ] **Task 4.1: Core SDK Packaging** #priority/high
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
{"kanban-plugin":"board","show-checkboxes":true,"full-list-lane-width":true,"show-relative-date":true,"link-date-to-daily-note":true}
```
%%