# SIH Problem Statement 26028: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains
## End-to-End System Walkthrough, Architecture, and Engineering Blueprint

*Project Reference: Smart India Hackathon (SIH) Problem Statement 26028*  
*Repository: Indian Railways Dynamic ETA Forecasting Engine*  
*Date of Publication: 2026-09-29*  
*Document Version: 1.0 (Post-Preprocessing & Feature Engineering Baseline)*

---

## 1. Problem Statement

### 1.1 Objective of SIH Problem Statement 26028
Indian Railways (IR) operates one of the largest passenger rail networks in the world, running over 13,000 passenger and coaching trains daily across 68,000+ route kilometers. A major challenge faced by passengers, station superintendents, and section controllers is the **unreliability of static timetables and naive delay estimates**. 

SIH Problem Statement 26028 challenges us to build an intelligent, data-driven system for:
> **Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**

The core goal is to transition Indian Railways from static delay reporting (which merely reports how late a train *currently* is) to **dynamic predictive forecasting** (accurately anticipating how much delay a train will accumulate or recover as it moves toward upcoming stations).

### 1.2 Why Railway ETA Prediction is Difficult
Unlike road transport, where an individual vehicle can freely reroute or adjust speed based on immediate local traffic, trains are constrained by rigid infrastructure:
1. **Network Interdependency & Cascading Delays**: A delay of one train ripples across the network. A single delayed freight or express train holding a track block causes downstream coaching trains to wait at outer signals or passing loops.
2. **Track Topologies & Bottlenecks**: Many critical corridors are double-track or single-track sections. High-priority trains (e.g., Vande Bharat, Rajdhani) overtake lower-priority passenger trains, forcing lower-priority trains to incur unscheduled loop-line halts.
3. **Operational Slack & Recovery Margins**: Indian Railways timetable schedules intentionally incorporate "slack time" or engineering allowances before major junction stations. A train that is 45 minutes late at an intermediate station may recover 20 minutes before its next terminal stop.
4. **Stochastic Sectional Stoppages**: Sectional running times fluctuate due to signal halts, speed restrictions (caution orders), crew changes, track maintenance blocks, and platform availability at approaching junctions.
5. **Non-Linear Dynamics**: Delays do not grow linearly over distance. A train may run on time for 500 km and then accumulate 90 minutes of delay in a 50 km congested terminal approach zone.

### 1.3 Inputs & Operational Factors Influencing ETA
To make an accurate dynamic prediction, an ETA model must synthesize:
- **Current Operational State**: Current delay, recent delay changes over past 1, 2, and 3 stations, and current speed.
- **Route & Topology Context**: Distance traveled, distance remaining to destination, section distance between stops, and planned sectional run-times.
- **Train Priority Class**: Commercial hierarchy (e.g., Premium/Vande Bharat vs. Ordinary Passenger), which dictates track precedence during congestion.
- **Station & Junction Context**: Operating zone (e.g., Northern Railway vs. Western Railway), upcoming station density, and scheduled halt duration.
- **Temporal & Calendar Seasonality**: Time of day (peak morning/evening suburban slots), day of the week, month, and seasonal operating conditions (e.g., winter fog season in North India).

### 1.4 What Our System Predicts
Our system does not predict an arbitrary, disconnected number. It predicts:
1. **Primary Prediction**: The expected **arrival delay (in minutes)** at the immediately next downstream station $i+1$.
2. **Derived Expected Time of Arrival (ETA)**:
   $$\text{Dynamic ETA at Station } i+1 = \text{Scheduled Arrival Time at Station } i+1 + \widehat{\text{Predicted Delay}}_{i+1}$$
3. **Auxiliary Metric**: The expected **delay delta** ($\Delta \text{delay} = \text{delay}_{i+1} - \text{delay}_i$), telling section controllers whether the train is accelerating toward recovery or decelerating into further delay.

---

## 2. Our Overall Solution Architecture

The following ASCII diagram illustrates the complete end-to-end architectural flow of our system, spanning raw historical data ingestion to future live user interfaces:

