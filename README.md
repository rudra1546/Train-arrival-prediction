# Dynamic Train ETA (SIH Problem Statement 26028)
> **AI-Powered Dynamic Forecast of Expected Time of Arrival (ETA) for Indian Railways Coaching Trains**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.1-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-Multi--Horizon-orange.svg?style=flat)](https://xgboost.readthedocs.io)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-8.x-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev)

---

## 1. Problem Statement & Objective

Indian Railways operates over 13,000 passenger coaching trains across 68,000+ route kilometers daily. Traditional delay reporting is static and naive: if a train is currently 30 minutes late, timetables often simply shift downstream arrival times by 30 minutes, ignoring line capacity, section travel dynamics, operational slack, and downstream congestion.

**SIH Problem Statement 26028** asks for an intelligent, data-driven system to forecast dynamic arrival delays and compute dynamic ETAs. 

This project delivers an end-to-end, multi-horizon machine-learning solution combining:
1. Live GPS/telemetry integration via the RailRadar API gateway.
2. Traversed station history and consecutive delay lag reconstruction.
3. 27 strictly leak-free operational, timetable, and route features.
4. Dedicated XGBoost models for multi-horizon delay forecasts ($H_1$, $H_2$, $H_3$).
5. Production FastAPI microservice with in-memory TTL caching.
6. Clean, responsive React + Vite operational dashboard.

---

## 2. System Architecture

```text
+-----------------------+
|  RailRadar Live API   |  (Live train telemetry & GPS location)
+-----------+-----------+
            |
            v
+-----------------------+
| Traversed Delay Lags  |  (Consecutive delays: prev, prev2, prev3)
+-----------+-----------+
            |
            v
+-----------------------+
| Feature Construction  |  (27 leak-free timetable, topology & delay features)
+-----------+-----------+
            |
            v
+-----------------------+
|   XGBoost Boosters    |  (H1: Next Station | H2: 2 Ahead | H3: 3 Ahead)
+-----------+-----------+
            |
            v
+-----------------------+
|    FastAPI Gateway    |  (GET /api/train/{train_no}/eta with TTL cache)
+-----------+-----------+
            |
            v
+-----------------------+
|    React Dashboard    |  (Dynamic Multi-Horizon Live ETA UI)
+-----------------------+
```

---

## 3. Technology Stack

- **Backend:**
  - Python 3.10+
  - FastAPI & Uvicorn (REST API Gateway)
  - XGBoost (Multi-Horizon Boosters)
  - Polars & Pandas (Data Processing)
  - Pydantic (Type & Schema Validation)
- **Frontend:**
  - React 19 & TypeScript
  - Vite 8 (Modern Frontend Tooling)
  - Vanilla CSS Design System (Professional Railway Telemetry)
  - Lucide React (Icons)
- **Data & Storage:**
  - Historical Indian Railways delay records (~38.4 million rows)
  - Scheduled Timetables & Station Master files
  - Apache Parquet storage for feature partitions

---

## 4. Reorganized Project Structure

```text
E:/train/
│
├── .env                              # Backend configuration & server secrets (DO NOT COMMIT)
├── .env.example                      # Template environment file
├── .gitignore                        # Git exclusion rules
├── README.md                         # Project documentation
│
├── backend/                          # Python Backend & ML Service
│   ├── app/
│   │   └── live/                     # FastAPI Live Service
│   │       ├── api_client.py         # RailRadar live & mock client adapters
│   │       ├── app.py                # FastAPI application & route endpoints
│   │       ├── cache.py              # Thread-safe in-memory TTL cache
│   │       ├── config.py             # Server config & safe secret masking
│   │       ├── exceptions.py         # Strongly-typed domain exceptions
│   │       ├── response_parser.py    # RailRadar payload parser & lag extractor
│   │       ├── schemas.py            # API request/response Pydantic models
│   │       └── service.py            # Orchestrator connecting API to ML predictor
│   │
│   ├── ml/                           # Machine Learning & Data Pipeline
│   │   ├── data/
│   │   │   ├── cleaning.py           # Delay filtering & anomaly thresholds
│   │   │   └── loader.py             # Timetable, delay, and station loaders
│   │   ├── features/
│   │   │   └── builder.py            # Leak-free feature construction
│   │   ├── inference/
│   │   │   ├── eta_calculator.py     # Scheduled arrival & dynamic ETA arithmetic
│   │   │   ├── model_loader.py       # Multi-horizon booster & manifest loader
│   │   │   ├── predictor.py          # MultiHorizonETAPredictor engine
│   │   │   └── schemas.py            # Inference domain dataclasses & errors
│   │   └── utils/
│   │       └── config.py             # Global paths & operational thresholds
│   │
│   ├── models/                       # Trained XGBoost native JSON models
│   │   ├── xgboost_eta_v1.json
│   │   ├── xgboost_eta_v1_features.json
│   │   ├── xgboost_eta_h1_v1.json
│   │   ├── xgboost_eta_h1_v1_features.json
│   │   ├── xgboost_eta_h2_v1.json
│   │   ├── xgboost_eta_h2_v1_features.json
│   │   ├── xgboost_eta_h3_v1.json
│   │   └── xgboost_eta_h3_v1_features.json
│   │
│   ├── scripts/                      # Verified test, training & audit scripts
│   │   ├── test_fastapi_eta.py       # 13/13 FastAPI endpoint test suite
│   │   ├── test_live_integration.py  # 14/14 offline live pipeline integration suite
│   │   ├── test_inference.py         # Multi-horizon inference validation suite
│   │   ├── test_real_connection.py   # Real RailRadar connection test
│   │   ├── train_multi_horizon.py    # XGBoost H1/H2/H3 training pipeline
│   │   ├── train_xgboost.py          # XGBoost v1 single-horizon trainer
│   │   ├── run_preprocessing.py      # Feature engineering pipeline
│   │   └── audit_*.py                # Rigorous data leakage & distribution audits
│   │
│   └── requirements.txt              # Curated Python backend dependencies
│
├── data/                             # Dataset Directory (Outside Backend)
│   ├── raw/                          # Source CSV files (delays, schedules, stations)
│   └── processed/                    # Partitioned Parquet feature datasets
│
├── frontend/                         # React + TypeScript + Vite Dashboard
│   ├── src/                          # UI components, types, services, and CSS
│   ├── public/                       # Static public assets
│   ├── test/                         # Frontend unit test suite (10/10 PASS)
│   ├── package.json                  # Frontend dependencies & scripts
│   ├── .env.example                  # VITE_API_BASE_URL=http://127.0.0.1:8000
│   └── .env                          # Local frontend config
│
├── reports/                          # Categorized Project Reports & Audits
│   ├── dataset/                      # Dataset inspection & walkthrough reports
│   ├── preprocessing/                # Cleaning, filtering & feature reports
│   ├── ml/                           # Model evaluation, training & inference reports
│   ├── api/                          # Live API setup, real test & FastAPI reports
│   └── frontend/                     # Frontend architecture & dashboard report
│
└── scratch/                          # Temporary diagnostics & one-off scratch scripts
```

---

## 5. Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
1. From the project root (`E:/train`), create or activate your Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Configure environment variables in `E:/train/.env`:
   ```env
   # Server-side RailRadar Live API Key (NEVER expose to client)
   RAILRADAR_API_KEY=your_actual_railradar_api_key_here
   RAILRADAR_BASE_URL=https://api.railradar.in/v1
   RAILRADAR_TIMEOUT_SECONDS=10.0
   RAILRADAR_CACHE_TTL_SECONDS=30.0
   APP_ENV=development
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```
2. Ensure `frontend/.env` is configured:
   ```env
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

---

## 6. Running the System

### Start FastAPI Backend
From the `backend/` directory:
```bash
cd E:\train\backend
python -m uvicorn app.live.app:app --host 127.0.0.1 --port 8000
```
- Swagger Interactive Docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

### Start React Frontend
From the `frontend/` directory:
```bash
cd E:\train\frontend
npm run dev
```
Open `http://127.0.0.1:5173` in your browser.

---

## 7. API Specification

### Endpoint: `GET /api/train/{train_no}/eta`
Fetches live telemetry for `{train_no}`, calculates consecutive historical delays, constructs the 27 dynamic ML features, executes XGBoost $H_1$/$H_2$/$H_3$ inference, and returns predicted ETAs.

**Example Request:**
```http
GET /api/train/12301/eta HTTP/1.1
Host: 127.0.0.1:8000
Accept: application/json
```

**Example JSON Response:**
```json
{
  "success": true,
  "train_no": "12301",
  "train_name": "Howrah - New Delhi Rajdhani Express",
  "status": "Departed",
  "journey_date": "2026-09-29",
  "current_station": {
    "code": "CNB",
    "name": "Kanpur Central",
    "delay_minutes": 0.0
  },
  "predictions": [
    {
      "horizon": 1,
      "station": "NDLS",
      "scheduled_arrival": "2026-09-30T10:05:00",
      "predicted_delay_minutes": 8.3,
      "predicted_eta": "2026-09-30T10:13:18"
    }
  ]
}
```

---

## 8. Verification & Test Commands

Run verified automated tests across all tiers:

```bash
# 1. FastAPI endpoint tests (13/13 PASS)
cd E:\train\backend
python scripts/test_fastapi_eta.py

# 2. Live API offline integration tests (14/14 PASS)
python scripts/test_live_integration.py

# 3. Multi-horizon inference benchmark tests (10/10 PASS)
python scripts/test_inference.py

# 4. Frontend logic & unit tests (10/10 PASS)
cd E:\train\frontend
npm test

# 5. Frontend production build
npm run build
```

---

## 9. Security Notice

> [!IMPORTANT]
> - `RAILRADAR_API_KEY` is maintained **strictly server-side** in `E:/train/.env`.
> - The frontend communicates **only with the FastAPI backend**. No client-side `Authorization` headers or third-party API keys exist in the frontend code.
> - Plaintext secrets are strictly masked (`rg_5...1c7f`) in all logs, health endpoints, and error responses.
