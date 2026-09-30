"""
Inference module for SIH 26028 Dynamic ETA Prediction Service.
Exposes schemas, model loader, ETA calculation utilities, and the core MultiHorizonETAPredictor.
"""

from ml.inference.schemas import (
    PredictionRequest,
    HorizonPrediction,
    MultiHorizonResponse,
    InferenceError,
    UnknownTrainError,
    UnknownStationError,
    StationNotOnRouteError,
    InsufficientRouteRemainingError,
    InvalidJourneyDateError,
    FeatureValidationError,
    ModelLoadError
)
from ml.inference.model_loader import MultiHorizonModelLoader
from ml.inference.eta_calculator import (
    parse_journey_date,
    compute_scheduled_arrival,
    compute_predicted_eta,
    calculate_station_eta,
    format_timestamp
)
from ml.inference.predictor import MultiHorizonETAPredictor

__all__ = [
    "PredictionRequest",
    "HorizonPrediction",
    "MultiHorizonResponse",
    "InferenceError",
    "UnknownTrainError",
    "UnknownStationError",
    "StationNotOnRouteError",
    "InsufficientRouteRemainingError",
    "InvalidJourneyDateError",
    "FeatureValidationError",
    "ModelLoadError",
    "MultiHorizonModelLoader",
    "MultiHorizonETAPredictor",
    "parse_journey_date",
    "compute_scheduled_arrival",
    "compute_predicted_eta",
    "calculate_station_eta",
    "format_timestamp"
]