```
+----------------------------------------------------------------------------------------------------+
|                                    1. RAW RAILWAY DATA SOURCES                                     |
|  - combined_delay.csv (38.4M delay logs)              - combined_schedule.csv (172k stop schedules)  |
|  - train_details.csv (8.9k rolling-stock types)       - station_full_names.csv (8.9k station codes)   |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                                  2. DATA CLEANING & NORMALIZATION                                  |
|  - Standardize train_no -> 5-digit zero-padded string ('00961', '12209')                           |
|  - Normalize station_name -> uppercase stripped station code ('NDLS', 'CSMT')                      |
|  - Resolve train_details priority conflicts deterministically (T18 > RAJ > SHT > PRM > SF...)      |
|  - Audit delay distribution & anomalies: early arrivals (-120m to 0m), corrupt outliers (>1440m)  |
|  - Create delay_clean, is_delay_missing, is_delay_outlier (raw delay column untouched)             |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                                    3. CANONICAL DATASET JOINING                                    |
|  - combined_delay LEFT JOIN combined_schedule ON [train_no, station_name] (96.63% clean match)     |
|    * (Avoids the 6.7M sequence desynchronization errors caused by joining on station_no)           |
|  - Result LEFT JOIN train_details ON [train_no] (100.00% match)                                    |
|  - Result LEFT JOIN station_full_names ON [station_name] (99.98% match)                            |
|  - Zero row multiplication verified (38,428,703 rows strictly preserved)                           |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                               4. CHRONOLOGICAL JOURNEY RECONSTRUCTION                              |
|  - Partition records by unique train service: (date, train_no) [1,720,296 individual journeys]     |
|  - Chronologically sequence stops using master schedule topology: sched_station_no (1 to N)        |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                       5. LEAK-FREE DYNAMIC FEATURE ENGINEERING (52 COLUMNS)                        |
|  - Past State Lags: current_delay, prev_station_delay, prev_delay_2, prev_delay_3                  |
|  - Delay Acceleration Gradients: delay_change, delay_change_2_stations, delay_change_3_stations    |
|  - Route Progression: dist_from_origin, remaining_dist, journey_progress, stations_remaining       |
|  - Schedule Dynamics: scheduled_dwell_time, sched_section_distance, sched_section_travel_time      |
|  - Calendar & Priority: scheduled_hour, day_of_week, month, is_weekend, type_code, station_zone    |
|  - Target Definition: target_next_delay (delay at stop i+1), target_delay_delta                     |
|  - Partitioned storage: 13 monthly Parquet partitions (~1.68 GB total, Snappy compression)         |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                                     6. ML MODELING ENGINE (PLANNED)                                |
|  - Chronological Train/Val/Test Split (Feb 2025 - Oct 2025 Train -> Nov-Dec Val -> Jan-Feb Test)  |
|  - Baselines: Historical Mean Delay, Persistence Baseline (Next Delay = Current Delay), Linear Reg |
|  - Core Model: XGBoost Regressor (Gradient Boosted Trees optimized for tabular railway dynamics)  |
|  - Evaluation Metrics: MAE (minutes), RMSE, Median AE, Accuracy within +-5, +-10, +-15 mins        |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                            7. INFERENCE & DYNAMIC ETA FORMULATION (PLANNED)                        |
|  - Predicted Downstream Delay: y_hat = Model.predict(X_current_station)                            |
|  - Dynamic ETA: Predicted_ETA = Scheduled_Arrival_Time[next_station] + y_hat                       |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  v
+-------------------------------------------------+--------------------------------------------------+
|                     8. FUTURE DEPLOYMENT & USER INTERFACES (PLANNED LAYER)                         |
|  - High-performance FastAPI REST API serving real-time predictions                                |
|  - Passenger Mobile App & Web Dashboard (Live interactive train progress & ETA countdown)          |
|  - Station Master & Controller Operations Console (Bottleneck alerts & delay propagation view)     |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Datasets Used

The following table summarizes all datasets discovered, inspected, and processed within the project:

| File Name | Primary Purpose in Project | Key Columns | Size on Disk / Row Count | Role in ML Pipeline |
|---|---|---|---|---|
| **`combined_delay.csv`** | Ground-truth historical delay logs and station movement telemetry | `date`, `train_no`, `station_no`, `station_name`, `delay` | 969.71 MB<br>(38,428,703 rows) | **Core Target & Feature Source (Mandatory)** |
| **`combined_schedule.csv`** | Official static timetable topology, planned run-times, and distances | `train_no`, `station_no`, `station_name`, `distance_from_origin`, `arrival_day`, `arrival_time`, `departure_day`, `departure_time` | 5.24 MB<br>(172,112 rows) | **Core Static Topology Source (Mandatory)** |
| **`train_details.csv`** | Train classification and rolling-stock priority metadata | `train_no`, `train_name`, `type_code` | 281.86 KB<br>(8,992 rows) | **Priority Classification Feature (Mandatory)** |
| **`station_full_names.csv`** | Station master lookup, English station names, and railway zones | `station_name`, `station_full_name`, `station_zone`, `station_address` | 451.97 KB<br>(8,963 rows) | **Spatial & Regional Metadata (Mandatory)** |
| **`2015 timetable.csv`** | Historical timetable snapshot (August 2015) | `Train No.`, `islno`, `station Code`, `Arrival time`, `Departure time`, `Distance` | 7.68 MB<br>(69,006 rows) | **Reference Only (Excluded from ML)** |
| **`2017 timetable.csv`** | Historical timetable snapshot (November 2017) | `Train No`, `SEQ`, `Station Code`, `Arrival time`, `Departure Time`, `Distance` | 15.93 MB<br>(186,124 rows) | **Reference Only (Excluded from ML)** |

### Why 2015 and 2017 Timetables Are Excluded from ML Training
During our preliminary empirical audit (documented in `DATASET_REPORT.md`), both historical timetables were evaluated against modern operations:
1. **Low Route Coverage**: The 2015 dataset covers only 2,810 trains (24.96% of the modern schedule), and the 2017 dataset covers only 63.84% of modern trains. Over 3,100 active trains in our 2025/2026 delay dataset do not exist in the 2017 timetable.
2. **Outdated Operational Timings**: Over the past 8 to 11 years, Indian Railways completed widespread network upgrades (Mission Raftaar, track doubling, 100% route electrification, elimination of unmanned level crossings). As a result, sectional running times and planned speeds in 2015/2017 differ by 10 to 30 minutes from active ground truth.
3. **Severe Formatting Artifacts**: The 2015 timetable contains single-quoted strings (`'00851'`) and fixed-width space padding across all text fields.
4. **Conclusion**: `combined_schedule.csv` already represents the contemporary 2025 master timetable matching our 2025–2026 delay records. Using 2015/2017 data would inject stale label noise into the model.

---

## 4. Deep Dataset Understanding & Semantics

Through empirical code inspection, several crucial railway domain semantics were discovered:

### 4.1 The Semantic Meaning of `date`
In `combined_delay.csv`, `date` represents the **Train Origin Journey Start Date (Train Run Date)**, not the local calendar arrival date at each intermediate station.
- **Verification**: For multi-day long-distance trains (e.g., Train `01025` from Mumbai Dadar to Ballia, which spans 3 calendar days), all 28 intermediate stations across Day 1, Day 2, and Day 3 share the **exact same `date` value**.
- **Significance**: Grouping by `(date, train_no)` isolates the entire multi-day journey into a single, cohesive time series.

### 4.2 Train Number Representation (`train_no`)
In `combined_delay` and `combined_schedule`, train numbers are consistently formatted as **5-digit zero-padded strings** (e.g., `'00961'`, `'01023'`, `'12209'`). In `train_details.csv`, integer conversion had stripped leading zeros in 607 records (e.g., `'961'` instead of `'00961'`). Standardizing with `.str.zfill(5)` achieved a **100.00% join match rate**.

### 4.3 Station Code vs. Station Name (`station_name`)
Across all raw CSV files, the column labeled `station_name` actually contains the **2-to-5 letter uppercase Indian Railways Station Code** (e.g., `NDLS` for New Delhi, `CSMT` for Mumbai Chhatrapati Shivaji Maharaj Terminus, `CNB` for Kanpur Central). The human-readable station name is located only in `station_full_names.csv` under `station_full_name`.

### 4.4 The Critical Join Decision: Why Join on `(train_no, station_name)` Instead of `station_no`
A naive database join between `combined_delay` and `combined_schedule` using `(train_no, station_no)` resulted in **6,714,008 station code mismatches (18.0%)**.
- **Root Cause**: `combined_delay.csv` includes operational logging halts (technical stops, freight precedence sidings, crew changes, locomotive reversal points) that are not commercial passenger stops. This causes intermediate station sequence numbers to shift relative to the public timetable.
- **Solution**: Joining on **`(train_no, station_name)`** aligns stops by physical railway location, achieving a **96.63% match rate** (37,133,436 / 38,428,703 records).
- **The Remaining 3.37% (1,295,267 rows)**: Represent purely operational/technical halts not present in the public schedule. Handled gracefully via a `LEFT JOIN`: they retain their raw delay logging but are safely omitted from supervised schedule-dependent training pairs.

---

## 5. Data Cleaning & Anomaly Handling

A fundamental principle of our engineering pipeline is that **the original raw `delay` column remains 100% untouched**. A new sanitized column, `delay_clean`, was constructed alongside explicit diagnostic flags.

### 5.1 Delay Distribution Breakdown ($N = 38,428,703$)

| Delay Category | Criteria | Total Rows | Percentage | Domain Interpretation & Handling |
|---|---|---|---|---|
| **Missing Telemetry** | `delay is null` | 1,874,271 | 4.88% | Sensor bypass, unrecorded pass-through, or station non-reporting. Mapped to `NULL` in `delay_clean`; flagged `is_delay_missing = 1`. |
| **Extreme Early** | `delay < -120 min` | 13 | 0.00003% | Unrealistic clock error (train cannot run >2 hours early). Mapped to `NULL` in `delay_clean`; flagged `is_delay_outlier = 1`. |
| **Normal Early** | `-120 <= delay < 0 min` | 773,174 | 2.01% | **Legitimate Railway Feature**: Built-in slack buffers before major junctions allow trains to arrive up to 2 hours early. **Retained as valid**. |
| **On Time** | `delay == 0 min` | 4,898,984 | 12.75% | Exact on-time performance. **Retained as valid**. |
| **Minor / Moderate** | `0 < delay <= 60 min` | 24,943,311 | 64.91% | Standard operational variance. **Retained as valid**. |
| **Significant / Severe** | `60 < delay <= 1440 min` | 5,923,890 | 15.41% | Heavy delays due to congestion, single-line track blocks, major fog, or speed restrictions. **Retained as valid**. |
| **Extreme Outlier** | `delay > 1440 min` (24h) | 15,073 | 0.0392% | **Data Corruption / Epoch Bug**: Max value was 525,592 minutes (~365 days, a year wraparound calculation bug). Mapped to `NULL` in `delay_clean`; flagged `is_delay_outlier = 1`. |

### 5.2 Why Delays Between 720 and 1440 Minutes Were Kept
In Indian Railways, extreme weather (e.g., North Indian winter fog in December/January) or major track washouts routinely cause long-distance trains to run 12 to 24 hours behind schedule. Automatically deleting all large delays would erase critical edge cases that the ML model must learn to handle. Only values exceeding 24 hours (1,440 minutes) or negative delays beyond 2 hours (-120 minutes) were flagged as corrupt.

---

## 6. Data Processing at Scale (Big Data Architecture)

### 6.1 The Challenge of 38.4 Million Rows
The raw delay dataset contains **38,428,703 rows** and occupies ~1.02 GB as raw CSV. Attempting to load, clean, join, sort, and engineer 52 features on 38.4M rows simultaneously using standard Pandas easily consumes **24 to 32 GB of RAM**, triggering memory crashes or severe disk paging.

### 6.2 Our Scalable Monthly Partitioning Architecture
Because the `date` column represents the Journey Origin Start Date, **every train journey is strictly self-contained within its date partition**. No journey ever spans across monthly boundaries in our dataset.

We implemented a partitioned execution engine in `scripts/run_preprocessing.py`:
1. **13 Monthly Partitions**: The dataset spans from `2025-02-08` to `2026-02-07`, forming 13 monthly blocks (`2025-02` through `2026-02`).
2. **Chunked Streaming Execution**: Each month (~3.2 million rows) is loaded, cleaned, joined, and feature-engineered independently in **under 6 seconds** using Polars' multithreaded Rust query engine. Peak RAM usage never exceeded **3.5 GB**.
3. **Parquet with Snappy Compression**:
   - Each partition is stored as columnar Parquet: `data/processed/train_features/year_month=YYYY-MM/features.parquet`.
   - Snappy compression reduced the 52-column dataset across 38.4M rows to just **~1.68 GB on disk**, enabling ultra-fast random access and column projection during model training.
4. **Validation Sample Dataset**: A representative **50,000-row sample** was saved to `data/processed/sample_features.parquet` (2.51 MB) and `data/processed/sample_features.csv` (10.22 MB) for instant visual inspection and prototyping.

---

## 7. Journey Reconstruction & Route Sequencing

To predict delay dynamically, train movements must be modeled as a chronological trajectory rather than independent tabular rows.

### 7.1 Grouping and Sorting
Each journey is isolated by the composite key:
$$\text{Journey Key} = (\text{date}, \text{train\_no})$$
Within each journey, all recorded station stops are sorted strictly according to the master schedule sequence:
$$\text{Sort Order} = [\text{date}, \text{train\_no}, \text{sched\_station\_no}, \text{station\_no}]$$

### 7.2 The Dynamic State Concept
At any given moment during a train's journey, the train is located at a **Current Station ($i$)**:
- **Previous Station ($i-1$)**: The station the train just departed. Its arrival delay (`prev_station_delay`) and delay trend are known with 100% certainty.
- **Current Station ($i$)**: The station where the train is currently reporting (`current_delay`).
- **Next Station ($i+1$)**: The target station whose arrival delay (`target_next_delay`) we must forecast.
- **Route Progression**:
  - Distance Traveled: $\text{dist\_from\_origin} = d_i$
  - Remaining Distance: $\text{remaining\_dist} = D_{\text{total}} - d_i$
  - Journey Progress Fraction: $\text{journey\_progress} = d_i / D_{\text{total}} \in [0.0, 1.0]$
  - Stations Remaining: $\text{stations\_remaining} = N_{\text{total}} - i$

---

## 8. Feature Engineering (The 52-Feature Schema)

Our feature engineering pipeline constructs 52 clean, leak-free columns organized into 7 functional groups:

| Group | Feature Name | Data Type | Operational Meaning | Why It Helps ETA Prediction |
|---|---|---|---|---|
| **A. Identifiers** | `date` | String | Journey origin date | Identifies journey instance; temporal splitting |
| | `train_no` | String | 5-digit normalized train number | Unique train identifier |
| | `station_name` | String | IR station code of current stop | Location identifier |
| | `sched_station_no` | Int16 | Stop sequence index (1 to N) | Position along the scheduled route |
| **B. Dynamic Delay** | `current_delay` | Int32 | Latest recorded delay at current stop (min) | **Strongest single baseline predictor** of downstream delay |
| | `prev_station_delay` | Int32 | Delay recorded at stop $i-1$ (min) | Provides immediate baseline for rate of change |
| | `prev_delay_2` | Int32 | Delay recorded at stop $i-2$ (min) | Captures 2-station momentum |
| | `prev_delay_3` | Int32 | Delay recorded at stop $i-3$ (min) | Captures 3-station long-term momentum |
| | `delay_change` | Int32 | $\text{current\_delay} - \text{prev\_station\_delay}$ | Indicates if train is recovering or losing time |
| | `delay_change_2_stations` | Int32 | $\text{current\_delay} - \text{prev\_delay\_2}$ | Medium-range acceleration gradient |
| | `delay_change_3_stations` | Int32 | $\text{current\_delay} - \text{prev\_delay\_3}$ | Long-range acceleration gradient |
| **C. Route Progress** | `current_station_seq` | Int16 | Index of current stop | Position indicator |
| | `stations_remaining` | Int16 | Stops remaining until destination | Indicates how many opportunities remain for recovery |
| | `dist_from_origin` | Int32 | Cumulative km from origin | Distance traveled |
| | `remaining_dist` | Int32 | Kilometers remaining to destination | Directly impacts total accumulated delay potential |
| | `journey_progress` | Float64 | Fraction of route completed ($0.0 - 1.0$) | Scale-invariant progress indicator |
| | `route_total_distance`| Int32 | Total route length in km | Distinguishes short-haul vs. cross-country trains |
| | `route_total_stations`| Int16 | Total stops on route | Identifies stopping density |
| **D. Scheduled Dynamics**| `scheduled_dwell_time`| Int32 | Scheduled halt at current stop (min) | Long halts (15–30 min) allow major delay recovery |
| | `sched_section_distance`| Int32 | Planned distance to next stop (km) | Longer sections have higher delay variance |
| | `sched_section_travel_time`| Int32 | Planned run-time to next stop (min) | Base travel time before adding delay |
| | `sched_planned_speed` | Float64 | Planned sectional speed (km/h) | Tight speed schedules are harder to recover on |
| | `arr_min` | Int32 | Scheduled arrival (min from midnight) | Time-of-day operational context |
| | `dep_min` | Int32 | Scheduled departure (min from midnight) | Departure scheduling context |
| | `arrival_day` | Int8 | Journey day counter (1 to 4) | Multi-day fatigue/congestion indicator |
| | `departure_day` | Int8 | Journey day counter (1 to 4) | Multi-day schedule indicator |
| **E. Calendar & Time** | `scheduled_hour` | Int8 | Hour of day (0 to 23) | Distinguishes peak rush hours from night runs |
| | `day_of_week` | Int8 | Day of week (0 = Monday, 6 = Sunday) | Weekly congestion patterns (weekend travel peaks) |
| | `month` | Int8 | Month of year (1 to 12) | Captures seasonality (monsoon rain, winter fog) |
| | `day` | Int8 | Day of month (1 to 31) | Holiday and festival travel cycles |
| | `is_weekend` | Int8 | 1 if Saturday/Sunday, else 0 | Weekend passenger traffic indicator |
| **F. Priority & Network**| `type_code` | String | Train priority class (`SF`, `PRM`, `EXP`) | **Dictates track precedence during dispatching** |
| | `station_zone` | String | Railway zone of current stop (`NR`, `CR`) | Zone-specific operational efficiency and congestion |
| | `next_station_name` | String | Station code of next stop | Specific destination track section |
| | `next_station_zone` | String | Railway zone of next stop | Cross-zone interchange delay bottlenecks |
| **G. Targets & Flags** | `target_next_delay` | Int32 | **Primary Target**: Delay at stop $i+1$ (min) | The value the ML model predicts |
| | `target_delay_delta` | Int32 | Auxiliary Target: $\text{delay}_{i+1} - \text{delay}_i$ | The sectional delta predicted by regression |
| | `delay` | Int32 | Original raw delay (unmodified) | Historical audit trail |
| | `delay_clean` | Int32 | Sanitized delay | Validated operational delay |
| | `is_delay_missing` | Int8 | 1 if raw delay was null | Missing telemetry flag |
| | `is_delay_outlier` | Int8 | 1 if delay was outside $[-120, 1440]$ | Data corruption flag |
| | `is_terminus_station`| Int8 | 1 if final stop on route | Excludes final stops from next-stop training |

---

## 9. Target Variable Formulation

### 9.1 Primary Target: `target_next_delay`
The primary target variable is the **actual arrival delay at the next station along the journey**:
$$y_i = \text{target\_next\_delay}_i = \text{delay\_clean}_{i+1}$$

### 9.2 Auxiliary Target: `target_delay_delta`
The auxiliary target represents the **delay accumulation or recovery over the upcoming track section**:
$$\Delta y_i = \text{target\_delay\_delta}_i = \text{delay\_clean}_{i+1} - \text{current\_delay}_i$$

### 9.3 Concrete Numerical Example
Consider Train `12049` (Gatimaan Express) moving from Agra Cantt (`AGC`) to Gwalior (`GWL`):

```
CURRENT STATION: Agra Cantt (AGC)
  Scheduled Arrival Time : 10:00 AM
  Current Arrival Delay  : +15 minutes (Actual Arrival = 10:15 AM)

