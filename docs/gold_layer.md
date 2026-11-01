# Gold Layer

Built on the silver model `int_service_requests_enriched`. Materialized as tables in the `gold` schema.

## Business questions

| # | Question | Answered by |
|---|---|---|
| Q1 | Which complaint types are most common? | `mart_complaint_trends.rank_in_month` |
| Q2 | Which complaint types are increasing over time? | `mart_complaint_trends.mom_change_pct` |
| Q3 | How long does each agency take to resolve requests? | `mart_agency_resolution` (avg / median / p90 hours, SLA breach %) |
| Q4 | How many requests are still unresolved? | `mart_open_backlog.open_count` |

## Star schema

Fact grain: **one row per service request**.

```
                dim_date (created / closed)
                      │
 dim_agency ── fct_service_requests ── dim_complaint_type
                      │
                 dim_location
```

| Table | Key | Contents |
|---|---|---|
| `fct_service_requests` | `unique_key` | FKs to every dimension; `status`, `channel_type`, timestamps, `is_closed`, `resolution_time_hours`, `is_sla_breached` |
| `dim_date` | `date_key` (YYYYMMDD) | year, quarter, month, month_start, day_of_week, is_weekend |
| `dim_agency` | `agency_key` | agency, agency_name |
| `dim_complaint_type` | `complaint_type_key` | complaint_type, descriptor |
| `dim_location` | `location_key` | borough (NULL shown as `UNSPECIFIED`), incident_zip |

Surrogate keys are `MD5()` of the natural key, so they stay stable across full rebuilds.
`status` and `channel_type` have only a handful of values, so they stay on the fact.

## Tests

Unique / not-null on every dimension key and on the fact key, plus `relationships`
from each fact foreign key to its dimension.

## Run

```bash
make dbt-run
make dbt-test
```

## Notes

- `sla_breach_pct` is mostly NULL: `due_date` is filled for well under 1% of requests.
- Q2 uses month-over-month change; a 3-month average could be less noisy.
