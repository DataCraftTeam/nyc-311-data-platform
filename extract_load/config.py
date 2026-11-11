"""Configuration management for the extract_load pipeline."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            database=os.getenv("POSTGRES_DB", "nyc311"),
        )


@dataclass(frozen=True)
class SocrataConfig:
    endpoint: str
    timeout: int = 30
    max_retries: int = 4
    backoff_factor: float = 1.0

    @classmethod
    def from_env(cls) -> "SocrataConfig":
        return cls(
            endpoint=os.getenv(
                "SOCRATA_ENDPOINT",
                "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
            ),
            timeout=int(os.getenv("SOCRATA_TIMEOUT", "30")),
            max_retries=int(os.getenv("SOCRATA_MAX_RETRIES", "4")),
            backoff_factor=float(os.getenv("SOCRATA_BACKOFF_FACTOR", "1.0")),
        )


@dataclass(frozen=True)
class PipelineConfig:
    db: DatabaseConfig
    socrata: SocrataConfig
    batch_size: int = 5000
    lookback_days: int = 30
    max_records: Optional[int] = None

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        max_rec_str = os.getenv("INGEST_MAX_RECORDS")
        max_rec = int(max_rec_str) if max_rec_str and max_rec_str.strip() else None

        return cls(
            db=DatabaseConfig.from_env(),
            socrata=SocrataConfig.from_env(),
            batch_size=int(os.getenv("INGEST_BATCH_SIZE", "5000")),
            lookback_days=int(os.getenv("INGEST_LOOKBACK_DAYS", "30")),
            max_records=max_rec,
        )
