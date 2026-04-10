#!/usr/bin/env python3
"""
Eleventh logger OTEL test script.

Sends a small mixed batch of logs for validation in collector + Elasticsearch + Kibana.
"""

import logging
import os

from twosteps_logger import StatusType, get_additional, get_logger, setup_logger


INDEX_PREFIX = os.getenv("LOGGER_INDEX_PREFIX", "eleventh-logger-test")
SERVICE_NAME = os.getenv("LOGGER_SERVICE_NAME", "eleventh-logger-test")
ENVIRONMENT = os.getenv("LOGGER_ENVIRONMENT", "development")
TRANSPORT = os.getenv("LOGGER_TRANSPORT", "otel")

setup_logger(
    level=logging.DEBUG,
    index_prefix=INDEX_PREFIX,
    service=SERVICE_NAME,
    environment=ENVIRONMENT,
    logger_transport=TRANSPORT,
)

logger = get_logger(__name__)


def run_test() -> None:
    logger.info(
        "eleventh logger: start",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 1, "transport": TRANSPORT},
        ),
    )
    logger.debug(
        "eleventh logger: debug trace",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 2, "trace": "elv-001"},
        ),
    )
    logger.warning(
        "eleventh logger: warning sample",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 3, "latency_ms": 310},
        ),
    )
    logger.error(
        "eleventh logger: error sample",
        extra=get_additional(
            status=StatusType.ERROR,
            error={"error_code": "ELEVENTH_001", "http_status": 500},
            custom_fields={"step": 4},
        ),
    )
    logger.info(
        "eleventh logger: completed",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 5, "result": "ok"},
        ),
    )
    print("Done. Sent 5 logs. Verify in collector and Kibana.")


if __name__ == "__main__":
    run_test()
