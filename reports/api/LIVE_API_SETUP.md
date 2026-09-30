# SIH Problem Statement 26028: Live Railway API Setup & Integration Architecture

This document specifies the complete configuration, security protocols, architecture, and verification procedures for integrating the **RailRadar Live Train Status API** with the SIH 26028 Multi-Horizon XGBoost ETA Inference Engine.

---

## 1. Live API Provider & Official Documentation

- **Provider**: RailRadar ([https://railradar.in](https://railradar.in))
- **Documentation**: [https://railradar.in/docs/live-train-status](https://railradar.in/docs/live-train-status)
- **Live Endpoint**: `GET https://api.railradar.in/v1/trains/{number}/live`
- **Authentication Scheme**: `Authorization: Bearer <API_KEY>`
- **HTTP Method**: `GET`
- **Request Parameters**:
  - Path Parameter: `number` (5-digit train number, e.g., `12301`)
  - Query Parameter: `date` (`YYYY-MM-DD`, optional journey commencement date)
  - Query Parameter: `authoritative=true` (forces live NTES/GPS sync)
  - Query Parameter: `haltsOnly=true` (filters out minor signaling waypoints)

---

## 2. Environment Configuration & Security Rules

### Environment Variables
The application reads configuration through system environment variables and local `.env` files:

| Variable | Description | Example / Default |
|---|---|---|
| `RAILRADAR_API_KEY` | Secret Bearer authentication token | *(Empty by default)* |
| `RAILRADAR_BASE_URL` | Base API endpoint | `https://api.railradar.in/v1` |
| `RAILRADAR_TIMEOUT_SECONDS` | HTTP request timeout in seconds | `10` |
| `APP_ENV` | Application environment mode | `development` |

### Where to Place the Real API Key
1. Copy `.env.example` to `.env` in the project root:
   ```bash
   cp e:/train/.env.example e:/train/.env
   ```
2. Open `e:/train/.env` and insert your supplied API key:
   ```ini
   RAILRADAR_API_KEY=your_actual_railradar_api_key_here
   ```
3. Save the file. **Do NOT commit `.env` to Git.**

### Security Protocols & Secret Redaction
- **Git Protection**: `.env`, `*.env`, and `.env.local` are explicitly excluded in `e:/train/.gitignore`.
- **Zero Mock Credentials**: No mock, fake, or guessed credentials exist in the codebase.
- **Strict Execution Gating**: If `RAILRADAR_API_KEY` is empty, unset, or a template placeholder, `RailRadarLiveClient` aborts at initialization and raises `APIKeyMissingError`. Under no circumstance is a socket or HTTP request initiated without a valid key.
- **Secret Redaction**: Any log, health check, or diagnostic message redacts keys using `mask_secret()` (e.g. `rr_l...4321` or `<UNCONFIGURED>`). Plaintext keys are never output to stdout, logs, or error responses.

---

## 3. End-to-End API Integration Architecture

The pipeline connects live tracking telemetry with the verified offline multi-horizon inference models without retraining or modifying model weights.

```
                      +-----------------------------+
                      |   RailRadar Live API        |
                      | (GET /v1/trains/{no}/live)  |
                      +--------------+--------------+
                                     | (Raw JSON)
                                     v
                      +-----------------------------+
                      |    Live API Adapter         |
                      |  (src/live/response_parser) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    NormalizedTrainState     |
                      |   [API + Derived Fields]    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Timetable Feature Builder |
                      | (Route Topology & Lags)     |
                      +--------------+--------------+
                                     | (30-Feature DMatrix)
                                     v
        +----------------------------+----------------------------+
        |                            |                            |
        v                            v                            v
+------------------+         +------------------+         +------------------+
|  Horizon 1 Model |         |  Horizon 2 Model |         |  Horizon 3 Model |
|  (Next Station)  |         |  (2 Stops Ahead) |         |  (3 Stops Ahead) |
+--------+---------+         +--------+---------+         +--------+---------+
         |                            |                            |
         | Predicted Delay 1          | Predicted Delay 2          | Predicted Delay 3
         +----------------------------+----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |       ETA Calculator        |
                      | (Sched Arrival + Pred Delay)|
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Unified JSON Response     |
                      | (Live / Demo API Endpoints) |
                      +-----------------------------+
```

---

## 4. Normalized Train State Schema

Fields in `NormalizedTrainState` are explicitly categorized into three distinct classes:

### A. Fields Provided Directly by the API
- `train_no`: 5-digit string train code
- `current_station`: Current station code (e.g. `CNB`)
- `current_delay_minutes`: Real-time operational delay in minutes
- `journey_date`: Date train departed origin (`YYYY-MM-DD`)
- `status_timestamp`: Timestamp of live GPS/NTES telemetry
- `latitude` / `longitude`: Real-time GPS coordinates of locomotive/rake
- `current_status`: Train status (`departed`, `arrived`, `running`)
- `train_name`: Commercial service name

### B. Fields Derived by Our System
- `station_sequence`: Station index in scheduled itinerary
- `prev_station_delay`: Delay at immediately preceding traversed stop
- `prev_delay_2`: Delay 2 stations prior
- `prev_delay_3`: Delay 3 stations prior
- `delay_change`: `current_delay - prev_station_delay`
- `delay_change_2_stations`: `current_delay - prev_delay_2`
- `delay_change_3_stations`: `current_delay - prev_delay_3`
- `stops_remaining`: Number of remaining stations to destination

### C. Fields Unavailable From Any Commercial API
Documented in `UNAVAILABLE_FROM_API`:
- `signal_block_aspect`: Real-time internal railway signaling block aspects (4-aspect signaling telemetry)
- `temporary_speed_restrictions`: Internal civil engineering caution orders (TSRs)
- `gradient_profile`: Track inclination profile along block sections
- `weather_telemetry_micro`: Sensor readings from trackside micro-weather stations
- `rolling_stock_health`: Real-time locomotive diagnostic telemetry

---

## 5. Historical Lag Feature Handling

Our XGBoost models (`xgboost_eta_h1_v1.json`, `xgboost_eta_h2_v1.json`, `xgboost_eta_h3_v1.json`) rely on temporal lag features:
- `current_delay`
- `prev_station_delay`, `prev_delay_2`, `prev_delay_3`
- `delay_change`, `delay_change_2_stations`, `delay_change_3_stations`

### Exact Reconstruction Mechanism
The official RailRadar live response includes a `route` array listing all halts for the journey. For all traversed stops (`status == "departed"` or having non-null actual times):
1. `response_parser.py` locates `current_station` in the route.
2. It walks backwards through preceding traversed stops to extract their actual arrival/departure delays.
3. Stop $i-1$ yields `prev_station_delay`, stop $i-2$ yields `prev_delay_2`, and stop $i-3$ yields `prev_delay_3`.
4. Deltas (`delay_change`, etc.) are computed directly from these extracted historical delays.

### Edge Case Handling
- **Train at Origin (Stop 0)**: Lags do not exist yet; they default gracefully to `None` / `np.nan` (routed down XGBoost's default tree split paths).
- **Train at Stop 1**: Only `prev_station_delay` exists; 2-station and 3-station lags default to `np.nan`.
- **Zero Hallucination Guarantee**: If historical halts are missing in the feed, values are **never invented**.

---

## 6. Development & Mock Provider Mode

To enable continuous development and automated testing without requiring live credentials:
- **`MockRailRadarClient`**: Provides deterministic synthetic responses for key high-density passenger services:
  - **Train 12301**: Kolkata Rajdhani (HWH -> NDLS), currently at CNB
  - **Train 12951**: Mumbai Tejas Rajdhani (MMCT -> NDLS), currently at BRC
  - **Train 12002**: New Delhi Bhopal Shatabdi (NDLS -> RKMP), currently at GWL
- **Clear Provenance Labeling**: All mock responses are tagged with:
  ```
  "data_source": "MOCK DATA — NOT LIVE RAILWAY DATA"
  "is_demo": true
  ```
- **Zero Network Interaction**: `MockRailRadarClient` never makes external network calls.

---

## 7. FastAPI Service Operations

### Starting the API Service
Run the uvicorn ASGI server from the project root:
```bash
uvicorn src.live.app:app --host 0.0.0.0 --port 8000 --reload
```

### Endpoints Overview

#### 1. System Health Check
- **Endpoint**: `GET /api/health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "SIH-26028 Live ETA Inference API",
    "live_api_configured": false,
    "api_key_status": "<UNCONFIGURED>",
    "timestamp": "2026-09-30T02:30:00Z"
  }
  ```

#### 2. Live Train ETA Prediction (Strictly Gated)
- **Endpoint**: `GET /api/train/{train_no}/eta`
- **When API Key is Missing**:
  ```json
  {
    "status": "live_api_not_configured",
    "message": "RailRadar API key has not been configured."
  }
  ```
- **When API Key is Configured**: Returns live predictions for H1, H2, and H3 using live RailRadar data.

#### 3. Demo / Mock Prediction Endpoint
- **Endpoint**: `GET /api/demo/train/{train_no}/eta`
- **Purpose**: Interactive testing with deterministic synthetic data. Always accessible without credentials.

---

## 8. Test Suite Verification

Run the automated offline validation test suite:
```bash
python e:/train/scripts/test_live_integration.py
```

### Verification Matrix (14/14 PASS)
| Test # | Requirement | Status | Verification Detail |
|---|---|---|---|
| 01 | Environment configuration | PASS | Loads `.env` parameters (`timeout`, `base_url`) |
| 02 | Missing key detection | PASS | Identifies empty or placeholder tokens |
| 03 | No unauthorized live calls | PASS | Raises `APIKeyMissingError` on unconfigured instantiation |
| 04 | Mock response parsing | PASS | Parses raw JSON into `NormalizedTrainState` |
| 05 | Normalized state creation | PASS | Reconstructs 3 consecutive delay lags from `route` |
| 06 | Feature construction | PASS | Builds complete 30-feature vector for inference |
| 07 | H1 prediction | PASS | Generates next-station delay prediction |
| 08 | H2 prediction | PASS | Generates 2-stations-ahead delay prediction |
| 09 | H3 prediction | PASS | Generates 3-stations-ahead delay prediction |
| 10 | ETA calculation | PASS | Produces valid scheduled + delay timestamps |
| 11 | Invalid train handling | PASS | Rejects non-existent trains with HTTP 404 |
| 12 | Malformed response rejection | PASS | Catches corrupted/truncated payloads |
| 13 | Timeout and error handling | PASS | Validates HTTP 504, 401, 422 exception mapping |
| 14 | Secret protection in logs | PASS | Validates `mask_secret` and zero key leakage |

---

## 9. Remaining Validation Once Real API Key is Provided

Once the user provides the real RailRadar API key:
1. **Network Connectivity**: Perform TLS handshake and bearer token authentication against `api.railradar.in`.
2. **Real-Time Data Latency**: Benchmark round-trip network response times.
3. **Live Payload Drift Check**: Confirm live response schema from production servers matches the documented schema across all 18 railway zones.
4. **Resilience Testing**: Test provider response to trains running off-schedule, diverted trains, and terminating stations.
