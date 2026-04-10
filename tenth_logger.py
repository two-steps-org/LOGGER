#!/usr/bin/env python3
"""
Tenth logger OTEL smoke test.

Sends 9 logs in one run for quick validation in Elasticsearch/Kibana.
"""

import logging
import os

from twosteps_logger import StatusType, get_additional, get_logger, setup_logger


INDEX_PREFIX = os.getenv("LOGGER_INDEX_PREFIX", "tenth-logger-test")
SERVICE_NAME = os.getenv("LOGGER_SERVICE_NAME", "tenth-logger-test")
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
        "tenth logger: bootstrap started",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 1, "transport": TRANSPORT},
        ),
    )
    logger.debug(
        "tenth logger: config loaded",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 2, "config": "loaded"},
        ),
    )
    logger.info(
        "tenth logger: db ping ok",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 3, "db_ping_ms": 18},
        ),
    )
    logger.warning(
        "tenth logger: cache latency high",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 4, "cache_latency_ms": 240},
        ),
    )
    logger.info(
        "tenth logger: user fetch complete",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 5, "records": 12},
        ),
    )
    logger.error(
        "tenth logger: payment call failed",
        extra=get_additional(
            status=StatusType.ERROR,
            error={"error_code": "TENTH_001", "http_status": 502},
            custom_fields={"step": 6, "retry": 1},
        ),
    )
    logger.info(
        "tenth logger: retry succeeded",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 7, "retry": 2},
        ),
    )
    logger.debug(
        "tenth logger: cleanup complete",
        extra=get_additional(
            status=StatusType.PENDING,
            custom_fields={"step": 8, "cleanup": True},
        ),
    )
    logger.info(
        "tenth logger: flow completed",
        extra=get_additional(
            status=StatusType.SUCCESS,
            custom_fields={"step": 9, "result": "done"},
        ),
    )
    print("Done. Sent 9 logs. Check collector -> Elasticsearch -> Kibana.")


if __name__ == "__main__":
    run_test()
