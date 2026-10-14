import os
import psycopg2
from psycopg2.extras import execute_values
from pipeline.extract import COLUMNS

def get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "nyc311"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )

def upsert_rows(conn, rows, partition_key: str) -> int:
    cols = COLUMNS + ["_source_partition"]
    values = [[r[c] for c in COLUMNS] + [partition_key] for r in rows]
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "unique_key")
    sql = f"""
        INSERT INTO bronze.nyc_311_raw ({", ".join(cols)}, _ingested_at)
        VALUES %s
        ON CONFLICT (unique_key) DO UPDATE SET {updates}, _ingested_at = now()
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, values, template="(" + ",".join(["%s"] * len(cols)) + ", now())")
    conn.commit()
    return len(values)