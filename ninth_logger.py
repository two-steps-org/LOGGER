#!/usr/bin/env python3
"""
Quick logger smoke test.

Usage:
  python ninth_logger.py
"""

import logging
import os

from twosteps_logger import StatusType, get_additional, get_logger, setup_logger


INDEX_PREFIX = os.getenv("LOGGER_INDEX_PREFIX", "ninth-logger-test")
SERVICE_NAME = os.getenv("LOGGER_SERVICE_NAME", "ninth-logger-test")
ENVIRONMENT = os.getenv("LOGGER_ENVIRONMENT", "development")

# Default to OTEL transport so it follows client architecture.
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
        "ninth logger: service started",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"transport": TRANSPORT},
        ),
    )
    logger.warning(
        "ninth logger: sample warning",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": "warning-check"},
        ),
    )
    logger.error(
        "ninth logger: sample error",
        extra=get_additional(
            status=StatusType.ERROR,
            error={"error_code": "NINTH_001", "http_status": 500},
        ),
    )
    print("Logs sent. Check collector -> elastic -> kibana flow.")


if __name__ == "__main__":
    run_test()
