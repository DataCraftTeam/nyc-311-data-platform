.PHONY: dbt-debug up down

-include .env
export

up:
	docker compose up -d

down:
	docker compose down

dbt-debug:
	dbt debug --project-dir dbt --profiles-dir dbt