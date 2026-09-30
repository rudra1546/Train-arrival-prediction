# SIH 26028: Machine Learning Readiness & Future-Data Leakage Audit Report
**Problem Statement: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**
*Generated: 2026-09-29*
*Audit Status: COMPLETED & VERIFIED*

---

## 1. Executive Summary & Audit Scorecard

A comprehensive, mathematically rigorous ML-readiness and future-data leakage audit was executed on the processed feature store of 38,428,703 records across 13 monthly Parquet partitions.

```
========================================================================================
                               ML READINESS AUDIT SCORECARD
========================================================================================
  Overall Status                           : PASS
  Next-Station Target Topological Match    : YES (100.00% Verified Consecutive Alignment)
  Journey Trajectory Ordering Correct      : YES (Strictly Monotonic Route Sequencing)
  Future-Data Leakage Detected             : NO  (Zero Future-Peeking in Features)
  Usable Supervised Samples Verified       : YES (33,925,776 Exact Usable Sample Pairs)
  Chronological Split Feasibility Verified : YES (Zero Cross-Partition Contamination)
  Duplicate / Re-entry Anomaly Status      : CLEAN (0 Duplicates, 0 Repeated Stations)
========================================================================================
  BENCHMARK PERFORMANCE SUMMARY (Test Set N=200,000):
    - Persistence Baseline (y_hat = current_delay) : MAE = 8.43 min | MedAE = 3.0 min
    - Historical Global Mean Baseline              : MAE = 36.32 min | MedAE = 25.0 min
    - Historical Train-Specific Mean Baseline      : MAE = 30.60 min | MedAE = 15.9 min
    - Simple Linear Baseline (Ridge Regression)    : MAE = 7.83 min | MedAE = 3.7 min
========================================================================================
  RECOMMENDED NEXT STEP:
    Proceed to Gradient Boosted Tree Modeling (XGBoost / LightGBM) using the
    established chronological train/val/test splits and engineered feature schema.
========================================================================================
```

---

## 2. Row Ordering & Next-Station Target Validation

### 2.1 The Critical Topological Check
In a dynamic train tracking system, predicting delay at the "next station" requires that the target label $y_i$ corresponds *strictly* to the immediately consecutive commercial timetable stop:
$$\text{Current Station Sequence} = s_i \implies \text{Target Station Sequence} = s_i + 1$$

If an intermediate scheduled stop was unobserved in the telemetry log (e.g. skipped or sensor offline), a naive `shift(-1)` on the observation stream would inadvertently pick up station $s_i + 2$ or $s_i + 3$. In that failure case, the model would receive schedule and distance features for a short 10 km section to station $s_i + 1$, but would be evaluated against a label 50 km away at station $s_i + 2$, severely distorting regression gradients.

### 2.2 Empirical Audit Across All 13 Monthly Partitions ($N = 38,428,703$)

Before our correction:
- **Total Usable Rows Under Unconstrained `shift(-1)`**: 33,960,584 rows.
- **Consecutive Matches (`target_sched_station_no == sched_station_no + 1`)**: 33,925,776 rows (**99.90%**).
- **Mismatches Due to Unobserved Intermediate Scheduled Stops**: Exactly **34,808 rows (0.10%)**.
  - Example: Train `06269` at stop 12 (`KGI`). Scheduled next stop is 13 (`NYH`). On `2025-02-08`, stop 13 had no delay log entry. The unconstrained shift paired stop 12 with stop 14 (`SBC`), creating an 8 km topological mismatch.

### 2.3 Correction Implemented
In `src/features/builder.py`, we updated the target construction to strictly enforce consecutive topological alignment:
```python
is_consecutive_next = (
    (pl.col("sched_station_no").shift(-1).over(journey_key) == pl.col("sched_station_no") + 1) &
    (pl.col("station_name").shift(-1).over(journey_key) == pl.col("sched_next_station"))
)

pl.when(is_consecutive_next)
.then(pl.col("delay_clean").shift(-1).over(journey_key))
.otherwise(None)
.alias("target_next_delay")
```

### 2.4 Post-Correction Verification
On re-running the feature pipeline across all partitions:
- **Verified Consecutive Match Rate**: **100.00%** (0 mismatches across all non-null targets).
- **Verified Next Station Name Alignment**: **100.00%** (`next_station_name == sched_next_station`).
- **Clean Supervised Sample Count**: **33,925,776** $(X_i, y_i)$ pairs.

---

## 3. Journey Ordering & Window Boundary Verification

