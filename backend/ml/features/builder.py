"""
Feature engineering module for dynamic ETA prediction.
Strictly prevents future-data leakage by computing features chronologically along each train journey.
"""

import polars as pl
from typing import Dict, Tuple


def perform_canonical_joins(
    delay_df: pl.DataFrame,
    sched_df: pl.DataFrame,
    td_df: pl.DataFrame,
    stn_df: pl.DataFrame
) -> Tuple[pl.DataFrame, Dict]:
    """
    Join combined_delay with schedule, train details, and station metadata.
    Uses canonical key [train_no, station_name] for schedule to avoid 6.7M sequence mismatches.
    Audits row counts, matches, and ensures no Cartesian row multiplication.
    """
    initial_count = len(delay_df)

    # 1. Delay LEFT JOIN Schedule ON [train_no, station_name]
    j1 = delay_df.join(sched_df, on=["train_no", "station_name"], how="left")
    j1_count = len(j1)
    j1_matched = j1.select(pl.col("sched_station_no").is_not_null().sum()).item()
    j1_unmatched = j1_count - j1_matched

    # 2. LEFT JOIN Train Details ON [train_no]
    j2 = j1.join(td_df.select(["train_no", "train_name", "type_code"]), on="train_no", how="left")
    j2_count = len(j2)
    j2_matched = j2.select(pl.col("type_code").is_not_null().sum()).item()
    j2_unmatched = j2_count - j2_matched

    # 3. LEFT JOIN Station Full Names ON [station_name]
    j3 = j2.join(stn_df.select(["station_name", "station_full_name", "station_zone"]), on="station_name", how="left")
    j3_count = len(j3)
    j3_matched = j3.select(pl.col("station_zone").is_not_null().sum()).item()
    j3_unmatched = j3_count - j3_matched

    audit = {
        "initial_delay_rows": initial_count,
        "join_schedule": {
            "rows_before": initial_count,
            "rows_after": j1_count,
            "matched_rows": j1_matched,
            "unmatched_rows": j1_unmatched,
            "match_pct": (j1_matched / initial_count) * 100.0,
            "row_multiplication": j1_count - initial_count
        },
        "join_train_details": {
            "rows_before": j1_count,
            "rows_after": j2_count,
            "matched_rows": j2_matched,
            "unmatched_rows": j2_unmatched,
            "match_pct": (j2_matched / j1_count) * 100.0,
            "row_multiplication": j2_count - j1_count
        },
        "join_station_master": {
            "rows_before": j2_count,
            "rows_after": j3_count,
            "matched_rows": j3_matched,
            "unmatched_rows": j3_unmatched,
            "match_pct": (j3_matched / j2_count) * 100.0,
            "row_multiplication": j3_count - j2_count
        },
        "final_rows": j3_count
    }

    return j3, audit


