"""
Predictor orchestration module for SIH 26028 Multi-Horizon ETA Service.
Coordinates route topology validation, timetable lookups, feature verification,
XGBoost booster inference for H1/H2/H3, and dynamic ETA calculation.
"""

from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sqlite3
import numpy as np
import pandas as pd
import polars as pl
import xgboost as xgb

from ml.utils.config import MODELS_DIR, resolve_search_db_path, KNOWN_STATION_ZONES
from ml.data.loader import load_schedule, load_station_master, load_train_details
from ml.inference.schemas import (
    PredictionRequest,
    HorizonPrediction,
    MultiHorizonResponse,
    UnknownTrainError,
    UnknownStationError,
    StationNotOnRouteError,
    InsufficientRouteRemainingError,
    InvalidJourneyDateError,
    FeatureValidationError
)
from ml.inference.model_loader import MultiHorizonModelLoader
from ml.inference.eta_calculator import (
    parse_journey_date,
    calculate_station_eta,
    parse_time_to_minutes
)


class MultiHorizonETAPredictor:
    """
    Core offline inference engine for Multi-Horizon ETA forecasting.
    Loads models H1, H2, H3, validates inputs against master timetables,
    and returns simultaneous predictions for the next 3 scheduled stops.
    """

    def __init__(
        self,
        models_dir: Path = MODELS_DIR,
        model_loader: Optional[MultiHorizonModelLoader] = None
    ):
        self.models_dir = Path(models_dir)
        self.model_loader = model_loader or MultiHorizonModelLoader.get_instance(models_dir=self.models_dir)
        
        # Load and index master railway timetables & metadata
        self._init_timetable_index()

    def _init_timetable_index(self) -> None:
        """Index timetable routes and master station lists for O(1) in-memory lookup."""
        db_path = resolve_search_db_path()
        if db_path.exists():
            self._init_from_db(db_path)
        else:
            self._init_from_raw_csv()

    def _init_from_db(self, db_path: Path) -> None:
        """Load timetable index from deployment-ready SQLite database."""
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # 1. Station zones & names
        stn_rows = cur.execute("SELECT code, name, zone FROM stations").fetchall()
        self.station_zones = {code.upper(): (zone or "NR").strip() for code, name, zone in stn_rows}
        self.station_full_names = {code.upper(): (name or code).strip() for code, name, zone in stn_rows}

        # Augment known modern station zones
        for code, zone in KNOWN_STATION_ZONES.items():
            if code not in self.station_zones:
                self.station_zones[code] = zone
                self.station_full_names[code] = f"Station {code}"
        self.known_stations = set(self.station_zones.keys())

        # 2. Train types & names
        train_rows = cur.execute("SELECT train_no, train_name, type_code FROM trains").fetchall()
        self.train_types = {str(t_no).zfill(5): (t_type or "EXP-TRAINS").strip() for t_no, t_name, t_type in train_rows}
        self.train_names = {str(t_no).zfill(5): (t_name or f"Train {t_no}").strip() for t_no, t_name, t_type in train_rows}
        self.known_trains_details = set(self.train_types.keys())

        # 3. Schedule routes
        sched_rows = cur.execute(
            "SELECT train_no, station_no, station_code, arrival_time, departure_time, distance "
            "FROM schedules ORDER BY train_no, station_no"
        ).fetchall()
        conn.close()

        def to_min(t: Optional[str]) -> Optional[int]:
            if not t or ":" not in t:
                return None
            parts = t.split(":")
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                return None

        self.routes: Dict[str, List[Dict[str, Any]]] = {}
        self.route_station_indices: Dict[str, Dict[str, int]] = {}

        current_train_no: Optional[str] = None
        current_stops: List[Dict[str, Any]] = []
        day = 1
        prev_m: Optional[int] = None

        for t_no_raw, s_no, s_code_raw, arr, dep, dist in sched_rows:
            t_no = str(t_no_raw).strip().zfill(5)
            s_code = str(s_code_raw).strip().upper()

            if t_no != current_train_no:
                if current_train_no is not None:
                    self._finalize_train_route(current_train_no, current_stops)
                current_train_no = t_no
                current_stops = []
                day = 1
                prev_m = None

            arr_m = to_min(arr)
            dep_m = to_min(dep)

            # Cumulative day rollover progression
            if arr_m is not None and prev_m is not None and arr_m < prev_m:
                day += 1
            arr_day = day

            check_m = arr_m if arr_m is not None else prev_m
            if dep_m is not None and check_m is not None and dep_m < check_m:
                day += 1
            dep_day = day

            prev_m = dep_m if dep_m is not None else arr_m

            current_stops.append({
                "train_no": t_no,
                "sched_station_no": int(s_no),
                "station_name": s_code,
                "arrival_time": arr or None,
                "departure_time": dep or None,
                "distance_from_origin": int(dist or 0),
                "arr_min": arr_m,
                "dep_min": dep_m,
                "arrival_day": arr_day,
                "departure_day": dep_day,
            })

        if current_train_no is not None:
            self._finalize_train_route(current_train_no, current_stops)

        self.known_trains = set(self.routes.keys())

    def _finalize_train_route(self, train_no: str, stops: List[Dict[str, Any]]) -> None:
        """Compute route section metrics, dwell times, and station indices."""
        self.routes[train_no] = stops
        self.route_station_indices[train_no] = {}

        num_stops = len(stops)
        for i, stop in enumerate(stops):
            self.route_station_indices[train_no][stop["station_name"]] = i

            # Scheduled dwell time in minutes
            if stop["dep_min"] is not None and stop["arr_min"] is not None:
                stop["scheduled_dwell_time"] = (
                    (stop["departure_day"] - stop["arrival_day"]) * 1440 + stop["dep_min"] - stop["arr_min"]
                )
            else:
                stop["scheduled_dwell_time"] = 0.0

            # Next station planned attributes
            if i < num_stops - 1:
                nxt = stops[i + 1]
                dist_diff = nxt["distance_from_origin"] - stop["distance_from_origin"]
                stop["sched_section_distance"] = dist_diff
                if nxt["arr_min"] is not None and stop["dep_min"] is not None:
                    trav_time = (
                        (nxt["arrival_day"] - stop["departure_day"]) * 1440 + nxt["arr_min"] - stop["dep_min"]
                    )
                    stop["sched_section_travel_time"] = trav_time
                    if trav_time > 0 and dist_diff > 0:
                        stop["sched_planned_speed"] = dist_diff / (trav_time / 60.0)
                    else:
                        stop["sched_planned_speed"] = None
                else:
                    stop["sched_section_travel_time"] = None
                    stop["sched_planned_speed"] = None
                stop["sched_next_zone"] = self.station_zones.get(nxt["station_name"], "NR")
            else:
                stop["sched_section_distance"] = None
                stop["sched_section_travel_time"] = None
                stop["sched_planned_speed"] = None
                stop["sched_next_zone"] = None

    def _init_from_raw_csv(self) -> None:
        """Legacy initialization from raw CSV datasets if SQLite database is absent."""
        sched_df, _ = load_schedule()
        stn_df, _ = load_station_master()
        td_df, _ = load_train_details()

        self.station_zones = dict(zip(
            stn_df["station_name"].to_list(),
            stn_df["station_zone"].to_list()
        ))
        self.station_full_names = dict(zip(
            stn_df["station_name"].to_list(),
            stn_df["station_full_name"].to_list()
        ))
        self.known_stations = set(self.station_zones.keys())

        self.train_types = dict(zip(
            td_df["train_no"].to_list(),
            td_df["type_code"].to_list()
        ))
        self.train_names = dict(zip(
            td_df["train_no"].to_list(),
            td_df["train_name"].to_list()
        ))
        self.known_trains_details = set(self.train_types.keys())

        self.routes = {}
        self.route_station_indices = {}

        sorted_sched = sched_df.sort(["train_no", "sched_station_no"])
        for row in sorted_sched.iter_rows(named=True):
            t_no = row["train_no"]
            if t_no not in self.routes:
                self.routes[t_no] = []
                self.route_station_indices[t_no] = {}

            idx = len(self.routes[t_no])
            self.routes[t_no].append(row)
            self.route_station_indices[t_no][row["station_name"]] = idx

        self.known_trains = set(self.routes.keys())

    def validate_train_and_station(self, train_no: str, current_station: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Validate train existence and confirm current station is on its scheduled route.
        Returns:
            Tuple[List[Dict], int]: (train route stops, current station index in route)
        """
        train_no = str(train_no).strip().zfill(5)
        current_station = str(current_station).strip().upper()

        if train_no not in self.routes:
            raise UnknownTrainError(train_no)

        route = self.routes[train_no]
        station_index_map = self.route_station_indices[train_no]

        if current_station not in station_index_map:
            if current_station not in self.known_stations:
                raise UnknownStationError(current_station)
            raise StationNotOnRouteError(train_no, current_station)

        curr_idx = station_index_map[current_station]
        return route, curr_idx

    def _enrich_features_from_timetable(
        self,
        train_no: str,
        journey_date: str,
        current_station: str,
        current_delay: float,
        route: List[Dict[str, Any]],
        curr_idx: int,
        provided_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge provided dynamic features with static timetable attributes to build
        the complete leak-free 30-feature vector expected by the XGBoost models.
        """
        feats = dict(provided_features or {})
        
        curr_stop = route[curr_idx]
        total_stops = len(route)
        curr_seq = curr_stop["sched_station_no"]
        dist_from_origin = curr_stop["distance_from_origin"]
        route_total_dist = route[-1]["distance_from_origin"]
        remaining_dist = max(0, route_total_dist - dist_from_origin)
        stations_remaining = max(0, total_stops - curr_seq)

        # Date parsing
        j_date = parse_journey_date(journey_date)

        # Base defaults from timetable
        defaults = {
            "current_delay": float(current_delay),
            "prev_station_delay": None,
            "prev_delay_2": None,
            "prev_delay_3": None,
            "delay_change": 0.0,
            "delay_change_2_stations": 0.0,
            "delay_change_3_stations": 0.0,
            "current_station_seq": curr_seq,
            "stations_remaining": stations_remaining,
            "dist_from_origin": dist_from_origin,
            "remaining_dist": remaining_dist,
            "journey_progress": (dist_from_origin / route_total_dist) if route_total_dist > 0 else 0.0,
            "route_total_distance": route_total_dist,
            "route_total_stations": total_stops,
            "scheduled_dwell_time": curr_stop.get("scheduled_dwell_time", 0.0) or 0.0,
            "sched_section_distance": curr_stop.get("sched_section_distance", 0.0) or 0.0,
            "sched_section_travel_time": curr_stop.get("sched_section_travel_time", 0.0) or 0.0,
            "sched_planned_speed": curr_stop.get("sched_planned_speed", 0.0) or 0.0,
            "arr_min": curr_stop.get("arr_min", 0) or 0,
            "dep_min": curr_stop.get("dep_min", 0) or 0,
            "arrival_day": curr_stop.get("arrival_day", 1) or 1,
            "departure_day": curr_stop.get("departure_day", 1) or 1,
            "scheduled_hour": (curr_stop.get("dep_min", 0) or curr_stop.get("arr_min", 0) or 0) // 60,
            "day_of_week": j_date.weekday() + 1,  # 1..7
            "month": j_date.month,
            "day": j_date.day,
            "is_weekend": 1 if j_date.weekday() in [5, 6] else 0,
            "type_code": self.train_types.get(train_no, "EXP-TRAINS"),
            "station_zone": self.station_zones.get(current_station, "NR"),
            "next_station_zone": curr_stop.get("sched_next_zone", "NR") or "NR"
        }

        # Populate defaults if missing in provided_features
        for k, v in defaults.items():
            if k not in feats or feats[k] is None:
                feats[k] = v

        # If prev_station_delay is provided, compute delay_change
        if feats.get("prev_station_delay") is not None:
            feats["delay_change"] = feats["current_delay"] - feats["prev_station_delay"]
        if feats.get("prev_delay_2") is not None:
            feats["delay_change_2_stations"] = feats["current_delay"] - feats["prev_delay_2"]
        if feats.get("prev_delay_3") is not None:
            feats["delay_change_3_stations"] = feats["current_delay"] - feats["prev_delay_3"]

        return feats

    def _prepare_feature_dmatrix(
        self,
        features: Dict[str, Any],
        horizon: int
    ) -> xgb.DMatrix:
        """
        Validate feature presence, align column ordering to the training manifest,
        and apply categorical category encoding.
        """
        manifest = self.model_loader.get_manifest(horizon)
        expected_cols = manifest["features"]
        cat_mappings = manifest.get("categorical_categories", {})

        # Check required columns
        missing_cols = [c for c in expected_cols if c not in features]
        if missing_cols:
            raise FeatureValidationError(f"Missing required features for Horizon {horizon}: {missing_cols}")

        row_dict = {}
        for col in expected_cols:
            val = features[col]
            if col in cat_mappings:
                # Validate or categorize
                valid_cats = cat_mappings[col]
                cat_val = str(val) if val is not None else None
                row_dict[col] = pd.Categorical([cat_val], categories=valid_cats)
            else:
                # Numeric float
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    row_dict[col] = [np.nan]
                else:
                    try:
                        row_dict[col] = [float(val)]
                    except (ValueError, TypeError):
                        raise FeatureValidationError(f"Non-numeric value for numeric feature '{col}': {val}")

        df = pd.DataFrame(row_dict)[expected_cols]
        return xgb.DMatrix(df, enable_categorical=True)

    def predict(self, request: PredictionRequest) -> MultiHorizonResponse:
        """
        Produce simultaneous multi-horizon ETA predictions for up to 3 stations ahead.
        
        Parameters:
        -----------
        request : PredictionRequest
            Input payload containing train_no, journey_date, current_station,
            current_delay_minutes, and optional dynamic features.
            
        Returns:
        --------
        MultiHorizonResponse : Structured prediction response with scheduled arrivals and ETAs.
        """
        # Validate journey date
        parse_journey_date(request.journey_date)

        # Validate train & station on route
        route, curr_idx = self.validate_train_and_station(request.train_no, request.current_station)
        total_stops = len(route)
        stops_remaining = (total_stops - 1) - curr_idx

        # Check terminus edge case
        if stops_remaining == 0:
            raise InsufficientRouteRemainingError(
                request.train_no,
                request.current_station,
                stops_remaining=0,
                requested_horizon=1
            )

        # Validate requested horizons
        requested_horizons = request.horizons or [1, 2, 3]
        valid_horizons = []
        for h in requested_horizons:
            if h <= stops_remaining:
                valid_horizons.append(h)

        if not valid_horizons:
            min_requested = min(requested_horizons)
            raise InsufficientRouteRemainingError(
                request.train_no,
                request.current_station,
                stops_remaining=stops_remaining,
                requested_horizon=min_requested
            )

        # Build / enrich full feature vector
        full_features = self._enrich_features_from_timetable(
            train_no=request.train_no,
            journey_date=request.journey_date,
            current_station=request.current_station,
            current_delay=request.current_delay_minutes,
            route=route,
            curr_idx=curr_idx,
            provided_features=request.features
        )

        predictions: List[HorizonPrediction] = []

        for h in valid_horizons:
            target_stop = route[curr_idx + h]
            target_station_name = target_stop["station_name"]
            target_seq = target_stop["sched_station_no"]
            target_arr_day = target_stop.get("arrival_day", 1) or 1
            target_arr_min = target_stop.get("arr_min")
            if target_arr_min is None:
                target_arr_min = parse_time_to_minutes(target_stop.get("arrival_time"))

            # Predict delay with horizon-specific booster
            booster = self.model_loader.get_model(h)
            dmat = self._prepare_feature_dmatrix(full_features, horizon=h)
            raw_pred = float(booster.predict(dmat)[0])
            pred_delay_minutes = round(raw_pred, 1)

            # Compute absolute datetimes for scheduled arrival and predicted ETA
            sched_arr_str, eta_str = calculate_station_eta(
                journey_date=request.journey_date,
                arrival_day=target_arr_day,
                arrival_time_or_minutes=target_arr_min,
                predicted_delay_minutes=pred_delay_minutes
            )

            pred_item = HorizonPrediction(
                horizon=h,
                station=target_station_name,
                station_sequence=target_seq,
                scheduled_arrival=sched_arr_str,
                predicted_delay_minutes=pred_delay_minutes,
                predicted_eta=eta_str,
                confidence=None  # Explicitly null per specification
            )
            predictions.append(pred_item)

        return MultiHorizonResponse(
            train_no=str(request.train_no).zfill(5),
            journey_date=request.journey_date,
            current_station=request.current_station.upper(),
            current_delay_minutes=float(request.current_delay_minutes),
            predictions=predictions
        )

    def predict_from_row(
        self,
        row: Dict[str, Any],
        horizons: List[int] = [1, 2, 3]
    ) -> MultiHorizonResponse:
        """
        Convenience execution on a historical processed record or database dict.
        """
        train_no = str(row["train_no"]).zfill(5)
        journey_date = str(row["date"])
        current_station = str(row["station_name"]).upper()
        current_delay = float(row.get("current_delay", row.get("delay_clean", 0.0)))

        request = PredictionRequest(
            train_no=train_no,
            journey_date=journey_date,
            current_station=current_station,
            current_delay_minutes=current_delay,
            features=row,
            horizons=horizons
        )
        return self.predict(request)
