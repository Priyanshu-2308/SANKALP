"""Dependency injection providers for FastAPI."""

from functools import lru_cache
from pathlib import Path
from sankalp_engine.datasource import TransportDataSource
from sankalp_engine.generator import SeededScheduleGenerator

from .config import settings
from .database import Database


@lru_cache()
def get_data_source() -> TransportDataSource:
    """Provide singleton instance of SeededScheduleGenerator."""
    return SeededScheduleGenerator(
        stations_path=settings.STATIONS_PATH,
        mct_path=settings.MCT_PATH,
        config_path=settings.GENERATOR_CONFIG_PATH,
    )


@lru_cache()
def get_database() -> Database:
    """Provide singleton instance of Database."""
    return Database(db_path=settings.DATABASE_PATH)
