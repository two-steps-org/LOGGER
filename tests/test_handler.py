"""Tests for twosteps_logger.handlers.elastic.handler."""
import logging
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from twosteps_logger.handlers import ElasticsearchHandler
from twosteps_logger.configuration import LoggerConfiguration


def _get_handler_module():
    """Return the dynamically-loaded elastic.handler module from sys.modules.

    The handlers __init__.py loads elastic.handler.py via importlib and registers
    it under the key 'twosteps_logger.handlers.elastic_handler'.
    """
    import twosteps_logger.handlers  # noqa: ensure package is initialised
    key = "twosteps_logger.handlers.elastic_handler"
    if key not in sys.modules:
        raise ImportError(f"Expected {key!r} in sys.modules after importing handlers package")
    return sys.modules[key]


def _make_handler(prefix="test-logs", **kwargs) -> ElasticsearchHandler:
    """Return a handler with a mocked Elasticsearch client."""
    # Isolate template-dedup state for this prefix
    hmod = _get_handler_module()
    hmod._templates_created.discard(prefix)

    config = LoggerConfiguration(index_name=prefix, **kwargs)
    with patch.object(ElasticsearchHandler, "_get_client") as mock_get:
        mock_es = MagicMock()
        mock_get.return_value = mock_es
        mock_es.indices.put_index_template.return_value = {}
        handler = ElasticsearchHandler(config=config)
    if handler._timer:
        handler._timer.cancel()
    return handler


def _mock_client_on(handler: ElasticsearchHandler) -> MagicMock:
    """Attach a fresh mock ES client to an existing handler."""
    mock_es = MagicMock()
    mock_es.bulk.return_value = {"errors": False, "items": []}
    handler._client = mock_es
    return mock_es


