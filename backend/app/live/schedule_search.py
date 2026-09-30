"""
Schedule search module for Indian Railways timetable database.
Provides fast indexed queries for:
- Station autocomplete / lookup against 8,963 master stations
- Direct route search finding trains where origin occurs BEFORE destination
- Formatting results with departure, arrival, duration, stops, and train type
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from pydantic import BaseModel

from ml.utils.config import PROCESSED_DATA_DIR

logger = logging.getLogger("sih26028.search")

SEARCH_DB_PATH = Path(os.getenv("RAILWAY_SEARCH_DB", str(PROCESSED_DATA_DIR / "railway_search.db")))
COORDS_JSON_PATH = PROCESSED_DATA_DIR / "station_coordinates.json"

_COORDS_CACHE: Optional[Dict[str, List[float]]] = None


def get_station_coords_cache() -> Dict[str, List[float]]:
    global _COORDS_CACHE
    if _COORDS_CACHE is None:
        if COORDS_JSON_PATH.exists():
            try:
                with open(COORDS_JSON_PATH, "r", encoding="utf-8") as f:
                    _COORDS_CACHE = json.load(f)
            except Exception as e:
                logger.warning("Could not load station_coordinates.json: %s", e)
                _COORDS_CACHE = {}
        else:
            _COORDS_CACHE = {}
    return _COORDS_CACHE


class StationSearchResult(BaseModel):
    code: str
    name: str
    zone: Optional[str] = None


class TrainSearchResult(BaseModel):
    train_no: str
    train_name: str
    type_code: str
    type_label: str
    train_type: str
    origin: str
    destination: str
    origin_station: str
    destination_station: str
    from_station: str
    from_station_name: str
    to_station: str
    to_station_name: str
    departure_time: str
    arrival_time: str
    duration: Optional[str] = None
    stops: int
    distance_km: Optional[int] = None
    total_stops: Optional[int] = None


class TrainSearchResponse(BaseModel):
    success: bool = True
    count: int
    from_station: StationSearchResult
    to_station: StationSearchResult
    journey_date: Optional[str] = None
    trains: List[TrainSearchResult]


class RouteStop(BaseModel):
    station_no: int
    station_code: str
    station_name: str
    arrival_time: str
    departure_time: str
    distance: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TrainRouteScheduleResponse(BaseModel):
    train_no: str
    train_name: str
    origin_code: Optional[str] = None
    origin_name: Optional[str] = None
    dest_code: Optional[str] = None
    dest_name: Optional[str] = None
    total_stops: int
    stops: List[RouteStop]


def get_db_connection() -> sqlite3.Connection:
    """
    Get a read-only SQLite connection to the railway search database.
    Verifies that the database exists before connecting.
    """
    if not SEARCH_DB_PATH.exists():
        logger.warning("Search database not found at %s. Attempting to build...", SEARCH_DB_PATH)
        from scripts.build_railway_search_db import build_search_db
        build_search_db(SEARCH_DB_PATH)

    uri = f"file:{SEARCH_DB_PATH.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def compute_duration(dep_time: Optional[str], arr_time: Optional[str]) -> str:
    """Compute journey duration string from 'HH:MM' departure and arrival times."""
    if not dep_time or not arr_time or ":" not in dep_time or ":" not in arr_time:
        return ""
    try:
        dep_h, dep_m = map(int, dep_time.split(":")[:2])
        arr_h, arr_m = map(int, arr_time.split(":")[:2])
        diff_m = (arr_h * 60 + arr_m) - (dep_h * 60 + dep_m)
        if diff_m < 0:
            diff_m += 24 * 60  # Crosses midnight
        hours = diff_m // 60
        mins = diff_m % 60
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0:
            parts.append(f"{mins}m")
        return " ".join(parts) if parts else "0m"
    except Exception:
        return ""


def resolve_station(input_val: str, conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """
    Resolve user input (station code or name) to a canonical station record.
    Returns dict with keys: 'code', 'name', 'zone'.
    """
    clean = input_val.strip()
    if not clean:
        return None

    cur = conn.cursor()

    # 1. Exact station code match
    cur.execute(
        "SELECT code, name, zone FROM stations WHERE UPPER(code) = UPPER(?) LIMIT 1",
        (clean,)
    )
    row = cur.fetchone()
    if row:
        return {"code": row["code"], "name": row["name"], "zone": row["zone"]}

    # 2. Exact station name match
    cur.execute(
        "SELECT code, name, zone FROM stations WHERE UPPER(name) = UPPER(?) LIMIT 1",
        (clean,)
    )
    row = cur.fetchone()
    if row:
        return {"code": row["code"], "name": row["name"], "zone": row["zone"]}

    # 3. Code prefix match
    cur.execute(
        "SELECT code, name, zone FROM stations WHERE UPPER(code) LIKE UPPER(?) ORDER BY code ASC LIMIT 1",
        (f"{clean}%",)
    )
    row = cur.fetchone()
    if row:
        return {"code": row["code"], "name": row["name"], "zone": row["zone"]}

    # 4. Name prefix match
    cur.execute(
        "SELECT code, name, zone FROM stations WHERE UPPER(name) LIKE UPPER(?) ORDER BY name ASC LIMIT 1",
        (f"{clean}%",)
    )
    row = cur.fetchone()
    if row:
        return {"code": row["code"], "name": row["name"], "zone": row["zone"]}

    # 5. Name substring match
    cur.execute(
        "SELECT code, name, zone FROM stations WHERE UPPER(name) LIKE UPPER(?) ORDER BY name ASC LIMIT 1",
        (f"%{clean}%",)
    )
    row = cur.fetchone()
    if row:
        return {"code": row["code"], "name": row["name"], "zone": row["zone"]}

    return None


def search_stations(query: str, limit: int = 10) -> List[StationSearchResult]:
    """
    Autocomplete / search stations by station code or city/station name.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        clean = query.strip()
        clamped_limit = max(1, min(limit, 50))

        if not clean:
            # Default popular junction stations
            popular_codes = ("NDLS", "HWH", "MMCT", "CSMT", "MAS", "SBC", "ADI", "CNB", "BPL", "PNBE")
            placeholders = ",".join("?" for _ in popular_codes)
            cur.execute(
                f"SELECT code, name, zone FROM stations WHERE code IN ({placeholders}) ORDER BY name ASC LIMIT ?",
                (*popular_codes, clamped_limit)
            )
            rows = cur.fetchall()
        else:
            pat = f"%{clean}%"
            prefix = f"{clean}%"
            cur.execute(
                """
                SELECT code, name, zone
                FROM stations
                WHERE UPPER(code) LIKE UPPER(?) OR UPPER(name) LIKE UPPER(?)
                ORDER BY 
                  CASE 
                    WHEN UPPER(code) = UPPER(?) THEN 0
                    WHEN UPPER(code) LIKE UPPER(?) THEN 1
                    WHEN UPPER(name) LIKE UPPER(?) THEN 2
                    ELSE 3
                  END,
                  name ASC
                LIMIT ?
                """,
                (pat, pat, clean, prefix, prefix, clamped_limit)
            )
            rows = cur.fetchall()

        return [
            StationSearchResult(
                code=row["code"],
                name=row["name"],
                zone=row["zone"]
            )
            for row in rows
        ]
    finally:
        conn.close()


