# Project Structure Reorganization Report
**SIH Problem Statement 26028 – Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**

---

## 1. Executive Summary & Verification Matrix

The SIH 26028 Dynamic Train ETA codebase has been safely reorganized into a clean, modular, and maintainable production structure without modifying the underlying machine-learning models, training parameters, feature definitions, or API response schemas. All existing tests (FastAPI, live integration, multi-horizon inference, and frontend unit tests) pass 100%.

```text
PROJECT REORGANIZATION: PASS
Backend structure: PASS
Backend imports: PASS
Backend startup: PASS
ML paths: PASS
Model paths: PASS
Data paths: PASS
Script paths: PASS
Reports organized: PASS
Frontend build: PASS
Frontend tests: PASS
FastAPI tests: 13/13 PASS
Integration tests: 14/14 PASS
Secrets check: PASS
Old broken path references: 0
```

---

## 2. Reorganized Directory Architecture

```text
E:/train/
├── backend/
│   ├── app/
│   │   ├── live/
│   │   │   ├── __init__.py
│   │   │   ├── api_client.py
│   │   │   ├── app.py
│   │   │   ├── cache.py
│   │   │   ├── config.py
│   │   │   ├── exceptions.py
│   │   │   ├── response_parser.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   └── __init__.py
│   ├── ml/
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── cleaning.py
│   │   │   └── loader.py
│   │   ├── features/
│   │   │   ├── __init__.py
│   │   │   └── builder.py
│   │   ├── inference/
│   │   │   ├── __init__.py
│   │   │   ├── eta_calculator.py
│   │   │   ├── model_loader.py
│   │   │   ├── predictor.py
│   │   │   └── schemas.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   └── __init__.py
│   ├── models/
│   │   ├── xgboost_eta_h1_v1.json
│   │   ├── xgboost_eta_h1_v1_features.json
│   │   ├── xgboost_eta_h2_v1.json
│   │   ├── xgboost_eta_h2_v1_features.json
│   │   ├── xgboost_eta_h3_v1.json
│   │   ├── xgboost_eta_h3_v1_features.json
│   │   ├── xgboost_eta_v1.json
│   │   └── xgboost_eta_v1_features.json
│   ├── scripts/
│   │   ├── audit_dataset_and_splits.py
│   │   ├── audit_duplicates_full.py
│   │   ├── audit_full_partition.py
│   │   ├── audit_multi_horizon.py
│   │   ├── audit_target_distribution.py
│   │   ├── audit_target_ordering.py
│   │   ├── evaluate_baselines.py
│   │   ├── run_preprocessing.py
│   │   ├── test_fastapi_eta.py
│   │   ├── test_inference.py
│   │   ├── test_live_integration.py
│   │   ├── test_real_connection.py
│   │   ├── train_multi_horizon.py
│   │   └── train_xgboost.py
│   ├── __init__.py
│   └── requirements.txt
├── data/
│   ├── raw/
│   │   ├── combined_delay.csv
│   │   ├── combined_schedule.csv
│   │   ├── train_details.csv
│   │   ├── station_full_names.csv
│   │   ├── 2015 timetable.csv
│   │   └── 2017 timetable.csv
│   └── processed/
│       ├── train_features/
│       │   └── year_month=*/features.parquet
│       ├── sample_features.csv
│       └── sample_features.parquet
├── frontend/
│   ├── src/
│   ├── public/
│   ├── test/
│   ├── .env
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
├── reports/
│   ├── dataset/
│   │   ├── DATASET_REPORT.md
│   │   └── SIH_26028_WALKTHROUGH.md
│   ├── preprocessing/
│   │   ├── feature_report.md
│   │   └── preprocessing_report.md
│   ├── ml/
│   │   ├── INFERENCE_SERVICE_REPORT.md
│   │   ├── ML_READINESS_AUDIT.md
│   │   ├── MULTI_HORIZON_RESULTS.md
│   │   ├── MULTI_HORIZON_TARGET_AUDIT.md
│   │   └── XGBOOST_RESULTS.md
│   ├── api/
│   │   ├── FASTAPI_ETA_API.md
│   │   ├── LIVE_API_REAL_TEST.md
│   │   ├── LIVE_API_SETUP.md
│   │   └── PROJECT_REORGANIZATION.md
│   └── frontend/
│       └── FRONTEND_ETA_DASHBOARD.md
├── scratch/
├── .env
├── .env.example
├── .gitignore
└── README.md
```

---

## 3. Inventory of Changes & Migrations

### A. Root Directory Cleanup
- Moved `DATASET_REPORT.md` into `reports/dataset/DATASET_REPORT.md`.
- Root directory now strictly contains only top-level project files (`.env`, `.env.example`, `.gitignore`, `README.md`) and designated directories (`backend/`, `data/`, `frontend/`, `reports/`, `scratch/`).

