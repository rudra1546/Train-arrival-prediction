"""
Live ETA Service integration layer for SIH 26028.
Connects the live adapter (or mock client) to the existing offline MultiHorizonETAPredictor.
Reuses existing feature enrichment, timetable lookups, XGBoost boosters, and ETA calculations.
"""

from typing import Optional, Dict, Any
from pathlib import Path

from ml.utils.config import MODELS_DIR
from ml.inference.predictor import MultiHorizonETAPredictor
from ml.inference.schemas import PredictionRequest, MultiHorizonResponse, InferenceError
from app.live.schemas import (
    NormalizedTrainState,
    LiveTrainETAResponse,
    LiveHorizonETA,
    FastAPITrainETAResponse,
    CurrentStationPayload,
    HorizonPredictionPayload
)
from app.live.api_client import (
    BaseRailRadarClient,
    RailRadarLiveClient,
    MockRailRadarClient,
    MOCK_LABEL
)
from app.live.config import is_live_configured
from app.live.exceptions import (
    APIKeyMissingError,
    LiveInferenceError,
    LiveAPIError
)


class LiveETAService:
    """
    Orchestration service linking live/mock tracking data to the multi-horizon ETA inference pipeline.
    """

    def __init__(
        self,
        client: Optional[BaseRailRadarClient] = None,
        predictor: Optional[MultiHorizonETAPredictor] = None,
        models_dir: Path = MODELS_DIR
    ):
        self.client = client
        self.predictor = predictor or MultiHorizonETAPredictor(models_dir=models_dir)

    def predict_for_train(
        self,
        train_no: str,
        journey_date: Optional[str] = None,
        force_mock: bool = False
    ) -> LiveTrainETAResponse:
        """
        Orchestrate end-to-end live prediction:
        1. Fetch state via client (live or mock)
        2. Convert to normalized train state
        3. Pass to existing feature builder & XGBoost models (H1, H2, H3)
        4. Return unified LiveTrainETAResponse
        """
        # Determine client to use
        active_client = self.client
        if force_mock or active_client is None:
            if force_mock:
                active_client = MockRailRadarClient()
            else:
                if is_live_configured():
                    active_client = RailRadarLiveClient()
                else:
                    active_client = MockRailRadarClient()

        # Step 1 & 2: Fetch normalized train state
        state: NormalizedTrainState = active_client.get_live_train_status(
            train_no=train_no,
            journey_date=journey_date
        )

        # Step 3: Connect to existing feature builder & inference service
        # Supply extracted lag features from live state; predictor fills timetable features
        pred_req = PredictionRequest(
            train_no=state.train_no,
            journey_date=state.journey_date,
            current_station=state.current_station,
            current_delay_minutes=state.current_delay_minutes,
            features=state.to_feature_dict(),
            horizons=[1, 2, 3]
        )

        try:
            inference_resp: MultiHorizonResponse = self.predictor.predict(pred_req)
        except (InferenceError, LiveAPIError):
            raise
        except Exception as e:
            raise LiveInferenceError(f"MultiHorizonETAPredictor failed on live state for train {state.train_no}: {e}")

        # Step 4: Map to unified clean response schema
        current_stn_code = state.current_station
        current_stn_name = (
            state.current_station_name
            or getattr(self.predictor, "station_full_names", {}).get(current_stn_code)
            or current_stn_code
        )
        train_name = (
            state.train_name
            or getattr(self.predictor, "train_names", {}).get(state.train_no)
            or f"Express Train {state.train_no}"
        )
        status_str = state.current_status or "running"

        horizon_predictions = [
            HorizonPredictionPayload(
                horizon=hp.horizon,
                station=hp.station,
                scheduled_arrival=hp.scheduled_arrival.replace(" ", "T") if " " in hp.scheduled_arrival else hp.scheduled_arrival,
                predicted_delay_minutes=round(float(hp.predicted_delay_minutes), 2),
                predicted_eta=hp.predicted_eta.replace(" ", "T") if " " in hp.predicted_eta else hp.predicted_eta
            )
            for hp in inference_resp.predictions
        ]

        return FastAPITrainETAResponse(
            success=True,
            train_no=state.train_no,
            train_name=train_name,
            status=status_str,
            journey_date=state.journey_date,
            current_station=CurrentStationPayload(
                code=current_stn_code,
                name=current_stn_name,
                delay_minutes=round(float(state.current_delay_minutes), 2)
            ),
            predictions=horizon_predictions
        )