def search_train_routes(
    from_input: str,
    to_input: str,
    journey_date: Optional[str] = None
) -> TrainSearchResponse:
    """
    Search real railway schedules for trains connecting origin and destination.
    Guarantees:
    - Origin occurs BEFORE destination along the train's route (s1.station_no < s2.station_no).
    - Validates station parameters and journey date format.
    - Returns structured information for frontend result cards.
    """
    clean_from = (from_input or "").strip()
    clean_to = (to_input or "").strip()

    # 1. Parameter presence validation
    if not clean_from or not clean_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'from' (origin) and 'to' (destination) station parameters are required."
        )

    # 2. Date validation (if supplied)
    normalized_date: Optional[str] = None
    if journey_date:
        clean_date = journey_date.strip()
        if clean_date:
            try:
                dt = datetime.strptime(clean_date, "%Y-%m-%d")
                normalized_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid journey date format '{clean_date}'. Expected format YYYY-MM-DD."
                )

    conn = get_db_connection()
    try:
        # 3. Resolve Origin station
        origin_meta = resolve_station(clean_from, conn)
        if not origin_meta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Origin station '{clean_from}' not found in railway master records."
            )

        # 4. Resolve Destination station
        dest_meta = resolve_station(clean_to, conn)
        if not dest_meta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Destination station '{clean_to}' not found in railway master records."
            )

        # 5. Same station validation
        if origin_meta["code"] == dest_meta["code"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Origin and destination stations cannot be identical."
            )

        # 6. Execute topological route search
        # CRITICAL: s1.station_no < s2.station_no enforces that origin occurs BEFORE destination
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                t.train_no,
                t.train_name,
                t.type_code,
                t.type_label,
                t.origin_code,
                t.origin_name,
                t.dest_code,
                t.dest_name,
                s1.station_code AS from_code,
                st1.name AS from_name,
                s1.departure_time,
                s1.station_no AS from_seq,
                s2.station_code AS to_code,
                st2.name AS to_name,
                s2.arrival_time,
                s2.station_no AS to_seq,
                (s2.distance - s1.distance) AS distance_km,
                (s2.station_no - s1.station_no) AS stops_between,
                t.total_stops
            FROM schedules s1
            JOIN schedules s2 ON s1.train_no = s2.train_no
            JOIN trains t ON t.train_no = s1.train_no
            JOIN stations st1 ON st1.code = s1.station_code
            JOIN stations st2 ON st2.code = s2.station_code
            WHERE s1.station_code = ? 
              AND s2.station_code = ? 
              AND s1.station_no < s2.station_no
            ORDER BY 
              CASE 
                WHEN t.type_code LIKE '%RAJ%' THEN 1
                WHEN t.type_code LIKE '%SHT%' THEN 2
                WHEN t.type_code LIKE '%T18%' OR t.type_code LIKE '%VB%' THEN 3
                WHEN t.type_code LIKE '%PRM%' OR t.type_code LIKE '%SPL%' THEN 4
                WHEN t.type_code LIKE '%SF%' THEN 5
                ELSE 6
              END,
              s1.departure_time ASC
            """,
            (origin_meta["code"], dest_meta["code"])
        )

        rows = cur.fetchall()
        results: List[TrainSearchResult] = []

        for r in rows:
            dep_time = r["departure_time"] or "--:--"
            arr_time = r["arrival_time"] or "--:--"
            duration_str = compute_duration(dep_time, arr_time)
            
            origin_terminal = f"{r['origin_name']} ({r['origin_code']})" if r["origin_code"] else (r["origin_name"] or "Unknown")
            dest_terminal = f"{r['dest_name']} ({r['dest_code']})" if r["dest_code"] else (r["dest_name"] or "Unknown")

            results.append(
                TrainSearchResult(
                    train_no=r["train_no"],
                    train_name=r["train_name"],
                    type_code=r["type_code"] or "EXP",
                    type_label=r["type_label"] or "Express",
                    train_type=r["type_label"] or "Express",
                    origin=origin_terminal,
                    destination=dest_terminal,
                    origin_station=origin_terminal,
                    destination_station=dest_terminal,
                    from_station=r["from_code"],
                    from_station_name=r["from_name"],
                    to_station=r["to_code"],
                    to_station_name=r["to_name"],
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    duration=duration_str,
                    stops=r["stops_between"],
                    distance_km=r["distance_km"],
                    total_stops=r["total_stops"]
                )
            )

        return TrainSearchResponse(
            success=True,
            count=len(results),
            from_station=StationSearchResult(
                code=origin_meta["code"],
                name=origin_meta["name"],
                zone=origin_meta["zone"]
            ),
            to_station=StationSearchResult(
                code=dest_meta["code"],
                name=dest_meta["name"],
                zone=dest_meta["zone"]
            ),
            journey_date=normalized_date,
            trains=results
        )

    finally:
        conn.close()


def get_train_route_schedule(train_no: str) -> Optional[TrainRouteScheduleResponse]:
    """
    Look up all real scheduled stops for a train from origin to terminus.
    """
    clean_no = str(train_no).strip()
    if not clean_no:
        return None

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT train_no, train_name, origin_code, origin_name, dest_code, dest_name, total_stops
            FROM trains
            WHERE train_no = ?
            """,
            (clean_no,)
        )
        t_row = cur.fetchone()
        if not t_row:
            return None

        cur.execute(
            """
            SELECT s.station_no, s.station_code, st.name AS station_name, s.arrival_time, s.departure_time, s.distance,
                   st.latitude, st.longitude
            FROM schedules s
            LEFT JOIN stations st ON st.code = s.station_code
            WHERE s.train_no = ?
            ORDER BY s.station_no ASC
            """,
            (clean_no,)
        )
        rows = cur.fetchall()
        coords_cache = get_station_coords_cache()
        stops = []
        for r in rows:
            lat = r["latitude"]
            lon = r["longitude"]
            code = (r["station_code"] or "").upper()
            if (lat is None or lon is None) and code in coords_cache:
                cached = coords_cache[code]
                if len(cached) >= 2:
                    lat, lon = cached[0], cached[1]

            stops.append(
                RouteStop(
                    station_no=r["station_no"],
                    station_code=r["station_code"],
                    station_name=r["station_name"] or r["station_code"],
                    arrival_time=r["arrival_time"] or "--:--",
                    departure_time=r["departure_time"] or "--:--",
                    distance=r["distance"] or 0,
                    latitude=lat,
                    longitude=lon
                )
            )

        return TrainRouteScheduleResponse(
            train_no=t_row["train_no"],
            train_name=t_row["train_name"],
            origin_code=t_row["origin_code"],
            origin_name=t_row["origin_name"],
            dest_code=t_row["dest_code"],
            dest_name=t_row["dest_name"],
            total_stops=t_row["total_stops"] or len(stops),
            stops=stops
        )
    finally:
        conn.close()


def get_station_coordinates(station_code: str) -> Optional[Dict[str, Any]]:
    """
    Look up real latitude & longitude coordinates for a railway station.
    Queries database first, falling back to static datameet cache.
    Returns None if coordinates are truly unavailable.
    """
    code = (station_code or "").strip().upper()
    if not code:
        return None

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT code, name, latitude, longitude FROM stations WHERE UPPER(code) = UPPER(?)",
            (code,)
        )
        row = cur.fetchone()
        if row and row["latitude"] is not None and row["longitude"] is not None:
            return {
                "code": row["code"],
                "name": row["name"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"])
            }

        cached = get_station_coords_cache().get(code)
        if cached and len(cached) >= 2:
            return {
                "code": code,
                "name": row["name"] if row else code,
                "latitude": float(cached[0]),
                "longitude": float(cached[1])
            }

        return None
    finally:
        conn.close()
