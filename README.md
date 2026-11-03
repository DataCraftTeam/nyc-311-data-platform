# NYC 311 Data Platform

## Project Goal
Build an end-to-end ETL pipeline that extracts NYC 311 service-request data,
cleans and transforms it, and loads it into a structured database for analysis.

## Tech Stack
- Python
- SQL
- Database: PostgreSQL

## How to Run Locally

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- `make`

> [NOTE]
> **Windows Users:** To run the exact same workflow without installing separate Windows build tools, use **Git Bash** (included with [Git for Windows](https://git-scm.com/downloads/win)) or **WSL** (Windows Subsystem for Linux). All commands will run identically.

---

### Step 1: Set Up Python Environment

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 2: Configure Environment Variables

Create your local `.env` file from the provided example:

```bash
cp .env.example .env
```

---

### Step 3: Start Database & Verify Connection

Start the PostgreSQL container in the background:

```bash
make docker-up
```

Verify that PostgreSQL is healthy and dbt can connect:

```bash
make dbt-debug
```

---

### Step 4: Ingest Raw Data (Bronze Layer)

Extract NYC 311 service request records and load them into `bronze.raw_nyc_311`:

```bash
make ingest
```

---

### Step 5: Run Transformations (Silver Layer)

Build the clean staging model and intermediate enriched view:

```bash
make dbt-run
```

---

### Step 6: Run Data Quality Tests

Run dbt automated tests to validate schema integrity, uniqueness, and column constraints:

```bash
make dbt-test
```

---

### Step 7: Build the Dashboard

`make docker-up` also starts Metabase on http://localhost:3000.
Set `METABASE_ADMIN_EMAIL` and `METABASE_ADMIN_PASSWORD` in `.env` (Metabase rejects common passwords), then run:

```bash
make dashboard
```

On the first run this creates the Metabase admin user, connects Metabase to the warehouse, and builds the
**NYC 311 Service Requests** dashboard from the gold tables. Re-running it rebuilds the dashboard.
Log in with the admin email and password from `.env`. See [docs/dashboard.md](docs/dashboard.md) for what each chart shows.

---

### Step 8: Stop Services

When finished, stop the containers:

```bash
make docker-down
```

## Team Roles
| Role | Responsibility |
|---|---|
| Data Ingestion Lead | Extracts raw NYC 311 data from the source |
| Transform & Quality Lead | Cleans, transforms, and validates the data |
| Load & Delivery Lead | Loads data into the target and confirms it is correct |
