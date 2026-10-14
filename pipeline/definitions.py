from datetime import datetime, timedelta, timezone
from dagster import (
    asset,
    define_asset_job,
    schedule,
    RunRequest,
    Definitions,
    MonthlyPartitionsDefinition,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
)
from pipeline.extract import fetch_window
from pipeline.load import get_conn, upsert_rows

monthly = MonthlyPartitionsDefinition(start_date="2020-01-01")


@asset(partitions_def=monthly, group_name="bronze")
def bronze_nyc_311(context: AssetExecutionContext) -> MaterializeResult:
    window = context.partition_time_window
    start = window.start.strftime("%Y-%m-%dT00:00:00")
    end = window.end.strftime("%Y-%m-%dT00:00:00")

    total = 0
    conn = get_conn()
    try:
        for page in fetch_window(start, end):
            total += upsert_rows(conn, page, context.partition_key)
            context.log.info(f"{context.partition_key}: {total} rows so far")
    finally:
        conn.close()

    return MaterializeResult(metadata={"rows_loaded": MetadataValue.int(total)})


bronze_job = define_asset_job(
    "bronze_job", selection=[bronze_nyc_311], partitions_def=monthly
)


@schedule(job=bronze_job, cron_schedule="0 3 * * *")
def daily_refresh():
    now = datetime.now(timezone.utc)
    this_m = now.strftime("%Y-%m-01")
    prev_m = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-01")
    return [
        RunRequest(partition_key=k, run_key=f"{k}-{now:%Y%m%d}")
        for k in (prev_m, this_m)
    ]


defs = Definitions(
    assets=[bronze_nyc_311], jobs=[bronze_job], schedules=[daily_refresh]
)
