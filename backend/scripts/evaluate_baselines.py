"""
Script to evaluate simple, leakage-safe baselines:
1. Persistence Baseline: y_hat = current_delay
2. Historical Mean Baseline: Global train mean & train-specific mean (leakage-safe from train split only)
3. Simple Linear Model: Ridge regression on a small set of numerical features

Evaluates strictly on chronological Validation (Nov-Dec 2025) and Test (Jan-Feb 2026) sets.
"""

import sys
import os
import glob
import numpy as np
import polars as pl
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, median_absolute_error

sys.stdout.reconfigure(encoding='utf-8')
data_dir = "e:/train/data/processed/train_features"

RANDOM_SEED = 42
TRAIN_SAMPLE_SIZE = 500000
EVAL_SAMPLE_SIZE = 200000

print("=" * 80)
print("EVALUATING BASELINES FOR SIH 26028")
print("=" * 80, flush=True)

# 1. Load Train Sample (from partitions 2025-02 through 2025-10)
print("\n[Step 1/4] Loading representative training sample from Feb-Oct 2025...", flush=True)
train_partitions = sorted(glob.glob(os.path.join(data_dir, "year_month=2025-0[2-9]*/features.parquet")) +
                          glob.glob(os.path.join(data_dir, "year_month=2025-10/features.parquet")))

cols_needed = [
    "date", "train_no", "station_name", "sched_station_no", "sched_next_station",
    "current_delay", "prev_station_delay", "delay_change", "dist_from_origin",
    "remaining_dist", "journey_progress", "sched_section_distance",
    "sched_section_travel_time", "scheduled_hour", "day_of_week", "target_next_delay"
]

train_slices = []
samples_per_train_part = TRAIN_SAMPLE_SIZE // len(train_partitions) + 5000

for p in train_partitions:
    df_p = pl.read_parquet(p, columns=cols_needed)
    # Filter valid supervised rows (target is not null)
    df_valid = df_p.filter(
        pl.col("current_delay").is_not_null() &
        pl.col("target_next_delay").is_not_null() &
        pl.col("sched_station_no").is_not_null() &
        pl.col("sched_section_distance").is_not_null() &
        pl.col("sched_section_travel_time").is_not_null()
    )
    sampled = df_valid.sample(n=min(samples_per_train_part, len(df_valid)), seed=RANDOM_SEED)
    train_slices.append(sampled)

train_df = pl.concat(train_slices).sample(n=TRAIN_SAMPLE_SIZE, seed=RANDOM_SEED)
print(f"  Loaded Train sample: {len(train_df):,} rows (from {len(train_partitions)} monthly partitions)")

# 2. Load Validation Sample (2025-11 and 2025-12)
print("\n[Step 2/4] Loading representative validation sample from Nov-Dec 2025...", flush=True)
val_partitions = [
    os.path.join(data_dir, "year_month=2025-11", "features.parquet"),
    os.path.join(data_dir, "year_month=2025-12", "features.parquet")
]
val_slices = []
samples_per_val_part = EVAL_SAMPLE_SIZE // len(val_partitions) + 5000

for p in val_partitions:
    df_p = pl.read_parquet(p, columns=cols_needed)
    df_valid = df_p.filter(
        pl.col("current_delay").is_not_null() &
        pl.col("target_next_delay").is_not_null() &
        pl.col("sched_station_no").is_not_null() &
        pl.col("sched_section_distance").is_not_null() &
        pl.col("sched_section_travel_time").is_not_null()
    )
    val_slices.append(df_valid.sample(n=min(samples_per_val_part, len(df_valid)), seed=RANDOM_SEED))

val_df = pl.concat(val_slices).sample(n=EVAL_SAMPLE_SIZE, seed=RANDOM_SEED)
print(f"  Loaded Validation sample: {len(val_df):,} rows (Nov-Dec 2025)")

# 3. Load Test Sample (2026-01 and 2026-02)
print("\n[Step 3/4] Loading representative test sample from Jan-Feb 2026...", flush=True)
test_partitions = [
    os.path.join(data_dir, "year_month=2026-01", "features.parquet"),
    os.path.join(data_dir, "year_month=2026-02", "features.parquet")
]
test_slices = []
samples_per_test_part = EVAL_SAMPLE_SIZE // len(test_partitions) + 5000

for p in test_partitions:
    df_p = pl.read_parquet(p, columns=cols_needed)
    df_valid = df_p.filter(
        pl.col("current_delay").is_not_null() &
        pl.col("target_next_delay").is_not_null() &
        pl.col("sched_station_no").is_not_null() &
        pl.col("sched_section_distance").is_not_null() &
        pl.col("sched_section_travel_time").is_not_null()
    )
    test_slices.append(df_valid.sample(n=min(samples_per_test_part, len(df_valid)), seed=RANDOM_SEED))

test_df = pl.concat(test_slices).sample(n=EVAL_SAMPLE_SIZE, seed=RANDOM_SEED)
print(f"  Loaded Test sample: {len(test_df):,} rows (Jan-Feb 2026)")

