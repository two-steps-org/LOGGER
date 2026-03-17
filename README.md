# twosteps_logger

A structured logging library for Python that ships logs to Elasticsearch with automatic monthly index rotation, JSON formatting, and async-safe request context propagation.

## Package Structure

```
twosteps_logger/
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
└── handlers/
    ├── __init__.py
    └── elastic.handler.py
```

CI/CD workflow: `.github/workflows/publish.yml`

---

## Install from private PyPI

```toml
# pyproject.toml (consumer app)
[tool.uv.sources]
twosteps_logger = { index = "twosteps-pypi" }

[project]
dependencies = ["twosteps_logger>=1.0.0"]
```

---

## Usage

### Recommended: configure once, log everywhere

Call `setup_logger` once at application startup (e.g. `main.py` or `app/__init__.py`).  
All Elasticsearch connection details are read from environment variables and the config set here.

```python
# main.py / app startup
from twosteps_logger import setup_logger

setup_logger(
    index_prefix="benchmark",   # becomes benchmark-MM_YY index names
    service="my-api",
    environment="production",   # or read from ENV
)
```

Then in every module, just get a logger by name:

```python
# any module
from twosteps_logger import get_logger

logger = get_logger(__name__)
logger.info("request handled")
```

### Zero-config quick start

If you have not called `setup_logger`, the logger resolves all settings from environment variables:

```python
from twosteps_logger import twosteps_logger

logger = twosteps_logger(__name__)
logger.info("ready")
```

### StatusType enum

```python
from twosteps_logger import StatusType

StatusType.SUCCESS   # "SUCCESS"
StatusType.FAILURE   # "FAILURE"
StatusType.PENDING   # "PENDING"
StatusType.ERROR     # "ERROR"
```

### Request context (async-safe)

Use `set_request_context` / `clear_request_context` in middleware to propagate per-request metadata
into every log record automatically (uses `contextvars.ContextVar`):

```python
from twosteps_logger import set_request_context, clear_request_context

# FastAPI / Starlette middleware example
async def logging_middleware(request, call_next):
    set_request_context(
        request_id=request.headers.get("X-Request-ID"),
        method=request.method,
        endpoint=str(request.url.path),
    )
    response = await call_next(request)
    clear_request_context()
    return response
```

### Building structured extra fields (`get_additional`)

> **Note:** `get_additional` is provided as a convenience helper. Teams that need project-specific
> extra field shapes should build their own helper instead of relying on this one.

```python
from twosteps_logger import get_logger, get_additional, StatusType

logger = get_logger(__name__)

extra = get_additional(
    status=StatusType.SUCCESS,
    custom_fields={"action": "checkout", "order_id": "ord-123"},
)
logger.info("order completed", extra=extra)
```

`get_additional` merges:
- **Core fields**: `status`, `message`, `timestamp`, `service`, `environment`
- **Request context**: any values set via `set_request_context`
- **Auth context** (optional `auth` dict): `email`, `name`, `user_id`, `session_id`, `ip_address`
- **Error context** (optional `error` dict): `error_code`, `error_type`, `error_message`, `http_status`
- **Custom fields** (optional): nested under `custom_fields` in the ES document

---

## Elasticsearch — index template & monthly indexes

### Index template

The handler automatically creates an index template on startup (one HTTP call per prefix per process).
You can also run the script once manually:

```bash
python scripts/create_es_template.py --prefix benchmark
```

Template covers the `benchmark-*` pattern with the required field mappings:

| Field         | ES type   |
|---------------|-----------|
| `severity`    | `keyword` |
| `message`     | `text`    |
| `timestamp`   | `date`    |
| `service`     | `keyword` |
| `environment` | `keyword` |
| `status`      | `keyword` |

### Monthly index naming

Indexes are named `{prefix}-MM_YY`, resolved at log-flush time:

| Month          | Index name         |
|----------------|--------------------|
| March 2026     | `benchmark-03_26`  |
| April 2026     | `benchmark-04_26`  |
| February 2026  | `benchmark-02_26`  |

### Environment variables

| Variable        | Default       | Description              |
|-----------------|---------------|--------------------------|
| `ELASTIC_HOST`  | `localhost`   | Elasticsearch hostname   |
| `ELASTIC_PORT`  | `9200`        | Elasticsearch port       |
| `ELASTIC_SCHEME`| `http`        | `http` or `https`        |

For local development no configuration is needed. For other environments, set these variables.

---

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
# or with coverage report:
pytest --cov=twosteps_logger --cov-report=term-missing
```

Coverage threshold is enforced at 80% (currently ~95%).

---

## CI/CD — GitHub Actions + uv

Workflow: `.github/workflows/publish.yml`

- **verify** job: runs on every PR and push to `main` — installs with `uv sync`, compiles, runs tests.
- **publish** job: runs only on `v*` tags — builds with `uv build`, publishes with `uv publish --index twosteps-pypi`.

Required GitHub secrets: `TWOSTEPS_PYPI_USERNAME`, `TWOSTEPS_PYPI_PASSWORD`.
