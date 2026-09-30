# Data Preprocessing & Validation Report
**SIH Problem Statement 26028: Dynamic Forecast of ETA for Coaching Trains**
*Generated: 2026-09-29 21:41:55*

---

## 1. Pipeline Execution Overview

The automated preprocessing and sanitization pipeline processed all **38,428,703** raw train stop observations partitioned across **13** monthly intervals.

- **Total Processed Rows**: 38,428,703
- **Total Unique Journeys `(date, train_no)`**: 1,895,758
- **Usable Supervised Samples (`current_delay` & `target_next_delay` valid)**: 33,925,776 (88.28%)
- **Data Protection**: Original raw CSVs in `e:/train/data/` were preserved 100% untouched.

---

## 2. Metadata Deduplication & Standardization

### 2.1 Train Details (`train_details.csv`)
- **Raw Rows**: 8,992
- **Normalized Unique Trains**: 8,720
- **Duplicate Rows Identified**: 544 (272 pairs)
- **Deduplication Rule**: Deterministic hierarchy: T18 > RAJ > SHT > GRB > PRM > SF > EXP > PASS
- **Resolution**: Resolved all collisions deterministically. Priority ranking:
  1. `T18-TRAINS` (Vande Bharat)
  2. `RAJ-TRAINS` (Rajdhani)
  3. `SHT-TRAINS` (Shatabdi)
  4. `GRB-TRAINS` (Garib Rath)
  5. `PRM-TRAINS` (Premium Special)
  6. `SF-TRAINS` (Superfast)
  7. `EXP-TRAINS` (Express)
  8. `PASS-TRAINS` (Passenger)

### 2.2 Station Master (`station_full_names.csv`)
- **Raw Master Stations**: 8,963
- **Augmented Modern Stations**: 10 (e.g. `BSBS` -> `NER`, `KCVL` -> `SR`)
- **Total Operational Stations**: 8,973
- **Station Code Formatting**: Normalized to uppercase stripped string.

### 2.3 Master Schedule (`combined_schedule.csv`)
- **Total Scheduled Stops**: 172,112
- **Unique Scheduled Trains**: 8,673
- **Max Route Distance**: 4,188 km
- **Max Scheduled Stations**: 119 stations
- **Enrichments**: Time parsing to minute integers, planned section run-times, planned dwell times, section distances, and planned section speed.

---

## 3. Delay Anomaly Analysis & Sanitization Decision

### 3.1 Delay Distribution Breakdown ($N = 38,428,703$)

| Delay Category | Threshold Criteria | Row Count | Percentage | Operational Meaning |
|---|---|---|---|---|
| **Null Telemetry** | `delay is null` | 1,874,271 | 4.88% | Skipped sensor, non-reporting station, bypass |
| **Extreme Early** | `delay < -120m` | 0 | 0.0000% | Unrealistic early arrival (corrupt timestamp) |
| **Normal Early** | `-120m <= delay < 0m` | 773,174 | 2.01% | Legitimate railway recovery & slack buffers |
| **Strictly On Time** | `delay == 0m` | 4,898,984 | 12.75% | On-time arrival |
| **Minor Delay** | `0m < delay <= 15m` | 12,438,101 | 32.37% | Right-time railway standard |
| **Moderate Delay** | `15m < delay <= 60m` | 12,505,210 | 32.54% | Normal operational variance |
| **Significant Delay** | `60m < delay <= 180m` | 4,802,089 | 12.50% | Congestion, freight precedence, crossings |
| **Severe Delay** | `180m < delay <= 720m` | 1,080,986 | 2.81% | Major block, technical fault, heavy fog |
| **Very Severe** | `720m < delay <= 1440m` | 40,815 | 0.11% | Severe disruption / rescheduling |
| **Extreme Outlier** | `delay > 1440m` (24h) | 15,073 | 0.0392% | Wraparound bug / date mismatch (max: 525,592m) |

### 3.2 Cleaning & Preservation Policy
1. **Raw Column Preservation**: The original `delay` column is preserved in the dataset completely unmodified.
2. **`delay_clean` Column**: Values in $[-120, 1440]$ minutes are retained. Extreme outliers ($> 1440$ min or $< -120$ min) and null values are mapped to `NULL` in `delay_clean`.
3. **Explicit Diagnostic Flags**:
   - `is_delay_missing`: 1 if original delay was null.
   - `is_delay_outlier`: 1 if original delay was outside $[-120, 1440]$.

---

## 4. Canonical Join Performance & Integrity Audit

All joins use the canonical keys discovered in the preliminary inspection to prevent sequence number desynchronization.

| Join Step | Left Table | Right Table | Join Keys | Rows Before | Rows After | Matched Rows | Match Rate | Row Multiplication |
|---|---|---|---|---|---|---|---|---|
| **Join 1** | `combined_delay` | `combined_schedule` | `[train_no, station_name]` | 2,189,691 | 2,189,691 | 2,118,453 | **96.75%** | **0** |
| **Join 2** | Result J1 | `train_details` | `[train_no]` | 2,189,691 | 2,189,691 | 2,189,691 | **100.00%** | **0** |
| **Join 3** | Result J2 | `station_full_names` | `[station_name]` | 2,189,691 | 2,189,691 | 2,185,554 | **99.81%** | **0** |

- **Row Multiplication**: Exactly 0 across all joins (strictly $1$-to-$1$ or $N$-to-$1$).
- **Integrity**: Avoided the 6.7M sequence mismatches caused by naive joining on `station_no`.
