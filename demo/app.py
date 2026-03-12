"""
FastAPI app with CustomLogger. Logs go to console + Elasticsearch.
Run: uvicorn demo.app:app --reload
"""
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from custom_logger import CustomLogger, query_logs, list_indices

logger = CustomLogger(
    name="demo-api",
    level=logging.DEBUG,
    elastic_hosts=[{"host": "localhost", "port": 9200}],
    index_name="demo-api",
    index_pattern="demo-api-{month}",  # demo-api-03-26, demo-api-02-26 (project + month)
    service_name="demo-api",
    project_name="demo-api",  # Top-level field in Kibana
    environment="development",
)

app = FastAPI(title="Demo API")



@app.get("/")
def root():
    logger.info("GET /")
    return {"message": "Hello"}


@app.get("/health")
def health():
    logger.info("Health check")
    return {"status": "ok"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id < 1:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    logger.info("User fetched", extra={"user_id": user_id})
    return {"user_id": user_id, "name": "Test User", "email": "user@test.com"}


@app.post("/items")
def create_item(name: str, price: float = 0.0):
    item_id = 100 + abs(hash(name)) % 900
    logger.info("Item created", extra={"item_id": item_id, "name": name, "price": price})
    return {"item_id": item_id, "name": name, "price": price}


@app.get("/debug")
def debug_endpoint():
    logger.debug("Debug trace", extra={"trace_id": "tr-001", "step": 1})
    return {"message": "Debug logged"}


@app.get("/warning")
def warning_endpoint():
    logger.warning("High memory usage", extra={"memory_mb": 512})
    return {"message": "Warning logged"}


@app.get("/error")
def error_endpoint():
    logger.error("Operation failed", extra={"error_code": "ERR_001", "retry_count": 3})
    raise HTTPException(status_code=500, detail="Operation failed")


@app.get("/critical")
def critical_endpoint():
    logger.critical("System unreachable", extra={"component": "database", "status": "down"})
    raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/exception")
def exception_endpoint():
    """Logs error with full stack trace to ES."""
    try:
        raise ValueError("Test error")
    except ValueError as e:
        logger.exception("Exception occurred", extra={"error_code": "ERR_002"})
        raise HTTPException(status_code=500, detail=str(e))


# --- Log filtering API (index name, date, month) ---
@app.get("/logs")
def get_logs(
    index_pattern: str = Query("demo-api*", description="Index name or pattern e.g. demo-api*, demo-api-03-26"),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD or ISO datetime"),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD or ISO datetime"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month 1-12 (use with year)"),
    severity: Optional[str] = Query(None, description="DEBUG, INFO, WARNING, ERROR, CRITICAL"),
    size: int = Query(100, ge=1, le=1000),
    from_: int = Query(0, ge=0, alias="from"),
):
    """Filter logs by index name, date range, month, severity."""
    try:
        resp = query_logs(
            index_pattern=index_pattern,
            from_date=from_date,
            to_date=to_date,
            year=year,
            month=month,
            severity=severity,
            size=size,
            from_=from_,
            hosts=[{"host": "localhost", "port": 9200}],
        )
        total = resp["hits"]["total"]
        if isinstance(total, dict):
            total = total.get("value", 0)
        hits_with_index = []
        for hit in resp["hits"]["hits"]:
            doc = hit.get("_source", {})
            doc["_index"] = hit.get("_index", "")
            hits_with_index.append(doc)
        return {
            "total": total,
            "size": size,
            "from": from_,
            "sort": [{"@timestamp": "desc"}],
            "hits": hits_with_index,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/indices")
def get_log_indices(pattern: str = Query("demo-api*", description="Index pattern to list")):
    """List available log indices for filter dropdown."""
    try:
        indices = list_indices(hosts=[{"host": "localhost", "port": 9200}], pattern=pattern)
        return {"indices": indices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
