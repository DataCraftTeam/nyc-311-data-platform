.PHONY: docker-up docker-down dbt-debug dbt-parse dbt-run dbt-test dashboard

-include .env
export

docker-up:
	docker compose up -d

docker-down:
	docker compose down

dbt-debug:
	dbt debug --project-dir dbt --profiles-dir dbt

dbt-parse:
	dbt parse --project-dir dbt --profiles-dir dbt

dbt-run:
	dbt run --project-dir dbt --profiles-dir dbt

dbt-test:
	dbt test --project-dir dbt --profiles-dir dbt

dashboard:
	python dashboard/setup_metabase.py