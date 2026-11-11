"""PostgreSQL database operations for bronze.raw_nyc_311."""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional
import psycopg2
from psycopg2.extras import execute_values

from extract_load.config import DatabaseConfig

logger = logging.getLogger(__name__)

BRONZE_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "due_date",
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "status",
    "resolution_description",
    "borough",
    "incident_zip",
    "latitude",
    "longitude",
    "open_data_channel_type",
]


class PostgresLoader:
    """Manages database connection, table initialization, watermark retrieval, and upserts."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def get_connection(self) -> Iterator[psycopg2.extensions.connection]:
        """Context manager yielding an active database connection."""
        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            dbname=self.config.database,
            connect_timeout=10,
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_bronze_table(self) -> None:
        """Create bronze schema and raw_nyc_311 table with required constraints if missing."""
        ddl = """
        CREATE SCHEMA IF NOT EXISTS bronze;

        CREATE TABLE IF NOT EXISTS bronze.raw_nyc_311 (
            unique_key TEXT PRIMARY KEY,
            created_date TEXT,
            closed_date TEXT,
            due_date TEXT,
            agency TEXT,
            agency_name TEXT,
            complaint_type TEXT,
            descriptor TEXT,
            status TEXT,
            resolution_description TEXT,
            borough TEXT,
            incident_zip TEXT,
            latitude TEXT,
            longitude TEXT,
            open_data_channel_type TEXT,
            _ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            _source_batch_id UUID
        );

        CREATE INDEX IF NOT EXISTS idx_raw_nyc_311_created_date
            ON bronze.raw_nyc_311 (created_date);
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        logger.info("Verified bronze schema and bronze.raw_nyc_311 table structure.")

    def get_watermark(self) -> Optional[str]:
        """Retrieve the maximum created_date currently stored in bronze.raw_nyc_311.

        Returns:
            Max created_date string or None if table is empty.
        """
        query = "SELECT MAX(created_date) FROM bronze.raw_nyc_311 WHERE created_date IS NOT NULL;"
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
                if row and row[0]:
                    return str(row[0])
        return None

    def upsert_batch(self, records: List[Dict[str, Any]], batch_id: str) -> int:
        """Upsert a batch of Socrata records into bronze.raw_nyc_311.

        Args:
            records: List of dictionaries from Socrata API.
            batch_id: Unique UUID string for this ingestion run.

        Returns:
            Number of rows upserted.
        """
        if not records:
            return 0

        now = datetime.now(timezone.utc)
        clean_rows = []
        skipped = 0

        for record in records:
            ukey = record.get("unique_key")
            if not ukey or not str(ukey).strip():
                skipped += 1
                continue

            row = [str(ukey).strip()]
            for col in BRONZE_COLUMNS[1:]:
                val = record.get(col)
                row.append(str(val) if val is not None else None)

            # Metadata columns
            row.append(now)
            row.append(batch_id)
            clean_rows.append(tuple(row))

        if skipped > 0:
            logger.warning(
                "Skipped %d records missing a valid unique_key in batch %s.",
                skipped,
                batch_id,
            )

        if not clean_rows:
            return 0

        cols_str = ", ".join(BRONZE_COLUMNS + ["_ingested_at", "_source_batch_id"])

        update_assignments = [
            f"{col} = EXCLUDED.{col}" for col in BRONZE_COLUMNS if col != "unique_key"
        ]
        update_assignments.append("_ingested_at = EXCLUDED._ingested_at")
        update_assignments.append("_source_batch_id = EXCLUDED._source_batch_id")
        update_clause = ", ".join(update_assignments)

        insert_sql = f"""
        INSERT INTO bronze.raw_nyc_311 ({cols_str})
        VALUES %s
        ON CONFLICT (unique_key) DO UPDATE SET
            {update_clause};
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_sql, clean_rows, page_size=1000)

        return len(clean_rows)
