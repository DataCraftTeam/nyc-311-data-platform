# Design Decisions

| Decision | Why chosen | Alternative | Why not |
|---|---|---|---|
| NYC 311 dataset | Real volume, daily API updates, built-in business questions | Retail/shipping data | Often paywalled, access could stall the project |
| Medallion layers (bronze/silver/gold) | Separates raw, cleaned, and analytics data | Single-layer transform | No raw copy to replay when cleaning logic changes |
| `extract_load/` as one folder | Bronze is one step: pull from API, land raw | Separate `extract/` and `load/` | Two folders for one job |
| dbt runs locally | Faster dev loop, fewer moving parts | Containerized dbt | Rebuild overhead with no benefit yet |
| Docker only for Postgres | One-command database setup | Local Postgres install | Setups drift between teammates |
| Orchestration (Dagster) added last | Build and test the pipeline first | Orchestrate from day one | Complexity before we know what to orchestrate |
| Conventional Commits,PR-only `main` | Readable history, protected main | Free-form commits, direct pushes | Messy history, accidental changes to `main` |
