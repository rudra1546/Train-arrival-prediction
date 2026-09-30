"""
Delay anomaly handling, distribution analysis, and data cleaning rules.
Preserves raw values and documents explicit filtering thresholds.
"""

import polars as pl
from typing import Dict, Tuple
from ml.utils.config import MIN_VALID_DELAY, MAX_VALID_DELAY


def analyze_delay_distribution(lazy_delay: pl.LazyFrame) -> Dict:
    """
    Compute fine-grained delay distribution metrics, percentiles,
    and anomaly breakdown across the entire dataset.
    """
    total_rows = lazy_delay.select(pl.len()).collect().item()

    # Binned counts
    bin_exprs = [
        pl.col("delay").is_null().sum().alias("null_count"),
        (pl.col("delay") < MIN_VALID_DELAY).sum().alias("extreme_early_count"),
        ((pl.col("delay") >= MIN_VALID_DELAY) & (pl.col("delay") < 0)).sum().alias("normal_early_count"),
        (pl.col("delay") == 0).sum().alias("on_time_count"),
        ((pl.col("delay") > 0) & (pl.col("delay") <= 15)).sum().alias("minor_delay_count"),
        ((pl.col("delay") > 15) & (pl.col("delay") <= 60)).sum().alias("moderate_delay_count"),
        ((pl.col("delay") > 60) & (pl.col("delay") <= 180)).sum().alias("significant_delay_count"),
        ((pl.col("delay") > 180) & (pl.col("delay") <= 720)).sum().alias("severe_delay_count"),
        ((pl.col("delay") > 720) & (pl.col("delay") <= MAX_VALID_DELAY)).sum().alias("very_severe_delay_count"),
        (pl.col("delay") > MAX_VALID_DELAY).sum().alias("extreme_outlier_count"),
        pl.col("delay").min().alias("raw_min_delay"),
        pl.col("delay").max().alias("raw_max_delay"),
        pl.col("delay").mean().alias("raw_mean_delay"),
        pl.col("delay").median().alias("raw_median_delay")
    ]

    stats = lazy_delay.select(bin_exprs).collect().to_dicts()[0]

    # Percentiles on non-null delay
    non_null_delay = lazy_delay.filter(pl.col("delay").is_not_null())
    quantiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999]
    q_exprs = [non_null_delay.select(pl.col("delay").quantile(q).alias(f"q_{int(q*1000)}")) for q in quantiles]
    q_results = pl.concat(q_exprs, how="horizontal").collect().to_dicts()[0]

    return {
        "total_rows": total_rows,
        "bins": {
            "null": {"count": stats["null_count"], "pct": stats["null_count"] / total_rows * 100},
            "extreme_early (< -120m)": {"count": stats["extreme_early_count"], "pct": stats["extreme_early_count"] / total_rows * 100},
            "early ([-120, 0)m)": {"count": stats["normal_early_count"], "pct": stats["normal_early_count"] / total_rows * 100},
            "on_time (0m)": {"count": stats["on_time_count"], "pct": stats["on_time_count"] / total_rows * 100},
            "minor ((0, 15]m)": {"count": stats["minor_delay_count"], "pct": stats["minor_delay_count"] / total_rows * 100},
            "moderate ((15, 60]m)": {"count": stats["moderate_delay_count"], "pct": stats["moderate_delay_count"] / total_rows * 100},
            "significant ((60, 180]m)": {"count": stats["significant_delay_count"], "pct": stats["significant_delay_count"] / total_rows * 100},
            "severe ((180, 720]m)": {"count": stats["severe_delay_count"], "pct": stats["severe_delay_count"] / total_rows * 100},
            "very_severe ((720, 1440]m)": {"count": stats["very_severe_delay_count"], "pct": stats["very_severe_delay_count"] / total_rows * 100},
            "extreme_outlier (> 1440m)": {"count": stats["extreme_outlier_count"], "pct": stats["extreme_outlier_count"] / total_rows * 100}
        },
        "summary": {
            "min": stats["raw_min_delay"],
            "max": stats["raw_max_delay"],
            "mean": stats["raw_mean_delay"],
            "median": stats["raw_median_delay"]
        },
        "quantiles": q_results
    }


def add_delay_cleaning_expressions() -> list:
    """
    Polars expressions to create cleaned delay columns without mutating raw delay.
    - delay_clean: retains values in [MIN_VALID_DELAY, MAX_VALID_DELAY], else None
    - is_delay_missing: 1 if raw delay was null
    - is_delay_outlier: 1 if raw delay was < -120 or > 1440
    """
    return [
        pl.when(
            (pl.col("delay").is_not_null()) &
            (pl.col("delay") >= MIN_VALID_DELAY) &
            (pl.col("delay") <= MAX_VALID_DELAY)
        )
        .then(pl.col("delay"))
        .otherwise(None)
        .alias("delay_clean"),

        pl.when(pl.col("delay").is_null())
        .then(1)
        .otherwise(0)
        .cast(pl.Int8)
        .alias("is_delay_missing"),

        pl.when(
            (pl.col("delay").is_not_null()) &
            ((pl.col("delay") < MIN_VALID_DELAY) | (pl.col("delay") > MAX_VALID_DELAY))
        )
        .then(1)
        .otherwise(0)
        .cast(pl.Int8)
        .alias("is_delay_outlier")
    ]
