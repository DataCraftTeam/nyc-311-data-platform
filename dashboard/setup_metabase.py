"""
Set up the NYC 311 dashboard in a local Metabase.

Creates the admin user on first run, connects Metabase to the warehouse,
and builds one dashboard with a chart per business question.
Safe to re-run: the dashboard and its questions are rebuilt each time.

Usage (Metabase and Postgres must be running, see `make docker-up`):
    make dashboard
"""

import os
import sys
import time

import requests

METABASE_URL = os.getenv("METABASE_URL", f"http://localhost:{os.getenv('METABASE_PORT', '3000')}")
ADMIN_EMAIL = os.environ["METABASE_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["METABASE_ADMIN_PASSWORD"]

DATABASE_NAME = "NYC 311 Warehouse"
DASHBOARD_NAME = "NYC 311 Service Requests"
COLLECTION_NAME = "NYC 311"

# Metabase runs in Docker, so it reaches Postgres by its compose service name
WAREHOUSE = {
    "host": "postgres",
    "port": 5432,
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
    "ssl": False,
}

# (name, display, SQL, visualization settings, (col, row, width, height))
QUESTIONS = [
    (
        "Total requests",
        "scalar",
        "SELECT COUNT(*) AS requests FROM gold.fct_service_requests",
        {},
        (0, 0, 6, 3),
    ),
    (
        "Open requests",
        "scalar",
        "SELECT SUM(open_count) AS open_requests FROM gold.mart_open_backlog",
        {},
        (6, 0, 6, 3),
    ),
    (
        "Median resolution time (hours)",
        "scalar",
        """
        SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_time_hours)::NUMERIC, 1) AS median_hours
        FROM gold.fct_service_requests
        WHERE resolution_time_hours IS NOT NULL
        """,
        {},
        (12, 0, 6, 3),
    ),
    (
        "Closed before created (data issue)",
        "scalar",
        "SELECT COUNT(*) AS requests FROM gold.fct_service_requests WHERE has_invalid_close_date",
        {},
        (18, 0, 6, 3),
    ),
    (
        "Q1 - Most common complaint types",
        "row",
        """
        SELECT complaint_type, SUM(request_count) AS requests
        FROM gold.mart_complaint_trends
        GROUP BY complaint_type
        ORDER BY requests DESC
        LIMIT 10
        """,
        {"graph.dimensions": ["complaint_type"], "graph.metrics": ["requests"]},
        (0, 3, 12, 8),
    ),
    (
        "Q2 - Monthly trend of the top 5 complaint types",
        "line",
        """
        WITH top_types AS (
            SELECT complaint_type
            FROM gold.mart_complaint_trends
            GROUP BY complaint_type
            ORDER BY SUM(request_count) DESC
            LIMIT 5
        )
        SELECT month_start, complaint_type, request_count
        FROM gold.mart_complaint_trends
        WHERE complaint_type IN (SELECT complaint_type FROM top_types)
        ORDER BY month_start
        """,
        {"graph.dimensions": ["month_start", "complaint_type"], "graph.metrics": ["request_count"]},
        (12, 3, 12, 8),
    ),
    (
        "Q3 - Median resolution time by agency (hours)",
        "bar",
        """
        SELECT
            a.agency,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.resolution_time_hours)::NUMERIC, 1) AS median_hours,
            COUNT(*) AS closed_requests
        FROM gold.fct_service_requests f
        JOIN gold.dim_agency a ON a.agency_key = f.agency_key
        WHERE f.resolution_time_hours IS NOT NULL
        GROUP BY a.agency
        ORDER BY closed_requests DESC
        LIMIT 10
        """,
        {"graph.dimensions": ["agency"], "graph.metrics": ["median_hours"]},
        (0, 11, 12, 8),
    ),
    (
        "Q4 - Open requests by borough",
        "bar",
        """
        SELECT borough, SUM(open_count) AS open_requests
        FROM gold.mart_open_backlog
        GROUP BY borough
        ORDER BY open_requests DESC
        """,
        {"graph.dimensions": ["borough"], "graph.metrics": ["open_requests"]},
        (12, 11, 12, 8),
    ),
    (
        "Q4 - Oldest open requests by agency and complaint type",
        "table",
        """
        SELECT agency, complaint_type, borough, open_count, avg_days_open
        FROM gold.mart_open_backlog
        ORDER BY open_count DESC
        LIMIT 20
        """,
        {},
        (0, 19, 24, 8),
    ),
]


def wait_for_metabase(timeout_seconds=300):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            if requests.get(f"{METABASE_URL}/api/health", timeout=5).json().get("status") == "ok":
                return
        except requests.RequestException:
            pass
        print("Waiting for Metabase to start...")
        time.sleep(5)
    sys.exit(f"Metabase did not start at {METABASE_URL}")


def get_session():
    properties = requests.get(f"{METABASE_URL}/api/session/properties", timeout=30).json()
    if properties.get("setup-token") and not properties.get("has-user-setup"):
        response = requests.post(f"{METABASE_URL}/api/setup", timeout=60, json={
            "token": properties["setup-token"],
            "user": {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "first_name": "NYC311",
                "last_name": "Admin",
                "site_name": "NYC 311",
            },
            "prefs": {"site_name": "NYC 311", "site_locale": "en", "allow_tracking": False},
        })
        response.raise_for_status()
        print(f"Created Metabase admin user {ADMIN_EMAIL}")
        return response.json()["id"]

    response = requests.post(f"{METABASE_URL}/api/session", timeout=30,
                             json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    response.raise_for_status()
    return response.json()["id"]


class Metabase:
    def __init__(self, session_id):
        self.http = requests.Session()
        self.http.headers["X-Metabase-Session"] = session_id

    def call(self, method, path, **kwargs):
        response = self.http.request(method, f"{METABASE_URL}/api{path}", timeout=60, **kwargs)
        if not response.ok:
            sys.exit(f"{method} {path} failed ({response.status_code}): {response.text[:500]}")
        return response.json() if response.content else None


def get_or_create_database(mb):
    databases = mb.call("GET", "/database")
    databases = databases.get("data", databases)
    for db in databases:
        if db["name"] == DATABASE_NAME:
            return db["id"]
    db = mb.call("POST", "/database", json={"engine": "postgres", "name": DATABASE_NAME, "details": WAREHOUSE})
    print(f"Connected Metabase to {WAREHOUSE['dbname']} as '{DATABASE_NAME}'")
    return db["id"]


def get_or_create_collection(mb):
    for collection in mb.call("GET", "/collection"):
        if collection.get("name") == COLLECTION_NAME and not collection.get("archived"):
            return collection["id"]
    return mb.call("POST", "/collection", json={"name": COLLECTION_NAME})["id"]


def archive_previous_version(mb, collection_id):
    for item in mb.call("GET", f"/collection/{collection_id}/items").get("data", []):
        if item["model"] == "dashboard":
            mb.call("PUT", f"/dashboard/{item['id']}", json={"archived": True})
        elif item["model"] == "card":
            mb.call("PUT", f"/card/{item['id']}", json={"archived": True})


def main():
    wait_for_metabase()
    mb = Metabase(get_session())
    database_id = get_or_create_database(mb)
    collection_id = get_or_create_collection(mb)
    archive_previous_version(mb, collection_id)

    dashboard = mb.call("POST", "/dashboard", json={
        "name": DASHBOARD_NAME,
        "description": "Answers the four business questions from the gold layer.",
        "collection_id": collection_id,
    })

    dashcards = []
    for index, (name, display, sql, settings, (col, row, width, height)) in enumerate(QUESTIONS):
        card = mb.call("POST", "/card", json={
            "name": name,
            "display": display,
            "collection_id": collection_id,
            "visualization_settings": settings,
            "dataset_query": {
                "type": "native",
                "database": database_id,
                "native": {"query": " ".join(sql.split())},
            },
        })
        dashcards.append({
            "id": -(index + 1),
            "card_id": card["id"],
            "col": col,
            "row": row,
            "size_x": width,
            "size_y": height,
        })

    mb.call("PUT", f"/dashboard/{dashboard['id']}", json={"dashcards": dashcards})
    print(f"Dashboard ready: {METABASE_URL}/dashboard/{dashboard['id']}")


if __name__ == "__main__":
    main()
