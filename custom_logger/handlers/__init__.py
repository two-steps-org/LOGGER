import importlib.util
from pathlib import Path

_handler_file = Path(__file__).with_name("elastic.handler.py")
_spec = importlib.util.spec_from_file_location("custom_logger.handlers.elastic_handler", _handler_file)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError("Unable to load elastic.handler.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

ElasticsearchHandler = _module.ElasticsearchHandler

__all__ = ["ElasticsearchHandler"]

