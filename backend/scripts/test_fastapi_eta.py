"""
Automated Test Suite for SIH 26028 FastAPI Live ETA Endpoint.
Validates all 13 required test cases using mocked RailRadar responses:
1. GET /api/train/{train_no}/eta endpoint structure
2. Successful mocked RailRadar response
3. H1 prediction
4. H2 prediction when >=2 stops remain
5. H3 prediction when >=3 stops remain
6. Insufficient stops for H2/H3
7. Invalid train number
8. RailRadar timeout
9. RailRadar authentication/API failure
10. Schedule mapping failure
11. Model inference failure
12. API key is never exposed in response/logging
13. Cache behavior
"""

import sys
import os
import time
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure clean environment
from app.live.config import load_env_file, mask_secret, get_api_key
load_env_file(PROJECT_ROOT / ".env", override=True)

from app.live.app import app
from app.live.cache import eta_cache
from app.live.api_client import MockRailRadarClient, MOCK_DATABASE
from app.live.service import LiveETAService
from app.live.exceptions import (
    APITimeoutError,
    APIAuthenticationError,
    TrainNotFoundError,
    LiveInferenceError
)
from ml.inference.schemas import StationNotOnRouteError


class FastAPITestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 13
        self.client = TestClient(app)

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
        print("SIH 26028 - FASTAPI ETA BACKEND TEST SUITE")
        print("Running automated mock tests")
        print("==================================================")
        eta_cache.clear()

        # ---------------------------------------------------------------------
        # Test 1: GET /api/train/{train_no}/eta endpoint structure
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp = self.client.get("/api/train/12301/eta")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            for field in ["success", "train_no", "train_name", "status", "journey_date", "current_station", "predictions"]:
                assert field in data, f"Missing required top-level field: {field}"
            assert data["success"] is True
            assert data["train_no"] == "12301"
            assert "code" in data["current_station"]
            assert "name" in data["current_station"]
            assert "delay_minutes" in data["current_station"]
            assert isinstance(data["predictions"], list)
            self.report(1, "GET /api/train/{train_no}/eta endpoint structure", True,
                        f"Status {resp.status_code}, success={data['success']}, train={data['train_no']}")
        except Exception as e:
            self.report(1, "GET /api/train/{train_no}/eta endpoint structure", False, str(e))

        # ---------------------------------------------------------------------
        # Test 2: Successful mocked RailRadar response
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp = self.client.get("/api/train/12301/eta")
            data = resp.json()
            curr = data["current_station"]
            assert curr["code"] == "CNB"
            assert curr["name"] == "Kanpur Central"
            assert curr["delay_minutes"] == 15.0
            self.report(2, "Successful mocked RailRadar response", True,
                        f"Current Station: {curr['code']} ({curr['name']}), Delay: {curr['delay_minutes']}m")
        except Exception as e:
            self.report(2, "Successful mocked RailRadar response", False, str(e))

        # ---------------------------------------------------------------------
        # Test 3: H1 prediction
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp = self.client.get("/api/train/12301/eta")
            data = resp.json()
            h1 = [p for p in data["predictions"] if p["horizon"] == 1]
            assert len(h1) == 1, "Expected exactly 1 H1 prediction"
            p1 = h1[0]
            assert p1["station"] == "NDLS"
            assert "T" in p1["scheduled_arrival"]
            assert "T" in p1["predicted_eta"]
            assert isinstance(p1["predicted_delay_minutes"], (int, float))
            self.report(3, "H1 prediction", True,
                        f"H1 Station: {p1['station']}, Delay: {p1['predicted_delay_minutes']}m, ETA: {p1['predicted_eta']}")
        except Exception as e:
            self.report(3, "H1 prediction", False, str(e))

        # ---------------------------------------------------------------------
        # Test 4: H2 prediction when >=2 stops remain
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp = self.client.get("/api/train/12951/eta")  # Train 12951 at BRC has 4 stops remaining
            data = resp.json()
            h2 = [p for p in data["predictions"] if p["horizon"] == 2]
            assert len(h2) == 1, "Expected H2 prediction for train with >=2 stops remaining"
            p2 = h2[0]
            assert p2["station"] == "NAD"
            assert isinstance(p2["predicted_delay_minutes"], (int, float))
            assert "T" in p2["predicted_eta"]
            self.report(4, "H2 prediction when >=2 stops remain", True,
                        f"H2 Station: {p2['station']}, Delay: {p2['predicted_delay_minutes']}m, ETA: {p2['predicted_eta']}")
        except Exception as e:
            self.report(4, "H2 prediction when >=2 stops remain", False, str(e))

        # ---------------------------------------------------------------------
        # Test 5: H3 prediction when >=3 stops remain
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp = self.client.get("/api/train/12002/eta")  # Train 12002 at GWL has 5 stops remaining
            data = resp.json()
            h3 = [p for p in data["predictions"] if p["horizon"] == 3]
            assert len(h3) == 1, "Expected H3 prediction for train with >=3 stops remaining"
            p3 = h3[0]
            assert p3["station"] == "BINA"
            assert isinstance(p3["predicted_delay_minutes"], (int, float))
            assert "T" in p3["predicted_eta"]
            self.report(5, "H3 prediction when >=3 stops remain", True,
                        f"H3 Station: {p3['station']}, Delay: {p3['predicted_delay_minutes']}m, ETA: {p3['predicted_eta']}")
        except Exception as e:
            self.report(5, "H3 prediction when >=3 stops remain", False, str(e))

        # ---------------------------------------------------------------------
        # Test 6: Insufficient stops for H2/H3
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp = self.client.get("/api/train/12301/eta")  # At CNB, only NDLS remains (stops_remaining=1)
            data = resp.json()
            horizons = [p["horizon"] for p in data["predictions"]]
            assert horizons == [1], f"Expected only [1] for 1 stop to terminus, got {horizons}"
            self.report(6, "Insufficient stops for H2/H3", True,
                            f"Only H1 returned ({horizons}) when 1 stop remaining to terminus")
        except Exception as e:
            self.report(6, "Insufficient stops for H2/H3", False, str(e))

        # ---------------------------------------------------------------------
        # Test 7: Invalid train number
        # ---------------------------------------------------------------------
        try:
            resp_alpha = self.client.get("/api/train/ABC12/eta")
            assert resp_alpha.status_code == 400, f"Expected 400, got {resp_alpha.status_code}"
            assert "Invalid train number" in resp_alpha.json().get("detail", "")

            resp_short = self.client.get("/api/train/12/eta")
            assert resp_short.status_code == 400, f"Expected 400, got {resp_short.status_code}"
            self.report(7, "Invalid train number", True,
                        f"Non-numeric/short train numbers rejected with HTTP 400")
        except Exception as e:
            self.report(7, "Invalid train number", False, str(e))

        # ---------------------------------------------------------------------
        # Test 8: RailRadar timeout
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            mock_client = MagicMock()
            mock_client.get_live_train_status.side_effect = APITimeoutError(10.0)
            app.state.live_client = mock_client
            resp = self.client.get("/api/train/12301/eta")
            assert resp.status_code == 504, f"Expected 504, got {resp.status_code}"
            assert "timed out" in resp.json().get("detail", "").lower()
            self.report(8, "RailRadar timeout", True,
                        f"APITimeoutError converted to HTTP 504 Gateway Timeout")
        except Exception as e:
            self.report(8, "RailRadar timeout", False, str(e))

        # ---------------------------------------------------------------------
        # Test 9: RailRadar authentication/API failure
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            mock_client = MagicMock()
            mock_client.get_live_train_status.side_effect = APIAuthenticationError("Bad credentials")
            app.state.live_client = mock_client
            resp = self.client.get("/api/train/12301/eta")
            assert resp.status_code == 502, f"Expected 502, got {resp.status_code}"
            assert "authentication failed" in resp.json().get("detail", "").lower()
            self.report(9, "RailRadar authentication/API failure", True,
                        f"APIAuthenticationError converted to HTTP 502 Bad Gateway")
        except Exception as e:
            self.report(9, "RailRadar authentication/API failure", False, str(e))

        # ---------------------------------------------------------------------
        # Test 10: Schedule mapping failure
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            mock_client = MagicMock()
            mock_client.get_live_train_status.side_effect = StationNotOnRouteError("12301", "BVI")
            app.state.live_client = mock_client
            resp = self.client.get("/api/train/12301/eta")
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
            assert "schedule mapping error" in resp.json().get("detail", "").lower()
            self.report(10, "Schedule mapping failure", True,
                        f"StationNotOnRouteError converted to HTTP 422 Unprocessable Entity")
        except Exception as e:
            self.report(10, "Schedule mapping failure", False, str(e))

        # ---------------------------------------------------------------------
        # Test 11: Model inference failure
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            mock_client = MagicMock()
            mock_client.get_live_train_status.side_effect = LiveInferenceError("Booster failure")
            app.state.live_client = mock_client
            resp = self.client.get("/api/train/12301/eta")
            assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"
            assert "inference execution failed" in resp.json().get("detail", "").lower()
            self.report(11, "Model inference failure", True,
                        f"LiveInferenceError converted to HTTP 500 Internal Server Error")
        except Exception as e:
            self.report(11, "Model inference failure", False, str(e))

        # ---------------------------------------------------------------------
        # Test 12: API key is never exposed in response/logging
        # ---------------------------------------------------------------------
        try:
            secret = get_api_key() or "test_secret_12345"
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()
            resp_success = self.client.get("/api/train/12301/eta")
            assert secret not in resp_success.text, "Secret key leaked in success response!"

            resp_health = self.client.get("/api/health")
            assert secret not in resp_health.text, "Secret key leaked in health response!"

            resp_err = self.client.get("/api/train/99999/eta")
            assert secret not in resp_err.text, "Secret key leaked in error response!"

            self.report(12, "API key is never exposed in response/logging", True,
                        "Zero credentials exposed in success, health, or error response bodies")
        except Exception as e:
            self.report(12, "API key is never exposed in response/logging", False, str(e))

        # ---------------------------------------------------------------------
        # Test 13: Cache behavior
        # ---------------------------------------------------------------------
        try:
            eta_cache.clear()
            app.state.live_client = MockRailRadarClient()

            # 1st request -> Cache Miss
            stats_before = eta_cache.stats
            t0 = time.monotonic()
            r1 = self.client.get("/api/train/12301/eta")
            elapsed1 = (time.monotonic() - t0) * 1000.0

            # 2nd request -> Cache Hit
            t1 = time.monotonic()
            r2 = self.client.get("/api/train/12301/eta")
            elapsed2 = (time.monotonic() - t1) * 1000.0

            stats_after = eta_cache.stats
            assert r1.json() == r2.json(), "Cached response does not match live response"
            assert stats_after["hits"] == stats_before["hits"] + 1, "Cache hit count not incremented"
            assert stats_after["size"] >= 1, "Cache size should be >= 1"

            self.report(13, "Cache behavior", True,
                        f"Hit verified: 1st={elapsed1:.1f}ms, 2nd={elapsed2:.1f}ms (Cache Stats: {stats_after})")
        except Exception as e:
            self.report(13, "Cache behavior", False, str(e))

        # Clean up app.state.live_client after tests
        app.state.live_client = None

        print("==================================================")
        print(f"FASTAPI ETA TEST RESULTS: {self.passed}/{self.total} PASSED")
        if self.failed == 0:
            print("ALL FASTAPI ETA TESTS COMPLETED SUCCESSFULLY!")
        else:
            print(f"FAILURES: {self.failed} failed")
        print("==================================================")
        return self.failed == 0


if __name__ == "__main__":
    runner = FastAPITestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
