# SIH Problem Statement 26028: FastAPI Live ETA Inference Backend

**Date**: 2026-09-30  
**Service**: SIH 26028 - Dynamic Train ETA Live Inference API  
**Server Framework**: FastAPI + Uvicorn ASGI  
**Status**: Production-Ready / Fully Verified  

---

## 1. Overview & Architecture

The FastAPI backend connects the verified **RailRadar Live Train Running Status API** with the trained multi-horizon **XGBoost ETA inference models** (`H1`, `H2`, `H3`) to deliver real-time arrival predictions for Indian Railways trains.

```
                          Client HTTP Request
                     GET /api/train/{train_no}/eta
                                  |
                                  v
                     +--------------------------+
                     |  FastAPI Routing Engine  |
                     | (Validation & Rate Gate) |
                     +------------+-------------+
                                  |
               +------------------+------------------+
               | (Cache Hit)                         | (Cache Miss)
               v                                     v
      +-----------------+                   +------------------+
      |  In-Memory TTL  |                   | RailRadar Client |
      |   Cache (30s)   |                   |  (Live or Mock)  |
      +--------+--------+                   +--------+---------+
               |                                     |
               |                                     v
               |                            +------------------+
               |                            | Response Parser  |
               |                            | (Normalized State|
               |                            |  & Delay Lags)   |
               |                            +--------+---------+
               |                                     |
               |                                     v
               |                            +------------------+
               |                            | Feature Builder  |
               |                            | (Route Topology) |
               |                            +--------+---------+
               |                                     |
               |                                     v
               |                            +------------------+
               |                            | XGBoost Boosters |
               |                            | (H1, H2, H3)     |
               |                            +--------+---------+
               |                                     |
               |                                     v
               |                            +------------------+
               |                            |  ETA Calculator  |
               |                            | (Sched + Delay)  |
               |                            +--------+---------+
               |                                     |
               +------------------+------------------+
                                  |
                                  v
                        Clean JSON Response
                 (ISO 8601 Timestamps, No Leakage)
```

---

## 2. API Endpoints

### 1. Live Train ETA Prediction
- **Endpoint**: `GET /api/train/{train_no}/eta`
- **Path Parameter**: `train_no` — 4 or 5 digit numeric train number (e.g., `12301`, `12951`, `12002`).
- **Query Parameter**: `date` — Optional journey start date (`YYYY-MM-DD`).
- **Description**: Gated live endpoint. Calls RailRadar, reconstructs delay lags, maps route timetable topology, runs XGBoost models, and caches response.

### 2. Demo Train ETA Prediction
- **Endpoint**: `GET /api/demo/train/{train_no}/eta`
- **Path Parameter**: `train_no` (e.g. `12301`, `12951`, `12002`).
- **Description**: Uses deterministic synthetic data. Always accessible for frontend development without consuming external API quota.

### 3. System Health & Diagnostics
- **Endpoint**: `GET /api/health`
- **Description**: Reports service operational status, live API configuration status (masked secret), and cache hit/miss metrics.

---

## 3. Request & Response Specification

### Successful Response Format
The endpoint returns a clean JSON structure adhering strictly to the SIH 26028 specification:

```json
{
  "success": true,
  "train_no": "12301",
  "train_name": "Howrah - New Delhi Rajdhani Express",
  "status": "running",
  "journey_date": "2026-09-29",
  "current_station": {
    "code": "CNB",
    "name": "Kanpur Central",
    "delay_minutes": 3.0
  },
  "predictions": [
    {
      "horizon": 1,
      "station": "NDLS",
      "scheduled_arrival": "2026-09-30T10:05:00",
      "predicted_delay_minutes": 7.60,
      "predicted_eta": "2026-09-30T10:12:36"
    }
  ]
}
```

### Response Attributes
- `success`: Boolean indicating successful query execution.
- `train_no`: 5-digit normalized Indian Railways train number.
- `train_name`: Commercial service name from railway timetable master.
- `status`: Real-time operational running status (`"running"`, `"departed"`, `"arrived"`).
- `journey_date`: Date the train commenced its run from the origin terminal (`YYYY-MM-DD`).
- `current_station`:
  - `code`: Station code of the last commercial scheduled stop passed (e.g. `CNB`).
  - `name`: Full commercial station name (e.g. `Kanpur Central`).
  - `delay_minutes`: Current operational delay at reference point.
