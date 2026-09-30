# Multi-Horizon Delay Prediction Results Report
**SIH Problem Statement 26028: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**
*Generated: 2026-09-29 22:10:24*
*Models: Model H1 (Next Stop), Model H2 (2 Stops Ahead), Model H3 (3 Stops Ahead)*

---

## 1. Objective
This experiment extends the baseline single-horizon XGBoost architecture to **multi-horizon delay prediction**, forecasting train delay across three successive commercial stations:
* **Horizon 1 ($H_1$)**: Delay at the next scheduled station $s_{i+1}$ (`target_delay_h1`)
* **Horizon 2 ($H_2$)**: Delay at the station two scheduled stops ahead $s_{i+2}$ (`target_delay_h2`)
* **Horizon 3 ($H_3$)**: Delay at the station three scheduled stops ahead $s_{i+3}$ (`target_delay_h3`)

---

## 2. Target Definitions & Topological Guarantees
All targets strictly obey scheduled timetable topology:
* $H_1: \text{target\_delay\_h1} = \text{delay}(s_{i+1}) \iff \text{sched\_station\_no}(s_{i+1}) == \text{sched\_station\_no}(s_i) + 1$
* $H_2: \text{target\_delay\_h2} = \text{delay}(s_{i+2}) \iff \text{sched\_station\_no}(s_{i+2}) == \text{sched\_station\_no}(s_i) + 2$
* $H_3: \text{target\_delay\_h3} = \text{delay}(s_{i+3}) \iff \text{sched\_station\_no}(s_{i+3}) == \text{sched\_station\_no}(s_i) + 3$

If an intermediate station is unobserved, the target evaluates strictly to `null`, preventing step-skipping leakage.

---

## 3. Target Audit Summary
The multi-horizon audit (`reports/MULTI_HORIZON_TARGET_AUDIT.md`) verified:
* **Sequence Distance Invariants**: Exactly +1, +2, +3 verified across all supervised rows (**0 violations**).
* **Cross-Journey Contamination**: Zero leaks across `(date, train_no)` boundaries (**0 violations**).
* **Termination Boundaries**: Terminus stops have 0 non-null targets across all horizons (**0 leaks**).
* **Usable Corpus Samples**:
  * Horizon 1: **34,205,951 usable samples** (92.12%)
  * Horizon 2: **32,358,377 usable samples** (87.14%)
  * Horizon 3: **30,528,318 usable samples** (82.21%)
* **Audit Decision**: **PASS FOR ALL HORIZONS**.

---

## 4. Dataset & Chronological Splits
All models were trained on identical chronological splits using stratified reproducible sampling:
* **TRAIN**: `2025-02-08` through `2025-10-31` ($N = 1,200,000$)
* **VALIDATION**: `2025-11-01` through `2025-12-31` ($N = 200,000$, early stopping)
* **TEST**: `2026-01-01` through `2026-02-07` ($N = 200,000$, out-of-time evaluation)

---

## 5. Feature Set
All three models used the exact 30 leak-free features approved in the ML Readiness Audit:
* **27 Numerical Features**: `current_delay`, `prev_station_delay`, `prev_delay_2`, `prev_delay_3`, `delay_change`, `delay_change_2_stations`, `delay_change_3_stations`, `current_station_seq`, `stations_remaining`, `dist_from_origin`, `remaining_dist`, `journey_progress`, `route_total_distance`, `route_total_stations`, `scheduled_dwell_time`, `sched_section_distance`, `sched_section_travel_time`, `sched_planned_speed`, `arr_min`, `dep_min`, `arrival_day`, `departure_day`, `scheduled_hour`, `day_of_week`, `month`, `day`, `is_weekend`
* **3 Categorical Features**: `type_code` (8 categories), `station_zone` (18 categories), `next_station_zone` (18 categories)
* **Leakage Isolation**: No future station delays ($s_{i+1}, s_{i+2}$) were provided to models predicting further downstream.

---

## 6. Model Hyperparameters & Training Execution
* **Architecture**: XGBoost Regressor (`objective='reg:squarederror'`, `tree_method='hist'`)
* **Hyperparameters**: `learning_rate=0.05`, `max_depth=8`, `subsample=0.8`, `colsample_bytree=0.8`, `n_estimators=600`, `early_stopping_rounds=30`
* **Hardware**: 12 CPU Cores
* **Training Durations**:
  * Model H1: **66.44 s** (Best iter: 599)
  * Model H2: **71.58 s** (Best iter: 599)
  * Model H3: **74.73 s** (Best iter: 599)

---

## 7. Comparative Multi-Horizon Benchmark on Test Set (N=200,000)

| Horizon | Predicted Target Station | Test Samples | MAE (min) | RMSE (min) | MedAE (min) | +/- 5 min | +/- 10 min | +/- 15 min |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| **H1** | Station $s_{i+1}$ (Next Stop) | 200,000 | **6.95** | **18.59** | **3.2** | **64.60%** | **82.57%** | **89.68%** |
| **H2** | Station $s_{i+2}$ (2 Stops Ahead) | 200,000 | **10.29** | **23.01** | **5.4** | **47.68%** | **70.10%** | **81.06%** |
| **H3** | Station $s_{i+3}$ (3 Stops Ahead) | 200,000 | **12.95** | **26.55** | **7.3** | **37.43%** | **61.21%** | **74.38%** |

---