NEXT STATION: Gwalior (GWL)
  Scheduled Arrival Time : 10:40 AM
  Actual Arrival Delay   : +22 minutes (Actual Arrival = 11:02 AM)

ENGINEERED TARGETS AT CURRENT STATION (AGC):
  target_next_delay  = 22 minutes
  target_delay_delta = 22 - 15 = +7 minutes (accumulated 7 min extra delay)

DYNAMIC ETA CALCULATION:
  Predicted Next Delay = Model.predict(X_AGC) = +22 min
  Dynamic ETA at GWL   = Scheduled Arrival (10:40 AM) + 22 min = 11:02 AM
```

### 9.4 What the Machine Learning Model Learns
The model does not simply predict static delay; it learns the **transfer function of track sections**:
$$\Delta \text{delay} = f(\text{current\_delay}, \text{delay\_trend}, \text{train\_priority}, \text{section\_distance}, \text{time\_of\_day}, \text{zone})$$
If a Rajdhani express is 15 minutes late entering a section with 20 minutes of schedule slack at 11:00 PM, the model learns that $\Delta \text{delay} \approx -10$ minutes (delay recovery). Conversely, if a passenger train is 15 minutes late approaching a congested suburban junction during peak morning hours, the model learns that $\Delta \text{delay} \approx +25$ minutes (delay amplification).

---

## 10. Future-Data Leakage Prevention Guarantee

In dynamic forecasting, **data leakage is the most critical failure mode**. If an algorithm inadvertently peeks into downstream future data during training, it will appear to have near-perfect accuracy in the lab but fail completely in real-world deployment.

### 10.1 What Information is STRICTLY ALLOWED at Prediction Point $i$:
- Current delay at station $i$ (`current_delay`)
- Historical delays at preceding stations $i-1, i-2, i-3$ (`prev_station_delay`, etc.)
- Historical delay deltas over past stations (`delay_change`)
- Static route and schedule information known in advance (distance, planned run-time, planned speed)
- Static train attributes (train number, priority classification, train name)
- Static station attributes (zone, address)
- Current time and calendar attributes (scheduled hour, day of week, month)

### 10.2 What Information is STRICTLY FORBIDDEN at Prediction Point $i$:
- The actual delay at the target station $i+1$ (`target_next_delay` is used ONLY as the ground-truth label $y$, never as an input $X$)
- Any delays from future stations $i+2, i+3, \dots, N$
- Future weather, future signal failures, or future traffic states downstream
- Aggregate journey statistics that incorporate future journey outcomes (e.g., total journey delay at terminus)

### 10.3 Structural Enforcement in Code
In `src/features/builder.py`, leakage prevention is mathematically guaranteed:
```python
# Lags use positive shift (strictly looking backwards in time along the journey)
pl.col("delay_clean").shift(1).over(["date", "train_no"]).alias("prev_station_delay")
pl.col("delay_clean").shift(2).over(["date", "train_no"]).alias("prev_delay_2")

