# Multi-Horizon ETA Inference Service Report
**SIH Problem Statement 26028: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**
*Generated: 2026-09-30 09:48:46*
*Module: `src/inference` (`model_loader.py`, `predictor.py`, `eta_calculator.py`, `schemas.py`)*

---

## 1. System Architecture

The offline Multi-Horizon Inference Service is structured as a modular, decoupled Python subsystem designed for low-latency operational serving:

```
[Client / API Request]
         |
         v
+------------------------------------------------------------------+
|                   MultiHorizonETAPredictor                       |
|  - Date Parsing & Format Validation (YYYY-MM-DD)                 |
|  - Timetable Route Resolution (O(1) in-memory route index)       |
|  - Boundary Check (Terminus & remaining stops validation)        |
+------------------------------------------------------------------+
         |
         +---------------------------------+
         |                                 |
         v                                 v
+-------------------------------+ +--------------------------------+
|    MultiHorizonModelLoader    | |     Feature Vector Builder     |
| - Booster H1 (Next stop)      | | - 30 Leak-Free Features        |
| - Booster H2 (2 stops ahead)  | | - Native Categorical Dtypes    |
| - Booster H3 (3 stops ahead)  | | - Preserves Null Lag Tree Paths|
+-------------------------------+ +--------------------------------+
         |                                 |
         +----------------+----------------+
                          |
                          v
+------------------------------------------------------------------+
|                     Booster Inference Matrix                     |
|  y_hat_H1 = Booster_H1.predict(dmatrix)                          |
|  y_hat_H2 = Booster_H2.predict(dmatrix)                          |
|  y_hat_H3 = Booster_H3.predict(dmatrix)                          |
+------------------------------------------------------------------+
                          |
                          v
+------------------------------------------------------------------+
|                      ETA Calculation Engine                      |
|  Sched_Arrival = journey_date + (arrival_day - 1) + arr_min      |
|  Predicted_ETA = Sched_Arrival + timedelta(minutes=y_hat)        |
|  - Midnight crossing date shift automatically handled            |
+------------------------------------------------------------------+
                          |
                          v
+------------------------------------------------------------------+
|                   MultiHorizonResponse (JSON)                    |
+------------------------------------------------------------------+
```

---

## 2. Input Schema
The inference service accepts structured input conforming to `PredictionRequest`:

```json
{
  "train_no": "01023",
  "journey_date": "2025-02-08",
  "current_station": "JJR",
  "current_delay_minutes": 21.0,
  "features": {
    "prev_station_delay": 6.0,
    "prev_delay_2": 2.0
  },
  "horizons": [1, 2, 3]
}
```
- **Validation**:
  - `train_no`: Zero-padded 5-digit Indian Railways train number. Checked against master timetable (8,673 routes).
  - `journey_date`: Validated against `YYYY-MM-DD` ISO regex.
  - `current_station`: Validated against train route sequence and master station dictionary (8,973 stations).
  - `current_delay_minutes`: Numeric delay observation at current station.

---

## 3. Output Schema
The response matches the exact JSON structure specified in the problem statement:

```json
{
  "train_no": "01023",
  "journey_date": "2025-02-08",
  "current_station": "JJR",
  "current_delay_minutes": 21.0,
  "predictions": [
    {
      "horizon": 1,
      "station": "NIRA",
      "station_sequence": 4,
      "scheduled_arrival": "2025-02-08 23:13:00",
      "predicted_delay_minutes": 22.5,
      "predicted_eta": "2025-02-08 23:35:30",
      "confidence": null
    },
    {
      "horizon": 2,
      "station": "LNN",
      "station_sequence": 5,
      "scheduled_arrival": "2025-02-08 23:23:00",
      "predicted_delay_minutes": 24.4,
      "predicted_eta": "2025-02-08 23:47:24",
      "confidence": null
    },
    {
      "horizon": 3,
      "station": "WTR",
      "station_sequence": 6,
      "scheduled_arrival": "2025-02-08 23:53:00",
      "predicted_delay_minutes": 26.1,
      "predicted_eta": "2025-02-09 00:19:06",
      "confidence": null
    }
  ]
}
```
*Note on Confidence*: Per instructions, `confidence` is strictly set to `null` until calibrated conformal prediction or quantile loss regression is integrated.

---

## 4. Model Loading & Feature Alignment
- Native boosters loaded via `MultiHorizonModelLoader`:
  - `backend/models/xgboost_eta_h1_v1.json` (12.4 MB)
  - `backend/models/xgboost_eta_h2_v1.json` (12.8 MB)
  - `backend/models/xgboost_eta_h3_v1.json` (13.2 MB)
- **Feature Ordering Guarantee**: Feature ordering is dynamically read from `backend/models/xgboost_eta_h{1,2,3}_v1_features.json` to eliminate feature desynchronization.
- **Categorical Encoding**: Categoricals (`type_code`, `station_zone`, `next_station_zone`) are enforced using `pd.Categorical(..., categories=manifest['categorical_categories'][col])`, matching the exact category indexes established during training.

---

