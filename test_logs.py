"""Test CustomLogger - Client Core Fields Specification format."""
import logging
from custom_logger import CustomLogger

logger = CustomLogger(
    "payment-processor",
    level=logging.DEBUG,
    elastic_hosts=[{"host": "localhost", "port": 9200}],
    service_name="payment-processor",
    environment="production",
)

# DEBUG
logger.debug("Debug message", extra={"debug_id": "dbg-1", "step": 1})

# INFO with auth and request_context
logger.info(
    "User login successful",
    extra={
        "email": "user@example.com",
        "name": "John Doe",  # auto-mapped to user_name (auth.name in output)
        "user_id": "usr_12345",
        "request_id": "req_abc123",
        "method": "POST",
        "endpoint": "/api/v1/users/login",
        "duration_ms": 234,
        "status_code": 200,
    },
)

# INFO with custom_fields
logger.info(
    "Order created",
    extra={
        "order_id": "ORD-001",
        "amount": 99.99,
        "transaction_id": "txn_456",
    },
)

# WARNING
logger.warning("High memory usage", extra={"memory_mb": 850})

# ERROR with error object and stack (exception logged to ES, not re-raised)
try:
    raise ValueError("Invalid payment gateway response")
except ValueError:
    logger.exception(
        "Payment processing failed",
        extra={
            "error_code": "PAYMENT_GATEWAY_ERR",
            "http_status": 502,
            "transaction_id": "txn_pay_456",
            "amount": 99.99,
        },
    )
    # Exception caught - stack goes to ES, no traceback in console

print("Done. Check: http://localhost:9200/python-logs/_search?pretty")

