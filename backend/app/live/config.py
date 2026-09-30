"""
Configuration module for Live Railway API integration.
Manages API key injection, environment variable loading, and security masking.
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(dotenv_path: Optional[Path] = None, override: bool = False) -> None:
    """Simple parser to load .env into os.environ if python-dotenv is not installed."""
    if dotenv_path is None:
        dotenv_path = Path("e:/train/.env")
    
    if dotenv_path.exists():
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key:
                    if override or key not in os.environ:
                        os.environ[key] = val


# Load local .env on import
load_env_file()


def get_api_key() -> Optional[str]:
    """Retrieve the RailRadar API key from environment, or None if unconfigured."""
    key = os.getenv("RAILRADAR_API_KEY", "").strip()
    if not key or key in ["", "placeholder", "YOUR_API_KEY", "rr_live_YOUR_API_KEY"]:
        return None
    return key


def is_live_configured() -> bool:
    """Check if a valid, non-placeholder RailRadar API key is configured in the environment."""
    return get_api_key() is not None


def mask_secret(secret: Optional[str]) -> str:
    """Mask secret for safe logging. Never returns or logs plaintext API keys."""
    if not secret:
        return "<UNCONFIGURED>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


# Global live service parameters
RAILRADAR_BASE_URL: str = os.getenv("RAILRADAR_BASE_URL", "https://api.railradar.in/v1").rstrip("/")
RAILRADAR_TIMEOUT_SECONDS: float = float(os.getenv("RAILRADAR_TIMEOUT_SECONDS", "10.0"))
RAILRADAR_CACHE_TTL_SECONDS: float = float(os.getenv("RAILRADAR_CACHE_TTL_SECONDS", "30.0"))
APP_ENV: str = os.getenv("APP_ENV", "development").lower()


def get_cors_origins() -> list[str]:
    """Parse comma-separated CORS_ORIGINS from environment into a list of origins."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173").strip()
    if not raw:
        return ["http://localhost:5173"]
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins if origins else ["http://localhost:5173"]


CORS_ORIGINS: list[str] = get_cors_origins()

