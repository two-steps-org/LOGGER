"""Tests for CustomLogger in twosteps_logger.__init__."""
import logging
import os
from unittest.mock import patch, MagicMock

import pytest
from twosteps_logger import CustomLogger, _filter_extra
from twosteps_logger.handlers import ElasticsearchHandler


def _make_custom_logger(name="test.logger", console=False, **kwargs) -> CustomLogger:
    """Build a CustomLogger with mocked ES client."""
    with patch.object(ElasticsearchHandler, "_get_client") as mock_get:
        mock_es = MagicMock()
        mock_get.return_value = mock_es
        mock_es.indices.put_index_template.return_value = {}
        logger = CustomLogger(name=name, console=console, **kwargs)
    # Cancel background flush timer to keep test suite clean
    for handler in logger.handlers:
        if isinstance(handler, ElasticsearchHandler) and handler._timer:
            handler._timer.cancel()
    return logger


class TestFilterExtra:
    def test_none_returns_empty_dict(self):
        assert _filter_extra(None) == {}

    def test_empty_dict_returns_empty_dict(self):
        assert _filter_extra({}) == {}

    def test_reserved_keys_removed(self):
        result = _filter_extra({"msg": "x", "status": "OK", "lineno": 1})
        assert "msg" not in result
        assert "lineno" not in result
        assert "status" in result  # 'status' is NOT reserved, only standard LogRecord attrs

    def test_name_remapped_to_user_name(self):
        result = _filter_extra({"name": "alice"})
        assert "user_name" in result
        assert result["user_name"] == "alice"
        assert "name" not in result

    def test_non_reserved_keys_preserved(self):
        result = _filter_extra({"status": "SUCCESS", "custom_key": "value"})
        assert result["status"] == "SUCCESS"
        assert result["custom_key"] == "value"


class TestCustomLoggerInit:
    def test_creates_logger_with_correct_name(self):
        logger = _make_custom_logger(name="my.app")
        assert logger.name == "my.app"

    def test_es_handler_attached(self):
        logger = _make_custom_logger()
        es_handlers = [h for h in logger.handlers if isinstance(h, ElasticsearchHandler)]
        assert len(es_handlers) == 1

    def test_console_handler_attached_when_enabled(self):
        logger = _make_custom_logger(console=True)
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                           and not isinstance(h, ElasticsearchHandler)]
        assert len(stream_handlers) == 1

    def test_console_handler_absent_when_disabled(self):
        logger = _make_custom_logger(console=False)
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                           and not isinstance(h, ElasticsearchHandler)]
        assert len(stream_handlers) == 0

    def test_level_set_correctly(self):
        logger = _make_custom_logger(level=logging.DEBUG)
        assert logger.level == logging.DEBUG


class TestDefaultHostsForEnv:
    def test_development_env_uses_localhost_by_default(self):
        hosts = CustomLogger._default_hosts_for_env("development")
        assert hosts[0]["host"] == "localhost"

    def test_local_env_uses_localhost(self):
        hosts = CustomLogger._default_hosts_for_env("local")
        assert hosts[0]["host"] == "localhost"

    def test_production_env_uses_elasticsearch_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ELASTIC_HOST", None)
            hosts = CustomLogger._default_hosts_for_env("production")
        assert hosts[0]["host"] == "elasticsearch"

    def test_elastic_host_env_var_overrides_default(self):
        with patch.dict(os.environ, {"ELASTIC_HOST": "my-es-host"}):
            hosts = CustomLogger._default_hosts_for_env("development")
        assert hosts[0]["host"] == "my-es-host"

    def test_elastic_port_env_var_respected(self):
        with patch.dict(os.environ, {"ELASTIC_PORT": "9300"}):
            hosts = CustomLogger._default_hosts_for_env("development")
        assert hosts[0]["port"] == 9300

    def test_elastic_scheme_env_var_respected(self):
        with patch.dict(os.environ, {"ELASTIC_SCHEME": "https"}):
            hosts = CustomLogger._default_hosts_for_env("development")
        assert hosts[0]["scheme"] == "https"


class TestCustomLoggerLog:
    def test_log_filters_reserved_keys_from_extra(self):
        """The _log override must strip reserved LogRecord keys before passing to super."""
        logger = _make_custom_logger()
        captured = {}

        def capturing_log(self, level, msg, args, exc_info=None, extra=None,
                          stack_info=False, stacklevel=1):
            captured["extra"] = extra

        with patch.object(logging.Logger, "_log", capturing_log):
            logger._log(logging.INFO, "hello", (), extra={"msg": "bad", "status": "OK"})

        extra_passed = captured.get("extra", {})
        assert "msg" not in extra_passed
        assert "status" in extra_passed
