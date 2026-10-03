"""Configuration settings for SANKALP API."""

from pathlib import Path


class Settings:
    PROJECT_NAME: str = "SANKALP Travel Recovery API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    DATA_DIR: Path = Path("data")
    STATIONS_PATH: Path = Path("data/stations.json")
    MCT_PATH: Path = Path("data/connections_mct.json")
    GENERATOR_CONFIG_PATH: Path = Path("data/generator_config.json")
    DATABASE_PATH: Path = Path("data/sankalp.sqlite3")
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sankalp.vercel.app",
    ]

settings = Settings()
