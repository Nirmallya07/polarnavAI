# Integration and Ownership

## Module Ownership

### Developer A — Data + Machine Learning

Responsible for:
- sea-ice data
- sea-ice model
- iceberg data
- iceberg trajectory model
- model preprocessing
- model artifacts

### Developer B — Environment + Risk

Responsible for:
- weather
- ocean
- environmental data standardization
- risk engine
- time-aware risk calculation

### Developer C — Backend + Routing + Frontend

Responsible for:
- Flask API
- A*
- SAFE/BALANCED/FUEL_SAVER
- React dashboard
- final integration

## API Boundaries

- Frontend communicates only through API endpoints and backend services.
- Routes may validate request structure and return JSON responses.
- Business logic belongs in services.
- Machine learning code belongs in models.
- The frontend must not read scientific datasets directly.
- The route optimizer must not read NetCDF or GRIB files directly.

## Timestamp Convention

- All navigation requests and predictive outputs should use UTC timestamps.
- Request field: departure_time_utc
- All risk calculations should be time-aware and consider vessel position at a given time.

## Coordinate Convention

- Use latitude and longitude in decimal degrees.
- Latitude must remain between -90 and 90.
- Longitude must remain between -180 and 180.

## Rules for Modifying Contracts

- Any API contract change must be documented in the relevant schema and route files.
- Contract changes must be reviewed before they are merged.
- Avoid breaking field names without a migration plan.
- Preserve backward compatibility when possible.

## Git Collaboration Rules

- Work in feature branches.
- Keep commits focused and descriptive.
- Do not commit large datasets, secrets, or environment files.
- Only stage files relevant to the task.
- Ensure tests pass before merging.

## Module Data Contracts

The project uses explicit JSON Schemas to define the contract boundary between modules. These contracts define the exact payload that moves between the user, backend, environmental services, prediction services, risk engine, route optimizer, and final frontend response.

User
-> Navigation Request
-> Data/Prediction Services
-> Risk Engine
-> Route Optimizer
-> Navigation Response

The contracts allow developers to work independently. A model can be replaced internally without breaking downstream modules as long as it produces the same contract.

### Contract Rules

- Timestamps use UTC and must be ISO 8601 date-times.
- Latitude and longitude use decimal degrees with valid geographic ranges.
- Sea-ice concentration uses a normalized value between 0 and 1.
- Risk scores live in the range 0 to 100.
- Model outputs must include a model version identifier.
- Iceberg predictions include uncertainty in kilometers.
- Risk is time-dependent and must be evaluated with respect to the vessel's predicted position at a given time.
- Contracts must not be changed casually; any schema change must be reviewed and coordinated across modules.

## Initial Boundary Summary

This is intentionally a clean foundation so the three developers can work independently while preserving strict module boundaries.
