import os, time, requests

BASE_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PAGE_SIZE = 50_000
COLUMNS = [
    "unique_key", "created_date", "closed_date", "agency", "complaint_type",
    "descriptor", "location_type", "incident_zip", "status",
    "resolution_description", "borough", "open_data_channel_type",
    "latitude", "longitude",
]

def fetch_window(start: str, end: str):
    """Yield pages of rows with start <= created_date < end."""
    headers = {"X-App-Token": os.getenv("SOCRATA_APP_TOKEN", "")}
    offset = 0
    while True:
        params = {
            "$select": ",".join(COLUMNS),
            "$where": f"created_date >= '{start}' AND created_date < '{end}'",
            "$order": "unique_key", 
            "$limit": PAGE_SIZE,
            "$offset": offset,
        }
        for attempt in range(5):
            try:
                r = requests.get(BASE_URL, params=params, headers=headers, timeout=120)
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
        rows = r.json()
        if not rows:
            return
        yield [{c: row.get(c) for c in COLUMNS} for row in rows]
        offset += PAGE_SIZE