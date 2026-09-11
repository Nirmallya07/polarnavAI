# Architecture Overview

## Intended Pipeline

User Input
→ Environmental Data
→ Preprocessing
→ Sea-Ice Prediction
→ Iceberg Prediction
→ Time-Aware Risk
→ A* Route Optimization
→ Navigation Recommendation
→ React Dashboard

## Responsibilities

### Environmental Data

Environmental data sources provide weather and ocean context needed to determine operating conditions along a vessel path.

### Preprocessing

This layer standardizes coordinate systems, timestamps, units, and spatial resolution before model inference.

### Sea-Ice Prediction

The sea-ice model estimates future coverage and risk around the vessel route. It is responsible only for prediction outputs, not route decision-making.

### Iceberg Prediction

The iceberg model estimates future iceberg drift and probability of encounter. It should output trajectories and confidence values, not final navigation actions.

### Time-Aware Risk

The risk engine combines environmental data, sea-ice output, and iceberg output into a time-aware risk model. This is the stage that converts predictions into a risk score over time and space.

### A* Route Optimization

The route optimizer interprets risk values and computes candidate routes. It should optimize for mode: SAFE, BALANCED, or FUEL_SAVER.

### Navigation Recommendation

The final recommendation layer translates the chosen route into a clear vessel-level navigation decision and supporting explanation.

### React Dashboard

The dashboard reads the final recommendation objects from the backend and presents them in a simple UI for monitoring and decision support.

## Architectural Rules

- Routes handle HTTP/API concerns only.
- Services contain business logic.
- Models contain ML logic only.
- The frontend never reads scientific datasets directly.
- The route optimizer never reads NetCDF or GRIB files directly.
- ML models never decide safe versus dangerous.
- The risk engine converts predictions into risk.
- The optimizer converts risk into route decisions.