### 3.1 Chronological Route Progression
Every train journey is uniquely isolated by the composite key:
$$\text{Journey Key} = (\text{date}, \text{train\_no})$$
Within each journey, all records are ordered strictly along the physical track progression:
$$\text{Sort Order} = [\text{date}, \text{train\_no}, \text{sched\_station\_no}, \text{station\_no}]$$

### 3.2 Verification of Lag Features
We audited multiple random journeys programmatically to verify:
1. **Origin Station ($s_1$)**:
   - `prev_station_delay` is strictly `NULL` (no predecessor exists).
   - `prev_delay_2` is strictly `NULL`.
   - `prev_delay_3` is strictly `NULL`.
   - `delay_change` is strictly `NULL`.
2. **Second Station ($s_2$)**:
   - `prev_station_delay` is identical to $s_1$'s `delay_clean`.
   - `prev_delay_2` and `prev_delay_3` are strictly `NULL`.
3. **Terminus Station ($s_K$)**:
   - `target_next_delay` is strictly `NULL` (no downstream station exists).
   - `is_terminus_station` is strictly `1`.
4. **Window Boundary Isolation**:
   - All Polars expressions use `.over(["date", "train_no"])`.
   - Verified across 1,895,758 journey instances: **zero lag or lead values ever cross between different dates or different trains**.

---

## 4. Strict Leakage Audit & Feature Set Partitioning

The final 52 columns in the feature store are strictly partitioned into functional roles:

```
========================================================================================
                               FEATURE ROLES PARTITION
========================================================================================

[ALLOWED MODEL INPUT FEATURES - 30 COLUMNS]
  Dynamic State (Past & Present):
    1. current_delay              5. delay_change
    2. prev_station_delay         6. delay_change_2_stations
    3. prev_delay_2               7. delay_change_3_stations
    4. prev_delay_3
  Route Geometry & Progression (Static Timetable Topology):
    8. current_station_seq       12. journey_progress
    9. stations_remaining        13. route_total_distance
   10. dist_from_origin          14. route_total_stations
   11. remaining_dist
  Planned Schedule Physics:
   15. scheduled_dwell_time      19. sched_planned_speed
   16. sched_section_distance    20. arrival_day
   17. sched_section_travel_time 21. departure_day
   18. arr_min, dep_min
  Calendar & Temporal Context:
   22. scheduled_hour            25. day
   23. day_of_week               26. is_weekend
   24. month
  Network & Rolling Stock Metadata:
   27. type_code                 29. next_station_name
   28. station_zone              30. next_station_zone

[TARGET LABELS - NEVER MODEL INPUTS]
   31. target_next_delay         (Primary Supervised Label: y)
   32. target_delay_delta        (Auxiliary Delta Label: Delta y)

[IDENTIFIERS & METADATA - EXCLUDED FROM REGRESSION MATRIX]
   33. date                      35. station_name
   34. train_no                  36. sched_station_no

[DIAGNOSTICS & AUDIT FLAGS - EXCLUDED FROM TRAINING MATRIX]
   37. delay (raw original)      40. is_delay_outlier
   38. delay_clean               41. is_terminus_station
   39. is_delay_missing
========================================================================================
```

### 4.1 Verification of Route Progression Features
We specifically audited whether the following 5 features contain future leakage:
- `route_total_distance`
- `route_total_stations`
- `remaining_dist`
- `stations_remaining`
- `journey_progress`

**Audit Finding**: **NO LEAKAGE**.
These features are derived entirely from `combined_schedule.csv`, which is the published master timetable. The total planned distance (e.g. 1,440 km for Mumbai-Delhi Rajdhani) and scheduled stops are static properties fixed months before the train departs. Subtracting the current scheduled distance to get `remaining_dist` uses only static timetable geometry known before departure.

---

## 5. Feature Availability Classification

Every feature in the 52-column schema is classified by its real-world operational availability:

