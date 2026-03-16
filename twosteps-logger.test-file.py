#!/usr/bin/env python3
"""
Twosteps logger standalone test script.
Run:
  python twosteps-logger.test-file.py
"""
import logging

from twosteps_logger import StatusType, get_additional, set_request_context, twosteps_logger


INDEX_PREFIX = "twosteps-logger-test"

logger = twosteps_logger(
    __name__,
    level=logging.DEBUG,
    index_prefix=INDEX_PREFIX,
    service=INDEX_PREFIX,
    environment="development",
)

print(f"Sending logs for index prefix: {INDEX_PREFIX}")

set_request_context(request_id="ts-001", method="GET", endpoint="/start", status_code=200)
logger.info("Twosteps test logger started", extra=get_additional(status=StatusType.SUCCESS))

set_request_context(request_id="ts-002", method="POST", endpoint="/action", status_code=201)
logger.info(
    "Test action completed",
    extra=get_additional(
        status=StatusType.SUCCESS,
        auth={"user_id": 21, "name": "Twosteps Tester", "email": "twosteps@test.com"},
        custom_fields={"action": "run_twosteps_test", "duration_ms": 180},
    ),
)

set_request_context(request_id="ts-003", method="GET", endpoint="/warn", status_code=200)
logger.warning(
    "Latency warning",
    extra=get_additional(status=StatusType.PENDING, custom_fields={"latency_ms": 620}),
)

set_request_context(request_id="ts-004", method="GET", endpoint="/error", status_code=500)
logger.error(
    "Operation failed",
    extra=get_additional(
        status=StatusType.ERROR,
        error={"error_code": "ERR_TS_001", "http_status": 500},
        custom_fields={"retry_count": 2},
    ),
)

logger.debug(
    "Debug trace",
    extra=get_additional(status=StatusType.PENDING, custom_fields={"step": 1, "trace_id": "tr-ts-001"}),
)

print(f"Done. Check Elasticsearch index pattern: {INDEX_PREFIX}*")