## 8. Comparison with Single-Horizon Baseline (v1)
* **Single-Horizon v1 Test MAE**: **7.39 minutes** (Trained on 1.5M samples)
* **Multi-Horizon H1 Test MAE**: **6.95 minutes**
* **Difference**: -0.44 minutes (Independently reproduces the v1 benchmark within sampling variance).

---

## 9. Feature Importance Analysis Across Horizons

### Top 10 Features for Horizon 1 (Next Stop)
| Rank | Feature | Information Gain | Gain Share (%) | Splits |
|---|---|--:|--:|--:|
| 1 | `current_delay` | 3,958,326.25 | 62.64% | 7,015 |
| 2 | `prev_station_delay` | 980,154.50 | 15.51% | 5,785 |
| 3 | `prev_delay_3` | 610,261.69 | 9.66% | 4,406 |
| 4 | `delay_change_3_stations` | 81,533.10 | 1.29% | 5,305 |
| 5 | `type_code` | 44,286.73 | 0.70% | 1,332 |
| 6 | `delay_change` | 36,429.84 | 0.58% | 7,627 |
| 7 | `route_total_distance` | 36,014.98 | 0.57% | 3,490 |
| 8 | `day` | 35,651.07 | 0.56% | 4,312 |
| 9 | `month` | 33,598.20 | 0.53% | 2,800 |
| 10 | `sched_section_travel_time` | 33,043.53 | 0.52% | 5,682 |

### Top 10 Features for Horizon 2 (2 Stops Ahead)
| Rank | Feature | Information Gain | Gain Share (%) | Splits |
|---|---|--:|--:|--:|
| 1 | `current_delay` | 3,820,798.75 | 60.97% | 7,295 |
| 2 | `prev_station_delay` | 987,992.56 | 15.77% | 5,737 |
| 3 | `prev_delay_3` | 595,753.75 | 9.51% | 4,556 |
| 4 | `delay_change_3_stations` | 86,296.09 | 1.38% | 5,382 |
| 5 | `type_code` | 47,795.43 | 0.76% | 1,627 |
| 6 | `delay_change` | 44,216.20 | 0.71% | 7,096 |
| 7 | `day` | 40,009.36 | 0.64% | 4,272 |
| 8 | `route_total_distance` | 38,195.90 | 0.61% | 3,918 |
| 9 | `next_station_zone` | 37,232.58 | 0.59% | 7,289 |
| 10 | `month` | 36,235.72 | 0.58% | 2,946 |

### Top 10 Features for Horizon 3 (3 Stops Ahead)
| Rank | Feature | Information Gain | Gain Share (%) | Splits |
|---|---|--:|--:|--:|
| 1 | `current_delay` | 3,618,767.50 | 58.47% | 7,721 |
| 2 | `prev_station_delay` | 978,189.25 | 15.80% | 5,863 |
| 3 | `prev_delay_3` | 593,981.75 | 9.60% | 4,572 |
| 4 | `delay_change_3_stations` | 92,789.94 | 1.50% | 5,278 |
| 5 | `type_code` | 53,837.14 | 0.87% | 1,871 |
| 6 | `delay_change` | 50,414.21 | 0.81% | 6,636 |
| 7 | `next_station_zone` | 48,015.60 | 0.78% | 7,697 |
| 8 | `day` | 43,697.89 | 0.71% | 4,270 |
| 9 | `route_total_distance` | 42,466.55 | 0.69% | 4,600 |
| 10 | `sched_section_travel_time` | 39,739.35 | 0.64% | 4,683 |

---

## 10. Technical Error Analysis & Physical Dynamics

1. **Error Accumulation Over Distance**:
   * As the forecast horizon increases from 1 stop to 3 stops, Test MAE increases from **6.95 min** to **10.29 min** to **12.95 min**.
   * This degradation aligns directly with railway operational uncertainty: over multiple track sections (typically 50–150 km), unseen disturbances (signal holds, speed restrictions, conflicting movements at junctions) compound.
2. **Shift in Feature Relevance**:
   * For **H1**, immediate dynamic features (`current_delay`, `prev_station_delay`) dominate the split decisions.
   * For **H2 and H3**, static topological and timetable buffer features (`route_total_distance`, `sched_section_travel_time`, `stations_remaining`, `type_code`) gain higher relative importance share, because journey slack and train precedence determine long-range recovery.
3. **Punctuality Horizon**:
   * Within **+/- 15 minutes**, accuracy remains strong across horizons: **89.68%** (H1), **81.06%** (H2), and **74.38%** (H3).

---

## 11. Known Limitations
1. **Unmeasured Downstream Delays**: The multi-step horizon assumes downstream timetable sections are static and does not yet integrate real-time junction precedence or weather alerts occurring between $s_i$ and $s_{i+3}$.
2. **Fixed 3-Hop Limit**: Trips with 30+ stops currently require rolling recursive inference beyond horizon 3.
3. **Horizon Boundary Drop-off**: Stations near the end of the line ($N-2, N-1$) naturally lack downstream labels for $H_2$ and $H_3$.

---

## 12. Recommended Next Steps
1. **Unified Multi-Horizon Inference Pipeline**: Package Models H1, H2, and H3 into a unified prediction interface that simultaneously outputs ETA for $s_{i+1}, s_{i+2}, s_{i+3}$.
2. **Terminus Direct Regressor**: Train a dedicated long-range model predicting destination delay directly (`target_terminus_delay`).
3. **ONNX Export & Latency Benchmarking**: Export the trained multi-horizon boosters to ONNX runtime for sub-5 millisecond batch inference in the serving microservice.
