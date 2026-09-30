"""
Configuration and constants for SIH 26028 ETA Prediction Pipeline.
"""

from pathlib import Path

# Base directories
BASE_DIR = Path("e:/train")
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "backend" / "models"

# Ensure directories exist
for path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, MODELS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

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
