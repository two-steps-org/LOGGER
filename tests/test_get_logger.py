"""Tests for twosteps_logger.get_logger module."""
import logging
import sys
import pytest
from unittest.mock import patch, MagicMock

# Import the package first so sys.modules is populated, then fetch the actual module.
import twosteps_logger  # noqa: F401
gl_module = sys.modules["twosteps_logger.get_logger"]

from twosteps_logger.get_logger import (
    set_request_context,
    clear_request_context,
    setup_logger,
    get_additional,
    twosteps_logger,
    get_logger,
    _request_context,
)
from twosteps_logger.constants import StatusType


@pytest.fixture(autouse=True)
def reset_state():
    """Reset module-level state between tests."""
    _request_context.set({})
    original_defaults = dict(gl_module._logger_defaults)
    gl_module._logger_defaults.clear()
    yield
    gl_module._logger_defaults.clear()
    gl_module._logger_defaults.update(original_defaults)
    _request_context.set({})


class TestRequestContext:
    def test_set_request_context_stores_values(self):
        set_request_context(request_id="r1", method="GET")
        ctx = _request_context.get()
        assert ctx["request_id"] == "r1"
        assert ctx["method"] == "GET"

    def test_set_request_context_merges(self):
        set_request_context(request_id="r1")
        set_request_context(method="POST")
        ctx = _request_context.get()
        assert ctx["request_id"] == "r1"
        assert ctx["method"] == "POST"

    def test_set_request_context_ignores_none_values(self):
        set_request_context(request_id=None, method="GET")
        ctx = _request_context.get()
        assert "request_id" not in ctx
        assert ctx["method"] == "GET"

    def test_clear_request_context_resets(self):
        set_request_context(request_id="r1")
        clear_request_context()
        ctx = _request_context.get()
        assert ctx == {}


class TestSetupLogger:
    def test_setup_logger_sets_index_prefix(self):
        setup_logger(index_prefix="benchmark")
        assert gl_module._logger_defaults["index_prefix"] == "benchmark"

    def test_setup_logger_index_name_alias(self):
        setup_logger(index_name="myapp")
        assert gl_module._logger_defaults["index_prefix"] == "myapp"

    def test_setup_logger_service(self):
        setup_logger(service="my-api")
        assert gl_module._logger_defaults["service"] == "my-api"

    def test_setup_logger_service_name_alias(self):
        setup_logger(service_name="my-api")
        assert gl_module._logger_defaults["service"] == "my-api"

    def test_setup_logger_environment(self):
        setup_logger(environment="production")
        assert gl_module._logger_defaults["environment"] == "production"

    def test_setup_logger_level(self):
        setup_logger(level=logging.DEBUG)
        assert gl_module._logger_defaults["level"] == logging.DEBUG

    def test_setup_logger_logger_level_alias(self):
        setup_logger(logger_level=logging.WARNING)
        assert gl_module._logger_defaults["level"] == logging.WARNING

    def test_setup_logger_elastic_hosts(self):
        hosts = [{"scheme": "http", "host": "eshost", "port": 9200}]
        setup_logger(elastic_hosts=hosts)
        assert gl_module._logger_defaults["elastic_hosts"] == hosts

    def test_setup_logger_hosts_alias(self):
        hosts = [{"scheme": "http", "host": "eshost", "port": 9200}]
        setup_logger(hosts=hosts)
        assert gl_module._logger_defaults["elastic_hosts"] == hosts

    def test_setup_logger_flush_interval(self):
        setup_logger(flush_interval=5.0)
        assert gl_module._logger_defaults["flush_interval"] == 5.0

    def test_setup_logger_bulk_size(self):
        setup_logger(bulk_size=200)
        assert gl_module._logger_defaults["bulk_size"] == 200

    def test_setup_logger_none_values_not_stored(self):
        setup_logger(service=None, environment=None)
        assert "service" not in gl_module._logger_defaults
        assert "environment" not in gl_module._logger_defaults

    def test_setup_logger_mutates_module_dict(self):
        """Verify it's a plain dict mutation, not ContextVar."""
        import contextvars
        setup_logger(service="svc-a")
        # Changes must be visible directly on the module-level dict
        assert gl_module._logger_defaults.get("service") == "svc-a"


