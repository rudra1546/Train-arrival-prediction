"""
RailRadar API client module.
Provides:
- BaseRailRadarClient: Abstract interface
- RailRadarLiveClient: Real HTTP client with strict key gating and secret masking
- MockRailRadarClient: Deterministic synthetic mock provider for offline development
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests

from app.live.config import (
    get_api_key,
    is_live_configured,
    mask_secret,
    RAILRADAR_BASE_URL,
    RAILRADAR_TIMEOUT_SECONDS
)
from app.live.schemas import NormalizedTrainState
from app.live.response_parser import parse_railradar_response
from app.live.exceptions import (
    APIKeyMissingError,
    APIAuthenticationError,
    APITimeoutError,
    APIResponseMalformedError,
    TrainNotFoundError,
    TrainNotRunningError,
    LiveAPIError
)


MOCK_LABEL = "MOCK DATA — NOT LIVE RAILWAY DATA"


class BaseRailRadarClient(ABC):
    """Abstract base class for RailRadar API clients."""

    @abstractmethod
    def get_live_train_status(
        self,
        train_no: str,
        journey_date: Optional[str] = None
    ) -> NormalizedTrainState:
        """
        Fetch and return the normalized train running state.
        
        Parameters:
        -----------
        train_no : str
            Train number (e.g. '12301')
        journey_date : Optional[str]
            Journey commencement date (YYYY-MM-DD)
            
        Returns:
        --------
        NormalizedTrainState
        """
        pass


class RailRadarLiveClient(BaseRailRadarClient):
    """
    Live RailRadar API Client connecting to official RailRadar endpoints.
    Strictly gates execution:
    - If RAILRADAR_API_KEY is missing or empty, raises APIKeyMissingError immediately.
    - Never generates, invents, or guesses credentials.
    - Never prints or leaks credentials in exceptions or log messages.
    """

    def __init__(
        self,
        base_url: str = RAILRADAR_BASE_URL,
        timeout: float = RAILRADAR_TIMEOUT_SECONDS
    ):
        if not is_live_configured():
            raise APIKeyMissingError(
                "Cannot initialize RailRadarLiveClient: RAILRADAR_API_KEY environment variable is missing or empty. "
                "Configure a valid key in .env or environment to enable live API functionality."
            )
        self.api_key: str = get_api_key()  # type: ignore[assignment]
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "SIH-26028-ETA-Inference-Engine/1.0"
        })

    def get_live_train_status(
        self,
        train_no: str,
        journey_date: Optional[str] = None
    ) -> NormalizedTrainState:
        """
        Make authenticated HTTP GET request to RailRadar live status endpoint.
        URL: {base_url}/trains/{number}/live
        """
        if not is_live_configured():
            raise APIKeyMissingError("Live API request aborted: API key is not configured.")

        train_no_clean = str(train_no).strip().zfill(5)
        url = f"{self.base_url}/trains/{train_no_clean}/live"
        params: Dict[str, Any] = {
            "authoritative": "true",
            "haltsOnly": "true"
        }
        if journey_date:
            params["date"] = journey_date.strip()

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise APITimeoutError(self.timeout)
        except requests.exceptions.RequestException as e:
            # Mask any potential credential leak in exception string
            safe_msg = mask_secret(str(e))
            raise LiveAPIError(f"Network transport error calling RailRadar API: {safe_msg}")

        # Check HTTP Status Codes
        if resp.status_code == 401 or resp.status_code == 403:
            raise APIAuthenticationError(
                f"RailRadar authentication failed (HTTP {resp.status_code}). Verify configured API key."
            )
        elif resp.status_code == 404:
            raise TrainNotFoundError(train_no_clean)
        elif resp.status_code >= 500:
            raise LiveAPIError(
                f"RailRadar server error (HTTP {resp.status_code}): {resp.text[:200]}",
                status_code=resp.status_code
            )
        elif resp.status_code != 200:
            raise LiveAPIError(
                f"RailRadar returned unexpected status (HTTP {resp.status_code}): {resp.text[:200]}",
                status_code=resp.status_code
            )

        try:
            payload = resp.json()
        except Exception as e:
            raise APIResponseMalformedError(f"Failed to decode response as JSON: {e}")

        return parse_railradar_response(payload, is_mock=False)


# -----------------------------------------------------------------------------
# Mock Client for Offline Development & Reproducible Testing
# -----------------------------------------------------------------------------

MOCK_DATABASE: Dict[str, Dict[str, Any]] = {
    # Train 12301: Kolkata Rajdhani (HWH -> NDLS), currently at CNB
    "12301": {
        "status": "success",
        "data": {
            "trainNumber": "12301",
            "trainName": "KOLKATA RAJDHANI",
            "startDate": "2026-03-24",
            "delayMinutes": 15.0,
            "currentLocation": {
                "stationCode": "CNB",
                "stationName": "Kanpur Central",
                "latitude": 26.4537,
                "longitude": 80.3507,
                "speed": 92.0,
                "status": "departed",
                "distanceCovered": 1008,
                "updatedAt": "2026-03-25T05:10:00Z"
            },
            "route": [
                {"stationCode": "HWH", "stationName": "Howrah Junction", "distance": 0, "day": 1, "scheduleArrival": "16:50", "scheduleDeparture": "16:50", "actualArrival": "16:50", "actualDeparture": "16:50", "delayArrival": 0, "delayDeparture": 0, "status": "departed", "hasHalted": True},
                {"stationCode": "ASN", "stationName": "Asansol Junction", "distance": 200, "day": 1, "scheduleArrival": "18:47", "scheduleDeparture": "18:49", "actualArrival": "18:52", "actualDeparture": "18:54", "delayArrival": 5, "delayDeparture": 5, "status": "departed", "hasHalted": True},
                {"stationCode": "DHN", "stationName": "Dhanbad Junction", "distance": 259, "day": 1, "scheduleArrival": "19:55", "scheduleDeparture": "20:00", "actualArrival": "20:03", "actualDeparture": "20:08", "delayArrival": 8, "delayDeparture": 8, "status": "departed", "hasHalted": True},
                {"stationCode": "PNME", "stationName": "Parasnath", "distance": 306, "day": 1, "scheduleArrival": "20:30", "scheduleDeparture": "20:32", "actualArrival": "20:40", "actualDeparture": "20:42", "delayArrival": 10, "delayDeparture": 10, "status": "departed", "hasHalted": True},
                {"stationCode": "GAYA", "stationName": "Gaya Junction", "distance": 458, "day": 1, "scheduleArrival": "22:32", "scheduleDeparture": "22:35", "actualArrival": "22:44", "actualDeparture": "22:47", "delayArrival": 12, "delayDeparture": 12, "status": "departed", "hasHalted": True},
                {"stationCode": "DDU", "stationName": "Pt DD Upadhyaya Junction", "distance": 661, "day": 2, "scheduleArrival": "00:40", "scheduleDeparture": "00:50", "actualArrival": "00:54", "actualDeparture": "01:04", "delayArrival": 14, "delayDeparture": 14, "status": "departed", "hasHalted": True},
                {"stationCode": "PRYJ", "stationName": "Prayagraj Junction", "distance": 813, "day": 2, "scheduleArrival": "02:43", "scheduleDeparture": "02:45", "actualArrival": "02:58", "actualDeparture": "03:00", "delayArrival": 15, "delayDeparture": 15, "status": "departed", "hasHalted": True},
                {"stationCode": "CNB", "stationName": "Kanpur Central", "distance": 1008, "day": 2, "scheduleArrival": "04:50", "scheduleDeparture": "04:55", "actualArrival": "05:05", "actualDeparture": "05:10", "delayArrival": 15, "delayDeparture": 15, "status": "departed", "hasHalted": True},
                {"stationCode": "NDLS", "stationName": "New Delhi", "distance": 1449, "day": 2, "scheduleArrival": "10:05", "scheduleDeparture": "10:05", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False}
            ]
        }
    },
    # Train 12951: Mumbai Rajdhani (MMCT -> NDLS), currently at BRC
    "12951": {
        "status": "success",
        "data": {
            "trainNumber": "12951",
            "trainName": "MUMBAI TEJAS RAJDHANI",
            "startDate": "2026-03-24",
            "delayMinutes": 22.0,
            "currentLocation": {
                "stationCode": "BRC",
                "stationName": "Vadodara Junction",
                "latitude": 22.3106,
                "longitude": 73.1812,
                "speed": 80.0,
                "status": "departed",
                "distanceCovered": 392,
                "updatedAt": "2026-03-24T21:38:00Z"
            },
            "route": [
                {"stationCode": "MMCT", "stationName": "Mumbai Central", "distance": 0, "day": 1, "scheduleArrival": "17:00", "scheduleDeparture": "17:00", "actualArrival": "17:00", "actualDeparture": "17:00", "delayArrival": 0, "delayDeparture": 0, "status": "departed", "hasHalted": True},
                {"stationCode": "BVI", "stationName": "Borivali", "distance": 30, "day": 1, "scheduleArrival": "17:20", "scheduleDeparture": "17:22", "actualArrival": "17:30", "actualDeparture": "17:32", "delayArrival": 10, "delayDeparture": 10, "status": "departed", "hasHalted": True},
                {"stationCode": "ST", "stationName": "Surat", "distance": 263, "day": 1, "scheduleArrival": "19:43", "scheduleDeparture": "19:48", "actualArrival": "20:01", "actualDeparture": "20:06", "delayArrival": 18, "delayDeparture": 18, "status": "departed", "hasHalted": True},
                {"stationCode": "BRC", "stationName": "Vadodara Junction", "distance": 392, "day": 1, "scheduleArrival": "21:06", "scheduleDeparture": "21:16", "actualArrival": "21:28", "actualDeparture": "21:38", "delayArrival": 22, "delayDeparture": 22, "status": "departed", "hasHalted": True},
                {"stationCode": "RTM", "stationName": "Ratlam Junction", "distance": 653, "day": 2, "scheduleArrival": "00:25", "scheduleDeparture": "00:28", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "NAD", "stationName": "Nagda Junction", "distance": 695, "day": 2, "scheduleArrival": "01:08", "scheduleDeparture": "01:10", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "KOTA", "stationName": "Kota Junction", "distance": 920, "day": 2, "scheduleArrival": "03:15", "scheduleDeparture": "03:20", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "NDLS", "stationName": "New Delhi", "distance": 1384, "day": 2, "scheduleArrival": "08:32", "scheduleDeparture": "08:32", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False}
            ]
        }
    },
    # Train 12002: Bhopal Shatabdi (NDLS -> RKMP), currently at GWL
    "12002": {
        "status": "success",
        "data": {
            "trainNumber": "12002",
            "trainName": "NEW DELHI BHOPAL SHATABDI",
            "startDate": "2026-03-24",
            "delayMinutes": 8.0,
            "currentLocation": {
                "stationCode": "GWL",
                "stationName": "Gwalior Junction",
                "latitude": 26.2183,
                "longitude": 78.1828,
                "speed": 88.0,
                "status": "departed",
                "distanceCovered": 313,
                "updatedAt": "2026-03-24T09:36:00Z"
            },
            "route": [
                {"stationCode": "NDLS", "stationName": "New Delhi", "distance": 0, "day": 1, "scheduleArrival": "06:00", "scheduleDeparture": "06:00", "actualArrival": "06:00", "actualDeparture": "06:00", "delayArrival": 0, "delayDeparture": 0, "status": "departed", "hasHalted": True},
                {"stationCode": "MTJ", "stationName": "Mathura Junction", "distance": 141, "day": 1, "scheduleArrival": "07:19", "scheduleDeparture": "07:20", "actualArrival": "07:21", "actualDeparture": "07:22", "delayArrival": 2, "delayDeparture": 2, "status": "departed", "hasHalted": True},
                {"stationCode": "AGC", "stationName": "Agra Cantt", "distance": 195, "day": 1, "scheduleArrival": "07:50", "scheduleDeparture": "07:55", "actualArrival": "07:55", "actualDeparture": "08:00", "delayArrival": 5, "delayDeparture": 5, "status": "departed", "hasHalted": True},
                {"stationCode": "DHO", "stationName": "Dholpur", "distance": 247, "day": 1, "scheduleArrival": "08:39", "scheduleDeparture": "08:40", "actualArrival": "08:45", "actualDeparture": "08:46", "delayArrival": 6, "delayDeparture": 6, "status": "departed", "hasHalted": True},
                {"stationCode": "MRA", "stationName": "Morena", "distance": 275, "day": 1, "scheduleArrival": "08:57", "scheduleDeparture": "08:58", "actualArrival": "09:04", "actualDeparture": "09:05", "delayArrival": 7, "delayDeparture": 7, "status": "departed", "hasHalted": True},
                {"stationCode": "GWL", "stationName": "Gwalior Junction", "distance": 313, "day": 1, "scheduleArrival": "09:23", "scheduleDeparture": "09:28", "actualArrival": "09:31", "actualDeparture": "09:36", "delayArrival": 8, "delayDeparture": 8, "status": "departed", "hasHalted": True},
                {"stationCode": "VGLJ", "stationName": "V Lakshmibai Jhansi", "distance": 410, "day": 1, "scheduleArrival": "10:45", "scheduleDeparture": "10:50", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "LAR", "stationName": "Lalitpur", "distance": 500, "day": 1, "scheduleArrival": "11:42", "scheduleDeparture": "11:43", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "BINA", "stationName": "Bina Junction", "distance": 563, "day": 1, "scheduleArrival": "12:40", "scheduleDeparture": "12:42", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "BPL", "stationName": "Bhopal Junction", "distance": 701, "day": 1, "scheduleArrival": "14:12", "scheduleDeparture": "14:15", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False},
                {"stationCode": "RKMP", "stationName": "Rani Kamlapati", "distance": 707, "day": 1, "scheduleArrival": "14:40", "scheduleDeparture": "14:40", "actualArrival": None, "actualDeparture": None, "delayArrival": None, "delayDeparture": None, "status": "yet_to_arrive", "hasHalted": False}
            ]
        }
    }
}


class MockRailRadarClient(BaseRailRadarClient):
    """
    Deterministic Mock Client for offline development and CI/test validation.
    - Never opens a network socket or contacts any external server.
    - Returns deterministic, verifiable responses matching RailRadar API specifications.
    - Clearly labels all data as: 'MOCK DATA — NOT LIVE RAILWAY DATA'
    """

    def __init__(self, canned_data: Optional[Dict[str, Dict[str, Any]]] = None):
        self._database = canned_data or MOCK_DATABASE

    def get_live_train_status(
        self,
        train_no: str,
        journey_date: Optional[str] = None
    ) -> NormalizedTrainState:
        """
        Return deterministic synthetic NormalizedTrainState.
        """
        clean_no = str(train_no).strip().zfill(5)
        # Check integer/string variations
        key = None
        for k in self._database:
            if str(k).strip().zfill(5) == clean_no:
                key = k
                break

        if key is None:
            raise TrainNotFoundError(clean_no)

        payload = self._database[key]
        return parse_railradar_response(payload, is_mock=True)
