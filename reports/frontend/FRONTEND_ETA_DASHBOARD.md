# Frontend ETA Dashboard Documentation
**SIH Problem Statement 26028 – Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**

---

## 1. Overview & Executive Summary

A clean, modern React + Vite frontend dashboard has been built for the **Dynamic Train ETA** system. It connects directly to the FastAPI live inference endpoint (`GET /api/train/{train_no}/eta`), visualizes live railway telemetry, and displays multi-horizon arrival predictions produced by the trained XGBoost models ($H_1$, $H_2$, $H_3$).

- **Frontend Location:** [`e:/train/frontend/`](file:///e:/train/frontend/)
- **Technology Stack:** React 19, TypeScript, Vite 8, Vanilla CSS Design System, Lucide Icons
- **Backend API:** FastAPI live prediction service (`http://127.0.0.1:8000`)
- **Security Posture:** 100% Zero-Trust Architecture. No RailRadar API credentials exist in frontend code or environment files. The frontend communicates exclusively with the internal FastAPI gateway.

---

## 2. Startup Commands

### FastAPI Backend
Run from backend directory (`E:/train/backend`):
```bash
cd E:\train\backend
python -m uvicorn app.live.app:app --host 127.0.0.1 --port 8000
```

### React Frontend
Run from frontend directory (`e:/train/frontend`):
```bash
npm run dev
```
*(Runs on `http://127.0.0.1:5173` by default)*

To build for production:
```bash
npm run build
```

To run automated unit & validation tests:
```bash
npm test
```

---

## 3. Environment Variable Configuration

### Frontend Configuration
The frontend uses standard Vite environment variables.

- **`.env.example`** and **`.env`** (`e:/train/frontend/`):
  ```env
  # FastAPI Backend API Base URL
  VITE_API_BASE_URL=http://127.0.0.1:8000
  ```

> [!NOTE]
> The base URL is never hardcoded. All service calls read `import.meta.env.VITE_API_BASE_URL`.
> No upstream railway API keys or credentials exist in the frontend.

---

## 4. Architecture & Component Structure

```
frontend/
├── .env.example
├── .env
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx                         # React root entrypoint
│   ├── App.tsx                          # Core orchestrator component
│   ├── index.css                        # Professional Railway Design System
│   ├── types/
│   │   └── eta.ts                       # TypeScript schemas matching FastAPI JSON
│   ├── services/
│   │   └── api.ts                       # Fetch client & error translation service
│   └── components/
│       ├── Header.tsx                   # Brand title, subtitle, live status pill
│       ├── TrainSearch.tsx              # Numeric input, Enter key, quick chips
│       ├── TrainSummary.tsx             # Train no, name, status, date, Refresh button
│       ├── CurrentStationCard.tsx       # Station name, code (CNB), delay tag
│       ├── PredictionCard.tsx           # Horizon tag (H1/H2/H3), times & delays
│       ├── PredictionList.tsx           # Dynamic container rendering available horizons
│       ├── PredictionExplanation.tsx    # Factual methodology disclaimer
│       ├── LoadingSkeleton.tsx          # Shimmer animated placeholder
│       ├── EmptyState.tsx               # Initial prompt with popular train chips
│       └── ErrorState.tsx               # User-friendly error card with retry button
└── test/
    └── frontend_unit.test.mjs           # Automated test suite (10/10 PASS)
```

---

## 5. Type Safety & API Response Schema

The frontend strictly enforces type safety via [`src/types/eta.ts`](file:///e:/train/frontend/src/types/eta.ts), matching the backend schema:

```typescript
export interface CurrentStation {
  code: string;
  name: string;
  delay_minutes: number;
}

export interface HorizonPrediction {
  horizon: number;
  station: string;
  scheduled_arrival: string;
  predicted_delay_minutes: number;
  predicted_eta: string;
}

export interface TrainETAResponse {
  success: boolean;
  train_no: string;
  train_name: string;
  status: string;
  journey_date: string;
  current_station: CurrentStation;
  predictions: HorizonPrediction[];
}

export interface APIErrorState {
  title: string;
  message: string;
  statusCode?: number;
}
```

---

## 6. UI Features & Design Decisions

1. **Header:**
   - Title: `Dynamic Train ETA`
   - Subtitle: `AI-powered real-time arrival prediction`
   - Status badge: `Live Prediction System` with animated green pulse indicator.
   - Refrains from claiming "100% accurate" or "guaranteed".

2. **Train Search:**
   - Prominent search input with `placeholder="Enter train number"`.
   - Client-side validation: Requires 4 or 5 numeric digits before issuing network calls.
   - Supports keyboard `Enter` submission and quick chips (`12301`, `12951`, `12002`).

3. **Loading State:**
   - Elegant skeleton cards with animated CSS shimmer gradient.
   - Spinner with label: *"Fetching live train data and computing dynamic ETA forecast..."*.

4. **Train Summary & Refresh:**
   - Displays train number badge, train name, journey date, and operational status badge (`Departed`, `Running`, `Arrived`).
   - "Updated just now" / "Updated 8:42 AM" timestamp.
   - On-demand "Refresh" button (no aggressive automatic polling).

5. **Current Location Card:**
   - Highlights current station name and station code (`CNB`).
   - Color-coded operational delay badge (green: on time $\le 5$ min, amber: moderate $5-20$ min, red: severe $> 20$ min).

6. **Multi-Horizon Predictions:**
   - Dynamically maps prediction horizons ($H_1$: *Next Station*, $H_2$: *2 Stations Ahead*, $H_3$: *3 Stations Ahead*).
   - Only displays horizons actually returned by the API. If only $H_1$ remains on route, only $H_1$ is rendered without phantom placeholders.
   - Shows Scheduled Arrival, Predicted Delay, and Predicted ETA with date context.

7. **Prediction Explanation:**
   - Small informational banner:
     > *"Predictions are generated using live train telemetry, historical delay patterns, timetable information, route progress, and an XGBoost machine-learning model."*

8. **Error Handling:**
   - Converts HTTP status codes to clear, human-readable explanations:
     - **400:** "Invalid Train Number. Train number must be 4 or 5 digits."
     - **404:** "Train Not Found. Train could not be found in active railway schedules or live tracking systems."
     - **422:** "Route or Journey Limitation. The train has either completed its run or is not running on this journey date."
     - **502:** "Live Tracking Service Unavailable. The upstream railway tracking provider returned an error."
     - **504:** "Request Timeout. The railway tracking service did not respond in time. Please try again."
     - **0 (Offline):** "Backend Offline. Unable to connect to the prediction backend at http://127.0.0.1:8000."
   - Never exposes backend internals, tracebacks, or credentials.

9. **Responsive Design:**
   - Built with CSS grid and flexbox with mobile-first breakpoints (`@media (max-width: 640px)`).
   - Verified on mobile viewport (390px) without horizontal scrollbars or clipping.

---

## 7. Verification & Test Results

### 1. Build Verification
```
> frontend@0.0.0 build
> tsc -b && vite build

✓ 1899 modules transformed.
dist/index.html                   0.90 kB │ gzip:  0.50 kB
dist/assets/index-Dq-ZzfeJ.css   13.64 kB │ gzip:  3.04 kB
dist/assets/index-BabqJ28t.js   238.86 kB │ gzip: 75.09 kB
✓ built in 552ms
```
- **Linter (oxlint):** 0 errors, 0 warnings.
- **TypeScript (tsc -b):** Clean pass with `verbatimModuleSyntax`.

### 2. Automated Unit Tests (`npm test`)
```
TAP version 13
# Subtest: Train Number Validation
  ok 1 - Accepts valid 5-digit train numbers
  ok 2 - Accepts valid 4-digit train numbers
  ok 3 - Rejects non-numeric, short, or oversized train numbers
# Subtest: API Error Handling and Human-Readable Messages
  ok 1 - Maps 404 to Train Not Found
  ok 2 - Maps 502 to Upstream Service Unavailable
  ok 3 - Maps 504 to Request Timeout
  ok 4 - Maps 0 (Network) to Backend Offline
# Subtest: Horizon Prediction Rendering Logic
  ok 1 - Gracefully handles single horizon (H1 only)
  ok 2 - Handles multi-horizon (H1, H2, H3)
# Subtest: Security Verification in Frontend Codebase
  ok 1 - Ensures no auth headers or secret tokens in frontend service
# tests 10, pass 10, fail 0
```

### 3. Real End-to-End Test (Train 12301)
Live controlled verification executed through browser subagent:
- **Query:** Train `12301`
- **FastAPI Endpoint:** `http://127.0.0.1:8000/api/train/12301/eta`
- **RailRadar Live State:** Departed, at Kanpur Central (`CNB`)
- **Current Delay:** 0 min (On Time)
- **Prediction Generated:**
  - Horizon: $H_1$ (Next Station)
  - Target Station: `NDLS` (New Delhi)
  - Scheduled Arrival: `10:05 AM, Sep 30`
  - Predicted Delay: `+8.3 min`
  - Predicted ETA: `10:13 AM, Sep 30`
- **UI Render Verification:** Train summary card, current location card, single horizon $H_1$ card, prediction explanation, and refresh action all rendered and verified.
- **Recording Artifact:** Saved as WebP video recording.

---

## 8. Security Verification Matrix

| Check | Requirement | Result |
|---|---|---|
| **Frontend Source Secrets** | No RailRadar API key in `src/` | **PASS (0 matches)** |
| **Frontend Env Secrets** | Only `VITE_API_BASE_URL` in `.env` | **PASS** |
| **Authorization Headers** | No custom Auth headers in client fetch | **PASS** |
| **Direct RailRadar Calls** | Frontend communicates only with FastAPI | **PASS** |
| **Error Exposure** | No stack traces or raw upstream payloads exposed | **PASS** |

---

## 9. Deliverables Summary

| Item | Status | Notes |
|---|---|---|
| **FRONTEND BUILD** | **PASS** | Vite + React + TypeScript builds cleanly |
| **API INTEGRATION** | **PASS** | Connects to `GET /api/train/{train_no}/eta` |
| **H1 DISPLAY** | **PASS** | Displays next station, scheduled, delay, ETA |
| **H2 DISPLAY** | **PASS** | Dynamic support when returned by API |
| **H3 DISPLAY** | **PASS** | Dynamic support when returned by API |
| **ERROR STATES** | **PASS** | 400, 404, 422, 502, 504, network offline |
| **RESPONSIVE UI** | **PASS** | Verified desktop & mobile (390px) |
| **SECURITY CHECK** | **PASS** | Zero secrets, zero auth headers in frontend |
| **REAL END-TO-END TEST** | **PASS** | Train 12301 live test rendered end-to-end |
| **DOCUMENTATION** | [`reports/FRONTEND_ETA_DASHBOARD.md`](file:///e:/train/reports/FRONTEND_ETA_DASHBOARD.md) | Complete report generated |
