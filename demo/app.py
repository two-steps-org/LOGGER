"""
FastAPI demo using modular custom_logger package.
Run: uvicorn demo.app:app --reload
"""
import logging

from fastapi import FastAPI, HTTPException

from custom_logger import StatusType, get_additional, set_request_context, twosteps_logger

logger = twosteps_logger(
    __name__,
    level=logging.DEBUG,
    index_prefix="benchmark",
    service="demo-api",
    environment="development",
)

app = FastAPI(title="Demo API")



@app.get("/")
def root():
    set_request_context(method="GET", endpoint="/", request_id="rq-root")
    logger.info("GET /", extra=get_additional(status=StatusType.SUCCESS))
    return {"message": "Hello"}


@app.get("/health")
def health():
    set_request_context(method="GET", endpoint="/health", request_id="rq-health")
    logger.info("Health check", extra=get_additional(status=StatusType.SUCCESS))
    return {"status": "ok"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id < 1:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    set_request_context(method="GET", endpoint="/users/{user_id}", request_id="rq-user")
    logger.info(
        "User fetched",
        extra=get_additional(
            status=StatusType.SUCCESS,
            auth={"user_id": user_id, "name": "Test User"},
        ),
    )
    return {"user_id": user_id, "name": "Test User", "email": "user@test.com"}


@app.post("/items")
def create_item(name: str, price: float = 0.0):
    item_id = 100 + abs(hash(name)) % 900
    set_request_context(method="POST", endpoint="/items", request_id="rq-item")
    logger.info(
        "Item created",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"item_id": item_id, "name": name, "price": price},
        ),
    )
    return {"item_id": item_id, "name": name, "price": price}


@app.get("/debug")
def debug_endpoint():
    set_request_context(method="GET", endpoint="/debug", request_id="rq-debug")
    logger.debug(
        "Debug trace",
        extra=get_additional(status=StatusType.PENDING, custom_fields={"trace_id": "tr-001", "step": 1}),
    )
    return {"message": "Debug logged"}


@app.get("/warning")
def warning_endpoint():
    set_request_context(method="GET", endpoint="/warning", request_id="rq-warn")
    logger.warning(
        "High memory usage",
        extra=get_additional(status=StatusType.PENDING, custom_fields={"memory_mb": 512}),
    )
    return {"message": "Warning logged"}


@app.get("/error")
def error_endpoint():
    set_request_context(method="GET", endpoint="/error", request_id="rq-error", status_code=500)
    logger.error(
        "Operation failed",
        extra=get_additional(
            status=StatusType.ERROR,
            error={"error_code": "ERR_001", "http_status": 500},
            custom_fields={"retry_count": 3},
        ),
    )
    raise HTTPException(status_code=500, detail="Operation failed")


@app.get("/critical")
def critical_endpoint():
    set_request_context(method="GET", endpoint="/critical", request_id="rq-critical", status_code=503)
    logger.critical(
        "System unreachable",
        extra=get_additional(
            status=StatusType.FAILURE,
            custom_fields={"component": "database", "status": "down"},
        ),
    )
    raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/exception")
def exception_endpoint():
    """Logs error with full stack trace to ES."""
    try:
        raise ValueError("Test error")
    except ValueError as e:
        set_request_context(method="GET", endpoint="/exception", request_id="rq-exception", status_code=500)
        logger.exception(
            "Exception occurred",
            extra=get_additional(
                status=StatusType.ERROR,
                error={
                    "error_code": "ERR_002",
                    "error_type": "ValueError",
                    "error_message": str(e),
                    "http_status": 500,
                },
            ),
        )
        raise HTTPException(status_code=500, detail=str(e))
