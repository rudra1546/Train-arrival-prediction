"""
Exceptions for Live Railway API Integration (RailRadar).
Defines clear domain errors for configuration, network, parsing, and data validation.
"""

from typing import Optional


class LiveAPIError(Exception):
    """Base exception for all live API integration errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class APIKeyMissingError(LiveAPIError):
    """Raised when an attempt to use live API is made without a configured API key."""
    def __init__(self, message: str = "RailRadar API key has not been configured in the environment."):
        super().__init__(message, status_code=503)


class APIAuthenticationError(LiveAPIError):
    """Raised when the API returns 401 Unauthorized or 403 Forbidden."""
    def __init__(self, message: str = "Invalid or expired RailRadar API credentials."):
        super().__init__(message, status_code=401)


class APITimeoutError(LiveAPIError):
    """Raised when a request to the live API times out."""
    def __init__(self, timeout_seconds: float):
        super().__init__(
            f"RailRadar API request timed out after {timeout_seconds:.1f}s.",
            status_code=504
        )
        self.timeout_seconds = timeout_seconds


class APIResponseMalformedError(LiveAPIError):
    """Raised when the live API response JSON does not conform to the expected schema."""
    def __init__(self, details: str):
        super().__init__(f"Malformed RailRadar API response: {details}", status_code=502)
        self.details = details


class TrainNotFoundError(LiveAPIError):
    """Raised when the specified train number is not found by the API."""
    def __init__(self, train_no: str):
        super().__init__(f"Train '{train_no}' not found in live tracking system.", status_code=404)
        self.train_no = train_no


class TrainNotRunningError(LiveAPIError):
    """Raised when the train is not running on the specified date or has already terminated."""
    def __init__(self, train_no: str, journey_date: str, details: str = ""):
        msg = f"Train '{train_no}' is not currently running for date '{journey_date}'."
        if details:
            msg += f" ({details})"
        super().__init__(msg, status_code=422)
        self.train_no = train_no
        self.journey_date = journey_date


class LiveInferenceError(LiveAPIError):
    """Raised when inference fails on normalized live train data."""
    def __init__(self, details: str):
        super().__init__(f"Failed to run inference on live train data: {details}", status_code=500)