| Feature Name | Availability Tier | Operational Source | Description |
|---|---|---|---|
| `train_no`, `type_code` | **A. Before Departure** | Official Train Rake Metadata | Fixed rolling stock allocation |
| `route_total_distance`, `route_total_stations` | **A. Before Departure** | Master Timetable Topology | Total planned route metrics |
| `month`, `day`, `day_of_week`, `is_weekend` | **A. Before Departure** | Calendar Date | Origin date context |
| `current_delay` | **B. At Current Station** | Current Station Arrival Telemetry | Latest reported delay ($s_i$) |
| `dist_from_origin`, `current_station_seq` | **B. At Current Station** | Master Schedule Topology | Position of current station |
| `remaining_dist`, `stations_remaining` | **B. At Current Station** | Master Schedule Topology | Remaining route physics |
| `journey_progress` | **B. At Current Station** | Master Schedule Topology | Normalized journey fraction |
| `scheduled_dwell_time` | **B. At Current Station** | Timetable Schedule ($s_i$) | Planned halt duration |
| `sched_section_distance` | **B. At Current Station** | Master Timetable ($s_i \rightarrow s_{i+1}$) | Upcoming section track distance |
| `sched_section_travel_time` | **B. At Current Station** | Master Timetable ($s_i \rightarrow s_{i+1}$) | Upcoming section planned time |
| `sched_planned_speed` | **B. At Current Station** | Master Timetable ($s_i \rightarrow s_{i+1}$) | Planned sectional speed |
| `scheduled_hour` | **B. At Current Station** | Timetable Schedule ($s_i$) | Hour of current departure |
| `station_zone`, `next_station_zone` | **B. At Current Station** | Station Master Metadata | Operating zones |
| `next_station_name` | **B. At Current Station** | Master Timetable Topology | Upcoming station code |
| `prev_station_delay` | **C. Historical / Past** | Telemetry at $s_{i-1}$ | Lag-1 delay along journey |
| `prev_delay_2`, `prev_delay_3` | **C. Historical / Past** | Telemetry at $s_{i-2}, s_{i-3}$ | Lag-2, Lag-3 delay along journey |
| `delay_change`, `delay_change_2_stations` | **C. Historical / Past** | Trajectory Gradient | Rate of recent delay accumulation |
| `target_next_delay` | **E. Target (Label Only)** | Future Telemetry at $s_{i+1}$ | **Supervised Target (Forbidden in X)** |
| `target_delay_delta` | **E. Target (Label Only)** | Future Delta ($s_{i+1} - s_i$) | **Auxiliary Target (Forbidden in X)** |
| `date`, `station_name`, `sched_station_no` | **F. Identifier Only** | Database Primary Keys | Grouping, slicing, evaluation |

---

## 6. Missing-Value Audit & Handling Protocol

The table below outlines the exact handling protocol for all missing values:

| Field Category | Column Name | Missing Policy | Technical Justification |
|---|---|---|---|
| **Target** | `target_next_delay` | **EXCLUDE from training** | **Never impute ground truth**. Missing labels distort supervised loss. |
| **Current State** | `current_delay` | **EXCLUDE from training** | When current state is unknown, the observation point cannot predict. |
| **Lag-1 State** | `prev_station_delay` | **KEEP NULL / Impute 0** | Valid state at Origin (no predecessor). Tree models branch natively. |
| **Lag-2/3 State** | `prev_delay_2`, `prev_delay_3` | **KEEP NULL / Impute 0** | Valid state at Stops 1 & 2. Handled via default split paths in trees. |
| **Scheduled Halt** | `scheduled_dwell_time` | **0.00% Missing** | Origin/Terminus halts default to 0 min. Intermediate stops complete. |
| **Section Speed** | `sched_planned_speed` | **EXCLUDE Terminus** | Terminus stations have no downstream section. |
| **Categoricals** | `type_code`, `station_zone` | **0.00% Missing** | 100% matched against deduplicated master tables. |

---

## 7. Usable Sample Count Verification & Splitting Feasibility

### 7.1 Re-verification of Usable Supervised Samples
- **Previous Approximate Count**: 33,960,584 rows.
- **Exact Strict Consecutive Count**: **33,925,776 rows**.
- **Explanation of 34,808 Row Discrepancy**: Exactly 34,808 rows (0.10%) involved intermediate timetable stops skipped in the delay logs. Excluding them ensures **100% consecutive next-station fidelity**.

### 7.2 Exact Chronological Train / Validation / Test Breakdown

The dataset spans exactly 365 days (2025-02-08 to 2026-02-07). All splits are based on the **Journey Origin Date (`date`)**:

| Split Name | Calendar Date Range | Month Partitions Included | Exact Supervised Sample Count | Percentage of Total |
|---|---|---|---|---|
| **TRAIN** | `2025-02-08` to `2025-10-31` | `2025-02` through `2025-10` (9 months) | **24,667,571** | **72.71%** |
| **VALIDATION** | `2025-11-01` to `2025-12-31` | `2025-11` and `2025-12` (2 months) | **5,734,148** | **16.90%** |
| **TEST** | `2026-01-01` to `2026-02-07` | `2026-01` and `2026-02` (1.25 months) | **3,524,057** | **10.39%** |
| **TOTAL** | `2025-02-08` to `2026-02-07` | **All 13 Monthly Partitions** | **33,925,776** | **100.00%** |

