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



## 5. FastAPI Demo

```bash
# Run demo app
uvicorn demo.app:app --reload
# Open http://localhost:8000
# Test: GET /, GET /health, GET /users/1, POST /items?name=book&price=10, GET /error
```

---

## 6. Test

```bash
# Required: activate venv (elasticsearch is installed in venv)
source .venv/bin/activate
python test_logs.py

# Or run directly: .venv/bin/python test_logs.py
```

Verify: http://localhost:9200/python-logs/_search?pretty

---

## 7. No Results in Kibana?

1. **Expand time range** – In the top-right, change "Last 15 minutes" to **"Last 24 hours"** or **"Last 7 days"** (logs may be older)
2. **Use venv** – If stderr shows `[elastic_logger] Error: pip install elasticsearch`, run with venv: `source .venv/bin/activate`
3. **Verify ES** – Run `python verify_es.py` to check that logs are in Elasticsearch
4. **Data view** – Index pattern should be `python-logs*`, Timestamp field should be **@timestamp**  

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

