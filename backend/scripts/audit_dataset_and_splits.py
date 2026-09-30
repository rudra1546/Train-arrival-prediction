import polars as pl
import os
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

data_dir = "e:/train/data/processed/train_features"
partitions = sorted(glob.glob(os.path.join(data_dir, "year_month=*", "features.parquet")))

print(f"Discovered {len(partitions)} partitions.")

total_raw_rows = 0
total_usable_raw_shift = 0
total_usable_consecutive = 0

train_usable = 0
val_usable = 0
test_usable = 0

train_targets = []
val_targets = []
test_targets = []

unique_train_types = set()
unique_zones = set()
unique_current_stations = set()
unique_next_stations = set()

journey_key = ["date", "train_no"]

print("Scanning all 13 partitions...")

for p in partitions:
    ym = os.path.basename(os.path.dirname(p)).split("=")[1]
    df = pl.read_parquet(p)
    n_rows = len(df)
    total_raw_rows += n_rows

    # Check shift(-1) target row
    df = df.with_columns([
        pl.col("sched_station_no").shift(-1).over(journey_key).alias("next_sched_stn"),
        pl.col("station_name").shift(-1).over(journey_key).alias("next_stn_code")
    ])

    # Usable in previous pipeline: current_delay & target_next_delay & sched_station_no are not null
    prev_usable_mask = (
        pl.col("current_delay").is_not_null() &
        pl.col("target_next_delay").is_not_null() &
        pl.col("sched_station_no").is_not_null()
    )
    n_prev_usable = df.filter(prev_usable_mask).select(pl.len()).item()
    total_usable_raw_shift += n_prev_usable

    # Strict consecutive match: next row is actually sched_station_no + 1 and matches sched_next_station
    strict_consecutive_mask = (
        prev_usable_mask &
        (pl.col("next_sched_stn") == pl.col("sched_station_no") + 1) &
        (pl.col("next_stn_code") == pl.col("sched_next_station"))
    )
    df_strict = df.filter(strict_consecutive_mask)
    n_strict = len(df_strict)
    total_usable_consecutive += n_strict

    # Split:
    # TRAIN: 2025-02-08 to 2025-10-31
    # VAL: 2025-11-01 to 2025-12-31
    # TEST: 2026-01-01 to 2026-02-07
    train_mask = pl.col("date") <= "2025-10-31"
    val_mask = (pl.col("date") >= "2025-11-01") & (pl.col("date") <= "2025-12-31")
    test_mask = pl.col("date") >= "2026-01-01"

    n_train_part = df_strict.filter(train_mask).select(pl.len()).item()
    n_val_part = df_strict.filter(val_mask).select(pl.len()).item()
    n_test_part = df_strict.filter(test_mask).select(pl.len()).item()

    train_usable += n_train_part
    val_usable += n_val_part
    test_usable += n_test_part

    # Collect categoricals
    unique_train_types.update(df["type_code"].drop_nulls().unique().to_list())
    unique_zones.update(df["station_zone"].drop_nulls().unique().to_list())
    unique_current_stations.update(df["station_name"].drop_nulls().unique().to_list())
    unique_next_stations.update(df["sched_next_station"].drop_nulls().unique().to_list())

    print(f"  {ym}: {n_rows:,} rows | prev_usable={n_prev_usable:,} | strict_consecutive={n_strict:,} (train={n_train_part:,}, val={n_val_part:,}, test={n_test_part:,})", flush=True)

print("\n=== TOTALS ACROSS ALL 13 PARTITIONS ===")
print(f"Total rows: {total_raw_rows:,}")
print(f"Total usable (previous raw shift): {total_usable_raw_shift:,}")
print(f"Total usable (strict consecutive next scheduled station): {total_usable_consecutive:,}")
print(f"Mismatches due to unobserved intermediate stops: {total_usable_raw_shift - total_usable_consecutive:,} ({(total_usable_raw_shift - total_usable_consecutive)/total_usable_raw_shift*100:.2f}%)")

print("\n=== EXACT SPLIT COUNTS (STRICT CONSECUTIVE) ===")
print(f"TRAIN (2025-02-08 to 2025-10-31): {train_usable:,} ({train_usable/total_usable_consecutive*100:.2f}%)")
print(f"VALIDATION (2025-11-01 to 2025-12-31): {val_usable:,} ({val_usable/total_usable_consecutive*100:.2f}%)")
print(f"TEST (2026-01-01 to 2026-02-07): {test_usable:,} ({test_usable/total_usable_consecutive*100:.2f}%)")
print(f"SUM CHECK: {train_usable + val_usable + test_usable:,} == {total_usable_consecutive:,} -> {train_usable + val_usable + test_usable == total_usable_consecutive}")

print("\n=== CATEGORICAL CARDINALITIES ===")
print(f"type_code unique: {len(unique_train_types)} -> {sorted(unique_train_types)}")
print(f"station_zone unique: {len(unique_zones)} -> {sorted(unique_zones)}")
print(f"station_name unique: {len(unique_current_stations):,}")
print(f"sched_next_station unique: {len(unique_next_stations):,}")
