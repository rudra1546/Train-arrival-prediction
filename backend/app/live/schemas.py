"""
Data schemas and normalized representations for Live Railway API integration.
Clearly categorizes fields into:
1. Provided by API (verified from official documentation)
2. Derived by our system (lag delays, station indices, delay deltas)
3. Unavailable from API (documented constraints)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


# -----------------------------------------------------------------------------
# Documentation of Feature Availability
# -----------------------------------------------------------------------------
UNAVAILABLE_FROM_API: List[str] = [
    "signal_block_aspect",          # Real-time signaling block aspect is internal railway telemetry
    "temporary_speed_restrictions",  # TSR (speed restrictions) are internal civil engineering orders
    "gradient_profile",             # Track slope / terrain gradient not provided in passenger status API
    "weather_telemetry_micro",      # Micro-climate weather sensors along track sections
    "rolling_stock_health",         # Locomotive / rake telemetry / sensor diagnostics
]


@dataclass
class NormalizedTrainState:
    """
    Normalized state of a running train extracted from the live tracking provider.
    
    Fields are explicitly partitioned:
    - [API] Directly supplied by the external provider (e.g. RailRadar)
    - [DERIVED] Reconstructed or computed by our preprocessing / topological engine
    """
    # --- Fields Provided by API ---
    train_no: str                        # 5-digit train identifier
    current_station: str                 # Current or last-passed station code (e.g. "CNB")
    current_delay_minutes: float         # Current delay at reference point in minutes
    journey_date: str                    # Journey commencement date (YYYY-MM-DD)
    status_timestamp: Optional[str] = None  # Timestamp of the status update from GPS/NTES
    latitude: Optional[float] = None     # GPS latitude if supplied by tracking unit
    longitude: Optional[float] = None    # GPS longitude if supplied by tracking unit
    current_status: Optional[str] = None # Status string: "departed", "arrived", "running", etc.
    train_name: Optional[str] = None     # Train commercial name (e.g. "KOLKATA RAJDHANI")
    current_station_name: Optional[str] = None # Station full name (e.g. "Kanpur Central")
    source: str = "railradar_live"       # Data provenance: "railradar_live" or "railradar_mock"

    # --- Fields Derived by Our System ---
    station_sequence: Optional[int] = None       # Index along scheduled timetable route
    prev_station_delay: Optional[float] = None   # Delay at immediately preceding traversed station
    prev_delay_2: Optional[float] = None         # Delay 2 stations prior
    prev_delay_3: Optional[float] = None         # Delay 3 stations prior
    delay_change: Optional[float] = None         # current_delay - prev_station_delay
    delay_change_2_stations: Optional[float] = None # current_delay - prev_delay_2
    delay_change_3_stations: Optional[float] = None # current_delay - prev_delay_3
    stops_remaining: Optional[int] = None        # Remaining halts to destination
    is_mock: bool = False                        # Flag indicating synthetic development data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_feature_dict(self) -> Dict[str, Any]:
        """
        Extract features dictionary formatted for MultiHorizonETAPredictor ingestion.
        """
        feats = {
            "current_delay": float(self.current_delay_minutes),
        }
        if self.prev_station_delay is not None:
            feats["prev_station_delay"] = float(self.prev_station_delay)
        if self.prev_delay_2 is not None:
            feats["prev_delay_2"] = float(self.prev_delay_2)
        if self.prev_delay_3 is not None:
            feats["prev_delay_3"] = float(self.prev_delay_3)
        if self.delay_change is not None:
            feats["delay_change"] = float(self.delay_change)
        if self.delay_change_2_stations is not None:
            feats["delay_change_2_stations"] = float(self.delay_change_2_stations)
        if self.delay_change_3_stations is not None:
            feats["delay_change_3_stations"] = float(self.delay_change_3_stations)
        return feats


@dataclass
class LiveHorizonETA:
    """Individual horizon ETA prediction returned by the live service."""
    horizon: int
    station_code: str
    station_sequence: int
    scheduled_arrival: str
    predicted_delay_minutes: float
    predicted_eta: str
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LiveTrainETAResponse:
    """
    Standard unified response schema for the live and demo ETA endpoints.
    """
    status: str                          # "success", "live_api_not_configured", "error"
    train_no: str
    journey_date: str
    current_station: str
    current_delay_minutes: float
    data_source: str                     # e.g. "RAILRADAR LIVE API" or "MOCK DATA — NOT LIVE RAILWAY DATA"
    is_demo: bool                        # True if returned from mock/demo provider
    predictions: List[LiveHorizonETA] = field(default_factory=list)
    message: Optional[str] = None
    derived_lags: Optional[Dict[str, Optional[float]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# -----------------------------------------------------------------------------
# FastAPI Unified Clean Response Schema
# -----------------------------------------------------------------------------

@dataclass
class CurrentStationPayload:
    code: str
    name: str
    delay_minutes: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HorizonPredictionPayload:
    horizon: int
    station: str
    scheduled_arrival: str
    predicted_delay_minutes: float
    predicted_eta: str

    @property
    def station_code(self) -> str:
        return self.station

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horizon": self.horizon,
            "station": self.station,
            "scheduled_arrival": self.scheduled_arrival,
            "predicted_delay_minutes": self.predicted_delay_minutes,
            "predicted_eta": self.predicted_eta
        }


@dataclass
class FastAPITrainETAResponse:
    """
    Clean unified JSON response format matching SIH 26028 specification.
    """
    success: bool
    train_no: str
    train_name: str
    status: str
    journey_date: str
    current_station: CurrentStationPayload
    predictions: List[HorizonPredictionPayload]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "train_no": self.train_no,
            "train_name": self.train_name,
            "status": self.status,
            "journey_date": self.journey_date,
            "current_station": self.current_station.to_dict(),
            "predictions": [p.to_dict() for p in self.predictions]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