# 4. Construct Models and Evaluate
print("\n[Step 4/4] Fitting models and evaluating metrics...", flush=True)

# Feature list for Linear Model
feature_cols = [
    "current_delay", "prev_delay_imp", "delay_change_imp", "dist_from_origin",
    "remaining_dist", "journey_progress", "sched_section_distance",
    "sched_section_travel_time", "scheduled_hour", "day_of_week"
]

def prepare_features(df: pl.DataFrame):
    # Impute missing lag features with current_delay / 0
    df_feat = df.with_columns([
        pl.col("prev_station_delay").fill_null(pl.col("current_delay")).alias("prev_delay_imp"),
        pl.col("delay_change").fill_null(0).alias("delay_change_imp")
    ])
    X = df_feat.select(feature_cols).to_numpy()
    y = df_feat["target_next_delay"].to_numpy()
    current_d = df_feat["current_delay"].to_numpy()
    train_no_list = df_feat["train_no"].to_list()
    return X, y, current_d, train_no_list

X_train, y_train, curr_train, tr_train = prepare_features(train_df)
X_val, y_val, curr_val, tr_val = prepare_features(val_df)
X_test, y_test, curr_test, tr_test = prepare_features(test_df)

# Fit Baseline B: Historical Means strictly from Training set
global_train_mean = float(np.mean(y_train))
# Train-specific historical mean
train_mean_lookup = {}
for t, target in zip(tr_train, y_train):
    train_mean_lookup.setdefault(t, []).append(target)
train_mean_dict = {t: float(np.mean(vals)) for t, vals in train_mean_lookup.items()}

# Fit Baseline C: Ridge Regression
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

ridge = Ridge(alpha=1.0)
ridge.fit(X_train_scaled, y_train)

# Evaluation Function
def evaluate_predictions(y_true, y_pred, name="Model"):
    err = np.abs(y_true - y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    medae = median_absolute_error(y_true, y_pred)
    acc_5 = np.mean(err <= 5.0) * 100.0
    acc_10 = np.mean(err <= 10.0) * 100.0
    acc_15 = np.mean(err <= 15.0) * 100.0
    return {
        "model": name,
        "mae": mae,
        "rmse": rmse,
        "medae": medae,
        "acc_5": acc_5,
        "acc_10": acc_10,
        "acc_15": acc_15
    }

# Predictions on Validation
pred_val_persist = curr_val
pred_val_global_mean = np.full_like(y_val, global_train_mean)
pred_val_train_mean = np.array([train_mean_dict.get(t, global_train_mean) for t in tr_val])
pred_val_ridge = ridge.predict(X_val_scaled)

# Predictions on Test
pred_test_persist = curr_test
pred_test_global_mean = np.full_like(y_test, global_train_mean)
pred_test_train_mean = np.array([train_mean_dict.get(t, global_train_mean) for t in tr_test])
pred_test_ridge = ridge.predict(X_test_scaled)

val_results = [
    evaluate_predictions(y_val, pred_val_persist, "Persistence (y_hat = current_delay)"),
    evaluate_predictions(y_val, pred_val_global_mean, "Historical Mean (Global Train Mean)"),
    evaluate_predictions(y_val, pred_val_train_mean, "Historical Mean (Train-Specific)"),
    evaluate_predictions(y_val, pred_val_ridge, "Simple Linear (Ridge Regression)")
]

test_results = [
    evaluate_predictions(y_test, pred_test_persist, "Persistence (y_hat = current_delay)"),
    evaluate_predictions(y_test, pred_test_global_mean, "Historical Mean (Global Train Mean)"),
    evaluate_predictions(y_test, pred_test_train_mean, "Historical Mean (Train-Specific)"),
    evaluate_predictions(y_test, pred_test_ridge, "Simple Linear (Ridge Regression)")
]

def print_table(results, title):
    print(f"\n=== {title} ===")
    print(f"{'Model':<40} | {'MAE (min)':<10} | {'RMSE (min)':<10} | {'MedAE':<8} | {'±5 min':<8} | {'±10 min':<8} | {'±15 min':<8}")
    print("-" * 106)
    for r in results:
        print(f"{r['model']:<40} | {r['mae']:>10.2f} | {r['rmse']:>10.2f} | {r['medae']:>8.1f} | {r['acc_5']:>7.2f}% | {r['acc_10']:>7.2f}% | {r['acc_15']:>7.2f}%")

print_table(val_results, "VALIDATION SET EVALUATION (Nov-Dec 2025, N=200,000)")
print_table(test_results, "TEST SET EVALUATION (Jan-Feb 2026, N=200,000)")

# Print Ridge Coefficients
print("\n=== RIDGE REGRESSION FEATURE COEFFICIENTS ===")
for col, coef in zip(feature_cols, ridge.coef_):
    print(f"  {col:<30}: {coef:>10.4f}")
print(f"  {'Intercept':<30}: {ridge.intercept_:>10.4f}")

