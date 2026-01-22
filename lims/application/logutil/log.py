import logging
import sys
from typing import Any


class LoggerProxy:
    """Proxy that returns per-module loggers automatically."""

    def __init__(self):
        self._cache: dict[str, logging.Logger] = {}

    def _get_logger(self) -> logging.Logger:
        # Go up two frames: caller → __getattr__ → here
        frame = sys._getframe(2)
        module_name = frame.f_globals.get("__name__", "__main__")

        if module_name not in self._cache:
            self._cache[module_name] = logging.getLogger(module_name)
        return self._cache[module_name]

    def __getattr__(self, name: str) -> Any:
        logger = self._get_logger()
        return getattr(logger, name)

    def __dir__(self):
        # IDE autocomplete support
        return dir(logging.getLogger())


# Default export: auto per-module logger
log: logging.Logger = LoggerProxy()


def get_named_logger(name: str) -> logging.Logger:
    """Get a logger with a custom name (bypasses module auto-detection)."""
    return logging.getLogger(name)
