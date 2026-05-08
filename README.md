# twosteps_logger

A structured logging library for Python that ships logs to Elasticsearch with automatic monthly index rotation, JSON formatting, and async-safe request context propagation.

## Package Structure


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

## Quick Start (Recommended)

### 1) Install library

Local development from this repo:

```bash
cd /home/saud/ESS/github/twosteps/logger
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

From git tag in another project:

```bash
uv add "twosteps_logger @ git+https://github.com/two-steps-org/LOGGER.git@v1.0.1"
```

### 2) Configure once at app startup

```python
import logging
from twosteps_logger import setup_logger

setup_logger(
    level=logging.DEBUG,
    index_prefix="my-project-logs",
    service="my-project-api",
    environment="development",
    logger_transport="otel",
)
```

### 3) Use anywhere in project

```python
from twosteps_logger import get_logger, get_additional, StatusType

logger = get_logger(__name__)
logger.info("service started", extra=get_additional(status=StatusType.SUCCESS))
```

### 4) Use a single env profile at a time

Create these files in project root:
- `.env.local` (local OTEL testing)
- `.env.client` (client/deployed OTEL endpoint)

Do not mix both profiles in one file.

`.env.local`:

```bash
export LOGGER_TRANSPORT=otel
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=twosteps-local-test
export LOGGER_INDEX_PREFIX=my-project-logs
export LOGGER_SERVICE_NAME=my-project-api
export LOGGER_ENVIRONMENT=development
```

`.env.client`:

```bash
export LOGGER_TRANSPORT=otel
export OTEL_LOGS_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.shayb-vps.cloud
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-token>"
export OTEL_SERVICE_NAME=claude-code
export OTEL_RESOURCE_ATTRIBUTES="environment=mac,host.name=shay-macbook-pro"
export LOGGER_INDEX_PREFIX=my-project-logs
export LOGGER_SERVICE_NAME=my-project-api
export LOGGER_ENVIRONMENT=development
```

Run with one profile:

```bash
source .venv/bin/activate
unset LOGGER_TRANSPORT OTEL_LOGS_EXPORTER OTEL_METRICS_EXPORTER OTEL_EXPORTER_OTLP_PROTOCOL OTEL_EXPORTER_OTLP_ENDPOINT OTEL_EXPORTER_OTLP_HEADERS OTEL_SERVICE_NAME OTEL_RESOURCE_ATTRIBUTES ELASTIC_HOST ELASTIC_PORT ELASTIC_SCHEME
source .env.local   # or: source .env.client
python thirteen_logger.py
```

### 5) Verify logs

Local collector mode:

```bash
docker logs --since 2m otel-collector
curl -s "http://localhost:9200/claude-code-logs/_search?size=5&sort=@timestamp:desc&pretty"
```

Kibana:
- Open `http://localhost:5601`
- Data view: `claude-code-logs*`
- KQL filter example: `attributes.service : "thirteen-logger-test"`

---

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

### How it works (current architecture)

This package supports two runtime paths:

1. `LOGGER_TRANSPORT=elastic` (legacy/direct):
   `app -> twosteps_logger -> Elasticsearch`
2. `LOGGER_TRANSPORT=otel` (recommended):
   `app -> twosteps_logger -> OTEL Collector -> Elasticsearch -> Kibana`

In OTEL mode, your app does not need to know Elasticsearch details. It only sends OTLP logs.

### Why Kibana shows `claude-code-logs`

In this repo's local OTEL setup, the collector exporter writes to a fixed data stream:
`claude-code-logs`.

This is expected and does not conflict with your project-level logger config.
Project identity still appears inside each record attributes:
- `attributes.service`
- `resource.attributes.logger.index_prefix`

So for project-level testing, filter in Kibana by these fields.

### OTEL transport mode (Collector pipeline)

Default transport is direct Elasticsearch.  
To route logs through OpenTelemetry Collector instead, set:

```bash
export LOGGER_TRANSPORT=otel
export OTEL_LOGS_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.shayb-vps.cloud
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-token>"
export OTEL_SERVICE_NAME=my-api
export OTEL_RESOURCE_ATTRIBUTES="environment=development,host.name=my-host"
```

Or configure once in code:

```python
setup_logger(
    index_prefix="benchmark",
    service="my-api",
    environment="development",
    logger_transport="otel",
    otlp_protocol="http/protobuf",           # or "grpc"
    otlp_endpoint="https://otel.shayb-vps.cloud",  # /v1/logs is auto-appended for HTTP mode
    otlp_headers="Authorization=Basic <base64-token>",
)
```

### Direct Elasticsearch mode (fallback)

```bash
export LOGGER_TRANSPORT=elastic
export ELASTIC_HOST=localhost
export ELASTIC_PORT=9200
export ELASTIC_SCHEME=http
```

Use this only when OTEL Collector is not available.

If you are OTEL-only, you do not need these:

```bash
export ELASTIC_HOST=localhost
export ELASTIC_PORT=9200
export ELASTIC_SCHEME=http
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
| `LOGGER_TRANSPORT`| `elastic`   | `elastic` or `otel`      |
| `OTEL_LOGS_EXPORTER` | (unset) | set `otlp` for OTEL logs |
| `OTEL_METRICS_EXPORTER` | (unset) | optional, set `otlp` if needed |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` | `grpc` or `http/protobuf` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Collector endpoint/base URL |
| `OTEL_EXPORTER_OTLP_HEADERS` | (unset) | e.g. `Authorization=Basic ...` |
| `OTEL_SERVICE_NAME` | `service` value | OTEL resource service name |
| `OTEL_RESOURCE_ATTRIBUTES` | (unset) | comma-separated `k=v` resource attrs |

