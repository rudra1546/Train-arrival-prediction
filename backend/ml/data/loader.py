"""
Data loading and normalization module for Indian Railways datasets.
Preserves raw files, applies strict types, zero-pads train numbers, and deduplicates metadata.
"""

import polars as pl
from pathlib import Path
from typing import Dict, Tuple
from ml.utils.config import (
    TRAIN_DETAILS_FILE,
    STATION_NAMES_FILE,
    SCHEDULE_FILE,
    DELAY_FILE,
    TRAIN_TYPE_PRIORITY,
    KNOWN_STATION_ZONES
)


def load_train_details(file_path: Path = TRAIN_DETAILS_FILE) -> Tuple[pl.DataFrame, Dict]:
    """
    Load train_details.csv, normalize train numbers to 5 digits, and deduplicate
    conflicting train numbers deterministically using operational priority hierarchy.
    """
    raw_df = pl.read_csv(file_path, schema_overrides={"train_no": pl.String})
    raw_count = len(raw_df)

    # Normalize train_no and string fields
    clean_df = raw_df.with_columns(
        pl.col("train_no").str.strip_chars().str.zfill(5).alias("train_no"),
        pl.col("train_name").str.strip_chars(),
        pl.col("type_code").str.strip_chars()
    )

    # Count duplicates before resolution
    dup_count = clean_df.select(pl.col("train_no").is_duplicated()).sum().item()
    unique_trains_before = clean_df.select(pl.col("train_no").n_unique()).item()

    # Assign priority rank (1 = highest priority / specificity)
    clean_df = clean_df.with_columns(
        pl.col("type_code")
        .replace_strict(TRAIN_TYPE_PRIORITY, default=99)
        .cast(pl.Int32)
        .alias("priority_rank")
    )

    # Sort by train_no and priority_rank ascending, then keep first
    dedup_df = (
        clean_df
        .sort(["train_no", "priority_rank"])
        .unique(subset=["train_no"], keep="first")
        .drop("priority_rank")
    )
    final_count = len(dedup_df)

    audit = {
        "raw_rows": raw_count,
        "duplicate_rows": dup_count,
        "unique_trains": final_count,
        "dedup_resolved": raw_count - final_count,
        "dedup_rule": "Deterministic hierarchy: T18 > RAJ > SHT > GRB > PRM > SF > EXP > PASS"
    }

    return dedup_df, audit


def load_station_master(file_path: Path = STATION_NAMES_FILE) -> Tuple[pl.DataFrame, Dict]:
    """
    Load station_full_names.csv, normalize station codes to uppercase,
    and augment with known modern stations missing from legacy master.
    """
    raw_df = pl.read_csv(file_path, schema_overrides={"station_name": pl.String})
    raw_count = len(raw_df)

    clean_df = raw_df.with_columns(
        pl.col("station_name").str.strip_chars().str.to_uppercase(),
        pl.col("station_full_name").str.strip_chars(),
        pl.col("station_zone").str.strip_chars(),
        pl.col("station_address").str.strip_chars()
    ).select(["station_name", "station_full_name", "station_zone", "station_address"])

    # Augment known missing modern stations
    extra_rows = [
        {"station_name": code, "station_full_name": f"Station {code}", "station_zone": zone, "station_address": "India"}
        for code, zone in KNOWN_STATION_ZONES.items()
        if code not in clean_df["station_name"].to_list()
    ]
    if extra_rows:
        extra_df = pl.DataFrame(extra_rows)
        clean_df = pl.concat([clean_df, extra_df], how="vertical")

    audit = {
        "raw_stations": raw_count,
        "augmented_stations": len(extra_rows),
        "total_stations": len(clean_df),
        "duplicate_stations": clean_df.select(pl.col("station_name").is_duplicated()).sum().item()
    }

    return clean_df, audit


def parse_time_expr(col_name: str) -> pl.Expr:
    """Polars expression to convert HH:MM string to integer minutes from midnight."""
    return (
        pl.when(pl.col(col_name).is_not_null() & (pl.col(col_name).str.contains(":")))
        .then(
            pl.col(col_name).str.split(":").list.get(0).cast(pl.Int32) * 60 +
            pl.col(col_name).str.split(":").list.get(1).cast(pl.Int32)
        )
        .otherwise(None)
    )