- `predictions`: Array of horizon predictions matching available route stops.
  - `horizon`: Target stop horizon (1 = next stop, 2 = 2 stops ahead, 3 = 3 stops ahead).
  - `station`: Scheduled station code.
  - `scheduled_arrival`: Standardized ISO 8601 timetable arrival timestamp (`YYYY-MM-DDTHH:MM:SS`).
  - `predicted_delay_minutes`: XGBoost model predicted delay rounded to 2 decimal places.
  - `predicted_eta`: Dynamic estimated time of arrival ISO 8601 timestamp (`YYYY-MM-DDTHH:MM:SS`).

> [!NOTE]
> Per specification constraints:
> - No fake confidence scores or intervals are claimed or fabricated.
> - Missing data is never invented.

---

## 4. Multi-Horizon Prediction Rules

Predictions are strictly generated according to remaining scheduled halts:

| Stops Remaining to Terminus | Predicted Horizons | Logic |
|---|---|---|
| `stops_remaining == 1` | `[H1]` | Train is approaching terminus; H2/H3 exceed journey boundary. |
| `stops_remaining == 2` | `[H1, H2]` | H1 and H2 predicted; H3 exceeds journey boundary. |
| `stops_remaining >= 3` | `[H1, H2, H3]` | Full multi-horizon predictions for all 3 upcoming stops. |
| `stops_remaining == 0` | Exception | Train has reached terminus; returns HTTP 422. |

---

## 5. Machine Learning Feature Pipeline & Models

### Models Ingestion
Models are loaded once into memory upon server startup and reused across requests without retraining or modification:
- **Horizon 1**: `e:/train/models/xgboost_eta_h1_v1.json`
- **Horizon 2**: `e:/train/models/xgboost_eta_h2_v1.json`
- **Horizon 3**: `e:/train/models/xgboost_eta_h3_v1.json`

### 27 Validated Leak-Free Features
Features are populated dynamically from the live feed and timetable route topology:
- **Live Running Lags**: `current_delay`, `prev_station_delay`, `prev_delay_2`, `prev_delay_3`.
- **Delay Deltas**: `delay_change`, `delay_change_2_stations`, `delay_change_3_stations`.
- **Topological Route Attributes**: `current_station_seq`, `stations_remaining`, `dist_from_origin`, `remaining_dist`, `journey_progress`, `route_total_distance`, `route_total_stations`.
- **Section Timetable Dynamics**: `scheduled_dwell_time`, `sched_section_distance`, `sched_section_travel_time`, `sched_planned_speed`.
- **Calendar & Categorical Encoding**: `scheduled_hour`, `day_of_week`, `month`, `day`, `is_weekend`, `type_code`, `station_zone`, `next_station_name`, `next_station_zone`.

---

## 6. In-Memory Response Caching

