#!/usr/bin/env python3
"""
Final logger test script.
Run:
  python final-test-logger.py
"""
import logging

from custom_logger import StatusType, get_additional, set_request_context, twosteps_logger


logger = twosteps_logger(
    __name__,
    level=logging.DEBUG,
    index_prefix="final-test-logger",
    service="final-test-logger",
    environment="development",
)

print("Sending final-test-logger logs...")

set_request_context(request_id="ftl-001", method="GET", endpoint="/start", status_code=200)
logger.info("Final test logger started", extra=get_additional(status=StatusType.SUCCESS))

set_request_context(request_id="ftl-002", method="POST", endpoint="/action", status_code=200)
logger.info(
    "Action completed",
    extra=get_additional(
        status=StatusType.SUCCESS,
        auth={"user_id": 11, "name": "Final User", "email": "final@test.com"},
        custom_fields={"action": "run_final_test", "duration_ms": 150},
    ),
)

set_request_context(request_id="ftl-003", method="GET", endpoint="/warn", status_code=200)
logger.warning(
    "High latency detected",
    extra=get_additional(status=StatusType.PENDING, custom_fields={"latency_ms": 580}),
)

set_request_context(request_id="ftl-004", method="GET", endpoint="/error", status_code=500)
logger.error(
    "Operation failed",
    extra=get_additional(
        status=StatusType.ERROR,
        error={"error_code": "ERR_FINAL_001", "http_status": 500},
        custom_fields={"retry_count": 1},
    ),
)

logger.debug(
    "Debug trace",
    extra=get_additional(status=StatusType.PENDING, custom_fields={"step": 1, "trace_id": "tr-final-001"}),
)

print("Done. Check Elasticsearch index pattern: final-test-logger*")