### B. Backend Consolidation (`backend/`)
- Migrated legacy `src/` to `backend/` with structured subpackages:
  - `backend/app/live/`: FastAPI application, API clients, cache, schemas, and live service.
  - `backend/ml/data/`: Data loading and cleaning modules.
  - `backend/ml/features/`: Feature engineering and manifest generator.
  - `backend/ml/inference/`: Prediction orchestrator, model loader, and ETA calculator.
  - `backend/ml/utils/`: Path configuration and operational constants.
- Updated all internal module imports to `backend.app.live...`, `backend.ml...`.
- Verified 0 remaining occurrences of `from src.` or `import src.` across all codebase files.
- Created curated `backend/requirements.txt` based strictly on verified dependencies.

### C. Models Relocation (`backend/models/`)
- Relocated all 8 trained JSON booster models and feature manifests:
  - `xgboost_eta_v1.json` + manifest
  - `xgboost_eta_h1_v1.json` + manifest
  - `xgboost_eta_h2_v1.json` + manifest
  - `xgboost_eta_h3_v1.json` + manifest
- Updated `backend/ml/utils/config.py` (`MODELS_DIR = BASE_DIR / "backend" / "models"`).
- Verified zero byte differences or retraining; existing models remain 100% operational.

### D. Data Organization (`data/raw/` & `data/processed/`)
- Moved all raw CSV files (`combined_delay.csv` 1GB, `combined_schedule.csv`, `train_details.csv`, `station_full_names.csv`, `2015 timetable.csv`, `2017 timetable.csv`) into `data/raw/` via instant filesystem rename pointers (zero data duplication).
- Retained processed Parquet partitions under `data/processed/train_features/`.
- Updated `backend/ml/utils/config.py` (`RAW_DATA_DIR = DATA_DIR / "raw"`).

### E. Scripts Relocation (`backend/scripts/`)
- Moved all 14 test, evaluation, preprocessing, and training scripts into `backend/scripts/`.
- Updated `sys.path` entries to point to the repository root (`PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent`).
- Updated all module imports across all scripts.

### F. Reports Reorganization (`reports/`)
- Classified all 13 documentation reports into 5 clean categories:
  - `reports/dataset/`: Dataset reports and walkthroughs.
  - `reports/preprocessing/`: Data cleaning and feature engineering reports.
  - `reports/ml/`: Training benchmarks, leakage audits, and inference reports.
  - `reports/api/`: Live API setup, real connectivity test, and FastAPI documentation.
  - `reports/frontend/`: Frontend architecture and dashboard documentation.

---

## 4. Verification Suite Results

### 1. FastAPI Mock & Contract Tests (13/13 PASS)
Executed: `python backend/scripts/test_fastapi_eta.py`
- Tests passed: 13 / 13 (Endpoint structure, H1, H2, H3, 400, 404, 422, 502, 504, 500, cache hit/miss, zero credentials exposure).

### 2. Live API Offline Integration Tests (14/14 PASS)
Executed: `python backend/scripts/test_live_integration.py`
- Tests passed: 14 / 14 (Configuration parsing, missing key detection, response normalization, lag construction, H1/H2/H3 inference, secret masking).

### 3. Multi-Horizon Inference Validation (10/10 PASS)
Executed: `python backend/scripts/test_inference.py`
- Tests passed: 10 / 10 edge cases verified + 100-sample historical benchmark (MAE: 8.98 min, 78% within $\pm 10$ min, 100% station sequence alignment).

### 4. Real End-to-End Live Hit (Train 12301)
Tested with: `python -m uvicorn backend.app.live.app:app --host 127.0.0.1 --port 8000`
- Query: `GET /api/train/12301/eta`
- Response: HTTP 200 OK
- Train: 12301 (Howrah - New Delhi Rajdhani Express)
- Current Station: CNB (Kanpur Central), Delay: 0.0 min (On Time)
- Prediction: $H_1$ to NDLS, Scheduled 10:05 AM, Predicted Delay +8.3 min, Predicted ETA 10:13 AM.

### 5. Frontend Unit Tests (10/10 PASS)
Executed: `npm test` from `frontend/`
- Tests passed: 10 / 10 (Train validation, error status code mapping, single-horizon display, security checks).

### 6. Frontend Production Build (PASS)
Executed: `npm run build` from `frontend/`
- Output: `dist/index.html` (0.90 kB), `index.css` (13.64 kB), `index.js` (239.10 kB). Build time: 316ms.

---

## 5. Startup Commands Reference

### Backend
```bash
cd E:\train\backend
python -m uvicorn app.live.app:app --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```
*(Accessible at `http://127.0.0.1:5173`)*
