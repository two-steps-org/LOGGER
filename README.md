# Elastic Logger

Python logging library that sends application logs to Elasticsearch. Uses **ECS format**. Works with Flask, Django, FastAPI, etc.

---

## 1. Project Setup

### Prerequisites
- Python 3.8+
- Docker (for Elasticsearch & Kibana)

### Steps

```bash
# Clone / enter project
cd /path/to/logger

# Create virtual environment
python -m venv .venv

# Activate (Linux / Mac)
source .venv/bin/activate

# Activate (Windows PowerShell)
# .venv\Scripts\Activate.ps1

# Install library
pip install -e .
```

---

## 2. Elasticsearch Setup (Docker)

### Create index template (for monthly logs like demo-api-03-26)

For project-specific indices (e.g. `demo-api-03-26`, `benchmark-02-26`), create the template first:

```bash
# Demo app
python scripts/create_es_template.py --prefix demo-api

# Benchmark project
python scripts/create_es_template.py --prefix benchmark
```

Then use `index_pattern="demo-api-{month}"` or `index_pattern="benchmark-{month}"` in CustomLogger.

### Start Elasticsearch

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Verify

```bash
curl http://localhost:9200
```

Expected: JSON with `"tagline" : "You Know, for Search"`

### Start / Stop

```bash
docker start elasticsearch   # Start
docker stop elasticsearch    # Stop
docker ps                    # Check status
```

---

## 3. Kibana Setup (Docker)

### Start Kibana

```bash
docker run -d \
  --name kibana \
  -p 5601:5601 \
  --add-host=host.docker.internal:host-gateway \
  -e "ELASTICSEARCH_HOSTS=http://host.docker.internal:9200" \
  docker.elastic.co/kibana/kibana:8.11.0
```

**Linux** (if `host.docker.internal` fails):
```bash
docker run -d \
  --name kibana \
  --network host \
  -e "ELASTICSEARCH_HOSTS=http://localhost:9200" \
  docker.elastic.co/kibana/kibana:8.11.0
```

### Open Kibana

Browser: **http://localhost:5601**

Wait 1–2 minutes for first load.

### Start / Stop

```bash
docker start kibana   # Start
docker stop kibana    # Stop
```

---



## 4. Usage

```python
from custom_logger import CustomLogger

logger = CustomLogger("app")
logger.info("Application started")
logger.info("User logged in", extra={"user_id": 123})
```

### Benchmark project (monthly indices: benchmark-03-26, benchmark-02-26)

1. Create template: `python scripts/create_es_template.py --prefix benchmark`
2. Use monthly pattern:

```python
logger = CustomLogger(
    "benchmark",
    index_name="benchmark",
    index_pattern="benchmark-{month}",  # benchmark-03-26, benchmark-02-26
    service_name="benchmark",
    project_name="benchmark",
)
```



## 5. FastAPI Demo

```bash
# Run demo app
uvicorn demo.app:app --reload
# Open http://localhost:8000
# Test: GET /, GET /health, GET /users/1, POST /items?name=book&price=10, GET /error
```

### Log Filtering API (index name, date, month)

| Endpoint | Query Params | Description |
|----------|--------------|-------------|
| `GET /logs` | `index_pattern`, `from_date`, `to_date`, `year`, `month`, `severity`, `size`, `from` | Filter logs |
| `GET /logs/indices` | `pattern` | List available indices |

**Examples:**
- `GET /logs?index_pattern=python-logs*` – all logs
- `GET /logs?index_pattern=python-logs-2025.03.11` – specific date index
- `GET /logs?year=2025&month=3` – March 2025
- `GET /logs?from_date=2025-03-01&to_date=2025-03-31` – date range
- `GET /logs?severity=ERROR` – errors only

---

## 6. Test

```bash
# Required: activate venv (elasticsearch is installed in venv)
source .venv/bin/activate
python test_logs.py

# Benchmark project test (see docs/BENCHMARK_TESTING.md)
python test_benchmark.py
```

Verify: http://localhost:9200/python-logs/_search?pretty  
Benchmark: http://localhost:9200/benchmark-03-26/_search?pretty

---

## 7. No Results in Kibana?

1. **Create Data View** – Stack Management → Data Views → Create. Index pattern: `demo-api*` or `benchmark*` (per project). Timestamp: **@timestamp**.
2. **Expand time range** – Top-right: change "Last 15 minutes" to **"Last 24 hours"** or **"Last 7 days"**.
3. **Correct index pattern** – Demo uses `demo-api-03-26`; select `demo-api*` in Discover, not `python-logs*`.
4. **Create template first** – `python scripts/create_es_template.py --prefix demo-api`  

---

## 8. Quick Reference

| Action | Command |
|--------|---------|
| Start Elasticsearch | `docker start elasticsearch` |
| Start Kibana | `docker start kibana` |
| Stop Elasticsearch | `docker stop elasticsearch` |
| Stop Kibana | `docker stop kibana` |
| Elasticsearch URL | http://localhost:9200 |
| Kibana URL | http://localhost:5601 |
| Logs search URL | http://localhost:9200/python-logs/_search?pretty |

