import importlib.util
import sys
from pathlib import Path

_HANDLER_MODULE_NAME = "twosteps_logger.handlers.elastic_handler"
_handler_file = Path(__file__).with_name("elastic.handler.py")
_spec = importlib.util.spec_from_file_location(_HANDLER_MODULE_NAME, _handler_file)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError("Unable to load elastic.handler.py")
_module = importlib.util.module_from_spec(_spec)
# Register in sys.modules so patch.object and inspect.getmodule can resolve it
sys.modules[_HANDLER_MODULE_NAME] = _module
_spec.loader.exec_module(_module)

ElasticsearchHandler = _module.ElasticsearchHandler

__all__ = ["ElasticsearchHandler"]

