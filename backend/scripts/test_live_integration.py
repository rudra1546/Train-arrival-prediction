"""
Comprehensive Test Suite for Live Railway API Integration (SIH 26028).
Validates all 14 requirements offline without making any real API calls or using any secret credentials.

Test Cases:
1. Environment configuration loads correctly
2. Missing API key is detected correctly
3. No real API request occurs without an API key
4. Mock API response parsing
5. Normalized train state creation
6. Feature construction
7. H1 prediction
8. H2 prediction
9. H3 prediction
10. ETA calculation
11. Invalid train handling
12. Malformed API response handling
13. API timeout/error handling
14. Secret is never printed in logs
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure clean environment for offline testing
os.environ["RAILRADAR_API_KEY"] = ""

from app.live.config import (
    load_env_file,
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
    TrainNotRunningError
)
from app.live.response_parser import parse_railradar_response
from app.live.api_client import (
    RailRadarLiveClient,
    MockRailRadarClient,
    MOCK_DATABASE,
    MOCK_LABEL
)
from app.live.service import LiveETAService
from ml.inference.predictor import MultiHorizonETAPredictor
from app.live.app import app


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 14
        self.predictor = None

    def get_predictor(self):
        if self.predictor is None:
            self.predictor = MultiHorizonETAPredictor()
        return self.predictor

    def report(self, test_num: int, name: str, success: bool, details: str = ""):
        if success:
            self.passed += 1
            print(f"Test {test_num:02d} [PASS]: {name}")
            if details:
                print(f"         {details}")
        else:
            self.failed += 1
            print(f"Test {test_num:02d} [FAIL]: {name}")
            if details:
                print(f"         Error: {details}")

    def run_all(self):
        print("==================================================")
        print("SIH 26028 - LIVE RAILWAY API INTEGRATION TEST SUITE")
        print("Running in SAFE OFFLINE mode (No live network calls)")
        print("==================================================")

        # ---------------------------------------------------------------------
        # Test 1: Environment configuration loads correctly
        # ---------------------------------------------------------------------
        try:
            load_env_file(PROJECT_ROOT / ".env", override=True)
            assert isinstance(RAILRADAR_BASE_URL, str) and len(RAILRADAR_BASE_URL) > 0
            assert isinstance(RAILRADAR_TIMEOUT_SECONDS, (int, float)) and RAILRADAR_TIMEOUT_SECONDS > 0
            self.report(1, "Environment configuration loads correctly", True,
                        f"Base URL: {RAILRADAR_BASE_URL}, Timeout: {RAILRADAR_TIMEOUT_SECONDS}s")
        except Exception as e:
            self.report(1, "Environment configuration loads correctly", False, str(e))

        # ---------------------------------------------------------------------
        # Test 2: Missing API key is detected correctly
        # ---------------------------------------------------------------------
        try:
            # Explicitly test with unset, empty, or placeholder key
            os.environ["RAILRADAR_API_KEY"] = ""
            assert is_live_configured() is False, "Empty key should return is_live_configured() == False"
            assert get_api_key() is None, "Empty key should return get_api_key() == None"

            os.environ["RAILRADAR_API_KEY"] = "YOUR_API_KEY"
            assert is_live_configured() is False, "Placeholder key should return is_live_configured() == False"
            assert get_api_key() is None, "Placeholder key should return get_api_key() == None"

            os.environ["RAILRADAR_API_KEY"] = ""
            self.report(2, "Missing API key is detected correctly", True,
                        "Correctly identifies unconfigured or placeholder API keys")
        except Exception as e:
            self.report(2, "Missing API key is detected correctly", False, str(e))

        # ---------------------------------------------------------------------
        # Test 3: No real API request occurs without an API key
        # ---------------------------------------------------------------------
        try:
            os.environ["RAILRADAR_API_KEY"] = ""

            blocked = False
            try:
                # Should fail at initialization
                client = RailRadarLiveClient()
                client.get_live_train_status("12301")
            except APIKeyMissingError:
                blocked = True

            assert blocked, "RailRadarLiveClient must raise APIKeyMissingError when unconfigured"
            self.report(3, "No real API request occurs without an API key", True,
                        "Instantiation and calls strictly aborted with APIKeyMissingError")
        except Exception as e:
            self.report(3, "No real API request occurs without an API key", False, str(e))

        # ---------------------------------------------------------------------
        # Test 4: Mock API response parsing
        # ---------------------------------------------------------------------
        try:
            raw_mock = MOCK_DATABASE["12301"]
            parsed_state = parse_railradar_response(raw_mock, is_mock=True)
            assert isinstance(parsed_state, NormalizedTrainState)
            assert parsed_state.train_no == "12301"
            assert parsed_state.current_station == "CNB"
            assert parsed_state.current_delay_minutes == 15.0
            assert parsed_state.journey_date == "2026-03-24"
            self.report(4, "Mock API response parsing", True,
                        f"Parsed train {parsed_state.train_no} at {parsed_state.current_station} delay={parsed_state.current_delay_minutes}m")
        except Exception as e:
            self.report(4, "Mock API response parsing", False, str(e))

        # ---------------------------------------------------------------------
        # Test 5: Normalized train state creation
        # ---------------------------------------------------------------------
        try:
            raw_mock = MOCK_DATABASE["12301"]
            state = parse_railradar_response(raw_mock, is_mock=True)
            # Check lag reconstruction from route
            assert state.prev_station_delay == 15.0  # PRYJ delay
            assert state.prev_delay_2 == 14.0        # DDU delay
            assert state.prev_delay_3 == 12.0        # GAYA delay
            assert state.delay_change == (15.0 - 15.0)
            assert state.delay_change_2_stations == (15.0 - 14.0)
            assert state.delay_change_3_stations == (15.0 - 12.0)
            assert state.is_mock is True
            assert state.source == "railradar_mock"
            assert len(UNAVAILABLE_FROM_API) >= 5
            self.report(5, "Normalized train state creation", True,
                        f"Lags extracted: prev={state.prev_station_delay}m, prev2={state.prev_delay_2}m, prev3={state.prev_delay_3}m")
        except Exception as e:
            self.report(5, "Normalized train state creation", False, str(e))

        # ---------------------------------------------------------------------
        # Test 6: Feature construction
        # ---------------------------------------------------------------------
        try:
            raw_mock = MOCK_DATABASE["12301"]
            state = parse_railradar_response(raw_mock, is_mock=True)
            feat_dict = state.to_feature_dict()
            assert "current_delay" in feat_dict
            assert "prev_station_delay" in feat_dict
            assert "delay_change" in feat_dict

            # Verify that existing predictor enriches this feature set completely
            predictor = self.get_predictor()
            route, curr_idx = predictor.validate_train_and_station(state.train_no, state.current_station)
            enriched = predictor._enrich_features_from_timetable(
                train_no=state.train_no,
                journey_date=state.journey_date,
                current_station=state.current_station,
                current_delay=state.current_delay_minutes,
                route=route,
                curr_idx=curr_idx,
                provided_features=feat_dict
            )
            # Verify required columns exist
            for col in ["journey_progress", "scheduled_hour", "day_of_week", "dist_from_origin", "remaining_dist"]:
                assert col in enriched, f"Feature {col} missing in enriched vector"

            self.report(6, "Feature construction", True,
                        f"Features successfully constructed and enriched ({len(enriched)} features total)")
        except Exception as e:
            self.report(6, "Feature construction", False, str(e))

        # ---------------------------------------------------------------------
        # Test 7: H1 prediction
        # ---------------------------------------------------------------------
        try:
            predictor = self.get_predictor()
            service = LiveETAService(client=MockRailRadarClient(), predictor=predictor)
            resp = service.predict_for_train("12301", force_mock=True)
            h1 = [p for p in resp.predictions if p.horizon == 1]
            assert len(h1) == 1, "Horizon 1 prediction not found"
            pred_h1 = h1[0]
            assert pred_h1.station_code == "NDLS"
            assert isinstance(pred_h1.predicted_delay_minutes, (int, float))
            assert isinstance(pred_h1.predicted_eta, str) and len(pred_h1.predicted_eta) > 0
            self.report(7, "H1 prediction", True,
                        f"Target: {pred_h1.station_code}, Pred Delay: {pred_h1.predicted_delay_minutes:.2f}m, Sched: {pred_h1.scheduled_arrival}")
        except Exception as e:
            self.report(7, "H1 prediction", False, str(e))

        # ---------------------------------------------------------------------
        # Test 8: H2 prediction
        # ---------------------------------------------------------------------
        try:
            predictor = self.get_predictor()
            service = LiveETAService(client=MockRailRadarClient(), predictor=predictor)
            resp = service.predict_for_train("12951", force_mock=True)  # Train 12951 at BRC
            h2 = [p for p in resp.predictions if p.horizon == 2]
            assert len(h2) == 1, "Horizon 2 prediction not found"
            pred_h2 = h2[0]
            assert pred_h2.station_code == "NAD"
            assert isinstance(pred_h2.predicted_delay_minutes, (int, float))
            self.report(8, "H2 prediction", True,
                        f"Target: {pred_h2.station_code}, Pred Delay: {pred_h2.predicted_delay_minutes:.2f}m, ETA: {pred_h2.predicted_eta}")
        except Exception as e:
            self.report(8, "H2 prediction", False, str(e))

        # ---------------------------------------------------------------------
        # Test 9: H3 prediction
        # ---------------------------------------------------------------------
        try:
            predictor = self.get_predictor()
            service = LiveETAService(client=MockRailRadarClient(), predictor=predictor)
            resp = service.predict_for_train("12002", force_mock=True)  # Train 12002 at GWL
            h3 = [p for p in resp.predictions if p.horizon == 3]
            assert len(h3) == 1, "Horizon 3 prediction not found"
            pred_h3 = h3[0]
            assert pred_h3.station_code == "BINA"
            assert isinstance(pred_h3.predicted_delay_minutes, (int, float))
            self.report(9, "H3 prediction", True,
                        f"Target: {pred_h3.station_code}, Pred Delay: {pred_h3.predicted_delay_minutes:.2f}m, ETA: {pred_h3.predicted_eta}")
        except Exception as e:
            self.report(9, "H3 prediction", False, str(e))

        # ---------------------------------------------------------------------
        # Test 10: ETA calculation
        # ---------------------------------------------------------------------
        try:
            predictor = self.get_predictor()
            service = LiveETAService(client=MockRailRadarClient(), predictor=predictor)
            resp = service.predict_for_train("12002", force_mock=True)
            for p in resp.predictions:
                # Valid ISO datetime
                dt = datetime.fromisoformat(p.predicted_eta)
                assert dt is not None
                assert p.predicted_delay_minutes is not None
            self.report(10, "ETA calculation", True,
                        f"All {len(resp.predictions)} horizons have valid timestamp ETAs verified")
        except Exception as e:
            self.report(10, "ETA calculation", False, str(e))

        # ---------------------------------------------------------------------
        # Test 11: Invalid train handling
        # ---------------------------------------------------------------------
        try:
            mock_client = MockRailRadarClient()
            train_not_found = False
            try:
                mock_client.get_live_train_status("99999")
            except TrainNotFoundError:
                train_not_found = True

            # Also verify via FastAPI demo endpoint
            client = TestClient(app)
            http_resp = client.get("/api/demo/train/99999/eta")
            assert http_resp.status_code == 404
            assert train_not_found, "MockClient should raise TrainNotFoundError for 99999"
            self.report(11, "Invalid train handling", True,
                        "Raises TrainNotFoundError and returns HTTP 404 for unknown train")
        except Exception as e:
            self.report(11, "Invalid train handling", False, str(e))

        # ---------------------------------------------------------------------
        # Test 12: Malformed API response handling
        # ---------------------------------------------------------------------
        try:
            malformed_cases = [
                {},  # empty
                {"status": "success"},  # missing data
                {"status": "success", "data": "not a dict"},
                {"status": "success", "data": {"trainNumber": "12301"}},  # missing currentLocation
                {"status": "success", "data": {"trainNumber": "12301", "startDate": "2026-03-24", "currentLocation": {"stationCode": "CNB", "delayMinutes": "NOT_A_NUMBER"}}}  # invalid delay
            ]
            caught = 0
            for case in malformed_cases:
                try:
                    parse_railradar_response(case)
                except APIResponseMalformedError:
                    caught += 1

            assert caught == len(malformed_cases), f"Expected {len(malformed_cases)} errors, caught {caught}"
            self.report(12, "Malformed API response handling", True,
                        f"All {caught} malformed payloads rejected with APIResponseMalformedError")
        except Exception as e:
            self.report(12, "Malformed API response handling", False, str(e))

        # ---------------------------------------------------------------------
        # Test 13: API timeout/error handling
        # ---------------------------------------------------------------------
        try:
            timeout_err = APITimeoutError(10.0)
            assert timeout_err.status_code == 504
            assert "10.0s" in str(timeout_err)

            auth_err = APIAuthenticationError()
            assert auth_err.status_code == 401

            not_running_err = TrainNotRunningError("12301", "2026-03-24", "Cancelled by fog")
            assert not_running_err.status_code == 422

            self.report(13, "API timeout/error handling", True,
                        "Timeout (504), Auth (401), and TrainNotRunning (422) exceptions verified")
        except Exception as e:
            self.report(13, "API timeout/error handling", False, str(e))

        # ---------------------------------------------------------------------
        # Test 14: Secret is never printed in logs
        # ---------------------------------------------------------------------
        try:
            test_secret = "rr_live_super_secret_production_key_987654321"
            masked = mask_secret(test_secret)
            assert test_secret not in masked, "Masked secret contains original plaintext!"
            assert masked == "rr_l...4321"

            # Check short secret
            assert mask_secret("short") == "***"
            # Check empty / None
            assert mask_secret("") == "<UNCONFIGURED>"
            assert mask_secret(None) == "<UNCONFIGURED>"

            # Ensure environment has empty key
            os.environ["RAILRADAR_API_KEY"] = ""
            client = TestClient(app)

            # Check FastAPI health endpoint does not leak key and shows unconfigured
            health = client.get("/api/health").json()
            assert health.get("live_api_configured") is False
            assert health.get("api_key_status") == "<UNCONFIGURED>"

            # Check unconfigured live train endpoint returns expected message
            live_ep = client.get("/api/train/12301/eta").json()
            assert live_ep.get("status") == "live_api_not_configured"
            assert "RailRadar API key has not been configured" in live_ep.get("message", "")

            # Check demo endpoint returns mock data
            demo_ep = client.get("/api/demo/train/12301/eta").json()
            assert demo_ep.get("success") is True
            assert demo_ep.get("train_no") == "12301"

            self.report(14, "Secret is never printed in logs", True,
                        "mask_secret redacts plaintext; health, live, and demo endpoints verified safe")
        except Exception as e:
            self.report(14, "Secret is never printed in logs", False, str(e))

        # ---------------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------------
        print("==================================================")
        print(f"TEST RESULTS: {self.passed}/{self.total} PASSED")
        if self.failed == 0:
            print("ALL LIVE INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        else:
            print(f"FAILURES DETECTED: {self.failed} failed")
        print("==================================================")

        return self.failed == 0


if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
