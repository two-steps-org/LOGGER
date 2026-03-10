"""
FastAPI app with CustomLogger. Logs go to console + Elasticsearch.
Run: uvicorn demo.app:app --reload
"""
import logging

from fastapi import FastAPI, HTTPException

from custom_logger import CustomLogger

logger = CustomLogger(
    name="demo-api",
    level=logging.DEBUG,
    elastic_hosts=[{"host": "localhost", "port": 9200}],
    service_name="demo-api",
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