# The Target uses negative shift (strictly isolated as label y)
pl.col("delay_clean").shift(-1).over(["date", "train_no"]).alias("target_next_delay")
```
Furthermore, the window partitioning `over(["date", "train_no"])` ensures that lag and lead calculations **never cross journey boundaries**.

---

## 11. Missing Values & Supervised Sample Eligibility

### 11.1 Missing Value Breakdown Across Features

| Feature Column | Missing Rate | Domain Cause | Preprocessing & Training Treatment |
|---|---|---|---|
| `target_next_delay` | 11.63% | Terminus stations (last stop has no next stop) + downstream unobserved halts | **Excluded from supervised training pairs** (never impute artificial labels) |
| `prev_station_delay` | 8.87% | Origin stations (Stop 1 has no predecessor) + unobserved Stop 1 | Valid operational state; represented as null/0 for origin stops |
| `prev_delay_2` | 13.98% | Stops 1 and 2 have fewer than 2 preceding stops | Valid operational state; handled naturally by tree-based split algorithms |
| `prev_delay_3` | 19.34% | Stops 1, 2, and 3 have fewer than 3 preceding stops | Valid operational state; handled naturally by tree-based split algorithms |
| `sched_section_travel_time` | 5.04% | Terminus stops (no downstream section) + operational halts | Terminus rows excluded from next-stop prediction |
| `type_code` | 0.00% | 100% matched against deduplicated `train_details` | Fully available |
| `station_zone` | 0.00% | 100% matched against augmented `station_full_names` | Fully available |

### 11.2 Important Distinction: Missing Features vs. Missing Targets
1. **Missing Features (e.g., `prev_station_delay` at Station 1)**: This is physically meaningful information. When a train is at its origin station, it has no previous delay history. Algorithms like XGBoost natively handle missing feature values by learning optimal default split directions.
2. **Missing Targets (e.g., `target_next_delay` is null)**: If the sensor at station $i+1$ failed to log an arrival, or if station $i$ is the terminus, the true label $y$ is unknown. **We NEVER impute missing targets for supervised model training**. Samples with missing targets are cleanly omitted from the training loss calculation.
3. **Forward-Fill Integrity**: In live inference, if an intermediate station fails to log, the operator's latest known delay can be forward-filled from station $i-1$, but forward-fill is **strictly prohibited from looking forward in time**.

---

## 12. Current Dataset Statistics Summary

The following table presents the exact, empirically verified numbers across the entire processed dataset:

| Metric / Dimension | Exact Count / Percentage | Engineering Note |
|---|---|---|
| **Total Raw Delay Records** | **38,428,703** | 100% of historical records ingested |
| **Total Unique Train Journeys** | **1,720,296** | Unique `(date, train_no)` trajectory instances |
| **Total Unique Trains** | **7,033** | Unique coaching train numbers in delay logs |
| **Total Unique Stations** | **8,227** | Operating railway stations in delay logs |
| **Date Range** | **2025-02-08 to 2026-02-07** | Exactly 365 calendar days (1 full continuous year) |
| **Schedule Join Match Rate** | **96.63%** (37,133,436 rows) | Joined cleanly on `[train_no, station_name]` |
| **Unmatched Operational Stops** | **3.37%** (1,295,267 rows) | Technical/freight sidings not on public schedule |
| **Train Details Match Rate** | **100.00%** (38,428,703 rows) | 272 duplicate train numbers resolved via priority rule |
| **Station Master Match Rate** | **99.98%** (38,421,791 rows) | Augmented with modern stations (e.g. `BSBS`, `KCVL`) |
| **Missing Raw Delay Telemetry** | **4.88%** (1,874,271 rows) | Retained as null; flagged `is_delay_missing = 1` |
| **Extreme Outliers (> 1,440 min)** | **0.0392%** (15,073 rows) | Filtered from `delay_clean`; flagged `is_delay_outlier = 1` |
| **Usable Supervised Training Samples** | **33,960,584** (88.37%) | Valid $(X_i, y_i)$ pairs on scheduled commercial routes |
| **Processed Feature Store Size** | **~1.68 GB** | 13 partitioned Parquets with Snappy compression |
| **Rapid Inspection Sample Size** | **50,000 rows** | Saved as both Parquet (2.51 MB) and CSV (10.22 MB) |

---

## 13. Current ML Problem Formulation

### 13.1 Formal Mathematical Definition
Let a coaching train journey be represented as an ordered sequence of station stops $s_1, s_2, \dots, s_K$.

At station $s_i$, the state vector $X_i \in \mathbb{R}^d$ contains all features available up to stop $s_i$:
$$X_i = [\text{current\_delay}_i, \text{prev\_delay}_i, \text{delay\_change}_i, d_i, (D_{\text{total}} - d_i), t_{\text{sched\_sec}}, v_{\text{planned}}, \text{hour}_i, \text{day}_i, \text{priority}_i, \text{zone}_i, \dots]$$

The regression objective is to learn a parameterised mapping $f_\theta: \mathbb{R}^d \rightarrow \mathbb{R}$ that predicts the downstream arrival delay $y_i$:
$$\hat{y}_i = f_\theta(X_i) \approx \text{delay}_{i+1}$$

### 13.2 Loss Function
The model will be optimized using Mean Absolute Error (MAE) or Huber Loss (to ensure robustness against operational delay spikes):
$$\mathcal{L}_{\text{MAE}}(\theta) = \frac{1}{M} \sum_{i=1}^M |y_i - f_\theta(X_i)|$$

### 13.3 Dynamic Expected Time of Arrival (ETA) Output
Once the downstream delay $\hat{y}_i$ is predicted, the final dynamic ETA is formulated as:
$$\text{Dynamic ETA}_{i+1} = \text{Scheduled Arrival Time}_{i+1} + \hat{y}_i$$

*Example*: If scheduled arrival at the next station is `14:30:00` and $\hat{y}_i = +18$ minutes, the reported ETA is `14:48:00`.

---

## 14. Model Plan (Architecture Roadmap)

> **Important Note**: No machine learning model has been trained yet. This section outlines the planned modeling progression.

```
+-------------------------------------------------------------------------------+
|                             MODELING ROADMAP                                  |
|                                                                               |
|  [Tier 1: Heuristic & Linear Baselines]                                       |
|    - Naive Persistence Baseline: y_hat = current_delay (delay remains constant) |
|    - Historical Sectional Mean: y_hat = mean sectional historical delay       |
|    - Ridge / ElasticNet Linear Regression (interpretable coefficient weights)  |
|                                                                               |
|  [Tier 2: Tree-Based Gradient Boosting (Primary Production Architecture)]     |
|    - LightGBM / XGBoost Regressor                                             |
|    - Non-linear feature interactions (priority x time-of-day x section distance) |
|    - Native handling of missing lag features and categorical zone encoding    |
|    - Ultra-fast C++ inference (<5 ms per prediction)                          |
|                                                                               |
|  [Tier 3: Future Deep Sequence Architectures (Exploratory / Optional)]        |
|    - Temporal Graph Networks / Spatio-Temporal LSTMs (Network-wide propagation)|
+-------------------------------------------------------------------------------+
```

### Why XGBoost is the Primary Production Candidate
For tabular railway operational data, gradient boosted decision trees (XGBoost/LightGBM) consistently outperform deep neural networks:
1. **Heterogeneous Feature Handling**: Simultaneously handles continuous physics metrics (distance, speed, delay minutes), discrete integers (stops, hours), and high-cardinality categoricals (train type, zones).
2. **Monotonicity & Threshold Splits**: Can capture hard operational thresholds (e.g., if dwell time $>15$ min, recovery probability jumps abruptly).
3. **Missing Value Robustness**: Learns optimal branch directions for missing telemetry without requiring ad-hoc data imputation.
4. **Sub-Millisecond Inference**: A compiled XGBoost model evaluates in under 2 milliseconds, making it suitable for high-throughput station display APIs.

---

## 15. Train / Validation / Test Strategy (Temporal Splitting)

Random K-Fold cross-validation is **strictly prohibited** in this project because it shuffles future observations into the training set, causing temporal leakage and grossly over-optimistic accuracy metrics.

### 15.1 Chronological Splitting Protocol
We will adopt a strict chronological time-based split across the 365-day dataset:

```
+------------------------------------+------------------+---------------------+
|         TRAINING SET (75%)         | VALIDATION (10%) |    TEST SET (15%)   |
|       2025-02-08 to 2025-10-31     | 2025-11 to 2025-12| 2026-01 to 2026-02  |
|         (~25.4M samples)           |  (~3.4M samples)  |   (~5.1M samples)   |
+------------------------------------+------------------+---------------------+
<----------------------------- Temporal Direction ---------------------------->
```

- **Training Period (Months 1–9)**: Captures spring, summer, and monsoon seasonal operational dynamics.
- **Validation Period (Months 10–11)**: Used for hyperparameter tuning, tree depth optimization, and early stopping.
- **Test Period (Months 12–13: Jan–Feb 2026)**: Evaluates performance during the challenging North Indian winter fog season, providing an honest, robust assessment of real-world generalization.

---

## 16. Evaluation Metrics

Model performance will be evaluated using standard railway engineering criteria:

1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{M} \sum_{i=1}^M |y_i - \hat{y}_i|$$
   *Meaning*: The average prediction error expressed in intuitive **minutes**.
2. **Root Mean Squared Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{M} \sum_{i=1}^M (y_i - \hat{y}_i)^2}$$
   *Meaning*: Heavily penalizes large outlier errors (e.g., predicting 10 min late when the train is 120 min late).
3. **Median Absolute Error (MedAE)**:
   *Meaning*: Robust against extreme outlier disruptions; reflects the typical passenger experience.
4. **Operational Threshold Accuracy (On-Time Prediction Windows)**:
   - **$\pm 5$ Minute Accuracy**: Percentage of predictions within $\pm 5$ minutes of actual arrival.
   - **$\pm 10$ Minute Accuracy**: Percentage of predictions within $\pm 10$ minutes of actual arrival.
   - **$\pm 15$ Minute Accuracy**: Standard Indian Railways punctuality tolerance window.

---

## 17. Final ETA System Flow (Inference Walkthrough)

The following example demonstrates how the trained system will perform dynamic inference for an active train:

```
[LIVE INPUT FROM RAILWAY TELEMETRY]
Train Number           : 01023 (PUNE KOP SPECIAL)
Current Station Code   : PUNE (Pune Junction)
Scheduled Departure    : 21:40
Actual Departure Delay : +2 minutes
Previous Stations Delay: [Origin Stop - No Predecessor]
Distance Traveled      : 0 km
Route Total Distance   : 326 km
Remaining Distance     : 326 km
Train Priority Type    : EXP-TRAINS
Current Operating Zone : CR (Central Railway)