For local development no configuration is needed. For other environments, set these variables.

### Client env mapping (important)

Some teams use env names like:
- `ELASTICSEARCH_HOST`
- `ELASTICSEARCH_PORT`
- `ELASTICSEARCH_INDEX`

This library directly reads:
- `ELASTIC_HOST`
- `ELASTIC_PORT`
- `ELASTIC_SCHEME`

If your project already uses `ELASTICSEARCH_*` names, map/export both names in shell or deployment env.
Example:

```bash
export ELASTICSEARCH_HOST=localhost
export ELASTICSEARCH_PORT=443
export ELASTICSEARCH_INDEX=client-test-{month}
export ENVIRONMENT=development

# twosteps_logger expected names
export ELASTIC_HOST="$ELASTICSEARCH_HOST"
export ELASTIC_PORT="$ELASTICSEARCH_PORT"
export ELASTIC_SCHEME=https
```

Notes:
- Use port `443` only when Elasticsearch endpoint is exposed via HTTPS/TLS.
- For local docker Elasticsearch, use `ELASTIC_PORT=9200` and `ELASTIC_SCHEME=http`.

---

## End-to-end local run (recommended OTEL flow)

### Step 1: Start infrastructure

```bash
cd /home/saud/ESS/github/twosteps/logger/logs-elastic
docker context use default
docker compose pull
docker compose up -d
docker compose ps
```

Expected running services:
- `elasticsearch`
- `kibana`
- `otel-collector`

### Step 2: Set runtime env and run logger test

```bash
cd /home/saud/ESS/github/twosteps/logger
source .venv/bin/activate
source logs-elastic/.env
python ninth_logger.py
```

### Step 3: Verify ingestion

```bash
docker logs --since 2m otel-collector
curl -s "http://localhost:9200/claude-code-logs/_search?size=5&sort=@timestamp:desc&pretty"
```

### Step 4: Verify in Kibana

- Open: `http://localhost:5601`
- Discover -> data view: `claude-code-logs*`
- Time range: Last 15 minutes
- Optional project filter in KQL:
  - `attributes.service : "tenth-logger-test"`
  - or `resource.attributes.logger.index_prefix : "tenth-logger-test"`

If needed, create dashboard/data view with:

```bash
cd /home/saud/ESS/github/twosteps/logger/logs-elastic
python3 create-dashboard.py
```

---

## Testing this logger in another project

### Install from git tag

```bash
uv add "twosteps_logger @ git+https://github.com/two-steps-org/LOGGER.git@v1.0.1"
```

### App startup (one-time setup)

```python
import logging
from twosteps_logger import setup_logger

setup_logger(
    level=logging.DEBUG,
    index_prefix="my-project-logs",
    service="my-project-api",
    environment="development",
    logger_transport="otel",  # recommended
)
```

### Any module

```python
from twosteps_logger import get_logger, get_additional, StatusType

logger = get_logger(__name__)
logger.info("ready", extra=get_additional(status=StatusType.SUCCESS))
```

### Required env in consumer project

```bash
export LOGGER_TRANSPORT=otel
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.shayb-vps.cloud
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-token>"
export OTEL_SERVICE_NAME=my-project-api
export OTEL_RESOURCE_ATTRIBUTES="environment=development,host.name=my-host"
```

If you also want a direct Elasticsearch fallback profile for consumer projects:

```bash
export LOGGER_TRANSPORT=elastic
export ELASTIC_HOST=localhost
export ELASTIC_PORT=9200
export ELASTIC_SCHEME=http
```

### Minimal smoke test in any project

```python
import logging
from twosteps_logger import setup_logger, get_logger, get_additional, StatusType

setup_logger(
    level=logging.DEBUG,
    index_prefix="my-project-logs",
    service="my-project-api",
    environment="development",
    logger_transport="otel",
)

logger = get_logger(__name__)
logger.info("hello from project", extra=get_additional(status=StatusType.SUCCESS))
```

Run:

```bash
python app.py
docker logs --since 2m otel-collector
```

Then verify in Kibana (`claude-code-logs*`) using project filters above.

---

## About `logs-elastic/` folder

`logs-elastic/` is an infra/example bundle (compose + collector config + dashboard script).
It is used to validate OTEL integration locally.

- Keep it if this repo is used for demos, onboarding, or local verification.
- You may remove it only after moving the same collector config to:
  - your infra repo, or
  - deployment environment (server/K8s).

If you remove it without moving config, local OTEL testing commands in this README will no longer work.

### If you still want to remove `logs-elastic/`

Before removing, move these files to your infra/deployment location:
- `docker-compose.yml`
- `otel-collector-config.yml`
- `.env` (or equivalent env management)

Without these, collector startup and local end-to-end OTEL tests will not work.

---

## Common issues

- **Containers visible in terminal but not Docker Desktop**
  - Cause: different Docker context (`default` vs `desktop-linux`).
  - Fix: run `docker context use default`.

- **`bind: address already in use :9200`**
  - Another service/container is already using Elasticsearch port.
  - Stop conflicting process/container, then restart compose.

- **Collector receives logs but ES shows 404**
  - Ensure index/data-stream setup exists for exporter target.
  - Recheck collector config and target index name.

- **`localhost:4317` does not open in browser**
  - This is expected. `4317` is OTLP gRPC ingest port, not a web UI.
  - Use:
    - Kibana UI: `http://localhost:5601`
    - Elasticsearch API: `http://localhost:9200`

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
