"""
Configuration and constants for SIH 26028 ETA Prediction Pipeline.
"""

import os
from pathlib import Path

# Base directories
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if (_REPO_ROOT / "data").exists():
    BASE_DIR = _REPO_ROOT
elif (Path.cwd().parent / "data").exists():
    BASE_DIR = Path.cwd().parent
elif (Path.cwd() / "data").exists():
    BASE_DIR = Path.cwd()
else:
    BASE_DIR = _REPO_ROOT

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "backend" / "models"

# Ensure directories exist
for path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, MODELS_DIR]:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def resolve_search_db_path() -> Path:
    """
    Resolve the deployment-safe SQLite timetable database path.
    Supports:
    - RAILWAY_SEARCH_DB environment variable override.
    - Repository root relative to backend code: backend/ml/utils/config.py -> 4 parents up -> data/processed/railway_search.db
    - Parent of current working directory (e.g. Render with Root Directory = backend)
    - Current working directory (when CWD is repo root)
    - PROCESSED_DATA_DIR
    """
    env_override = os.getenv("RAILWAY_SEARCH_DB", "").strip()
    if env_override:
        return Path(env_override).resolve()

    candidate = (_REPO_ROOT / "data" / "processed" / "railway_search.db").resolve()
    if candidate.exists():
        return candidate

    candidate = (Path.cwd().parent / "data" / "processed" / "railway_search.db").resolve()
    if candidate.exists():
        return candidate

    candidate = (Path.cwd() / "data" / "processed" / "railway_search.db").resolve()
    if candidate.exists():
        return candidate

    return (PROCESSED_DATA_DIR / "railway_search.db").resolve()


SEARCH_DB_PATH = resolve_search_db_path()

# Raw file paths
DELAY_FILE = RAW_DATA_DIR / "combined_delay.csv"
SCHEDULE_FILE = RAW_DATA_DIR / "combined_schedule.csv"
TRAIN_DETAILS_FILE = RAW_DATA_DIR / "train_details.csv"
STATION_NAMES_FILE = RAW_DATA_DIR / "station_full_names.csv"

# Preprocessing thresholds
# Indian Railways operational delays: early arrivals up to -120 min (2 hrs slack buffer)
# Extreme delays: delays exceeding 1440 min (24 hrs) are flagged as extreme/anomalous
MIN_VALID_DELAY = -120
MAX_VALID_DELAY = 1440

# Train Type Specificity / Priority Hierarchy (lower number = higher operational specificity)
TRAIN_TYPE_PRIORITY = {
    "T18-TRAINS": 1,   # Vande Bharat Express (Train 18)
    "RAJ-TRAINS": 2,   # Rajdhani Express
    "SHT-TRAINS": 3,   # Shatabdi / Gatimaan Express
    "GRB-TRAINS": 4,   # Garib Rath Express
    "PRM-TRAINS": 5,   # Premium / Suvidha Special
    "SF-TRAINS": 6,    # Superfast Express
    "EXP-TRAINS": 7,   # Mail / Express
    "PASS-TRAINS": 8   # Ordinary Passenger / DEMU / MEMU
}

# Missing station codes known in 2025/2026 data not in older master
KNOWN_STATION_ZONES = {
    "BSBS": "NER",  # Banaras (formerly Manduadih)
    "KCVL": "SR",   # Kochuveli (Thiruvananthapuram)
    "BARS": "ECR",  # Barsoi junction
    "RJIN": "NR",   # Rajpura
    "CLC": "ECR",   # Chaura Halt
    "MLYC": "SCR",  # Moula Ali C Cabin
    "BPHI": "NCR",  # Bahedi
    "KCCN": "SR",   # Kachcheguda
    "BNDE": "NCR",  # Banda
    "BADR": "NR"    # Badarpur
}
