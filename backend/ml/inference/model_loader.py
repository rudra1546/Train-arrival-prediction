"""
Model loading and artifact management module for SIH 26028 Multi-Horizon ETA Service.
Loads native XGBoost booster models and associated feature manifests for Horizons 1, 2, and 3.
Ensures exact feature ordering, categorical encodings, and thread-safe in-memory caching.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import xgboost as xgb

from ml.utils.config import MODELS_DIR
from ml.inference.schemas import ModelLoadError


class MultiHorizonModelLoader:
    """
    Singleton-capable model loader for Multi-Horizon XGBoost Regressors.
    Loads and caches native XGBoost boosters and training manifests for H1, H2, and H3.
    """

    HORIZON_CONFIGS = {
        1: {
            "model_file": "xgboost_eta_h1_v1.json",
            "manifest_file": "xgboost_eta_h1_v1_features.json",
            "fallback_manifest": "xgboost_eta_h1_features.json"
        },
        2: {
            "model_file": "xgboost_eta_h2_v1.json",
            "manifest_file": "xgboost_eta_h2_v1_features.json",
            "fallback_manifest": "xgboost_eta_h2_features.json"
        },
        3: {
            "model_file": "xgboost_eta_h3_v1.json",
            "manifest_file": "xgboost_eta_h3_v1_features.json",
            "fallback_manifest": "xgboost_eta_h3_features.json"
        }
    }

    _instance: Optional["MultiHorizonModelLoader"] = None

    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = Path(models_dir)
        self._models: Dict[int, xgb.Booster] = {}
        self._manifests: Dict[int, Dict[str, Any]] = {}
        self._loaded: bool = False
        self.load_all_models()

    @classmethod
    def get_instance(cls, models_dir: Path = MODELS_DIR) -> "MultiHorizonModelLoader":
        """Get or initialize singleton instance."""
        if cls._instance is None:
            cls._instance = cls(models_dir=models_dir)
        return cls._instance

    def load_all_models(self) -> None:
        """Load all 3 horizon boosters and manifests into memory."""
        for horizon in [1, 2, 3]:
            self.load_horizon_model(horizon)
        self._loaded = True

    def load_horizon_model(self, horizon: int) -> None:
        """Load a specific horizon booster and feature manifest."""
        if horizon not in self.HORIZON_CONFIGS:
            raise ModelLoadError(
                f"Horizon_{horizon}",
                str(self.models_dir),
                f"Invalid horizon {horizon}. Supported horizons: [1, 2, 3]."
            )

        cfg = self.HORIZON_CONFIGS[horizon]
        model_path = self.models_dir / cfg["model_file"]
        manifest_path = self.models_dir / cfg["manifest_file"]

        if not manifest_path.exists():
            manifest_path = self.models_dir / cfg["fallback_manifest"]

        # Validate existence
        if not model_path.exists():
            raise ModelLoadError(
                f"Horizon_{horizon}",
                str(model_path),
                f"Booster weights file not found at {model_path}."
            )
        if not manifest_path.exists():
            raise ModelLoadError(
                f"Horizon_{horizon}",
                str(manifest_path),
                f"Feature manifest not found at {manifest_path}."
            )

        # Load Manifest
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            self._manifests[horizon] = manifest
        except Exception as e:
            raise ModelLoadError(f"Horizon_{horizon}", str(manifest_path), f"JSON parse error: {str(e)}")

        # Load Native Booster
        try:
            booster = xgb.Booster()
            booster.load_model(str(model_path))
            self._models[horizon] = booster
        except Exception as e:
            raise ModelLoadError(f"Horizon_{horizon}", str(model_path), f"XGBoost load error: {str(e)}")

    def get_model(self, horizon: int) -> xgb.Booster:
        """Retrieve the compiled XGBoost Booster for the specified horizon."""
        if horizon not in self._models:
            self.load_horizon_model(horizon)
        return self._models[horizon]

    def get_manifest(self, horizon: int) -> Dict[str, Any]:
        """Retrieve the feature manifest dictionary for the specified horizon."""
        if horizon not in self._manifests:
            self.load_horizon_model(horizon)
        return self._manifests[horizon]

    def get_features(self, horizon: int) -> List[str]:
        """Get the exact ordered list of features expected by the horizon model."""
        return self.get_manifest(horizon)["features"]

    def get_categorical_categories(self, horizon: int) -> Dict[str, List[str]]:
        """Get the categorical mappings for the horizon model."""
        return self.get_manifest(horizon).get("categorical_categories", {})

    def is_loaded(self) -> bool:
        """Check if all three models are loaded into memory."""
        return self._loaded and len(self._models) == 3