class TestMonthlyIndexNaming:
    def test_month_placeholder_substituted(self):
        handler = _make_handler()
        handler.config.index_pattern = "benchmark-{month}"
        index = handler._get_index_name()
        from datetime import timezone
        now = datetime.now(timezone.utc)
        expected = now.strftime("benchmark-%m_%y")
        assert index == expected

    def test_date_placeholder_substituted(self):
        handler = _make_handler()
        handler.config.index_pattern = "logs-{date}"
        index = handler._get_index_name()
        from datetime import timezone
        now = datetime.now(timezone.utc)
        expected = now.strftime("logs-%Y.%m.%d")
        assert index == expected

    def test_no_placeholder_returns_pattern_as_is(self):
        handler = _make_handler()
        handler.config.index_pattern = "static-index-name"
        assert handler._get_index_name() == "static-index-name"

    def test_march_2026_naming(self):
        handler = _make_handler()
        handler.config.index_pattern = "benchmark-{month}"
        hmod = _get_handler_module()
        with patch.object(hmod, "datetime") as mock_dt:
            from datetime import timezone
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: datetime(2026, 3, 15).strftime(fmt)
            mock_dt.now.return_value = mock_now
            index = handler._get_index_name()
        assert index == "benchmark-03_26"

    def test_april_2026_naming(self):
        handler = _make_handler()
        handler.config.index_pattern = "benchmark-{month}"
        hmod = _get_handler_module()
        with patch.object(hmod, "datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: datetime(2026, 4, 1).strftime(fmt)
            mock_dt.now.return_value = mock_now
            index = handler._get_index_name()
        assert index == "benchmark-04_26"

    def test_february_2026_naming(self):
        handler = _make_handler()
        handler.config.index_pattern = "benchmark-{month}"
        hmod = _get_handler_module()
        with patch.object(hmod, "datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: datetime(2026, 2, 1).strftime(fmt)
            mock_dt.now.return_value = mock_now
            index = handler._get_index_name()
        assert index == "benchmark-02_26"


class TestIndexTemplateCreation:
    def test_template_created_on_init(self):
        hmod = _get_handler_module()
        prefix = "myapp-tmpl-test"
        hmod._templates_created.discard(prefix)
        config = LoggerConfiguration(index_name=prefix)
        with patch.object(ElasticsearchHandler, "_get_client") as mock_get:
            mock_es = MagicMock()
            mock_get.return_value = mock_es
            mock_es.indices.put_index_template.return_value = {}
            handler = ElasticsearchHandler(config=config)
            if handler._timer:
                handler._timer.cancel()
        mock_es.indices.put_index_template.assert_called_once()
        call_kwargs = mock_es.indices.put_index_template.call_args.kwargs
        assert call_kwargs["name"] == f"{prefix}-template"
        assert call_kwargs["index_patterns"] == [f"{prefix}-*"]

    def test_template_uses_direct_kwargs_not_body(self):
        """Verify deprecated body= kwarg is not used."""
        hmod = _get_handler_module()
        prefix = "no-body-test"
        hmod._templates_created.discard(prefix)
        config = LoggerConfiguration(index_name=prefix)
        with patch.object(ElasticsearchHandler, "_get_client") as mock_get:
            mock_es = MagicMock()
            mock_get.return_value = mock_es
            mock_es.indices.put_index_template.return_value = {}
            handler = ElasticsearchHandler(config=config)
            if handler._timer:
                handler._timer.cancel()
        call_kwargs = mock_es.indices.put_index_template.call_args
        assert "body" not in (call_kwargs.kwargs or {})

    def test_template_not_recreated_for_same_prefix(self):
        hmod = _get_handler_module()
        prefix = "dedup-prefix-unique"
        hmod._templates_created.discard(prefix)
        config = LoggerConfiguration(index_name=prefix)
        with patch.object(ElasticsearchHandler, "_get_client") as mock_get:
            mock_es = MagicMock()
            mock_get.return_value = mock_es
            mock_es.indices.put_index_template.return_value = {}
            h1 = ElasticsearchHandler(config=config)
            if h1._timer:
                h1._timer.cancel()
            h2 = ElasticsearchHandler(config=config)
            if h2._timer:
                h2._timer.cancel()
        assert mock_es.indices.put_index_template.call_count == 1

    def test_template_silent_on_error(self, capsys):
        hmod = _get_handler_module()
        prefix = "fail-prefix-silent"
        hmod._templates_created.discard(prefix)
        config = LoggerConfiguration(index_name=prefix)
        with patch.object(ElasticsearchHandler, "_get_client") as mock_get:
            mock_es = MagicMock()
            mock_es.indices.put_index_template.side_effect = Exception("ES down")
            mock_get.return_value = mock_es
            handler = ElasticsearchHandler(config=config)
            if handler._timer:
                handler._timer.cancel()
        captured = capsys.readouterr()
        assert "template warning" in captured.err


class TestEmitAndFlush:
    def test_emit_adds_to_buffer(self):
        handler = _make_handler()
        _mock_client_on(handler)
        record = logging.LogRecord("test", logging.INFO, "", 0, "hello", (), None)
        handler.emit(record)
        with handler._lock:
            assert len(handler._buffer) == 1

    def test_flush_sends_bulk_request(self):
        handler = _make_handler()
        mock_es = _mock_client_on(handler)
        record = logging.LogRecord("test", logging.INFO, "", 0, "hello", (), None)
        handler.emit(record)
        with handler._lock:
            handler._flush_buffer()
        mock_es.bulk.assert_called_once()

    def test_flush_clears_buffer(self):
        handler = _make_handler()
        _mock_client_on(handler)
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        handler.emit(record)
        with handler._lock:
            handler._flush_buffer()
        assert handler._buffer == []

    def test_flush_empty_buffer_noop(self):
        handler = _make_handler()
        mock_es = _mock_client_on(handler)
        with handler._lock:
            handler._flush_buffer()
        mock_es.bulk.assert_not_called()

    def test_flush_sends_correct_index(self):
        handler = _make_handler(prefix="benchmark")
        handler.config.index_pattern = "benchmark-{month}"
        mock_es = _mock_client_on(handler)
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        handler.emit(record)
        with handler._lock:
            handler._flush_buffer()
        bulk_call = mock_es.bulk.call_args
        body = bulk_call.kwargs.get("body") or (bulk_call.args[0] if bulk_call.args else [])
        index_ops = [item for item in body if isinstance(item, dict) and "index" in item]
        assert any(op["index"]["_index"].startswith("benchmark-") for op in index_ops)

    def test_bulk_size_triggers_immediate_flush(self):
        handler = _make_handler()
        handler.config.bulk_size = 2
        mock_es = _mock_client_on(handler)
        r1 = logging.LogRecord("t", logging.INFO, "", 0, "m1", (), None)
        r2 = logging.LogRecord("t", logging.INFO, "", 0, "m2", (), None)
        handler.emit(r1)
        handler.emit(r2)
        mock_es.bulk.assert_called()

    def test_flush_on_exit_flushes_remaining(self):
        handler = _make_handler()
        mock_es = _mock_client_on(handler)
        r = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        handler.emit(r)
        handler._flush_on_exit()
        mock_es.bulk.assert_called()

    def test_flush_error_does_not_raise(self):
        handler = _make_handler()
        mock_es = _mock_client_on(handler)
        mock_es.bulk.side_effect = Exception("connection error")
        record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        handler.emit(record)
        # Should not raise
        with handler._lock:
            handler._flush_buffer()

    def test_build_document_sets_service_and_environment(self):
        handler = _make_handler()
        _mock_client_on(handler)
        handler.config.service_name = "test-svc"
        handler.config.environment = "prod"
        record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        doc = handler._build_document(record)
        assert doc.get("service") == "test-svc"
        assert doc.get("environment") == "prod"
