import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from memory.config import get_settings


class StructuredLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._configured = False

    def _configure(self) -> None:
        if self._configured:
            return
        settings = get_settings()
        self._logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s",
                timestamp=True,
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

        self._configured = True

    def debug(self, message: str, **kwargs: Any) -> None:
        self._configure()
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._configure()
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._configure()
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._configure()
        self._logger.error(message, extra=kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self._configure()
        self._logger.exception(message, extra=kwargs)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)