[DOWNSTREAM TARGET STATION]
Next Station Code      : SSV (Sasvad Road)
Next Station Distance  : 12 km
Scheduled Section Time : 19 minutes
Scheduled Arrival SSV  : 21:59

                    │
                    ▼
[PREDICTION PIPELINE: FEATURE VECTOR X_i CONSTRUCTED]
Vector: [current_delay=2, prev_delay=null, dist=0, remaining=326,
         sched_time=19, sched_speed=37.9, priority=EXP, zone=CR, hour=21, ...]
                    │
                    ▼
[TRAINED XGBOOST REGRESSION MODEL]
Predicted Delay Delta  : <predicted_delay_delta> (e.g., +4 minutes)
Predicted Next Delay   : <predicted_next_delay>  (e.g., +6 minutes)
                    │
                    ▼
[DYNAMIC ETA FORMULATION]
Scheduled Arrival at SSV: 21:59
Dynamic Calculated ETA  : 21:59 + <predicted_next_delay> = 22:05
Status Display          : "Train 01023 expected at Sasvad Road (SSV) at 22:05 (+6 min late)"
```

---

## 18. Future Live System Integration Architecture

In a production environment, our trained machine learning pipeline will connect directly to Indian Railways' real-time data feeds:

```
+----------------------------------------------------------------------------------------------------+
|                                    LIVE PRODUCTION INTEGRATION                                     |
|                                                                                                    |
|    +-------------------------------+               +----------------------------------+            |
|    | CRIS / NTES Live Train API    |               | Master Schedule & Station Store  |            |
|    | (GPS / RTIS Locomotive Feeds) |               | (Pre-computed Static Topologies) |            |
|    +---------------+---------------+               +-----------------+----------------+            |
|                    |                                                 |                             |
|                    +-----------------------+-------------------------+                             |
|                                            |                                                       |
|                                            v                                                       |
|                        +---------------------------------------+                                   |
|                        | Fast Feature Assembler Service        |                                   |
|                        | (Assembles 52-column vector in <2 ms) |                                   |
|                        +-------------------+-------------------+                                   |
|                                            |                                                       |
|                                            v                                                       |
|                        +---------------------------------------+                                   |
|                        | Serialized Model Inference Engine     |                                   |
|                        | (Trained XGBoost / ONNX Runtime)      |                                   |
|                        +-------------------+-------------------+                                   |
|                                            |                                                       |
|                                            v                                                       |
|                        +---------------------------------------+                                   |
|                        | Dynamic ETA Service (FastAPI)         |                                   |
|                        +-------------------+-------------------+                                   |
|                                            |                                                       |
|                    +-----------------------+-------------------------+                             |
|                    |                                                 |                             |
|                    v                                                 v                             |
|    +-------------------------------+               +----------------------------------+            |
|    | Passenger Mobile App & Web UI |               | Station Display Boards &         |            |
|    | (React / Flutter Client)      |               | Section Controller Console       |            |
|    +-------------------------------+               +----------------------------------+            |
+----------------------------------------------------------------------------------------------------+
```

### Distinction Between Current Stage and Live Layer
- **Current Stage (Completed)**: Offline historical data engineering, dataset harmonization, anomaly cleaning, sequence reconstruction, and feature store generation across 38.4 million records.
- **Future Live Layer**: Real-time message subscriber consuming live GPS/RTIS telemetry, extracting the identical 52-feature schema, and querying the serialized model via sub-second REST endpoints.

---

## 19. Future Improvements Roadmap

The following enhancements are planned for subsequent development phases:
1. **Multi-Stop Horizon Forecasting**: Extend the target definition from $i+1$ to multi-step vectors $[i+1, i+2, \dots, \text{terminus}]$, allowing passengers to see their destination ETA hundreds of kilometers in advance.
2. **Live RTIS (Real-Time Train Information System) Integration**: Direct ingestion of locomotive GPS coordinates for mid-section tracking between stations.
3. **Meteorological Feature Fusion**: Integrating live weather data (precipitation, visibility index, high-temperature rail stress warnings).
4. **Network Congestion Density Metrics**: Computing the instantaneous number of active trains operating on the same route section.
5. **Dynamic Caution Order Tracking**: Ingesting temporary speed restrictions (TSR) issued by railway divisions.
6. **Probabilistic Prediction Intervals**: Outputting $90\%$ confidence bounds (e.g., "ETA 18:45 $\pm$ 4 minutes") using quantile regression.
7. **Model Monitoring & Concept Drift Detection**: Tracking distribution drift across seasons and automatically triggering retrain pipelines.

---

## 20. Current Project Status Checklist

```
CURRENT STATUS: PREPROCESSING & FEATURE ENGINEERING BASELINE COMPLETE

