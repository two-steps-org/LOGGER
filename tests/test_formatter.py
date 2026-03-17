"""Tests for twosteps_logger.formatters.json_formatter."""
import json
import logging
import pytest
from twosteps_logger.formatters import JsonFormatter, ECSFormatter
from twosteps_logger.formatters.json_formatter import SKIP_KEYS, AUTH_KEYS, REQUEST_CONTEXT_KEYS


def _make_record(
    msg="test message",
    level=logging.INFO,
    name="test.logger",
    **extra,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


class TestJsonFormatterDocShape:
    def setup_method(self):
        self.fmt = JsonFormatter()

    def test_format_returns_valid_json(self):
        record = _make_record()
        output = self.fmt.format(record)
        doc = json.loads(output)
        assert isinstance(doc, dict)

    def test_doc_has_required_root_keys(self):
        record = _make_record()
        doc = self.fmt._record_to_client_format(record)
        for key in ("@timestamp", "severity", "message", "timestamp", "service", "environment", "status"):
            assert key in doc, f"Missing key: {key}"

    def test_severity_mapped_correctly(self):
        for level, expected in [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]:
            record = _make_record(level=level)
            doc = self.fmt._record_to_client_format(record)
            assert doc["severity"] == expected

    def test_message_content(self):
        record = _make_record(msg="hello world")
        doc = self.fmt._record_to_client_format(record)
        assert doc["message"] == "hello world"

    def test_message_truncated_at_2048(self):
        long_msg = "x" * 3000
        record = _make_record(msg=long_msg)
        doc = self.fmt._record_to_client_format(record)
        assert len(doc["message"]) == 2048
        assert doc["message"].endswith("...")

    def test_service_from_record_attribute(self):
        record = _make_record(service="my-service")
        doc = self.fmt._record_to_client_format(record)
        assert doc["service"] == "my-service"

    def test_environment_from_record_attribute(self):
        record = _make_record(environment="production")
        doc = self.fmt._record_to_client_format(record)
        assert doc["environment"] == "production"

    def test_default_status_is_pending(self):
        record = _make_record()
        doc = self.fmt._record_to_client_format(record)
        assert doc["status"] == "PENDING"

    def test_status_from_record_attribute(self):
        record = _make_record(status="SUCCESS")
        doc = self.fmt._record_to_client_format(record)
        assert doc["status"] == "SUCCESS"


class TestRequestContext:
    def setup_method(self):
        self.fmt = JsonFormatter()

    def test_request_context_nested_when_fields_present(self):
        record = _make_record(request_id="abc-123", method="GET", endpoint="/api/v1")
        doc = self.fmt._record_to_client_format(record)
        assert "request_context" in doc
        assert doc["request_context"]["request_id"] == "abc-123"
        assert doc["request_context"]["method"] == "GET"

    def test_request_context_from_dict_attribute(self):
        ctx = {"request_id": "xyz", "method": "POST"}
        record = _make_record(request_context=ctx)
        doc = self.fmt._record_to_client_format(record)
        assert doc["request_context"] == ctx

    def test_request_context_absent_when_no_fields(self):
        record = _make_record()
        doc = self.fmt._record_to_client_format(record)
        assert "request_context" not in doc


class TestAuthContext:
    def setup_method(self):
        self.fmt = JsonFormatter()

    def test_auth_nested_when_auth_keys_present(self):
        record = _make_record(user_name="alice", email="alice@example.com")
        doc = self.fmt._record_to_client_format(record)
        assert "auth" in doc
        assert doc["auth"]["email"] == "alice@example.com"

    def test_auth_from_dict_attribute(self):
        auth = {"email": "bob@example.com", "user_id": 42}
        record = _make_record(auth=auth)
        doc = self.fmt._record_to_client_format(record)
        assert doc["auth"] == auth

    def test_auth_absent_when_no_auth_fields(self):
        record = _make_record()
        doc = self.fmt._record_to_client_format(record)
        assert "auth" not in doc

    def test_user_name_remapped_to_name_in_output(self):
        record = _make_record(user_name="charlie")
        doc = self.fmt._record_to_client_format(record)
        assert doc["auth"]["name"] == "charlie"


class TestErrorContext:
    def setup_method(self):
        self.fmt = JsonFormatter()

    def test_error_fields_only_for_error_level(self):
        record = _make_record(level=logging.INFO, error_type="ValueError")
        doc = self.fmt._record_to_client_format(record)
        assert "error" not in doc

    def test_error_extracted_for_error_level(self):
        record = _make_record(level=logging.ERROR, error_type="RuntimeError", error_message="boom")
        doc = self.fmt._record_to_client_format(record)
        assert "error" in doc
        assert doc["error"]["error_type"] == "RuntimeError"
        assert doc["error"]["error_message"] == "boom"

    def test_error_extracted_for_critical_level(self):
        record = _make_record(level=logging.CRITICAL, error_type="OSError")
        doc = self.fmt._record_to_client_format(record)
        assert "error" in doc

    def test_stack_error_absent_for_info(self):
        record = _make_record(level=logging.INFO)
        doc = self.fmt._record_to_client_format(record)
        assert "stack_error" not in doc

    def test_error_from_exc_info(self):
        try:
            raise ValueError("test exc")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = _make_record(level=logging.ERROR)
        record.exc_info = exc_info
        doc = self.fmt._record_to_client_format(record)
        assert "error" in doc
        assert doc["error"]["error_type"] == "ValueError"
        assert "stack_error" in doc


class TestCustomFields:
    def setup_method(self):
        self.fmt = JsonFormatter()

    def test_custom_fields_nested(self):
        record = _make_record(custom_fields={"action": "login", "duration_ms": 120})
        doc = self.fmt._record_to_client_format(record)
        assert "custom_fields" in doc
        assert doc["custom_fields"]["action"] == "login"

    def test_status_not_duplicated_in_custom_fields(self):
        record = _make_record(status="SUCCESS")
        doc = self.fmt._record_to_client_format(record)
        cf = doc.get("custom_fields", {})
        assert "status" not in cf

    def test_service_not_duplicated_in_custom_fields(self):
        record = _make_record(service="my-svc")
        doc = self.fmt._record_to_client_format(record)
        cf = doc.get("custom_fields", {})
        assert "service" not in cf

    def test_environment_not_duplicated_in_custom_fields(self):
        record = _make_record(environment="staging")
        doc = self.fmt._record_to_client_format(record)
        cf = doc.get("custom_fields", {})
        assert "environment" not in cf

    def test_auth_keys_not_in_custom_fields(self):
        record = _make_record(user_name="alice", email="alice@example.com")
        doc = self.fmt._record_to_client_format(record)
        cf = doc.get("custom_fields", {})
        for key in AUTH_KEYS:
            assert key not in cf

    def test_request_context_keys_not_in_custom_fields(self):
        record = _make_record(request_id="r1", method="GET")
        doc = self.fmt._record_to_client_format(record)
        cf = doc.get("custom_fields", {})
        for key in REQUEST_CONTEXT_KEYS:
            assert key not in cf


class TestSkipKeys:
    def test_skip_keys_contains_root_level_fields(self):
        for key in ("status", "service", "environment"):
            assert key in SKIP_KEYS, f"Expected '{key}' in SKIP_KEYS"

    def test_skip_keys_contains_log_record_internals(self):
        for key in ("name", "msg", "args", "levelname", "levelno", "lineno"):
            assert key in SKIP_KEYS


class TestECSFormatterAlias:
    def test_ecs_formatter_is_json_formatter(self):
        assert ECSFormatter is JsonFormatter
