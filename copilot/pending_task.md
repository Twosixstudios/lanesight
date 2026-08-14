# Task ID: 5.1 - Live Telemetry & GPS Matching

## Objective
1. Implement a telemetry ingestion module to process live GPS coordinates.
2. Develop a matching algorithm to compare current vehicle location against the active OSRM route polyline to calculate remaining distance and ETA.

## Target Files
- `lanesight/core/telemetry.py` (New)
- `lanesight/core/router.py`
- `lanesight/Tasks.md`

## Step-by-Step Requirements
1. Create `lanesight/core/telemetry.py` to handle incoming GPS data points (lat, lon, timestamp).
2. Implement a function `match_to_route(current_coords, route_polyline)` that identifies the nearest point on the route and calculates the remaining distance to the destination.
3. Update `lanesight/core/router.py` to expose an `update_eta(remaining_distance, average_speed)` method.
4. Update `lanesight/Tasks.md` to mark Task 5.1 as `[x]` and update the Active Phase to Phase 5.

## Guardrails & Verification
- Ensure the matching algorithm handles GPS drift (e.g., tolerance threshold of 50 meters).
- All new logic must be covered by unit tests in `tests/test_telemetry.py`.
- Run `git add . && git commit -m "feat(telemetry): complete Task 5.1 - Live Telemetry & GPS Matching" && git push origin main` upon successful verification.