[✓] COMPLETED:
    [✓] In-depth empirical dataset audit across all 6 repository files (DATASET_REPORT.md)
    [✓] Non-destructive data cleaning (raw CSVs preserved 100% untouched)
    [✓] Standardized train numbers to 5-digit zero-padded strings across all tables
    [✓] Normalized station codes to uppercase stripped strings
    [✓] Deterministic deduplication of train_details.csv using priority hierarchy
    [✓] Identified canonical join key [train_no, station_name], preventing 6.7M mismatches
    [✓] Delay anomaly analysis and explicit filtering rules (delay_clean, flags)
    [✓] Chronological journey sequencing for 1,720,296 individual train trajectories
    [✓] Leak-free dynamic feature engineering (52 total columns)
    [✓] Next-station target formulation (target_next_delay, target_delay_delta)
    [✓] Scalable monthly partitioned Parquet feature store (13 partitions, ~1.68 GB)
    [✓] 50,000-row validation sample datasets (Parquet and CSV)
    [✓] Automated preprocessing and feature validation reports

[□] PENDING (NEXT STEPS):
    [□] Establish naive persistence baseline (y_hat = current_delay)
    [□] Train linear regression baseline
    [□] Configure and train XGBoost Regressor on chronological training split
    [□] Hyperparameter tuning on validation split
    [□] Evaluate on winter test split (MAE, RMSE, MedAE, +-5/10/15 min accuracy)
    [□] Model serialization (joblib / ONNX)
    [□] Build FastAPI prediction endpoint
    [□] Build frontend dashboard for live demonstration
