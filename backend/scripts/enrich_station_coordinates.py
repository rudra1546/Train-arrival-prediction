"""
Enrich railway_search.db with authentic Indian Railways station coordinates
from the open-source datameet/railways geospatial dataset.
Stores both:
1. data/processed/station_coordinates.json (static lookup)
2. stations.latitude and stations.longitude in data/processed/railway_search.db
"""

import os
import sys
import json
import sqlite3
import urllib.request
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.utils.config import PROCESSED_DATA_DIR

STATIONS_GEOJSON_URL = "https://raw.githubusercontent.com/datameet/railways/master/stations.json"
CACHE_JSON_PATH = PROCESSED_DATA_DIR / "station_coordinates.json"
DB_PATH = PROCESSED_DATA_DIR / "railway_search.db"


def fetch_or_load_coordinates() -> dict:
    if CACHE_JSON_PATH.exists():
        print(f"Loading cached station coordinates from {CACHE_JSON_PATH}...")
        with open(CACHE_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"Fetching station coordinates from {STATIONS_GEOJSON_URL}...")
    req = urllib.request.Request(STATIONS_GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    coords_map = {}
    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        code = (props.get("code") or "").strip().upper()
        geom = feat.get("geometry")
        if geom and isinstance(geom, dict):
            coords = geom.get("coordinates") or []
            if code and len(coords) >= 2:
                lon = float(coords[0])
                lat = float(coords[1])
                coords_map[code] = [lat, lon]

    # Save cache
    with open(CACHE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(coords_map, f)
    print(f"Saved {len(coords_map)} station coordinates to {CACHE_JSON_PATH}")
    return coords_map


def update_database(coords_map: dict):
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check if columns exist
    cur.execute("PRAGMA table_info(stations)")
    cols = [r[1] for r in cur.fetchall()]
    if "latitude" not in cols:
        print("Adding column 'latitude' to stations table...")
        cur.execute("ALTER TABLE stations ADD COLUMN latitude REAL")
    if "longitude" not in cols:
        print("Adding column 'longitude' to stations table...")
        cur.execute("ALTER TABLE stations ADD COLUMN longitude REAL")

    # Update station coordinates
    updates = []
    for code, (lat, lon) in coords_map.items():
        updates.append((lat, lon, code))

    cur.executemany("UPDATE stations SET latitude = ?, longitude = ? WHERE code = ?", updates)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM stations WHERE latitude IS NOT NULL")
    matched = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM stations")
    total = cur.fetchone()[0]
    print(f"Updated {matched} / {total} stations with coordinates in {DB_PATH} ({matched/total*100:.1f}%)")

    # Check index
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stations_coords ON stations(code) WHERE latitude IS NOT NULL")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    coords = fetch_or_load_coordinates()
    update_database(coords)