def load_schedule(file_path: Path = SCHEDULE_FILE) -> Tuple[pl.DataFrame, Dict]:
    """
    Load combined_schedule.csv, normalize keys, parse scheduled times,
    and compute planned section run times, dwell times, and cumulative metrics.
    """
    raw_df = pl.read_csv(
        file_path,
        schema_overrides={
            "station_no": pl.Int16,
            "station_name": pl.String,
            "distance_from_origin": pl.Int32,
            "arrival_day": pl.Int8,
            "arrival_time": pl.String,
            "departure_day": pl.Int8,
            "departure_time": pl.String,
            "train_no": pl.String
        }
    )
    raw_count = len(raw_df)

    clean_df = raw_df.with_columns(
        pl.col("train_no").str.strip_chars().str.zfill(5),
        pl.col("station_name").str.strip_chars().str.to_uppercase(),
        parse_time_expr("arrival_time").alias("arr_min"),
        parse_time_expr("departure_time").alias("dep_min")
    )

    # Route summary per train
    route_stats = clean_df.group_by("train_no").agg([
        pl.col("distance_from_origin").max().alias("route_total_distance"),
        pl.col("station_no").max().alias("route_total_stations")
    ])

    sched_df = clean_df.join(route_stats, on="train_no", how="left")
    sched_df = sched_df.sort(["train_no", "station_no"])

    # Scheduled dwell time in minutes (dep_time - arr_time)
    sched_df = sched_df.with_columns(
        pl.when(pl.col("dep_min").is_not_null() & pl.col("arr_min").is_not_null())
        .then(
            (pl.col("departure_day") - pl.col("arrival_day")) * 1440 + pl.col("dep_min") - pl.col("arr_min")
        )
        .otherwise(0)
        .alias("scheduled_dwell_time")
    )

    # Next station planned attributes
    sched_df = sched_df.with_columns([
        pl.col("station_name").shift(-1).over("train_no").alias("sched_next_station"),
        pl.col("distance_from_origin").shift(-1).over("train_no").alias("sched_next_dist"),
        pl.col("arrival_day").shift(-1).over("train_no").alias("sched_next_arr_day"),
        pl.col("arr_min").shift(-1).over("train_no").alias("sched_next_arr_min")
    ])

    sched_df = sched_df.with_columns([
        (pl.col("sched_next_dist") - pl.col("distance_from_origin")).alias("sched_section_distance"),
        pl.when(pl.col("sched_next_arr_min").is_not_null() & pl.col("dep_min").is_not_null())
        .then(
            (pl.col("sched_next_arr_day") - pl.col("departure_day")) * 1440 + pl.col("sched_next_arr_min") - pl.col("dep_min")
        )
        .otherwise(None)
        .alias("sched_section_travel_time")
    ])

    # Planned section speed in km/h
    sched_df = sched_df.with_columns(
        pl.when((pl.col("sched_section_travel_time") > 0) & (pl.col("sched_section_distance") > 0))
        .then(
            (pl.col("sched_section_distance") / (pl.col("sched_section_travel_time") / 60.0))
        )
        .otherwise(None)
        .alias("sched_planned_speed")
    )

    # Attach next station zone
    stn_zone_lookup = pl.read_csv(STATION_NAMES_FILE, schema_overrides={"station_name": pl.String}).select([
        pl.col("station_name").str.strip_chars().str.to_uppercase(),
        pl.col("station_zone").str.strip_chars()
    ])
    sched_df = sched_df.join(
        stn_zone_lookup.rename({"station_name": "sched_next_station", "station_zone": "sched_next_zone"}),
        on="sched_next_station",
        how="left"
    )

    # Rename station_no to sched_station_no to avoid join ambiguity
    sched_df = sched_df.rename({"station_no": "sched_station_no"})

    audit = {
        "raw_schedule_rows": raw_count,
        "unique_trains": sched_df.select(pl.col("train_no").n_unique()).item(),
        "unique_stations": sched_df.select(pl.col("station_name").n_unique()).item(),
        "max_distance": sched_df.select(pl.col("distance_from_origin").max()).item(),
        "max_stations": sched_df.select(pl.col("sched_station_no").max()).item()
    }

    return sched_df, audit


def scan_delay_data(file_path: Path = DELAY_FILE) -> pl.LazyFrame:
    """
    Return a memory-efficient Polars LazyFrame scanning combined_delay.csv
    with explicit string overrides to preserve leading zeros and formats.
    """
    return pl.scan_csv(
        file_path,
        schema_overrides={
            "date": pl.String,
            "station_no": pl.Int16,
            "station_name": pl.String,
            "delay": pl.Int32,
            "train_no": pl.String
        },
        ignore_errors=True
    ).with_columns(
        pl.col("train_no").str.strip_chars().str.zfill(5),
        pl.col("station_name").str.strip_chars().str.to_uppercase(),
        pl.col("date").str.strip_chars()
    )
