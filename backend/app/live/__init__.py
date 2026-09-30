"""
Live Railway API Integration Package for SIH 26028.
Handles live tracking provider integration (RailRadar), schema normalization,
deterministic mock development, and pipeline orchestration.
"""

from app.live.config import (
    get_api_key,
    is_live_configured,
    mask_secret,
    RAILRADAR_BASE_URL,
    RAILRADAR_TIMEOUT_SECONDS
)
from app.live.schemas import (
    NormalizedTrainState,
    LiveHorizonETA,
    LiveTrainETAResponse,
    UNAVAILABLE_FROM_API
)
from app.live.exceptions import (
    LiveAPIError,
    APIKeyMissingError,
    APIAuthenticationError,
    APITimeoutError,
    APIResponseMalformedError,
    TrainNotFoundError,
    TrainNotRunningError,
    LiveInferenceError
)
from app.live.response_parser import parse_railradar_response
from app.live.api_client import (
    BaseRailRadarClient,
    RailRadarLiveClient,
    MockRailRadarClient,
    MOCK_LABEL
)
from app.live.service import LiveETAService

__all__ = [
    "get_api_key",
    "is_live_configured",
    "mask_secret",
    "RAILRADAR_BASE_URL",
    "RAILRADAR_TIMEOUT_SECONDS",
    "NormalizedTrainState",
    "LiveHorizonETA",
    "LiveTrainETAResponse",
    "UNAVAILABLE_FROM_API",
    "LiveAPIError",
    "APIKeyMissingError",
    "APIAuthenticationError",
    "APITimeoutError",
    "APIResponseMalformedError",
    "TrainNotFoundError",
    "TrainNotRunningError",
    "LiveInferenceError",
    "parse_railradar_response",
    "BaseRailRadarClient",
    "RailRadarLiveClient",
    "MockRailRadarClient",
    "MOCK_LABEL",
    "LiveETAService"
]
