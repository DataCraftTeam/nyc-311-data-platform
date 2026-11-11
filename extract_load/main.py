"""CLI entrypoint for extracting NYC 311 service requests and loading into PostgreSQL Bronze layer."""

import argparse
import logging
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from extract_load.client import SocrataAPIError, SocrataClient
from extract_load.config import PipelineConfig
from extract_load.db import PostgresLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("extract_load")


def run_pipeline(
    batch_size: int,
    max_records: Optional[int],
    lookback_days: int,
    start_date: Optional[str],
    full_refresh: bool,
) -> int:
    """Run the extract and load pipeline.

    Returns:
        Total number of records upserted.
    """
    batch_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info("Starting NYC 311 Ingestion Run [Batch ID: %s]", batch_id)
    config = PipelineConfig.from_env()

    # Initialize Postgres loader
    loader = PostgresLoader(config.db)
    try:
        loader.ensure_bronze_table()
    except Exception as e:
        logger.error("Failed to connect or initialize PostgreSQL bronze table: %s", e)
        raise

    # Determine watermark / start date
    active_watermark: Optional[str] = None
    active_start_date: Optional[str] = start_date

    if full_refresh:
        logger.info("Flag --full-refresh specified: bypassing high-watermark check.")
        if not active_start_date:
            fallback = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            active_start_date = fallback.strftime("%Y-%m-%dT%H:%M:%S.000")
            logger.info("Using default fallback lookback of %d days: %s", lookback_days, active_start_date)
    else:
        existing_watermark = loader.get_watermark()
        if existing_watermark:
            active_watermark = existing_watermark
            logger.info("Found existing Bronze high-watermark: %s", active_watermark)
        else:
            if not active_start_date:
                fallback = datetime.now(timezone.utc) - timedelta(days=lookback_days)
                active_start_date = fallback.strftime("%Y-%m-%dT%H:%M:%S.000")
                logger.info(
                    "Bronze table is empty. Starting initial load with lookback of %d days: %s",
                    lookback_days,
                    active_start_date,
                )
            else:
                logger.info("Bronze table is empty. Starting initial load from specified start date: %s", active_start_date)

    # Initialize Socrata API client
    client = SocrataClient(config.socrata)

    total_records = 0
    page_count = 0

    try:
        for page in client.paginate_records(
            watermark=active_watermark,
            start_date=active_start_date,
            batch_size=batch_size,
            max_records=max_records,
        ):
            page_count += 1
            upserted = loader.upsert_batch(page, batch_id)
            total_records += upserted
            logger.info(
                "Page %d: upserted %d records (Cumulative total: %d)",
                page_count,
                upserted,
                total_records,
            )

    except SocrataAPIError as e:
        logger.error("Socrata API error occurred during extraction: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error during ingestion: %s", e)
        raise

    elapsed = time.time() - start_time
    new_watermark = loader.get_watermark()

    logger.info(
        "Ingestion completed successfully: %d records processed across %d pages in %.2f seconds.",
        total_records,
        page_count,
        elapsed,
    )
    logger.info("Current Bronze high-watermark is now: %s", new_watermark)
    return total_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract NYC 311 service requests from Socrata API and load into PostgreSQL Bronze layer."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Page size per API request (default: INGEST_BATCH_SIZE or 5000).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Maximum total records to extract in this run (default: unlimited / all new).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="Number of days to look back on initial run if Bronze table is empty (default: 30).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Explicit starting created_date timestamp (e.g. '2026-01-01T00:00:00.000').",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Bypass high-watermark check and re-ingest starting from lookback-days or start-date.",
    )

    args = parser.parse_args()
    config = PipelineConfig.from_env()

    batch_size = args.batch_size or config.batch_size
    max_records = args.max_records if args.max_records is not None else config.max_records
    lookback_days = args.lookback_days or config.lookback_days

    try:
        run_pipeline(
            batch_size=batch_size,
            max_records=max_records,
            lookback_days=lookback_days,
            start_date=args.start_date,
            full_refresh=args.full_refresh,
        )
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
