"""
Builder script to generate lightweight, indexed SQLite database for railway route and station search.
Processes ~1 GB raw CSV files into an indexed ~15 MB SQLite database:
- stations (code PRIMARY KEY, name, zone)
- trains (train_no PRIMARY KEY, train_name, type_code, type_label, origin_code, origin_name, dest_code, dest_name, total_stops)
- schedules (train_no, station_no, station_code, arrival_time, departure_time, distance, PRIMARY KEY(train_no, station_no))
- Indexes on (station_code, train_no, station_no) and (code, name) for sub-millisecond route search.
"""

import os
import sys
import time
import sqlite3
from pathlib import Path

# Add backend directory to sys.path if not present
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.utils.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    SCHEDULE_FILE,
    TRAIN_DETAILS_FILE,
    STATION_NAMES_FILE
)


def format_train_type(type_code: str) -> str:
    norm = (type_code or "").upper().strip()
    if "RAJ" in norm:
        return "Rajdhani Express"
    if "SHT" in norm:
        return "Shatabdi Express"
    if "T18" in norm or "VB" in norm:
        return "Vande Bharat Express"
    if "GRB" in norm:
        return "Garib Rath"
    if "PRM" in norm or "SPL" in norm:
        return "Special Express"
    if "SF" in norm:
        return "Superfast Express"
    if "EXP" in norm:
        return "Mail / Express"
    if "PASS" in norm:
        return "Passenger Service"
    return type_code or "Express"


def build_search_db(db_path: Path = None) -> Path:
    if db_path is None:
        db_path = PROCESSED_DATA_DIR / "railway_search.db"

    print(f"Building railway search DB at: {db_path}...")
    t0 = time.time()

    # Ensure parent dir exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Use temporary file to allow atomic overwrite
    tmp_path = db_path.with_suffix(".tmp.db")
    if tmp_path.exists():
        tmp_path.unlink()

    conn = sqlite3.connect(tmp_path)
    cur = conn.cursor()

    cur.execute("PRAGMA journal_mode = OFF")
    cur.execute("PRAGMA synchronous = OFF")

    # 1. Create tables
    cur.execute("""
    CREATE TABLE stations (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        zone TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE trains (
        train_no TEXT PRIMARY KEY,
        train_name TEXT NOT NULL,
        type_code TEXT,
        type_label TEXT,
        origin_code TEXT,
        origin_name TEXT,
        dest_code TEXT,
        dest_name TEXT,
        total_stops INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE schedules (
        train_no TEXT NOT NULL,
        station_no INTEGER NOT NULL,
        station_code TEXT NOT NULL,
        arrival_time TEXT,
        departure_time TEXT,
        distance INTEGER,
        PRIMARY KEY (train_no, station_no)
    )
    """)

    # 2. Populate stations
    print("Loading station names...")
    import polars as pl
    stn_df = pl.read_csv(STATION_NAMES_FILE)
    stn_records = []
    for row in stn_df.iter_rows(named=True):
        code = str(row.get("station_code") or "").strip().upper()
        name = str(row.get("station_name") or "").strip()
        zone = str(row.get("zone") or "").strip()
        if code:
            stn_records.append((code, name or code, zone or None))

    cur.executemany("INSERT OR IGNORE INTO stations (code, name, zone) VALUES (?, ?, ?)", stn_records)
    print(f"Loaded {len(stn_records)} stations.")

    # 3. Populate train details
    print("Loading train details...")
    td_df = pl.read_csv(TRAIN_DETAILS_FILE)
    train_records = []
    for row in td_df.iter_rows(named=True):
        t_no = str(row.get("train_no") or "").strip()
        t_name = str(row.get("train_name") or "").strip()
        t_type = str(row.get("train_type") or "").strip()
        orig_code = str(row.get("source_station_code") or "").strip().upper()
        orig_name = str(row.get("source_station_name") or "").strip()
        dest_code = str(row.get("destination_station_code") or "").strip().upper()
        dest_name = str(row.get("destination_station_name") or "").strip()
        stops = row.get("total_stops") or 0

        type_label = format_train_type(t_type)
        if t_no:
            train_records.append((
                t_no,
                t_name or f"Train {t_no}",
                t_type,
                type_label,
                orig_code or None,
                orig_name or orig_code or None,
                dest_code or None,
                dest_name or dest_code or None,
                int(stops)
            ))

    cur.executemany("""
    INSERT OR REPLACE INTO trains 
    (train_no, train_name, type_code, type_label, origin_code, origin_name, dest_code, dest_name, total_stops)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, train_records)
    print(f"Loaded {len(train_records)} trains.")

    # 4. Populate schedules
    print("Loading schedule routes...")
    sched_df = pl.read_csv(
        SCHEDULE_FILE,
        columns=["train_no", "station_no", "station_name", "distance_from_origin", "arrival_time", "departure_time"]
    )
    sched_records = []
    missing_stations = set()
    for row in sched_df.iter_rows(named=True):
        t_no = str(row.get("train_no") or "").strip()
        s_no = int(row.get("station_no") or 0)
        s_code = str(row.get("station_name") or "").strip().upper()
        arr = str(row.get("arrival_time") or "").strip() or None
        dep = str(row.get("departure_time") or "").strip() or None
        dist = int(round(float(row.get("distance_from_origin") or 0)))

        if t_no and s_code:
            sched_records.append((t_no, s_no, s_code, arr, dep, dist))
            missing_stations.add(s_code)

    cur.executemany("""
    INSERT OR REPLACE INTO schedules (train_no, station_no, station_code, arrival_time, departure_time, distance)
    VALUES (?, ?, ?, ?, ?, ?)
    """, sched_records)
    print(f"Loaded {len(sched_records)} schedule stops.")

    # Ensure any missing stations in schedule exist in stations table
    cur.executemany(
        "INSERT OR IGNORE INTO stations (code, name, zone) VALUES (?, ?, NULL)",
        [(code, code) for code in missing_stations]
    )

    # 5. Create Search Indexes
    print("Creating search indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sched_station ON schedules(station_code, train_no, station_no)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sched_train ON schedules(train_no, station_no)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_station_code ON stations(code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_station_name ON stations(name)")

    conn.commit()
    conn.close()

    if db_path.exists():
        db_path.unlink()
    tmp_path.rename(db_path)

    elapsed = time.time() - t0
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"Done in {elapsed:.2f}s! DB size: {size_mb:.2f} MB")
    return db_path


if __name__ == "__main__":
    build_search_db()
