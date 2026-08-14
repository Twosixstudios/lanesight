/clea# Task ID: 4.2 - FastAPI Headless Wrapper

## Objective
1. Implement a FastAPI application to expose `/api/v1/route` and `/api/v1/geocode` endpoints.
2. Utilize the `lanesight.core` package (Task 4.1) to handle business logic.
3. Ensure the API is documented via Swagger/OpenAPI (default FastAPI behavior).

## Target Files
- `lanesight/api/main.py` (new: FastAPI application entry point)
- `lanesight/api/schemas.py` (new: Pydantic models for request/response validation)
- `Tasks.md` (mark Task 4.2 as [x] once verified)

## Step-by-Step Requirements
1. Create `lanesight/api/schemas.py` defining request models for `RouteRequest` (origins, destinations, vehicle specs) and `GeocodeRequest`.
2. Create `lanesight/api/main.py`:
   - Initialize `FastAPI` instance.
   - Implement `POST /api/v1/route` that calls `lanesight.core.router.Router`.
   - Implement `POST /api/v1/geocode` that calls `lanesight.core.router.geocoder`.
3. Add a simple test in `tests/test_api.py` using `fastapi.testclient.TestClient` to verify endpoint responses.
4. Update `Tasks.md` to mark Task 4.2 as `[x]`.

## Guardrails & Verification
- Ensure the API handles errors gracefully (e.g., invalid coordinates) and returns appropriate HTTP status codes.
- Do not expose database internals directly; use Pydantic schemas for all I/O.
- Run `pytest tests/test_api.py` to verify the new endpoints.
- Run `git add . && git commit -m "feat(api): complete Task 4.2 - FastAPI Headless Wrapper" && git push origin main` upon successful verification.