To prevent redundant API queries to RailRadar and protect upstream rate limits:
- **Implementation**: [`src/live/cache.py`](file:///e:/train/src/live/cache.py) — Thread-safe `LiveETACache` with monotonic expiration timestamps.
- **Configurable TTL**: `RAILRADAR_CACHE_TTL_SECONDS=30` (configured in `.env.example`).
- **Cache Key**: `f"{clean_train_no}:{journey_date or 'latest'}"`.
- **Performance**:
  - Cache Miss (Live Query): ~3000ms (includes upstream HTTPS round-trip + inference).
  - Cache Hit: **0.0ms** (instant memory lookup).
- **Diagnostics**: Current hit/miss metrics are exposed via `/api/health`.

---

## 7. Error Handling & HTTP Status Code Mapping

The backend handles upstream, validation, and domain errors with standardized status codes:

| Error Scenario | HTTP Status | Detail / Action |
|---|---|---|
| **Invalid Train Format** | `400 Bad Request` | Train number must be 4 or 5 numeric digits. |
| **Train Not Found** | `404 Not Found` | Train does not exist in master timetable or live feed. |
| **Schedule Mapping Error** | `422 Unprocessable Entity` | Station is not on train's scheduled route itinerary. |
| **Insufficient Route** | `422 Unprocessable Entity` | Train has already terminated at destination. |
| **Train Cancelled** | `422 Unprocessable Entity` | Train is cancelled or not running on queried date. |
| **Authentication Failure** | `502 Bad Gateway` | RailRadar rejected credentials (key masked in logs). |
| **API Timeout** | `504 Gateway Timeout` | Upstream request exceeded timeout threshold (`10s`). |
| **Malformed Upstream Data**| `502 Bad Gateway` | Upstream response schema mismatch or truncated JSON. |
| **Model / Inference Error**| `500 Internal Error`| Booster evaluation or feature encoding failure. |

---

## 8. Security Protocols & Safe Logging

- **Zero Secret Exposure**: Plaintext API keys and `Authorization` headers are **never** logged, printed, or included in response payloads.
- **Secret Redaction**: Any status or exception reference is sanitized via `mask_secret()` (`rg_5...1c7f`).
- **Safe Request Logging**: The logging middleware records only safe telemetry:
  ```text
  [2026-09-30 08:35:04] [INFO] [API] Live ETA [LIVE HIT] train=12301 status=200 elapsed=3252.2ms
  [2026-09-30 08:35:19] [INFO] [API] Live ETA [CACHE HIT] train=12301 status=200 elapsed=0.0ms
  ```

---

## 9. Automated Test Verification (13/13 PASS)

Test execution script:
```bash
python e:/train/scripts/test_fastapi_eta.py
```

### Test Results Matrix
| Test # | Test Name | Status | Verification Detail |
|---|---|---|---|
| 01 | GET /api/train/{train_no}/eta | PASS | Validated top-level schema and types |
| 02 | Mocked RailRadar response | PASS | Parsed commercial halt and delay |
| 03 | H1 prediction | PASS | Horizon 1 scheduled arrival and predicted ETA |
| 04 | H2 prediction (>=2 stops) | PASS | Verified Horizon 2 prediction for Train 12951 |
| 05 | H3 prediction (>=3 stops) | PASS | Verified Horizon 3 prediction for Train 12002 |
| 06 | Insufficient stops for H2/H3 | PASS | Only H1 produced when 1 stop to terminus |
| 07 | Invalid train number | PASS | Rejected alpha/short train numbers with HTTP 400 |
| 08 | RailRadar timeout | PASS | Converted timeout into HTTP 504 |
| 09 | RailRadar auth failure | PASS | Converted auth failure into HTTP 502 |
| 10 | Schedule mapping failure | PASS | Converted station mismatch into HTTP 422 |
| 11 | Model inference failure | PASS | Converted booster error into HTTP 500 |
| 12 | Zero API key exposure | PASS | Verified secret absent from success, health, and errors |
| 13 | In-memory cache behavior | PASS | Verified cache hit and hit count increment |

---

## 10. Real Live Endpoint End-to-End Verification

A controlled real request was executed against the running FastAPI application for **Train 12301**:

```bash
# Endpoint
GET /api/train/12301/eta
```

### Actual Output
```json
{
  "success": true,
  "train_no": "12301",
  "train_name": "Howrah - New Delhi Rajdhani Express",
  "status": "departed",
  "journey_date": "2026-09-29",
  "current_station": {
    "code": "CNB",
    "name": "Kanpur Central",
    "delay_minutes": 3.0
  },
  "predictions": [
    {
      "horizon": 1,
      "station": "NDLS",
      "scheduled_arrival": "2026-09-30T10:05:00",
      "predicted_delay_minutes": 7.60,
      "predicted_eta": "2026-09-30T10:12:36"
    }
  ]
}
```

---

## 11. How to Start the Server Locally

To launch the backend server locally:

```bash
uvicorn src.live.app:app --host 127.0.0.1 --port 8000 --reload
```

Once running, access the live endpoint:
- **Live Endpoint**: [http://127.0.0.1:8000/api/train/12301/eta](http://127.0.0.1:8000/api/train/12301/eta)
- **Demo Endpoint**: [http://127.0.0.1:8000/api/demo/train/12301/eta](http://127.0.0.1:8000/api/demo/train/12301/eta)
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
