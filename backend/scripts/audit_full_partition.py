import polars as pl
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load the full 2025-02 partition (2,189,691 rows)
p = "e:/train/data/processed/train_features/year_month=2025-02/features.parquet"
print(f"Reading {p}...")
df = pl.read_parquet(p)
print(f"Loaded {len(df):,} rows.")

journey_key = ["date", "train_no"]

# Add next row attributes
df_audit = df.with_columns([
    pl.col("sched_station_no").shift(-1).over(journey_key).alias("target_sched_station_no"),
    pl.col("station_name").shift(-1).over(journey_key).alias("target_station_name")
])

usable = df_audit.filter(
    pl.col("sched_station_no").is_not_null() &
    pl.col("target_next_delay").is_not_null() &
    pl.col("current_delay").is_not_null()
)

total_usable = len(usable)
print(f"Total usable rows in 2025-02: {total_usable:,}")

# Exact consecutive check
match_consecutive = usable.filter(
    (pl.col("target_sched_station_no") == pl.col("sched_station_no") + 1) &
    (pl.col("target_station_name") == pl.col("sched_next_station"))
)
n_match = len(match_consecutive)
n_mismatch = total_usable - n_match

print(f"Consecutive scheduled matches: {n_match:,} ({n_match/total_usable*100:.2f}%)")
print(f"Mismatches (skipped stop in delay log or operational halt): {n_mismatch:,} ({n_mismatch/total_usable*100:.2f}%)")

# Let's inspect the reasons for mismatches
mismatches = usable.filter(
    (pl.col("target_sched_station_no") != pl.col("sched_station_no") + 1) |
    (pl.col("target_station_name") != pl.col("sched_next_station"))
)

# 1. Target row is an operational halt (target_sched_station_no is null)
op_halt_target = mismatches.filter(pl.col("target_sched_station_no").is_null())
print(f"  Mismatches where next logged row was an operational halt: {len(op_halt_target):,} ({len(op_halt_target)/n_mismatch*100:.2f}%)")

# 2. Target row skipped one or more scheduled stations (target_sched_station_no > sched_station_no + 1)
skipped_station_target = mismatches.filter(
    pl.col("target_sched_station_no").is_not_null() &
    (pl.col("target_sched_station_no") > pl.col("sched_station_no") + 1)
)
print(f"  Mismatches where intermediate scheduled station was skipped: {len(skipped_station_target):,} ({len(skipped_station_target)/n_mismatch*100:.2f}%)")

# 3. Other mismatches (e.g. sequence decrease)
other_mismatches = mismatches.filter(
    pl.col("target_sched_station_no").is_not_null() &
    (pl.col("target_sched_station_no") <= pl.col("sched_station_no"))
)
print(f"  Mismatches with sequence decrease/repeat: {len(other_mismatches):,} ({len(other_mismatches)/n_mismatch*100:.2f}%)")

