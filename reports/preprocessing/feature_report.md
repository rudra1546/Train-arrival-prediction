# Feature Engineering & Target Definition Report
**SIH Problem Statement 26028: Dynamic Forecast of ETA for Coaching Trains**
*Generated: 2026-09-29 21:41:55*

---

## 1. Feature Architecture & Leakage Prevention Guarantee

Dynamic ETA forecasting predicts arrival delay at a downstream station based *strictly* on information known up to the train's current reporting station.

### 1.1 Strict Leakage Prevention Rules
1. **Journey Boundary Isolation**: All lag and lead expressions (`shift(k)`) are executed strictly within `over(['date', 'train_no'])`. No information can leak across different dates or train services.
2. **Chronological Progression**: Stops within each journey are strictly sorted by `['date', 'train_no', 'sched_station_no', 'station_no']`.
3. **Past-Only Predictors**:
   - `current_delay`: Delay at current station k.
   - `prev_station_delay`, `prev_delay_2`, `prev_delay_3`: Delays at k-1, k-2, k-3.
   - `delay_change`: Gradient of delay accumulation over preceding sections.
   - Downstream delays (k+1, k+2, ...) are NEVER permitted as input features.
4. **Target Isolation**:
   - The primary target `target_next_delay` is constructed via `shift(-1)` representing the actual arrival delay at station k+1.
   - It is completely excluded from feature columns.

---

## 2. Target Variable Formulation

- **Primary Target Formula**:
  `target_next_delay = delay_clean[i+1]` (Arrival delay at downstream station in minutes)
- **Auxiliary Delta Target**:
  `target_delay_delta = delay_clean[i+1] - current_delay[i]` (Delay accumulation/recovery across section)
- **Dynamic ETA Derivation**:
  `Predicted ETA = Scheduled Arrival Time[i+1] + Predicted Next Delay`

- **Terminus Stations**: At the final destination of a journey, station i+1 does not exist. Hence, `target_next_delay` is naturally NULL. Terminus rows represent final journey completion and are not training points for next-station forecasting.
- **Usable Supervised Samples**: **33,925,776** valid (x_i, y_i) sample pairs across the entire dataset.

---

## 3. Comprehensive Feature Manifest

| Feature Group | Column Name | Type | Description |
|---|---|---|---|
| **Identifiers** | `date` | String | Train Origin Journey Start Date (YYYY-MM-DD) |
| | `train_no` | String | 5-digit zero-padded train number |
| | `station_name` | String | Current IR station code (e.g. NDLS, CSMT) |
| | `sched_station_no` | Int16 | Commercial scheduled stop sequence number (1..N) |
| **Target Variables** | `target_next_delay` | Int32 | **Primary Target**: Actual delay at next station (minutes) |
| | `target_delay_delta` | Int32 | Change in delay between current stop and next stop (minutes) |
| **Dynamic State** | `current_delay` | Int32 | Latest recorded delay at current station (minutes) |
| | `prev_station_delay` | Int32 | Lag-1 delay: delay at immediately preceding stop (minutes) |
| | `prev_delay_2` | Int32 | Lag-2 delay: delay 2 stops prior (minutes) |
| | `prev_delay_3` | Int32 | Lag-3 delay: delay 3 stops prior (minutes) |
| | `delay_change` | Int32 | Delay delta over 1 stop (`current_delay - prev_station_delay`) |
| | `delay_change_2_stations` | Int32 | Delay delta over 2 stops |
| | `delay_change_3_stations` | Int32 | Delay delta over 3 stops |
| **Route Progress** | `current_station_seq` | Int16 | Current stop index along the route |
| | `stations_remaining` | Int16 | Remaining scheduled stops until destination |
| | `dist_from_origin` | Int32 | Distance traveled from origin (km) |
| | `remaining_dist` | Int32 | Distance remaining to destination (km) |
| | `journey_progress` | Float64 | Fraction of journey completed ($0.0$ to $1.0$) |
| | `route_total_distance` | Int32 | Total route length (km) |
| | `route_total_stations` | Int16 | Total scheduled stops on route |
| **Planned Schedule** | `scheduled_dwell_time` | Int32 | Scheduled halt duration at current stop (minutes) |
| | `sched_section_distance` | Int32 | Planned distance to next station (km) |
| | `sched_section_travel_time` | Int32 | Planned run time to next station (minutes) |
| | `sched_planned_speed` | Float64 | Planned sectional speed (km/h) |
| | `arr_min` | Int32 | Scheduled arrival time (minutes from midnight) |
| | `dep_min` | Int32 | Scheduled departure time (minutes from midnight) |
| | `arrival_day` | Int8 | Journey day counter for arrival (1..4) |
| | `departure_day` | Int8 | Journey day counter for departure (1..4) |
| **Temporal Context** | `scheduled_hour` | Int8 | Hour of scheduled movement (0..23) |
| | `day_of_week` | Int8 | Day of week (0 = Monday, 6 = Sunday) |
| | `month` | Int8 | Month of year (1..12) |
| | `day` | Int8 | Day of month (1..31) |
| | `is_weekend` | Int8 | 1 if Saturday or Sunday, else 0 |
| **Network & Priority** | `type_code` | String | Train priority class (`SF-TRAINS`, `PRM-TRAINS`, etc.) |
| | `station_zone` | String | Railway zone of current station (`NR`, `CR`, `WR`, etc.) |
| | `next_station_name` | String | Station code of the upcoming station |
| | `next_station_zone` | String | Railway zone of the upcoming station |