def build_journey_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    Sort chronologically by (date, train_no, sched_station_no) and build leak-free
    dynamic state, static route, planned schedule, and temporal features.
    Computes initial target: delay at next station.
    """
    journey_key = ["date", "train_no"]

    # Ensure deterministic chronological route sorting
    sorted_df = df.sort(["date", "train_no", "sched_station_no", "station_no"])

    # First pass: shift and sequence features along journey
    features_df = sorted_df.with_columns([
        # Current delay state at reporting point
        pl.col("delay_clean").alias("current_delay"),

        # Historical lag delays along the current journey (Strictly past info)
        # Only assign prev_station_delay if previous logged row is strictly the preceding scheduled station (i-1)
        pl.when(
            pl.col("sched_station_no").shift(1).over(journey_key) == pl.col("sched_station_no") - 1
        )
        .then(pl.col("delay_clean").shift(1).over(journey_key))
        .otherwise(None)
        .alias("prev_station_delay"),

        pl.when(
            pl.col("sched_station_no").shift(2).over(journey_key) == pl.col("sched_station_no") - 2
        )
        .then(pl.col("delay_clean").shift(2).over(journey_key))
        .otherwise(None)
        .alias("prev_delay_2"),

        pl.when(
            pl.col("sched_station_no").shift(3).over(journey_key) == pl.col("sched_station_no") - 3
        )
        .then(pl.col("delay_clean").shift(3).over(journey_key))
        .otherwise(None)
        .alias("prev_delay_3"),

        # Route progression
        pl.col("sched_station_no").alias("current_station_seq"),
        (pl.col("route_total_stations") - pl.col("sched_station_no")).alias("stations_remaining"),
        pl.col("distance_from_origin").alias("dist_from_origin"),
        (pl.col("route_total_distance") - pl.col("distance_from_origin")).alias("remaining_dist"),
        pl.when(pl.col("route_total_distance") > 0)
        .then(pl.col("distance_from_origin") / pl.col("route_total_distance"))
        .otherwise(0.0)
        .alias("journey_progress"),

        # Temporal features
        pl.col("date").str.to_date().dt.weekday().alias("day_of_week"),
        pl.col("date").str.to_date().dt.month().alias("month"),
        pl.col("date").str.to_date().dt.day().alias("day"),
        pl.when(pl.col("date").str.to_date().dt.weekday().is_in([5, 6]))
        .then(1)
        .otherwise(0)
        .cast(pl.Int8)
        .alias("is_weekend"),

        pl.when(pl.col("dep_min").is_not_null())
        .then(pl.col("dep_min") // 60)
        .when(pl.col("arr_min").is_not_null())
        .then(pl.col("arr_min") // 60)
        .otherwise(None)
        .cast(pl.Int8)
        .alias("scheduled_hour"),

        # Next station identification bound to true timetable topology
        pl.col("sched_next_station").alias("next_station_name"),
        pl.col("sched_next_zone").alias("next_station_zone"),

        # Initial Target: Delay at NEXT station along the active journey
        # Guaranteed consecutive: next logged stop must be sched_station_no + 1 and match sched_next_station
        pl.when(
            (pl.col("sched_station_no").shift(-1).over(journey_key) == pl.col("sched_station_no") + 1) &
            (pl.col("station_name").shift(-1).over(journey_key) == pl.col("sched_next_station"))
        )
        .then(pl.col("delay_clean").shift(-1).over(journey_key))
        .otherwise(None)
        .alias("target_next_delay"),

        # Terminus indicator
        pl.when(pl.col("sched_station_no") == pl.col("route_total_stations"))
        .then(1)
        .otherwise(0)
        .cast(pl.Int8)
        .alias("is_terminus_station")
    ])

    # Second pass: dynamic delta calculations
    features_df = features_df.with_columns([
        # Rate of delay accumulation/absorption across past stations
        (pl.col("current_delay") - pl.col("prev_station_delay")).alias("delay_change"),
        (pl.col("current_delay") - pl.col("prev_delay_2")).alias("delay_change_2_stations"),
        (pl.col("current_delay") - pl.col("prev_delay_3")).alias("delay_change_3_stations"),

        # Auxiliary target delta (how much delay changes between current station and next station)
        (pl.col("target_next_delay") - pl.col("current_delay")).alias("target_delay_delta")
    ])

    return features_df


def get_feature_column_manifest() -> Dict[str, list]:
    """
    Return categorised manifest of features and targets for documentation and modeling.
    """
    return {
        "identifiers": [
            "date",
            "train_no",
            "station_name",
            "sched_station_no"
        ],
        "target": [
            "target_next_delay",      # Primary target: actual delay at next stop (min)
            "target_delay_delta"      # Secondary target: change in delay to next stop (min)
        ],
        "dynamic_delay_features": [
            "current_delay",             # Delay at current station (min)
            "prev_station_delay",        # Lag 1 delay (min)
            "prev_delay_2",              # Lag 2 delay (min)
            "prev_delay_3",              # Lag 3 delay (min)
            "delay_change",              # Delay delta over 1 station (min)
            "delay_change_2_stations",   # Delay delta over 2 stations (min)
            "delay_change_3_stations"    # Delay delta over 3 stations (min)
        ],
        "journey_progress_features": [
            "current_station_seq",       # Stop index along route (1..N)
            "stations_remaining",        # Number of remaining stops
            "dist_from_origin",          # Kilometers traveled from origin
            "remaining_dist",            # Kilometers remaining to destination
            "journey_progress",          # Normalized progress (0.0 to 1.0)
            "route_total_distance",      # Total route length (km)
            "route_total_stations"       # Total planned stops
        ],
        "scheduled_operational_features": [
            "scheduled_dwell_time",         # Planned stoppage duration (min)
            "sched_section_distance",       # Planned distance to next station (km)
            "sched_section_travel_time",    # Planned run time to next station (min)
            "sched_planned_speed",          # Planned speed to next station (km/h)
            "arr_min",                      # Scheduled arrival (min from midnight)
            "dep_min",                      # Scheduled departure (min from midnight)
            "arrival_day",                  # Journey day of arrival (1..4)
            "departure_day"                 # Journey day of departure (1..4)
        ],
        "temporal_features": [
            "scheduled_hour",            # Hour of scheduled run (0..23)
            "day_of_week",               # 0 (Monday) to 6 (Sunday)
            "month",                     # 1 to 12
            "day",                       # 1 to 31
            "is_weekend"                 # 1 if Sat/Sun, else 0
        ],
        "network_and_metadata_features": [
            "type_code",                 # Train priority classification (SF, PRM, EXP, etc.)
            "station_zone",              # Railway zone of current station
            "next_station_name",         # Station code of next station
            "next_station_zone"          # Railway zone of next station
        ],
        "diagnostics": [
            "delay",                     # Raw original delay (unmodified)
            "delay_clean",               # Sanitized delay
            "is_delay_missing",          # 1 if raw delay was null
            "is_delay_outlier",          # 1 if raw delay was outside [-120, 1440]
            "is_terminus_station"        # 1 if terminus station
        ]
    }