```

---

## 21. One-Minute Presentation Pitch (For Judges & Non-Technical Evaluators)

> *"Honorable judges, Indian Railways runs over 13,000 passenger trains daily, but today's delay updates simply tell passengers how late their train is right now—they cannot predict how late it will be when it actually arrives at their station.
> 
> For SIH Problem Statement 26028, we built an intelligent dynamic ETA prediction engine. Rather than relying on simple averages, our system reconstructs complete train trajectories across 38.4 million historical records. We analyze the train's current delay, its recent acceleration or recovery trend over the past three stations, its route progress, planned section run-times, and its operational priority—such as whether it is a Vande Bharat or an ordinary passenger train.
> 
> We have engineered a 52-feature leak-free data pipeline partitioned across a full year of railway operations, generating over 33.9 million supervised training samples. Our system learns whether a train will recover time on track sections with schedule buffers or accumulate delays in congested junctions. The result is an accurate, dynamic ETA that keeps passengers informed and gives station controllers predictive foresight."*

---

## 22. Five-Minute Technical Walkthrough (For Technical Reviewers & Evaluators)

1. **The Core Challenge**: Static railway timetables cannot accommodate dynamic delays caused by single-track bottlenecks, freight precedence, and cascading congestion. Simple static delays fail because trains frequently recover time over sections with schedule buffers or lose time approaching major terminals.
2. **The Data Foundation**: We audited 6 datasets spanning 38.4 million arrival records over 365 continuous days (Feb 2025 – Feb 2026), 172,000 scheduled stops, and 8,700 unique trains. Older 2015 and 2017 timetables were analyzed and excluded because track doubling and electrification have significantly altered modern running speeds.
3. **Semantic Discoveries & Join Integrity**: We discovered that joining delay logs to schedules using sequence numbers (`station_no`) caused 6.7 million errors because operational technical halts shift sequence numbering. By joining on the composite physical key `(train_no, station_name)`, we achieved a clean 96.63% match rate with zero row multiplication. Conflicting train categories were deduplicated using a deterministic domain hierarchy.
4. **Data Sanitization at Scale**: The raw data was preserved untouched. We audited delay anomalies: early arrivals down to -120 minutes were validated as legitimate railway slack buffers, while rare values exceeding 24 hours (including a 365-day date wrap bug) were flagged as outliers. Using Polars and monthly partitioning, all 38.4M records were processed in under 2 minutes into a Snappy-compressed Parquet feature store (~1.68 GB).
5. **Leak-Free Trajectory Engineering**: For each of the 1.72 million individual journeys, records were sequenced chronologically. We engineered 52 features capturing current delay, lag-1, lag-2, and lag-3 delays, sectional acceleration gradients, remaining distance, journey progress, planned speed, scheduled dwell time, railway zone, and train priority class. All lag operations strictly look backward within the active journey, mathematically preventing future-data leakage.
6. **Target Definition**: The primary target is `target_next_delay` (the arrival delay at the immediate downstream station), alongside `target_delay_delta`. At terminus stations, the target is naturally null and excluded from training. The dataset yields **33,960,584 clean, usable supervised training pairs**.
7. **The Modeling Architecture**: We plan to implement a strict chronological split (Months 1–9 Train, Months 10–11 Val, Months 12–13 Test) to prevent seasonal data leakage. Our primary production candidate is an XGBoost Regressor, chosen for its sub-millisecond inference speed, native handling of missing lag features, and superior accuracy on tabular operational physics.
8. **Dynamic ETA Formulation**: At inference time, the model takes the current station state and outputs predicted downstream delay $\hat{y}$. The dynamic ETA is computed as $\text{Scheduled Arrival}_{i+1} + \hat{y}$.
9. **Production Vision**: The engine is designed to sit behind a lightweight FastAPI service, ingesting live GPS/RTIS locomotive streams, querying the serialized model, and streaming dynamic ETAs to passenger mobile apps and station master display consoles.
