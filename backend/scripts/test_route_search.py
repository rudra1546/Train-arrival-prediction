"""
Automated Test Suite for Indian Railways Route and Station Search API.
Tests all required cases:
1. Station search (autocomplete by code, city name, empty query, limit)
2. Valid route search (direct schedule lookup, train details, duration, stops)
3. Origin appearing after destination (ensures topological sequence s1.station_no < s2.station_no)
4. No-result search (unconnected stations return clean empty list with 200 OK)
5. Invalid parameters (missing from/to, identical stations, unknown station, malformed date)
"""

import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.live.app import app


class RouteSearchTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.client = TestClient(app)

    def report(self, name: str, success: bool, details: str = ""):
        if success:
            self.passed += 1
            print(f"PASS: {name}")
            if details:
                print(f"      {details}")
        else:
            self.failed += 1
            print(f"FAIL: {name}")
            if details:
                print(f"      {details}")

    def run_all(self):
        print("=" * 70)
        print("SIH 26028 - ROUTE & STATION SEARCH BACKEND API TEST SUITE")
        print("=" * 70)

        # -------------------------------------------------------------
        # Group 1: Station Search / Autocomplete Tests
        # -------------------------------------------------------------
        print("\n--- 1. STATION SEARCH TESTS ---")
        
        # Test 1.1: Station code search
        resp = self.client.get("/api/stations/search?q=NDLS")
        data = resp.json()
        self.report(
            "Station search by code 'NDLS'",
            resp.status_code == 200 and len(data) >= 1 and data[0]["code"] == "NDLS",
            f"Returned: {data[0] if data else 'None'}"
        )

        # Test 1.2: Station name search
        resp = self.client.get("/api/stations/search?q=Ahmedabad")
        data = resp.json()
        has_adi = any(s["code"] == "ADI" for s in data)
        self.report(
            "Station search by city name 'Ahmedabad'",
            resp.status_code == 200 and has_adi,
            f"Found ADI among {len(data)} results: {[s['code'] for s in data]}"
        )

        # Test 1.3: Empty station query returns popular hubs
        resp = self.client.get("/api/stations/search?q=")
        data = resp.json()
        codes = [s["code"] for s in data]
        self.report(
            "Default popular stations on empty query",
            resp.status_code == 200 and len(data) >= 5 and "NDLS" in codes,
            f"Returned {len(data)} stations: {codes}"
        )

        # Test 1.4: Station limit clamping
        resp = self.client.get("/api/stations/search?q=A&limit=3")
        data = resp.json()
        self.report(
            "Station search respects limit parameter",
            resp.status_code == 200 and len(data) == 3,
            f"Requested limit=3, received count={len(data)}"
        )

        # -------------------------------------------------------------
        # Group 2: Valid Route Search Tests
        # -------------------------------------------------------------
        print("\n--- 2. VALID ROUTE SEARCH TESTS ---")

        # Test 2.1: Direct route search (ADI -> NDLS)
        resp = self.client.get("/api/trains/search?from=ADI&to=NDLS")
        data = resp.json()
        trains = data.get("trains", [])
        self.report(
            "Valid route search: ADI -> NDLS",
            resp.status_code == 200 and data.get("success") is True and len(trains) >= 3,
            f"Found {len(trains)} trains. Top train: {trains[0]['train_no']} ({trains[0]['train_name']})"
        )

        # Test 2.2: Result card fields verification
        first = trains[0] if trains else {}
        has_required_fields = all(
            k in first and first[k] is not None
            for k in [
                "train_no", "train_name", "train_type", "origin_station",
                "destination_station", "from_station", "to_station",
                "departure_time", "arrival_time", "duration", "stops"
            ]
        )
        self.report(
            "Train result card contains all required metadata",
            has_required_fields,
            f"Departure: {first.get('departure_time')}, Arrival: {first.get('arrival_time')}, "
            f"Duration: {first.get('duration')}, Stops: {first.get('stops')}"
        )

        # Test 2.3: Search using station names (Ahmedabad -> New Delhi)
        resp = self.client.get("/api/trains/search?from=Ahmedabad&to=New Delhi")
        data = resp.json()
        self.report(
            "Route search resolves full station names automatically",
            resp.status_code == 200 and data.get("from_station", {}).get("code") == "ADI" and data.get("to_station", {}).get("code") == "NDLS",
            f"Resolved: {data.get('from_station')} -> {data.get('to_station')}"
        )

        # Test 2.4: Journey date parameter handling
        resp = self.client.get("/api/trains/search?from=ADI&to=NDLS&date=2026-10-15")
        data = resp.json()
        self.report(
            "Route search with valid journey date YYYY-MM-DD",
            resp.status_code == 200 and data.get("journey_date") == "2026-10-15",
            f"Preserved date: {data.get('journey_date')}"
        )

        # -------------------------------------------------------------
        # Group 3: Origin Appearing After Destination Tests
        # -------------------------------------------------------------
        print("\n--- 3. ORIGIN APPEARING AFTER DESTINATION TESTS ---")

        # Test 3.1: Train 12473 runs GIMB -> ADI -> NDLS -> SVDK.
        # ADI is stop 5, NDLS is stop 22.
        # Searching NDLS -> ADI must NEVER return train 12473 because NDLS comes AFTER ADI on 12473.
        resp = self.client.get("/api/trains/search?from=NDLS&to=ADI")
        data = resp.json()
        return_trains = [t["train_no"] for t in data.get("trains", [])]
        self.report(
            "Reverse search excludes trains where origin occurs after destination (12473 omitted)",
            resp.status_code == 200 and "12473" not in return_trains and "12474" in return_trains,
            f"Returned {return_trains} (12474 correct return train, 12473 correctly excluded)"
        )

        # Test 3.2: Strictly unidirectional route where station B is after station A on train 55089 (AA -> BNZ)
        # Searching BNZ -> AA must return 0 results because BNZ is stop 13 and AA is stop 8 on train 55089.
        resp = self.client.get("/api/trains/search?from=BNZ&to=AA")
        data = resp.json()
        self.report(
            "Topological order enforcement: no trains returned when origin occurs after destination",
            resp.status_code == 200 and data.get("count") == 0 and len(data.get("trains", [])) == 0,
            f"BNZ -> AA correctly returned 0 trains (train 55089 correctly omitted)"
        )

        # -------------------------------------------------------------
        # Group 4: No-Result Search Tests
        # -------------------------------------------------------------
        print("\n--- 4. NO-RESULT SEARCH TESTS ---")

        # Test 4.1: Two unconnected distant stations with no direct train
        resp = self.client.get("/api/trains/search?from=AABH&to=CSMT")
        data = resp.json()
        self.report(
            "No direct trains returns 200 OK with empty trains list and count=0",
            resp.status_code == 200 and data.get("success") is True and data.get("count") == 0 and data.get("trains") == [],
            f"Response: count={data.get('count')}, trains={data.get('trains')}"
        )

        # -------------------------------------------------------------
        # Group 5: Invalid Parameters Tests
        # -------------------------------------------------------------
        print("\n--- 5. INVALID PARAMETERS TESTS ---")

        # Test 5.1: Identical origin and destination stations
        resp = self.client.get("/api/trains/search?from=NDLS&to=NDLS")
        self.report(
            "Identical origin and destination rejected with 400 Bad Request",
            resp.status_code == 400 and "identical" in resp.json().get("detail", "").lower(),
            f"Response detail: '{resp.json().get('detail')}'"
        )

        # Test 5.2: Unknown origin station
        resp = self.client.get("/api/trains/search?from=XYZNONEXISTENT99&to=NDLS")
        self.report(
            "Unknown origin station rejected with 400 Bad Request",
            resp.status_code == 400 and "not found" in resp.json().get("detail", "").lower(),
            f"Response detail: '{resp.json().get('detail')}'"
        )

        # Test 5.3: Unknown destination station
        resp = self.client.get("/api/trains/search?from=NDLS&to=XYZNONEXISTENT99")
        self.report(
            "Unknown destination station rejected with 400 Bad Request",
            resp.status_code == 400 and "not found" in resp.json().get("detail", "").lower(),
            f"Response detail: '{resp.json().get('detail')}'"
        )

        # Test 5.4: Missing destination parameter
        resp = self.client.get("/api/trains/search?from=NDLS")
        self.report(
            "Missing 'to' parameter rejected with 422 Unprocessable Entity",
            resp.status_code == 422,
            f"Status code: {resp.status_code}"
        )

        # Test 5.5: Invalid date format
        resp = self.client.get("/api/trains/search?from=ADI&to=NDLS&date=invalid-date-format")
        self.report(
            "Invalid journey date rejected with 400 Bad Request",
            resp.status_code == 400 and "date format" in resp.json().get("detail", "").lower(),
            f"Response detail: '{resp.json().get('detail')}'"
        )

        # -------------------------------------------------------------
        # Group 6: Train Scheduled Route Stops Tests
        # -------------------------------------------------------------
        print("\n--- 6. TRAIN SCHEDULED ROUTE STOPS TESTS ---")

        # Test 6.1: Valid train route stops (12473 -> 31 stops)
        resp = self.client.get("/api/train/12473/route")
        data = resp.json()
        stops = data.get("stops", [])
        self.report(
            "Train route schedule lookup: 12473 returns all 31 real stops",
            resp.status_code == 200 and len(stops) == 31 and stops[0]["station_code"] == "GIMB" and stops[-1]["station_code"] == "SVDK",
            f"Returned {len(stops)} stops. Origin: {stops[0]['station_name']} ({stops[0]['station_code']}), Terminus: {stops[-1]['station_name']} ({stops[-1]['station_code']})"
        )

        # Test 6.2: Train route schedule lookup: 12301 (9 stops)
        resp = self.client.get("/api/train/12301/route")
        data = resp.json()
        stops = data.get("stops", [])
        self.report(
            "Train route schedule lookup: 12301 returns all 9 real stops",
            resp.status_code == 200 and len(stops) == 9 and stops[0]["station_code"] == "HWH" and stops[-1]["station_code"] == "NDLS",
            f"Returned {len(stops)} stops. Origin: {stops[0]['station_name']} -> Destination: {stops[-1]['station_name']}"
        )

        # Test 6.3: Unknown train route returns 404
        resp = self.client.get("/api/train/99999/route")
        self.report(
            "Unknown train route schedule returns 404 Not Found",
            resp.status_code == 404 and "not found" in resp.json().get("detail", "").lower(),
            f"Response detail: '{resp.json().get('detail')}'"
        )

        # -------------------------------------------------------------
        # Group 7: Station Geographic Coordinates Tests
        # -------------------------------------------------------------
        print("\n--- 7. STATION GEOGRAPHIC COORDINATES TESTS ---")

        # Test 7.1: Real coordinates for New Delhi (NDLS)
        resp = self.client.get("/api/station/NDLS/coordinates")
        data = resp.json()
        self.report(
            "Station coordinates lookup: NDLS returns authentic latitude & longitude",
            resp.status_code == 200 and data.get("code") == "NDLS" and 28.0 < data.get("latitude", 0) < 29.0 and 77.0 < data.get("longitude", 0) < 78.0,
            f"Returned: code={data.get('code')}, name={data.get('name')}, lat={data.get('latitude')}, lon={data.get('longitude')}"
        )

        # Test 7.2: Real coordinates for Ahmedabad (ADI)
        resp = self.client.get("/api/station/ADI/coordinates")
        data = resp.json()
        self.report(
            "Station coordinates lookup: ADI returns authentic latitude & longitude",
            resp.status_code == 200 and data.get("code") == "ADI" and 22.5 < data.get("latitude", 0) < 23.5 and 72.0 < data.get("longitude", 0) < 73.0,
            f"Returned: code={data.get('code')}, name={data.get('name')}, lat={data.get('latitude')}, lon={data.get('longitude')}"
        )

        # Test 7.3: Unknown station coordinates lookup returns 404
        resp = self.client.get("/api/station/NONEXISTENT999/coordinates")
        self.report(
            "Unknown station coordinates returns 404 Not Found without fabricating data",
            resp.status_code == 404 and "unavailable" in resp.json().get("detail", "").lower(),
            f"Response detail: '{resp.json().get('detail')}'"
        )

        # Test 7.4: Route stops include real coordinates
        resp = self.client.get("/api/train/12473/route")
        stops = resp.json().get("stops", [])
        with_coords = [s for s in stops if s.get("latitude") is not None and s.get("longitude") is not None]
        self.report(
            "Train route schedule provides authentic station coordinates for route polyline",
            len(with_coords) >= 30,
            f"{len(with_coords)} / {len(stops)} stops have verified geographic coordinates"
        )

        # -------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        total = self.passed + self.failed
        print(f"TEST SUMMARY: {self.passed}/{total} PASSED ({self.failed} FAILED)")
        print("=" * 70)
        return self.failed == 0


if __name__ == "__main__":
    runner = RouteSearchTestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