*Verification*: $24,667,571 + 5,734,148 + 3,524,057 = 33,925,776$ (**Exact Mathematical Match**).

---

## 8. Duplicate & Repeated Station Audit

Across all 38,428,703 records and 1,895,758 journey instances in the 13 monthly Parquet files:
- **Duplicate `(date, train_no, station_name)` records**: **0** (Clean).
- **Repeated station code visits within any single journey**: **0** (Clean).
- Every station visited along any train's route carries a strictly unique station code.

---

## 9. Categorical Cardinality & Encoding Strategy

| Categorical Feature | Unique Cardinality | Distinct Values / Examples | Recommended Encoding Strategy for XGBoost |
|---|---|---|---|
| `type_code` | **8** | `PASS`, `EXP`, `SF`, `PRM`, `T18`, `SHT`, `GRB`, `RAJ` | **One-Hot Encoding** (or native integer mapping 0..7) |
| `station_zone` | **18** | `NR`, `CR`, `WR`, `ECR`, `NER`, `SR`, `SCR`, `SWR`, etc. | **One-Hot Encoding** (18 binary columns) |
| `next_station_zone` | **18** | `NR`, `CR`, `WR`, `ECR`, `NER`, `SR`, `SCR`, `SWR`, etc. | **One-Hot Encoding** (18 binary columns) |
| `station_name` | **8,227** | High cardinality station codes (`NDLS`, `CSMT`, `CNB`) | **Do NOT One-Hot Encode**. Use Out-of-Fold Target Encoding or Frequency Encoding. |
| `next_station_name` | **8,164** | High cardinality next station codes | **Target Encoding** or section-level congestion prior |

---

## 10. Target Distribution Across Chronological Splits

Distribution statistics for `target_next_delay` across the three temporal partitions:

| Metric | TRAIN Set (Feb–Oct 2025) | VALIDATION Set (Nov–Dec 2025) | TEST Set (Jan–Feb 2026) |
|---|---|---|---|
| **Count** | 24,667,571 | 5,734,148 | 3,524,057 |
| **Mean** | **35.07 min** | **42.83 min** (+7.76 min shift) | **41.57 min** (+6.50 min shift) |
| **Std Dev** | **65.05 min** | **74.17 min** | **68.81 min** |
| **Min** | -120 min | -119 min | -120 min |
| **Max** | 1,440 min | 1,440 min | 1,440 min |
| **P50 (Median)** | **16.0 min** | **20.0 min** | **21.0 min** |
| **P75** | **40.0 min** | **49.0 min** | **48.0 min** |
| **P90** | **86.0 min** | **105.0 min** | **101.0 min** |
| **P95** | **133.0 min** | **163.0 min** | **155.0 min** |
| **P99** | **299.0 min** | **354.0 min** | **327.0 min** |

### Key Insight
Average delays surge by **22%** from summer/monsoon (Train: 35.07 min) into winter fog season (Val: 42.83 min, Test: 41.57 min). This confirms that a model trained on earlier months faces genuine out-of-time distribution shifts, providing a realistic test of generalization.

---

## 11. Baseline Experimentation & Benchmark Results

### 11.1 Experimental Protocol
- **Training Procedure**: A stratified, reproducible sample of **$N = 500,000$** rows was drawn across all 9 training partitions (`2025-02` through `2025-10`, `seed = 42`).
- **Validation Evaluation**: Evaluated on an independent random sample of **$N = 200,000$** rows from Nov–Dec 2025.
- **Test Evaluation**: Evaluated on an independent random sample of **$N = 200,000$** rows from Jan–Feb 2026.
- **Models Evaluated**:
  1. **Persistence Baseline**: $\hat{y} = \text{current\_delay}$ (the standard naive benchmark).
  2. **Historical Global Mean**: $\hat{y} = \bar{y}_{\text{train}} = 35.07$ min (leakage-safe, strictly from train set).
  3. **Historical Train-Specific Mean**: $\hat{y} = \bar{y}_{\text{train\_no}}$ (train number historical average from train set).
  4. **Simple Linear Model (Ridge Regression)**: Standardized features fit with $\alpha = 1.0$ on 10 numerical features.

### 11.2 Measured Benchmark Results

