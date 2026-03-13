# custom_logger

Refactored logger library with modular package structure, monthly Elasticsearch indexing, and uv-based CI/CD publishing.

## Target Structure (implemented in `custom_logger/`)

```text
custom_logger/
├── __init__.py
├── configuration/
│   ├── __init__.py
│   ├── get_logger_configuration.py
│   └── logger_configuration.py
├── constants.py
├── formatters/
│   ├── __init__.py
│   └── json_formatter.py
├── get_logger.py
├── github/
│   └── workflows/
└── handlers/
    ├── __init__.py
    └── elastic.handler.py
```

## Usage

```python
from custom_logger import twosteps_logger, get_additional, StatusType

logger = twosteps_logger(__name__)

extra_fields = get_additional(
    status=StatusType.SUCCESS
)

logger.info("done", extra=extra_fields)
```

All logger internals (ES client, index routing, context enrichment, JSON formatting) are handled during initialization.

## Extra fields and context

`get_additional()` supports:

- Core fields: `status`, `message`, `timestamp`, `service`, `environment`
- Global request context: `request_id`, `method`, `endpoint`, `duration_ms`, `status_code`
- Auth context: `email`, `name`, `user_id`, `session_id`, `ip_address`
- Error context: `error_code`, `error_type`, `error_message`, `http_status`, `stack_error`
- `custom_fields`: any additional data

### Status enum

```python
from custom_logger import StatusType

StatusType.SUCCESS
StatusType.FAILURE
StatusType.PENDING
StatusType.ERROR
```

## Elasticsearch template and monthly index

Create template before sending logs:

```bash
python scripts/create_es_template.py --prefix benchmark
```

Template pattern: `benchmark-*`

Monthly index naming:

- March 2026 -> `benchmark-03_26`
- April 2026 -> `benchmark-04_26`
- February 2026 -> `benchmark-02_26`

`elastic.handler.py` resolves current index dynamically at log time.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Demo run

```bash
uvicorn demo.app:app --reload
```

## Testing guide

1) Start services:

```bash
docker start elasticsearch
docker start kibana
curl http://localhost:9200
```

2) Create template:

```bash
python scripts/create_es_template.py --prefix benchmark
```

3) Generate demo logs:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/users/1
curl http://localhost:8000/debug
curl http://localhost:8000/warning
curl http://localhost:8000/error
```

4) Verify in Elasticsearch:

```bash
curl "http://localhost:9200/_cat/indices/benchmark*?v"
curl "http://localhost:9200/benchmark-03_26/_search?pretty"
```

5) Kibana:

- Data view: `benchmark*`
- Time field: `@timestamp`
- Time range: Last 15 minutes / Last 24 hours

6) Unit tests:

```bash
pytest -q
pytest --cov=custom_logger --cov-report=term-missing
```

## CI/CD (GitHub Actions + uv)

Workflow: `.github/workflows/publish.yml`

Build and publish:

```bash
uv build
uv publish --index twosteps-pypi
```

Required secrets:

- `TWOSTEPS_PYPI_USERNAME`
- `TWOSTEPS_PYPI_PASSWORD`

