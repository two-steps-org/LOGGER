#!/usr/bin/env python3
"""
Send sample logs to PostHog to verify the integration.

Usage:
    export POSTHOG_API_KEY=phc_xxx            # use a Dev environment token
    export POSTHOG_HOST=https://us.i.posthog.com   # optional
    python scripts/check_posthog_logs.py [--handlers posthog] [--environment development]

Expected in PostHog Logs: the info, warning and error lines below (not the debug line).
The setup_logger(...) call is the same one an app needs at startup.
"""
import argparse
import logging
import os
import sys
import time

from twosteps_logger import get_logger, setup_logger


def main():
    parser = argparse.ArgumentParser(description="Send sample logs to PostHog")
    parser.add_argument("--service", default="posthog-check", help="service.name attribute")
    parser.add_argument("--environment", default="development", help="deployment.environment attribute")
    parser.add_argument(
        "--handlers",
        default=None,
        help="Comma-separated handlers to use: otel, posthog (default: otel + posthog when a key is set)",
    )
    args = parser.parse_args()

    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        sys.exit("Set POSTHOG_API_KEY (a phc_ project token) first.")

    setup_logger(
        service=args.service,
        environment=args.environment,
        posthog_api_key=api_key,
        posthog_host=os.getenv("POSTHOG_HOST"),
        handlers=args.handlers.split(",") if args.handlers else None,
        level=logging.DEBUG,
    )

    log = get_logger("posthog.check")
    run_id = int(time.time())
    log.debug("posthog-check debug (must NOT appear in PostHog) run=%s", run_id)
    log.info("posthog-check info run=%s", run_id, extra={"user_id": "123"})
    log.warning("posthog-check warning run=%s", run_id)
    log.error("posthog-check error run=%s", run_id)

    for handler in log.handlers:
        handler.close()
    print(f"Sent run={run_id}. In PostHog > Logs search: posthog-check")


if __name__ == "__main__":
    main()