class TestGetAdditional:
    def test_default_status_is_pending(self):
        result = get_additional()
        assert result["status"] == "PENDING"

    def test_status_enum_converted_to_value(self):
        result = get_additional(status=StatusType.SUCCESS)
        assert result["status"] == "SUCCESS"

    def test_status_string_passthrough(self):
        result = get_additional(status="FAILURE")
        assert result["status"] == "FAILURE"

    def test_message_included_when_provided(self):
        result = get_additional(message="something happened")
        assert result["message"] == "something happened"

    def test_message_absent_when_none(self):
        result = get_additional(message=None)
        assert "message" not in result

    def test_timestamp_present_and_utc_format(self):
        result = get_additional()
        ts = result["timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts

    def test_service_default(self):
        result = get_additional()
        assert "service" in result

    def test_service_override(self):
        result = get_additional(service="custom-svc")
        assert result["service"] == "custom-svc"

    def test_environment_override(self):
        result = get_additional(environment="staging")
        assert result["environment"] == "staging"

    def test_request_context_merged(self):
        set_request_context(request_id="req-1", method="GET")
        result = get_additional()
        assert result["request_id"] == "req-1"
        assert result["method"] == "GET"

    def test_auth_dict_merged_flat(self):
        result = get_additional(auth={"email": "a@b.com", "user_id": 1})
        assert result["email"] == "a@b.com"
        assert result["user_id"] == 1

    def test_error_dict_merged_flat(self):
        result = get_additional(error={"error_code": 500, "error_type": "ServerError"})
        assert result["error_code"] == 500

    def test_custom_fields_nested(self):
        result = get_additional(custom_fields={"action": "login"})
        assert result["custom_fields"] == {"action": "login"}

    def test_extra_kwargs_included(self):
        result = get_additional(my_extra_key="my_value")
        assert result["my_extra_key"] == "my_value"

    def test_none_values_excluded(self):
        result = get_additional(message=None, service=None)
        assert "message" not in result


class TestTwostepsLoggerFactory:
    def _make_logger(self, name="test", **kwargs):
        """Create a twosteps_logger with mocked ES handler.

        Uses patch.object instead of string-path patch because the handler
        module is loaded dynamically via importlib and is not importable by name.
        """
        from twosteps_logger.handlers import ElasticsearchHandler
        with patch.object(ElasticsearchHandler, "_get_client") as mock_client:
            mock_es = MagicMock()
            mock_client.return_value = mock_es
            mock_es.indices.put_index_template.return_value = {}
            logger = twosteps_logger(name, **kwargs)
        return logger

    def test_returns_logger_instance(self):
        logger = self._make_logger()
        assert isinstance(logger, logging.Logger)

    def test_logger_name_set_correctly(self):
        logger = self._make_logger("my.module")
        assert logger.name == "my.module"

    def test_get_logger_alias_works(self):
        from twosteps_logger.handlers import ElasticsearchHandler
        with patch.object(ElasticsearchHandler, "_get_client") as mock_client:
            mock_es = MagicMock()
            mock_client.return_value = mock_es
            mock_es.indices.put_index_template.return_value = {}
            logger = get_logger("alias.test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "alias.test"

    def test_uses_defaults_from_setup_logger(self):
        from twosteps_logger.handlers import ElasticsearchHandler
        setup_logger(service="from-setup", environment="test-env")
        with patch.object(ElasticsearchHandler, "_get_client") as mock_client:
            mock_es = MagicMock()
            mock_client.return_value = mock_es
            mock_es.indices.put_index_template.return_value = {}
            logger = twosteps_logger("app.module")
        assert logger is not None
