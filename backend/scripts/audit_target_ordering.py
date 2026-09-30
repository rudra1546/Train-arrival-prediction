import polars as pl
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

sample_path = "e:/train/data/processed/sample_features.parquet"
df = pl.read_parquet(sample_path)

print(f"Auditing sample dataset: {sample_path} ({len(df)} rows)")

# Filter to rows that have both current_delay and target_next_delay and sched_station_no
# We want to see how target_next_delay was formed and what the target row actually is.
journey_key = ["date", "train_no"]

# Let's inspect rows with shift(-1) vs sched_next_station from combined_schedule
# Note: sched_next_station is the next station according to the master schedule!
# In builder.py:
# pl.col("station_name").shift(-1).over(journey_key).alias("next_station_name")
# pl.col("delay_clean").shift(-1).over(journey_key).alias("target_next_delay")
# And from schedule: sched_next_station was joined from combined_schedule!

# Let's check:
# 1. next_station_name (from shift(-1)) vs sched_next_station (from schedule)
# 2. next row's sched_station_no vs current sched_station_no + 1

# Let's add target row attributes using shift(-1) on sched_station_no
df_audit = df.with_columns([
    pl.col("sched_station_no").shift(-1).over(journey_key).alias("target_sched_station_no"),
    pl.col("station_no").shift(-1).over(journey_key).alias("target_raw_station_no"),
    pl.col("station_name").shift(-1).over(journey_key).alias("target_station_name")
])

# Let's inspect usable rows (sched_station_no is not null, target_next_delay is not null)
usable = df_audit.filter(
    pl.col("sched_station_no").is_not_null() &
    pl.col("target_next_delay").is_not_null() &
    pl.col("current_delay").is_not_null()
)

print(f"Usable supervised rows in sample: {len(usable):,}")

# Check 1: Does target_station_name == sched_next_station?
match_sched_next = usable.filter(pl.col("target_station_name") == pl.col("sched_next_station"))
print(f"Rows where target_station_name == sched_next_station: {len(match_sched_next):,} / {len(usable):,} ({len(match_sched_next)/len(usable)*100:.2f}%)")

# Check 2: Does target_sched_station_no == sched_station_no + 1?
consecutive = usable.filter(pl.col("target_sched_station_no") == pl.col("sched_station_no") + 1)
print(f"Rows where target_sched_station_no == sched_station_no + 1: {len(consecutive):,} / {len(usable):,} ({len(consecutive)/len(usable)*100:.2f}%)")

# Let's inspect the non-consecutive or mismatched rows
mismatches = usable.filter(pl.col("target_sched_station_no") != pl.col("sched_station_no") + 1)
print(f"Mismatched rows count: {len(mismatches):,} ({len(mismatches)/len(usable)*100:.2f}%)")

if len(mismatches) > 0:
    print("\nSample mismatched rows:")
    sample_mismatch = mismatches.select([
        "date", "train_no", "station_name", "sched_station_no", "sched_next_station",
        "target_station_name", "target_sched_station_no", "current_delay", "target_next_delay"
    ]).head(10)
    print(sample_mismatch)
