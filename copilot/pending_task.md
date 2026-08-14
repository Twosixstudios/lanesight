# Task ID: 5.2 - Route Deviation Alerts

## Objective
Implement a monitoring service that triggers alerts when a vehicle's telemetry data indicates it has deviated beyond the `GPS_DRIFT_TOLERANCE_METERS` (50m) from the active route polyline.

## Target Files
- `lanesight/core/telemetry.py`
- `lanesight/core/alerts.py` (New)
- `lanesight/Tasks.md`

## Step-by-Step Requirements
1. Create `lanesight/core/alerts.py` to define an `Alert` dataclass and a `DeviationMonitor` class.
2. Integrate `DeviationMonitor` with the existing `TelemetrySession` to track consecutive "off-route" samples.
3. Implement a threshold-based alert trigger (e.g., if a vehicle is off-route for > 3 consecutive samples, flag a `ROUTE_DEVIATION` alert).
4. Update `lanesight/Tasks.md` to mark Task 5.2 as `[x]` and confirm Phase 5 completion.

## Guardrails & Verification
- Ensure alerts are only triggered for significant, sustained deviations to avoid noise from minor GPS jitter.
- Add unit tests in `tests/test_alerts.py` to simulate on-route and off-route telemetry streams.
- Run `git add . && git commit -m "feat(alerts): complete Task 5.2 - Route Deviation Alerts" && git push origin main` upon successful verification.