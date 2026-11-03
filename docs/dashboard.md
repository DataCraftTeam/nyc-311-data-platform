# Dashboard

Metabase dashboard **NYC 311 Service Requests**, built by `make dashboard` (`dashboard/setup_metabase.py`)
from the gold tables. Every chart is a native SQL question, so the queries live in the repo and not only in Metabase.

## Layout

| Row | Charts |
|---|---|
| KPIs | Total requests · Open requests · Median resolution time (hours) · Closed before created (data issue) |
| Q1 / Q2 | Most common complaint types (top 10) · Monthly trend of the top 5 complaint types |
| Q3 / Q4 | Median resolution time by agency (top 10 by volume) · Open requests by borough |
| Q4 detail | Open requests by agency, complaint type and borough (top 20) |

## Sources

| Chart | Table |
|---|---|
| Most common complaint types, monthly trend | `gold.mart_complaint_trends` |
| Median resolution time by agency | `gold.fct_service_requests` + `gold.dim_agency` |
| Open requests (KPI, by borough, detail) | `gold.mart_open_backlog` |
| Total requests, median resolution, data issue | `gold.fct_service_requests` |

Median is used for resolution time instead of the average, because a few very old requests stretch the average a lot.
Agency medians are computed from the fact table, not by averaging the monthly medians in `mart_agency_resolution`.

Requests closed before they were created (`has_invalid_close_date`) have no `resolution_time_hours`, so they are
already left out of the resolution charts. They are shown as their own KPI so the data issue stays visible.

## Notes

- Metabase stores its own settings (users, dashboards) in the `metabase_data` volume. `make docker-down` keeps it; `docker compose down -v` deletes it.
- Metabase reaches Postgres through the compose service name `postgres`, so `POSTGRES_HOST=localhost` in `.env` is only for dbt and scripts on the host.
