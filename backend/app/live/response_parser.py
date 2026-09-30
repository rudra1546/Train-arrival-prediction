"""
Response parser for RailRadar Live API responses.
Validates raw payload, extracts current operational state, reconstructs consecutive
historical delay lags from traversed halts, and returns NormalizedTrainState.
"""

from typing import Dict, Any, List, Optional
import math

from app.live.schemas import NormalizedTrainState
from app.live.exceptions import APIResponseMalformedError, TrainNotRunningError


def parse_railradar_response(payload: Dict[str, Any], is_mock: bool = False) -> NormalizedTrainState:
    """
    Parse a RailRadar live-train response dictionary into a NormalizedTrainState.
    
    Parameters:
    -----------
    payload : Dict[str, Any]
        Raw JSON response dictionary from RailRadar API.
    is_mock : bool
        Whether this response originated from a mock/synthetic client.
        
    Returns:
    --------
    NormalizedTrainState : Clean, validated domain object.
    
    Raises:
    -------
    APIResponseMalformedError : If required fields are missing or wrong types.
    TrainNotRunningError : If the train is reported as cancelled or not running.
    """
    if not isinstance(payload, dict):
        raise APIResponseMalformedError("Root response must be a JSON object.")

    status = payload.get("status")
    success = payload.get("success")
    if status == "error" or success is False or not payload.get("data"):
        msg = payload.get("message", "Unknown API error occurred or missing data.")
        raise APIResponseMalformedError(f"API returned error: {msg}")

    data = payload["data"]
    if not isinstance(data, dict):
        raise APIResponseMalformedError("Field 'data' must be an object.")

    # 1. Extract Train Identity & Base State
    train_no_raw = data.get("trainNumber")
    if not train_no_raw:
        raise APIResponseMalformedError("Missing required field 'trainNumber' in 'data'.")
    train_no = str(train_no_raw).strip().zfill(5)

    journey_date = data.get("startDate")
    if not journey_date:
        raise APIResponseMalformedError("Missing required field 'startDate' in 'data'.")
    journey_date = str(journey_date).strip()

    train_name = data.get("trainName")

    # Current Location sub-object
    curr_loc = data.get("currentLocation")
    if not isinstance(curr_loc, dict):
        raise APIResponseMalformedError("Missing or malformed 'currentLocation' in 'data'.")

    curr_stn_code = curr_loc.get("stationCode")
    prev_halt = data.get("previousHalt")

    current_station_name = None
    # If currently between halts (isHalt is False) and previous commercial halt is available,
    # use previous commercial halt as the scheduled station reference.
    if curr_loc.get("isHalt") is False and isinstance(prev_halt, dict) and prev_halt.get("stationCode"):
        current_station = str(prev_halt["stationCode"]).strip().upper()
        current_station_name = prev_halt.get("stationName")
    elif curr_stn_code:
        current_station = str(curr_stn_code).strip().upper()
        current_station_name = curr_loc.get("stationName")
    else:
        raise APIResponseMalformedError("Missing 'stationCode' in 'currentLocation'.")

    # Delay minutes
    # Prefer delayMinutes from top-level or from currentLocation
    delay_val = data.get("delayMinutes")
    if delay_val is None:
        delay_val = curr_loc.get("delayMinutes", 0.0)
    try:
        current_delay_minutes = float(delay_val)
    except (ValueError, TypeError):
        raise APIResponseMalformedError(f"Invalid non-numeric delayMinutes: {delay_val}")

    status_timestamp = curr_loc.get("updatedAt") or data.get("lastUpdatedAt")
    current_status = curr_loc.get("status")
    
    # Coordinates (if available) - supports both flat and nested coordinates object
    coords = curr_loc.get("coordinates")
    if isinstance(coords, dict):
        lat = coords.get("lat")
        lon = coords.get("lng")
    else:
        lat = curr_loc.get("latitude")
        lon = curr_loc.get("longitude")
    latitude = float(lat) if lat is not None else None
    longitude = float(lon) if lon is not None else None

    # Check for train status conditions (e.g. cancelled)
    if current_status and current_status.lower() in ["cancelled", "canceled"]:
        raise TrainNotRunningError(train_no, journey_date, "Train is cancelled.")

    # 2. Extract Route Halts & Reconstruct Historical Lag Delays
    route = data.get("route")
    prev_station_delay: Optional[float] = None
    prev_delay_2: Optional[float] = None
    prev_delay_3: Optional[float] = None
    station_sequence: Optional[int] = None
    stops_remaining: Optional[int] = None

    if isinstance(route, list) and len(route) > 0:
        # Find index of current station in the route
        curr_idx = -1
        for idx, stop in enumerate(route):
            if isinstance(stop, dict) and str(stop.get("stationCode", "")).strip().upper() == current_station:
                curr_idx = idx
                break

        if curr_idx != -1:
            station_sequence = curr_idx + 1
            stops_remaining = len(route) - 1 - curr_idx

            # Collect traversed stops prior to current station
            traversed_delays: List[float] = []
            for i in range(curr_idx - 1, -1, -1):
                prev_stop = route[i]
                if not isinstance(prev_stop, dict):
                    continue
                # Delay at stop: check delayDeparture first, then delayArrival
                d_dep = prev_stop.get("delayDeparture")
                d_arr = prev_stop.get("delayArrival")
                d_val = d_dep if d_dep is not None else d_arr
                if d_val is not None:
                    try:
                        traversed_delays.append(float(d_val))
                    except (ValueError, TypeError):
                        pass

            # Assign lags: traversed_delays[0] is prev_station_delay, [1] is prev_delay_2, [2] is prev_delay_3
            if len(traversed_delays) >= 1:
                prev_station_delay = traversed_delays[0]
            if len(traversed_delays) >= 2:
                prev_delay_2 = traversed_delays[1]
            if len(traversed_delays) >= 3:
                prev_delay_3 = traversed_delays[2]

    # 3. Compute Delay Deltas
    delay_change: Optional[float] = None
    delay_change_2_stations: Optional[float] = None
    delay_change_3_stations: Optional[float] = None

    if prev_station_delay is not None:
        delay_change = current_delay_minutes - prev_station_delay
    if prev_delay_2 is not None:
        delay_change_2_stations = current_delay_minutes - prev_delay_2
    if prev_delay_3 is not None:
        delay_change_3_stations = current_delay_minutes - prev_delay_3

    source_label = "railradar_mock" if is_mock else "railradar_live"

    return NormalizedTrainState(
        train_no=train_no,
        current_station=current_station,
        current_delay_minutes=current_delay_minutes,
        journey_date=journey_date,
        status_timestamp=status_timestamp,
        latitude=latitude,
        longitude=longitude,
        current_status=current_status,
        train_name=train_name,
        current_station_name=current_station_name,
        source=source_label,
        station_sequence=station_sequence,
        prev_station_delay=prev_station_delay,
        prev_delay_2=prev_delay_2,
        prev_delay_3=prev_delay_3,
        delay_change=delay_change,
        delay_change_2_stations=delay_change_2_stations,
        delay_change_3_stations=delay_change_3_stations,
        stops_remaining=stops_remaining,
        is_mock=is_mock
    )
