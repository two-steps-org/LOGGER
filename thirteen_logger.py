#!/usr/bin/env python3
"""
Thirteen logger OTEL test script.

Sends 6 structured logs for quick verification in collector/Kibana.
"""

import logging
import os

from twosteps_logger import StatusType, get_additional, get_logger, setup_logger


INDEX_PREFIX = os.getenv("LOGGER_INDEX_PREFIX", "thirteen-logger")
SERVICE_NAME = os.getenv("LOGGER_SERVICE_NAME", "thirteen-logger-service")
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
        "thirteen logger: start",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 1, "transport": TRANSPORT},
        ),
    )
    logger.debug(
        "thirteen logger: debug checkpoint",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 2, "debug": True},
        ),
    )
    logger.info(
        "thirteen logger: processing",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 3, "phase": "processing"},
        ),
    )
    logger.warning(
        "thirteen logger: warning threshold",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 4, "latency_ms": 330},
        ),
    )
    logger.error(
        "thirteen logger: error sample",
        extra=get_additional(
            status=StatusType.ERROR,
            error={"error_code": "THIRTEEN_001", "http_status": 500},
            custom_fields={"step": 5},
        ),
    )
    logger.info(
        "thirteen logger: completed",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 6, "result": "ok"},
        ),
    )
    print("Done. Sent 6 logs from thirteen_logger.py")


if __name__ == "__main__":
    run_test()
