import polars as pl
import os
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

data_dir = "e:/train/data/processed/train_features"
partitions = sorted(glob.glob(os.path.join(data_dir, "year_month=*", "features.parquet")))

print("Calculating target distribution across Train, Validation, and Test splits...")

journey_key = ["date", "train_no"]

train_dfs = []
val_dfs = []
test_dfs = []

# Collect target column and date from each partition with strict consecutive filter
for p in partitions:
    ym = os.path.basename(os.path.dirname(p)).split("=")[1]
    df = pl.read_parquet(p, columns=["date", "train_no", "sched_station_no", "station_name", "sched_next_station", "current_delay", "target_next_delay"])

    # Strict consecutive filter
    df = df.with_columns([
        pl.col("sched_station_no").shift(-1).over(journey_key).alias("next_sched_stn"),
        pl.col("station_name").shift(-1).over(journey_key).alias("next_stn_code")
    ])

    mask = (
        pl.col("current_delay").is_not_null() &
        pl.col("target_next_delay").is_not_null() &
        pl.col("sched_station_no").is_not_null() &
        (pl.col("next_sched_stn") == pl.col("sched_station_no") + 1) &
        (pl.col("next_stn_code") == pl.col("sched_next_station"))
    )

    valid_targets = df.filter(mask).select(["date", "target_next_delay"])

    if ym <= "2025-10":
        train_dfs.append(valid_targets)
    elif ym in ["2025-11", "2025-12"]:
        val_dfs.append(valid_targets)
    else:
        test_dfs.append(valid_targets)

train_data = pl.concat(train_dfs)
val_data = pl.concat(val_dfs)
test_data = pl.concat(test_dfs)

def compute_stats(name: str, df: pl.DataFrame):
    targets = df["target_next_delay"]
    cnt = len(targets)
    mean_val = targets.mean()
    std_val = targets.std()
    min_val = targets.min()
    max_val = targets.max()
    p50 = targets.quantile(0.50)
    p75 = targets.quantile(0.75)
    p90 = targets.quantile(0.90)
    p95 = targets.quantile(0.95)
    p99 = targets.quantile(0.99)

    print(f"\n=== {name} TARGET DISTRIBUTION ===")
    print(f"  Count: {cnt:,}")
    print(f"  Mean:  {mean_val:.2f} min")
    print(f"  Std:   {std_val:.2f} min")
    print(f"  Min:   {min_val} min")
    print(f"  Max:   {max_val} min")
    print(f"  P50 (Median): {p50:.1f} min")
    print(f"  P75:   {p75:.1f} min")
    print(f"  P90:   {p90:.1f} min")
    print(f"  P95:   {p95:.1f} min")
    print(f"  P99:   {p99:.1f} min")
    return {
        "count": cnt, "mean": mean_val, "std": std_val, "min": min_val, "max": max_val,
        "median": p50, "p50": p50, "p75": p75, "p90": p90, "p95": p95, "p99": p99
    }

stats_train = compute_stats("TRAIN (Feb-Oct 2025)", train_data)
stats_val = compute_stats("VALIDATION (Nov-Dec 2025)", val_data)
stats_test = compute_stats("TEST (Jan-Feb 2026)", test_data)

