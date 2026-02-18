"""
Application configuration management.

Centralized configuration using environment variables with sensible defaults.
Supports .env file loading for local development.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration class."""
    
    # Database settings
    DB_PATH: Path = Path(os.getenv("DB_PATH", "data/factory.db"))
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")  # sqlite or postgres
    
    # PostgreSQL settings (if DB_TYPE=postgres)
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "factory")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "factory_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Model settings
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "data/maintenance_model.joblib"))
    MODEL_RETRAIN_INTERVAL_DAYS: int = int(os.getenv("MODEL_RETRAIN_INTERVAL_DAYS", "7"))
    
    # Alert settings
    MAINTENANCE_RISK_THRESHOLD: float = float(os.getenv("MAINTENANCE_RISK_THRESHOLD", "0.6"))
    ENERGY_SPIKE_THRESHOLD_MULTIPLIER: float = float(os.getenv("ENERGY_SPIKE_THRESHOLD", "1.3"))
    
    # UI settings
    AUTO_REFRESH_INTERVAL_SECONDS: int = int(os.getenv("AUTO_REFRESH_INTERVAL", "30"))
    DEFAULT_DATE_RANGE_DAYS: int = int(os.getenv("DEFAULT_DATE_RANGE_DAYS", "30"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[Path] = Path(os.getenv("LOG_FILE", "logs/app.log")) if os.getenv("LOG_FILE") else None
    
    # Feature flags
    ENABLE_REAL_TIME_STREAMING: bool = os.getenv("ENABLE_REAL_TIME_STREAMING", "false").lower() == "true"
    ENABLE_ALERT_NOTIFICATIONS: bool = os.getenv("ENABLE_ALERT_NOTIFICATIONS", "false").lower() == "true"
    
    @classmethod
    def get_db_connection_string(cls) -> str:
        """Get database connection string based on DB_TYPE."""
        if cls.DB_TYPE == "postgres":
            return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        return str(cls.DB_PATH)
    
    @classmethod
    def load_env_file(cls, env_path: Path = Path(".env")) -> None:
        """Load environment variables from .env file."""
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()


# Load .env file if it exists
Config.load_env_file()

