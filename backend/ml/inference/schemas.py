"""
Inference schemas and domain models for SIH 26028 Multi-Horizon ETA Prediction Service.
Defines strict dataclasses, validation types, and domain-specific exceptions.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


# -----------------------------------------------------------------------------
# Custom Domain Exceptions
# -----------------------------------------------------------------------------

class InferenceError(Exception):
    """Base exception for all inference errors."""
    pass


class UnknownTrainError(InferenceError):
    """Raised when the requested train number is not found in master timetable."""
    def __init__(self, train_no: str):
        super().__init__(f"Train '{train_no}' not found in master timetable schedule.")
        self.train_no = train_no


class UnknownStationError(InferenceError):
    """Raised when a station code is not found in railway master data."""
    def __init__(self, station_code: str):
        super().__init__(f"Station '{station_code}' not recognized in railway station master.")
        self.station_code = station_code


class StationNotOnRouteError(InferenceError):
    """Raised when the station exists, but does not lie on the train's scheduled itinerary."""
    def __init__(self, train_no: str, station_code: str):
        super().__init__(f"Station '{station_code}' is not on scheduled route for Train '{train_no}'.")
        self.train_no = train_no
        self.station_code = station_code


class InsufficientRouteRemainingError(InferenceError):
    """Raised when prediction is requested beyond the train terminus."""
    def __init__(self, train_no: str, current_station: str, stops_remaining: int, requested_horizon: int):
        super().__init__(
            f"Insufficient route remaining for Train '{train_no}' at '{current_station}'. "
            f"Stops remaining to terminus: {stops_remaining}, requested horizon: {requested_horizon}."
        )
        self.train_no = train_no
        self.current_station = current_station
        self.stops_remaining = stops_remaining
        self.requested_horizon = requested_horizon


class InvalidJourneyDateError(InferenceError):
    """Raised when the journey start date is malformed or invalid."""
    def __init__(self, date_str: str, reason: str = "Invalid format"):
        super().__init__(f"Invalid journey date '{date_str}': {reason}. Expected YYYY-MM-DD.")
        self.date_str = date_str


class FeatureValidationError(InferenceError):
    """Raised when required features are missing, non-numeric, or unencodable."""
    def __init__(self, details: str):
        super().__init__(f"Feature validation error: {details}")
        self.details = details


class ModelLoadError(InferenceError):
    """Raised when model weights or feature manifests fail to load."""
    def __init__(self, model_name: str, path: str, error_msg: str):
        super().__init__(f"Failed to load model '{model_name}' from '{path}': {error_msg}")
        self.model_name = model_name
        self.path = path


# -----------------------------------------------------------------------------
# Request & Response Dataclasses
# -----------------------------------------------------------------------------

@dataclass
class PredictionRequest:
    """Input payload for multi-horizon ETA prediction."""
    train_no: str
    journey_date: str
    current_station: str
    current_delay_minutes: float
    features: Optional[Dict[str, Any]] = None
    horizons: List[int] = field(default_factory=lambda: [1, 2, 3])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HorizonPrediction:
    """Individual prediction for a single future scheduled station."""
    horizon: int
    station: str
    station_sequence: int
    scheduled_arrival: str
    predicted_delay_minutes: float
    predicted_eta: str
    confidence: Optional[float] = None  # Strictly null per specification

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MultiHorizonResponse:
    """Output structure containing simultaneous predictions for up to 3 horizons."""
    train_no: str
    journey_date: str
    current_station: str
    current_delay_minutes: float
    predictions: List[HorizonPrediction]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
