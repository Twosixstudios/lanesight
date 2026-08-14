# Task ID: 4.3 - Test Suite Expansion

## Objective
1. Expand the `pytest` suite to provide comprehensive coverage for multi-stop routing logic and HOS calculation edge cases.
2. Ensure all new tests are integrated into the existing CI/CD pipeline.

## Target Files
- `tests/test_routing.py` (or relevant test file)
- `tests/test_hos.py` (or relevant test file)
- `lanesight/Tasks.md`

## Step-by-Step Requirements
1. Develop unit and integration tests for `lanesight.core.router.route()` specifically targeting multi-stop waypoints (e.g., 3+ stops, circular routes, and invalid waypoint sequences).
2. Develop tests for `lanesight.core.hos` to verify 30-minute break triggers and 10-hour sleeper berth reset logic under various driving hour scenarios.
3. Ensure all tests use `pytest` and mock external dependencies where necessary to maintain speed and reliability.
4. Update `lanesight/Tasks.md` to mark Task 4.3 as `[x]` and update the overall progress to 15/15.

## Guardrails & Verification
- All tests must pass with `python -m pytest`.
- Maintain 100% pass rate for existing tests.
- Run `git add . && git commit -m "feat(test): complete Task 4.3 - Test Suite Expansion" && git push origin main` upon successful verification.