---

## 4. Sample Dataset Column Null Rates ($N = 50,000$)

| `date` | `String` | 0 | 0.00% |
| `station_no` | `Int16` | 0 | 0.00% |
| `station_name` | `String` | 0 | 0.00% |
| `delay` | `Int32` | 4,318 | 8.64% |
| `train_no` | `String` | 0 | 0.00% |
| `delay_clean` | `Int32` | 4,326 | 8.65% |
| `is_delay_missing` | `Int8` | 0 | 0.00% |
| `is_delay_outlier` | `Int8` | 0 | 0.00% |
| `sched_station_no` | `Int16` | 2,116 | 4.23% |
| `distance_from_origin` | `Int32` | 2,116 | 4.23% |
| `arrival_day` | `Int8` | 2,116 | 4.23% |
| `arrival_time` | `String` | 4,076 | 8.15% |
| `departure_day` | `Int8` | 2,116 | 4.23% |
| `departure_time` | `String` | 4,077 | 8.15% |
| `arr_min` | `Int32` | 4,076 | 8.15% |
| `dep_min` | `Int32` | 4,077 | 8.15% |
| `route_total_distance` | `Int32` | 2,116 | 4.23% |
| `route_total_stations` | `Int16` | 2,116 | 4.23% |
| `scheduled_dwell_time` | `Int32` | 2,116 | 4.23% |
| `sched_next_station` | `String` | 4,077 | 8.15% |
| `sched_next_dist` | `Int32` | 4,077 | 8.15% |
| `sched_next_arr_day` | `Int8` | 4,077 | 8.15% |
| `sched_next_arr_min` | `Int32` | 4,077 | 8.15% |
| `sched_section_distance` | `Int32` | 4,077 | 8.15% |
| `sched_section_travel_time` | `Int32` | 4,077 | 8.15% |
| `sched_planned_speed` | `Float64` | 4,086 | 8.17% |
| `sched_next_zone` | `String` | 4,077 | 8.15% |
| `train_name` | `String` | 0 | 0.00% |
| `type_code` | `String` | 0 | 0.00% |
| `station_full_name` | `String` | 81 | 0.16% |
| `station_zone` | `String` | 81 | 0.16% |
| `current_delay` | `Int32` | 4,326 | 8.65% |
| `prev_station_delay` | `Int32` | 7,009 | 14.02% |
| `prev_delay_2` | `Int32` | 8,881 | 17.76% |
| `prev_delay_3` | `Int32` | 10,757 | 21.51% |
| `current_station_seq` | `Int16` | 2,116 | 4.23% |
| `stations_remaining` | `Int16` | 2,116 | 4.23% |
| `dist_from_origin` | `Int32` | 2,116 | 4.23% |
| `remaining_dist` | `Int32` | 2,116 | 4.23% |
| `journey_progress` | `Float64` | 0 | 0.00% |
| `day_of_week` | `Int8` | 0 | 0.00% |
| `month` | `Int8` | 0 | 0.00% |
| `day` | `Int8` | 0 | 0.00% |
| `is_weekend` | `Int8` | 0 | 0.00% |
| `scheduled_hour` | `Int8` | 2,116 | 4.23% |
| `next_station_name` | `String` | 4,077 | 8.15% |
| `next_station_zone` | `String` | 4,077 | 8.15% |
| `target_next_delay` | `Int32` | 7,017 | 14.03% |
| `is_terminus_station` | `Int8` | 0 | 0.00% |
| `delay_change` | `Int32` | 8,014 | 16.03% |
| `delay_change_2_stations` | `Int32` | 9,891 | 19.78% |
| `delay_change_3_stations` | `Int32` | 11,750 | 23.50% |
| `target_delay_delta` | `Int32` | 8,013 | 16.03% |

---

## 5. Recommended Validation Strategy (Chronological Split)

Because dynamic train delay exhibits strong temporal seasonality (fog seasons in North India, monsoon disruptions, holiday peak traffic), **random K-Fold cross validation will result in catastrophic data leakage**.

### Recommended Chronological Split
- **Training Set (Months 1–9)**: `2025-02-08` through `2025-10-31` (~28.5M rows)
- **Validation Set (Month 10)**: `2025-11-01` through `2025-11-30` (~3.2M rows)
- **Test Set (Months 11–12)**: `2025-12-01` through `2026-02-07` (~6.7M rows, winter fog season)
