"""
FastAPI application for SIH 26028 Live Railway ETA Integration.
Connects verified RailRadar live pipeline to trained multi-horizon XGBoost models (H1, H2, H3).

Endpoints:
- GET /api/health
- GET /api/train/{train_no}/eta (Live RailRadar ETA endpoint with TTL cache)
- GET /api/demo/train/{train_no}/eta (Deterministic mock endpoint)
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.live.config import (
    is_live_configured,
    mask_secret,
    get_api_key,
    RAILRADAR_CACHE_TTL_SECONDS,
    get_cors_origins
)
from app.live.service import LiveETAService
from app.live.api_client import MockRailRadarClient, RailRadarLiveClient
from app.live.cache import eta_cache
from app.live.schedule_search import (
    search_stations,
    search_train_routes,
    get_train_route_schedule,
    get_station_coordinates,
    StationSearchResult,
    TrainSearchResponse,
    TrainRouteScheduleResponse
)
from ml.inference.predictor import MultiHorizonETAPredictor
from app.live.exceptions import (
    APIKeyMissingError,
    TrainNotFoundError,
    TrainNotRunningError,
    APITimeoutError,
    APIAuthenticationError,
    APIResponseMalformedError,
    LiveInferenceError,
    LiveAPIError
)
from ml.inference.schemas import (
    InferenceError,
    UnknownTrainError,
    UnknownStationError,
    StationNotOnRouteError,
    InsufficientRouteRemainingError,
    InvalidJourneyDateError,
    FeatureValidationError,
    ModelLoadError
)

# Safe logging setup: only logs public route metadata, response time, and status codes.
# NEVER logs Authorization headers, raw secrets, or payload tokens.
logger = logging.getLogger("sih26028.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [API] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def create_app() -> FastAPI:
    """Factory creating configured FastAPI instance."""
    app = FastAPI(
        title="SIH 26028 - Dynamic Train ETA Live Inference API",
        description=(
            "Multi-horizon ETA prediction service integrating live railway tracking (RailRadar) "
            "with XGBoost inference models (H1, H2, H3)."
        ),
        version="1.0.0"
    )

    # Enable CORS for frontend dashboard / external consumers
    cors_origins = get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_shared_predictor() -> MultiHorizonETAPredictor:
        if not hasattr(app.state, "predictor") or app.state.predictor is None:
            app.state.predictor = MultiHorizonETAPredictor()
        return app.state.predictor

    def get_demo_service() -> LiveETAService:
        client = getattr(app.state, "demo_client", None) or MockRailRadarClient()
        return LiveETAService(client=client, predictor=get_shared_predictor())

    def get_live_service() -> LiveETAService:
        if not is_live_configured():
            raise APIKeyMissingError("RailRadar API key has not been configured.")
        client = getattr(app.state, "live_client", None)
        if client is None:
            client = RailRadarLiveClient()
        return LiveETAService(client=client, predictor=get_shared_predictor())

    # -------------------------------------------------------------------------
    # Health & System Status Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/health", tags=["System"])
    def health_check() -> Dict[str, Any]:
        """Health check endpoint displaying system, cache, and live configuration status."""
        configured = is_live_configured()
        return {
            "status": "healthy",
            "service": "SIH-26028 Live ETA Inference API",
            "live_api_configured": configured,
            "api_key_status": mask_secret(get_api_key()),
            "cache_ttl_seconds": RAILRADAR_CACHE_TTL_SECONDS,
            "cache_stats": eta_cache.stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # -------------------------------------------------------------------------
    # Live Train ETA Prediction Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/train/{train_no}/eta", tags=["Live ETA"])
    def get_live_train_eta(
        train_no: str,
        date: Optional[str] = Query(None, description="Journey date YYYY-MM-DD (optional)")
    ):
        """
        Produce live multi-horizon ETA predictions using RailRadar tracking data.
        Integrates in-memory TTL caching to protect upstream API rate limits.
        """
        start_time = time.monotonic()
        clean_train = str(train_no).strip()

        # 1. Train number format validation
        if not clean_train.isdigit() or len(clean_train) not in [4, 5]:
            logger.warning("Invalid train format requested: '%s'", clean_train)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid train number '{clean_train}'. Expected a 4 or 5 digit numeric train number."
            )

        # 2. Strict API key configuration gate
        if not is_live_configured():
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "live_api_not_configured",
                    "message": "RailRadar API key has not been configured."
                }
            )

        # 3. Check in-memory TTL Cache
        cached_resp = eta_cache.get(clean_train, date)
        if cached_resp is not None:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            logger.info("Live ETA [CACHE HIT] train=%s status=200 elapsed=%.1fms", clean_train, elapsed_ms)
            return cached_resp

        # 4. Invoke Live ETAService with exact exception mapping
        try:
            service = get_live_service()
            response = service.predict_for_train(train_no=clean_train, journey_date=date, force_mock=False)
            resp_dict = response.to_dict()

            # Store in cache
            eta_cache.set(clean_train, resp_dict, date)
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            logger.info("Live ETA [LIVE HIT] train=%s status=200 elapsed=%.1fms", clean_train, elapsed_ms)
            return resp_dict

        except (TrainNotFoundError, UnknownTrainError) as e:
            logger.warning("Train not found: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Train '{clean_train}' not found in timetable or tracking system.")
        except TrainNotRunningError as e:
            logger.warning("Train not running: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except StationNotOnRouteError as e:
            logger.warning("Station not on route: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Schedule mapping error: {str(e)}")
        except InsufficientRouteRemainingError as e:
            logger.warning("Insufficient route remaining: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Insufficient route remaining: {str(e)}")
        except (UnknownStationError, FeatureValidationError, InvalidJourneyDateError) as e:
            logger.warning("Validation failure: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except APITimeoutError as e:
            logger.error("RailRadar timeout: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="RailRadar live API request timed out.")
        except APIAuthenticationError as e:
            logger.error("RailRadar auth failure: train=%s", clean_train)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="RailRadar authentication failed. Please check configured credentials.")
        except APIResponseMalformedError as e:
            logger.error("RailRadar malformed response: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Invalid response from RailRadar API: {e.details}")
        except ModelLoadError as e:
            logger.critical("Model load failure: error=%s", str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ETA model loading failure.")
        except (LiveInferenceError, InferenceError) as e:
            logger.error("Inference failure: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ETA model inference execution failed.")
        except LiveAPIError as e:
            logger.error("RailRadar upstream API failure: train=%s status=%s error=%s", clean_train, e.status_code, str(e))
            status_code = e.status_code if e.status_code and e.status_code >= 400 else status.HTTP_502_BAD_GATEWAY
            raise HTTPException(status_code=status_code, detail=f"RailRadar upstream error: {e.message}")
        except Exception as e:
            logger.error("Unexpected error: train=%s error=%s", clean_train, str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing live train ETA.")

    # -------------------------------------------------------------------------
    # Demo / Mock Train ETA Prediction Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/demo/train/{train_no}/eta", tags=["Demo ETA"])
    def get_demo_train_eta(
        train_no: str,
        date: Optional[str] = Query(None, description="Journey date YYYY-MM-DD (optional)")
    ):
        """
        Produce deterministic multi-horizon ETA predictions using synthetic mock data.
        Always accessible for frontend evaluation without consuming external API quota.
        """
        clean_train = str(train_no).strip()
        if not clean_train.isdigit() or len(clean_train) not in [4, 5]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid train number '{clean_train}'. Expected a 4 or 5 digit numeric train number."
            )

        try:
            demo_service = get_demo_service()
            response = demo_service.predict_for_train(train_no=clean_train, journey_date=date, force_mock=True)
            return response.to_dict()

        except (TrainNotFoundError, UnknownTrainError) as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Train '{clean_train}' not found in demo database.")
        except (StationNotOnRouteError, InsufficientRouteRemainingError) as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except (LiveInferenceError, InferenceError) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

    # -------------------------------------------------------------------------
    # Station Autocomplete & Master Lookup Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/stations/search", response_model=List[StationSearchResult], tags=["Schedule Search"])
    def get_station_autocomplete(
        q: str = Query("", description="Station code or name query"),
        limit: int = Query(10, ge=1, le=50, description="Max station suggestions")
    ):
        """
        Search stations across Indian Railways master dataset for autocomplete and selection.
        Matches station codes (e.g. NDLS, ADI) and station/city names.
        """
        try:
            return search_stations(query=q, limit=limit)
        except Exception as e:
            logger.error("Station search error: query='%s' error=%s", q, str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to search stations.")

    # -------------------------------------------------------------------------
    # Train Route Search Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/trains/search", response_model=TrainSearchResponse, tags=["Schedule Search"])
    def search_trains(
        from_station: str = Query(..., alias="from", description="Origin station code or name"),
        to_station: str = Query(..., alias="to", description="Destination station code or name"),
        date: Optional[str] = Query(None, description="Journey date YYYY-MM-DD (optional)")
    ):
        """
        Search real railway schedules for trains connecting origin and destination.
        Guarantees origin occurs BEFORE destination along the scheduled route.
        Returns complete information for train result cards.
        """
        start_time = time.monotonic()
        clean_from = from_station.strip()
        clean_to = to_station.strip()

        # Log public route parameters only (never logs secrets)
        logger.info("Train route search requested: from=%s to=%s date=%s", clean_from, clean_to, date)

        try:
            result = search_train_routes(
                from_input=clean_from,
                to_input=clean_to,
                journey_date=date
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            logger.info(
                "Train route search [HIT] from=%s to=%s found=%d elapsed=%.1fms",
                clean_from, clean_to, result.count, elapsed_ms
            )
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error in train search: from=%s to=%s error=%s", clean_from, clean_to, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error processing train search."
            )

    # -------------------------------------------------------------------------
    # Train Scheduled Route Stops Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/train/{train_no}/route", response_model=TrainRouteScheduleResponse, tags=["Schedule Search"])
    def get_train_route(train_no: str):
        """
        Return all real scheduled stops for a train from origin to terminus.
        Used by Live Tracking to display complete route progression.
        """
        clean_no = str(train_no).strip()
        route = get_train_route_schedule(clean_no)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route schedule for train '{clean_no}' not found in database."
            )
        return route

    # -------------------------------------------------------------------------
    # Station Coordinates Lookup Endpoint
    # -------------------------------------------------------------------------
    @app.get("/api/station/{station_code}/coordinates", tags=["Schedule Search"])
    def get_station_coords(station_code: str):
        """
        Return real geographic latitude & longitude coordinates for a railway station.
        Used by the interactive railway map.
        """
        clean_code = str(station_code).strip().upper()
        coords = get_station_coordinates(clean_code)
        if not coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Coordinates for station '{clean_code}' are unavailable."
            )
        return coords

    return app


# Module-level application instance for uvicorn
app = create_app()
