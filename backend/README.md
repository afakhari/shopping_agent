# Bazaar Compass API

Django REST Framework backend. Implemented in this milestone:

- health endpoints: `/api/v1/health/live/`, `/api/v1/health/ready/`
- catalog search: `GET /api/v1/catalog/search/`
- product details/offers: `/api/v1/products/{product_id}/`, `/api/v1/products/{product_id}/offers/`
- shop details: `/api/v1/shops/{shop_id}/`
- `Product`, `Shop`, `Offer` models and initial migrations
- idempotent, batch-based CSV/ZIP importer (`import_dataset`)

Runtime verification remains pending because dependencies were not installable in the builder environment. Do not describe these features as runtime-tested until commands below pass in a dependency-enabled environment.

## Local setup (Windows/macOS/Linux)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest -q
ruff check .
ruff format --check .
```

Without `DATABASE_URL`, local settings use SQLite for basic tests. PostgreSQL is the target database and should be used for representative distance-filter and performance tests.

## Import dataset

From this `backend/` directory:

```bash
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip --dry-run
python manage.py import_dataset --archive ../data/starcoach-dataset-v16-cap300-csv.zip
```

Keep the ZIP and extracted CSVs outside Git. See `../docs/import-and-search.fa.md` for the data contract, eligibility policy and query examples.