## 5. ETA Calculation & Midnight Crossing Protocol
- Timetable arrival times are defined relative to the train origin departure date using `arrival_day` (Day 1, Day 2, Day 3).
- **Scheduled Timestamp**:
  $$\text{Sched\_Arrival} = \text{journey\_date} + (\text{arrival\_day} - 1) \times 24\text{h} + \text{arr\_min}$$
- **Dynamic ETA**:
  $$\text{Predicted\_ETA} = \text{Sched\_Arrival} + \Delta t_{\text{pred\_delay}}$$
- **Midnight Crossing**: When a late-night train (e.g. scheduled at 23:53) accumulates delay pushing arrival to 00:19, the timestamp automatically rolls over to the next calendar date with 100% mathematical consistency.

---

## 6. Deterministic Test Case Results

All 10 deterministic test cases passed verification:

| Test Case Name | Status | Observed Execution Outcome |
|---|---|---|
| Case 1: Normal Train & Station | **PASS** | Predicted H1=JJR (delay=14.7m, ETA=2025-02-08 22:58:42) |
| Case 2: Non-Zero Delay Momentum | **PASS** | Current=21m -> Predicted H1=22.5m, H2=24.4m, H3=26.1m |
| Case 3: Midnight Boundary Crossing | **PASS** | Scheduled=2025-02-09 00:22:00 -> Predicted ETA=2025-02-09 00:46:54 |
| Case 4: Near-Terminus Truncation | **PASS** | 1 stop remaining -> Produced 1 horizon (H1=KOP) |
| Case 5: Missing Optional Features (NaN Lags) | **PASS** | Preserved None lags -> H1 delay=7.5m |
| Case 6: Unknown Train Error Handling | **PASS** | Caught expected exception: Train '99999' not found in master timetable schedule. |
| Case 7: Station Route Validation | **PASS** | Correctly caught UnknownStationError for 'ZZZZZ' and StationNotOnRouteError for 'NDLS' |
| Case 8: Beyond Terminus Error Handling | **PASS** | Caught expected exception: Insufficient route remaining for Train '01023' at 'KOP'. Stops remaining to terminus: 0, requested horizon: 1. |
| Case 9: Multi-Train Type Generalization | **PASS** | Vande Bharat H1=PMY | Rajdhani H1=QLN | Passenger H1=MZR |
| Case 10: Extreme Delay Robustness (+240m) | **PASS** | Input=240m -> Predicted H1=204.0m, ETA=2025-02-09 02:37:00 |

---

## 7. Prediction Examples on Real Historical Journeys

Representative sample of predictions against ground truth records from historical journeys:

| Train | Journey Date | Current Station | Current Delay | Target (H1) | Scheduled Arrival | Predicted Delay | Ground Truth | Predicted Dynamic ETA | Discrepancy |
|---|---|---|--:|---|---|--:|--:|---|--:|
| `18190` | `2025-02-08` | `PTJ` | 0m | `TUP` | 2025-02-08 12:10:00 | **7.1m** | 0m | `2025-02-08 12:17:06` | 7.1m |
| `13032` | `2025-02-08` | `BUP` | 21m | `KPRD` | 2025-02-09 06:05:00 | **22.3m** | 21m | `2025-02-09 06:27:18` | 1.3m |
| `20705` | `2025-02-08` | `MMR` | 1m | `NK` | 2025-02-08 10:58:00 | **3.6m** | 17m | `2025-02-08 11:01:36` | 13.4m |
| `17015` | `2025-02-08` | `ANV` | 26m | `SLO` | 2025-02-08 18:48:00 | **29.4m** | 28m | `2025-02-08 19:17:24` | 1.4m |
| `18044` | `2025-02-08` | `NMBR` | 11m | `BTS` | 2025-02-08 06:43:00 | **10.5m** | 24m | `2025-02-08 06:53:30` | 13.5m |

### Historical Validation Metrics:
- **Sample Evaluated**: 100 historical journeys
- **Horizon 1 Sample MAE**: **8.98 minutes**
- **Median Absolute Error**: **4.7 minutes**
- **10-Minute Punctuality**: **78.00%**
- **Target Station Sequence Fidelity**: **100.00%**

---

## 8. Error Handling Specifications
The service raises strongly-typed exceptions caught by higher-level REST APIs:
1. `UnknownTrainError`: Train number not present in master schedule.
2. `UnknownStationError`: Station code unrecognized across Indian Railways.
3. `StationNotOnRouteError`: Station exists in IR, but train does not stop there.
4. `InsufficientRouteRemainingError`: Requested horizon extends beyond train terminus.
5. `InvalidJourneyDateError`: Malformed date format.
6. `FeatureValidationError`: Missing required dynamic inputs.
7. `ModelLoadError`: Corrupted or missing booster weights.

---

## 9. Known Limitations
1. **Static Timetable Basis**: Route lookups assume the scheduled timetable is current; unplanned emergency diversions require dynamic route override.
2. **Deterministic Output**: Currently outputs point predictions; does not yet emit probabilistic $\pm 5$ min uncertainty envelopes.
3. **Python In-Memory Execution**: Currently runs via native XGBoost C++ API in Python; has not yet been exported to compiled ONNX runtime.

---

## 10. Recommended Next Step
Proceed to **packaging the service as a REST API (FastAPI)** and **exporting the boosters to ONNX Runtime**, followed by building the real-time simulation / demo dashboard.
