# Multi-Horizon Target Audit Report
**SIH Problem Statement 26028: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**
*Generated: 2026-09-29 22:05:02*
*Audit Scope: Multi-Horizon Target Construction, Topological Ordering & Temporal Leakage Validation*

---

## 1. Target Construction Methodology

To evaluate multi-horizon delay forecasting, each train journey identified by the compound primary key `(date, train_no)` is sorted deterministically along the commercial scheduled route sequence `sched_station_no`.

For any current observation station s_i with sequence index i:
1. **Horizon 1 (`target_delay_h1`)**: Delay at the immediately adjacent scheduled commercial station s_(i+1).
   `target_delay_h1 = delay(s_{i+1})  <==>  sched_station_no(s_{i+1}) == sched_station_no(s_i) + 1`
2. **Horizon 2 (`target_delay_h2`)**: Delay at the commercial station two scheduled stops ahead s_(i+2).
   `target_delay_h2 = delay(s_{i+2})  <==>  sched_station_no(s_{i+2}) == sched_station_no(s_i) + 2`
3. **Horizon 3 (`target_delay_h3`)**: Delay at the commercial station three scheduled stops ahead s_(i+3).
   `target_delay_h3 = delay(s_{i+3})  <==>  sched_station_no(s_{i+3}) == sched_station_no(s_i) + 3`

### Strict Consecutive Topological Enforcement
Raw observational row shifts are strictly prohibited. Unscheduled operational halts (e.g. cabin sidings, goods loops) have `sched_station_no = null` and are isolated from the commercial sequence. If an intermediate commercial station is unobserved in the operational delay logs, the horizon target evaluates strictly to `null`, ensuring **100% guarantee against step-skipping leakage**.

---

## 2. Examples of Valid Horizon 1, 2, and 3 Mappings

Demonstration from empirical journey **Train `01023` on `2025-02-08`** across successive reporting stations:

| Current Seq | Current Station | Current Delay | Horizon 1 Target (s_(i+1)) | Horizon 2 Target (s_(i+2)) | Horizon 3 Target (s_(i+3)) |
|---|---|--:|---|---|---|
| 1 | `PUNE` | 2 min | `SSV` (seq 2, 6m) | `JJR` (seq 3, 21m) | `NIRA` (seq 4, 25m) |
| 2 | `SSV` | 6 min | `JJR` (seq 3, 21m) | `NIRA` (seq 4, 25m) | `LNN` (seq 5, 28m) |
| 3 | `JJR` | 21 min | `NIRA` (seq 4, 25m) | `LNN` (seq 5, 28m) | `WTR` (seq 6, 29m) |
| 4 | `NIRA` | 25 min | `LNN` (seq 5, 28m) | `WTR` (seq 6, 29m) | `STR` (seq 7, 26m) |
| 5 | `LNN` | 28 min | `WTR` (seq 6, 29m) | `STR` (seq 7, 26m) | `KRG` (seq 8, 40m) |
| 6 | `WTR` | 29 min | `STR` (seq 7, 26m) | `KRG` (seq 8, 40m) | `RMP` (seq 9, 44m) |

*All downstream targets are strictly prospective, topologically aligned, and belong to the identical journey instance.*

---

## 3. Number of Available Samples Across Chronological Splits

Evaluated across the entire historical corpus of **38,428,703 records** ($37,133,436$ commercial scheduled stations):

| Split Name | Calendar Period | Commercial Records | Horizon 1 Supervised Samples | Horizon 2 Supervised Samples | Horizon 3 Supervised Samples |
|---|---|--:|--:|--:|--:|
| **TRAIN** | `2025-02-08` to `2025-10-31` | 26,981,089 | **24,922,979** (92.37%) | **23,576,407** (87.38%) | **22,241,777** (82.43%) |
| **VALIDATION** | `2025-11-01` to `2025-12-31` | 6,258,457 | **5,751,280** (91.89%) | **5,440,563** (86.93%) | **5,133,371** (82.02%) |
| **TEST** | `2026-01-01` to `2026-02-07` | 3,893,890 | **3,531,692** (90.69%) | **3,341,407** (85.81%) | **3,153,170** (80.97%) |
| **TOTAL** | **Entire 365-Day Corpus** | **37,133,436** | **34,205,951** (92.12%) | **32,358,377** (87.14%) | **30,528,318** (82.21%) |

---

## 4. Missing-Target Percentage & Physical Rationale