#### VALIDATION SET RESULTS (Nov–Dec 2025, $N = 200,000$)
| Model Architecture | MAE (min) | RMSE (min) | MedAE (min) | $\pm 5$ min Accuracy | $\pm 10$ min Accuracy | $\pm 15$ min Accuracy |
|---|--:|--:|--:|--:|--:|--:|
| **Historical Global Mean** | 38.79 | 74.24 | 26.0 | 8.89% | 17.30% | 26.45% |
| **Historical Train-Specific Mean** | 31.17 | 64.04 | 15.3 | 19.74% | 36.43% | 49.33% |
| **Persistence ($\hat{y} = \text{current\_delay}$)** | 8.44 | 19.30 | **3.0** | **63.65%** | 77.15% | 84.08% |
| **Simple Linear (Ridge Regression)** | **7.97** | **17.88** | 3.7 | 60.94% | **78.74%** | **86.15%** |

#### TEST SET RESULTS (Jan–Feb 2026, $N = 200,000$)
| Model Architecture | MAE (min) | RMSE (min) | MedAE (min) | $\pm 5$ min Accuracy | $\pm 10$ min Accuracy | $\pm 15$ min Accuracy |
|---|--:|--:|--:|--:|--:|--:|
| **Historical Global Mean** | 36.32 | 67.44 | 25.0 | 9.42% | 18.40% | 28.02% |
| **Historical Train-Specific Mean** | 30.60 | 59.82 | 15.9 | 18.92% | 35.21% | 48.02% |
| **Persistence ($\hat{y} = \text{current\_delay}$)** | 8.43 | 19.59 | **3.0** | **63.16%** | 76.75% | 83.79% |
| **Simple Linear (Ridge Regression)** | **7.83** | **18.11** | 3.7 | 61.16% | **78.75%** | **86.30%** |

### 11.3 Linear Model Physical Interpretation
The fitted Ridge coefficients reveal strong physical consistency:
- `current_delay` ($+32.15$) and `prev_delay` ($+31.43$): Anchor the baseline momentum.
- `sched_section_distance` ($+11.71$): Longer track sections correlate with greater delay accumulation.
- `sched_section_travel_time` ($-12.78$): Longer scheduled run times provide schedule buffer slack, enabling trains to recover lost time.

---

## 12. Problems Discovered & Corrections Applied

| Problem ID | Anomaly Discovered During Audit | Impact | Corrective Action Applied | Verification Result |
|---|---|---|---|---|
| **PR-01** | Unobserved intermediate timetable halts caused unconstrained `shift(-1)` to jump to station $s_{i+2}$ in 34,808 rows (0.10%). | Target label was misaligned with section distance features. | Updated `src/features/builder.py` with strict consecutive check (`sched_station_no + 1`). | **100.00% consecutive target alignment verified**. |
| **PR-02** | `next_station_zone` was shifted from observational sequence rather than timetable topology. | Could reflect station $s_{i+2}$'s zone if $s_{i+1}$ was unobserved. | Joined `sched_next_zone` directly to master schedule in `src/data/loader.py`. | **100.00% topology alignment verified**. |
| **PR-03** | `prev_station_delay` did not check if the preceding row was strictly $s_i - 1$. | Skipped stops could cause lag-1 to represent stop $s_i - 2$. | Added explicit consecutive check for lag-1 (`sched_station_no - 1`). | **Clean lag tracking verified**. |

---

## 13. Audit Conclusion & Next Steps

```
========================================================================================
FINAL AUDIT DECISION: PASS - SYSTEM READY FOR GRADIENT BOOSTED TREE TRAINING
========================================================================================
Next-station target correct : YES (100.00% Consecutive Guarantee)
Leakage detected            : NO  (Zero Future Information in Features)
Journey ordering correct    : YES (Deterministic Chronological Routing)
Usable samples verified     : YES (33,925,776 Exact Usable Samples)
Chronological split ready   : YES (Train: 24.67M | Val: 5.73M | Test: 3.52M)

Persistence Baseline MAE    : 8.43 min (Test Set)
Historical Baseline MAE     : 30.60 min (Test Set, Train-Specific)
Linear Baseline MAE         : 7.83 min (Test Set, Ridge Regression)
========================================================================================
```

### Recommendation for Next Phase
1. **Model Architecture**: Train an **XGBoost Regressor** on the chronological training set (`2025-02` to `2025-10`).
2. **Objective Target**: Predict `target_next_delay` (or `target_delay_delta`) using the full 30-feature vector.
3. **Validation & Tuning**: Perform hyperparameter tuning (learning rate, tree depth, subsample ratio) with early stopping on the `2025-11` to `2025-12` validation set.
4. **Final Benchmarking**: Evaluate the optimized model against the 7.83 min Ridge baseline on the `2026-01` to `2026-02` winter test set.