| Horizon | Total Missing Targets | Missing Target Share | Dominant Physical & Operational Reasons |
|---|--:|--:|---|
| **Horizon 1** | 2,927,485 | **7.88%** | **Terminus stations (N)** have no subsequent station (~5.1%); unlogged delays at s_(i+1) (~2.8%). |
| **Horizon 2** | 4,775,059 | **12.86%** | **Stops N-1 and N** have no station two stops ahead (~10.2%); unlogged delays at s_(i+2) (~2.7%). |
| **Horizon 3** | 6,605,118 | **17.79%** | **Stops N-2, N-1, and N** have no station three stops ahead (~15.3%); unlogged delays at s_(i+3) (~2.5%). |

The missing target rates expand naturally and deterministically due to the boundary geometry of train journeys.

---

## 5. Sequence & Order Validation Results

| Horizon Audit Criterion | Expected Invariant | Measured Violations | Status |
|---|---|--:|---|
| **H1 Sequence Distance** | `sched_station_no(H1) - sched_station_no(current) == 1` | **0** | **PASS** |
| **H2 Sequence Distance** | `sched_station_no(H2) - sched_station_no(current) == 2` | **0** | **PASS** |
| **H3 Sequence Distance** | `sched_station_no(H3) - sched_station_no(current) == 3` | **0** | **PASS** |
| **H1 Journey Boundary** | `date(H1) == date(current)` & `train_no(H1) == train_no(current)` | **0** | **PASS** |
| **H2 Journey Boundary** | `date(H2) == date(current)` & `train_no(H2) == train_no(current)` | **0** | **PASS** |
| **H3 Journey Boundary** | `date(H3) == date(current)` & `train_no(H3) == train_no(current)` | **0** | **PASS** |

---

## 6. Leakage Audit for Multi-Horizon Targets

1. **Feature-to-Target Isolation**: Target columns (`target_delay_h1`, `target_delay_h2`, `target_delay_h3`) are strictly downstream labels and are excluded from the model input feature matrix.
2. **Current-Station State Exclusivity**: Features (`current_delay`, `prev_station_delay`, `prev_delay_2`, `prev_delay_3`, `stations_remaining`, `journey_progress`) represent only information available at the current reporting station s_i.
3. **No Intermediate Target Leakage**: Model H2 uses only information known at station s_i; it does NOT receive the actual observed delay at station s_(i+1). Similarly, Model H3 does NOT receive observed delays at s_(i+1) or s_(i+2).
4. **Temporal Partition Integrity**: Models H1, H2, and H3 are trained exclusively on Train partitions (`2025-02` to `2025-10`), using Validation (`2025-11` to `2025-12`) for early stopping and Test (`2026-01` to `2026-02`) for final benchmarking.

---

## 7. Edge Cases Near Journey Termination

Inspection of terminal stations confirms clean handling with zero index overflow:

| Stop Position | Description | Expected H1 Target | Expected H2 Target | Expected H3 Target | Measured Leakage |
|---|---|---|---|---|--:|
| **$N-2$ (Antepenultimate)** | 2 stops before terminus | Valid (Stop $N-1$) | Valid (Terminus $N$) | **Null** (No stop $N+1$) | **0 leaks** |
| **$N-1$ (Penultimate)** | 1 stop before terminus | Valid (Terminus $N$) | **Null** (No stop $N+1$) | **Null** (No stop $N+2$) | **0 leaks** |
| **$N$ (Terminus)** | End of journey | **Null** (Journey finished) | **Null** (Journey finished) | **Null** (Journey finished) | **0 leaks** |

### Empirical Journey Termination Example (Train `01023`):
| Station Position | Station Code | Current Delay | Horizon 1 Target | Horizon 2 Target | Horizon 3 Target |
|---|---|--:|---|---|---|
| 20 (of 22) | `RKD` | 37 min | `VV` (37m) | `KOP` (-27m) | *None (End of line)* |
| 21 (of 22) | `VV` | 37 min | `KOP` (-27m) | *None (End of line)* | *None (End of line)* |
| 22 (of 22) | `KOP` | -27 min | *None (Terminus reached)* | *None (End of line)* | *None (End of line)* |

---

## 8. Audit Decision Summary

```
========================================================================================
FINAL AUDIT DECISION: PASS FOR ALL HORIZONS (H1, H2, H3)
========================================================================================
Horizon 1 (Next Scheduled Stop)      : PASS (34,205,951 usable samples, 0 sequence errors)
Horizon 2 (2 Scheduled Stops Ahead)  : PASS (32,358,377 usable samples, 0 sequence errors)
Horizon 3 (3 Scheduled Stops Ahead)  : PASS (30,528,318 usable samples, 0 sequence errors)
Temporal Leakage Detected            : NONE
Cross-Journey Contamination          : NONE
Terminal Boundary Leakage            : NONE
System Ready for Multi-Horizon ML    : YES
========================================================================================
```
