from __future__ import annotations

import json
import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Iterator

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_job_type: ContextVar[str | None] = ContextVar("job_type", default=None)

_context_vars = {
    "request_id": _request_id,
    "correlation_id": _correlation_id,
    "job_type": _job_type,
}

_reserved_log_record_keys = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}
_MANAGED_HANDLER_ATTR = "_talenti_managed_handler"


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field_name, context_var in _context_vars.items():
            value = context_var.get()
            if value:
                payload[field_name] = value

        for key, value in record.__dict__.items():
            if key in _reserved_log_record_keys or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(*, service_name: str, log_level: str = "INFO", disable_uvicorn_access: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    setattr(handler, _MANAGED_HANDLER_ATTR, True)

    root_logger = logging.getLogger()
    _remove_managed_handlers(root_logger)
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        _remove_managed_handlers(logger)
        logger.propagate = True
        logger.setLevel(log_level.upper())

    if disable_uvicorn_access:
        logging.getLogger("uvicorn.access").disabled = True


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for existing_handler in list(logger.handlers):
        if getattr(existing_handler, _MANAGED_HANDLER_ATTR, False):
            logger.removeHandler(existing_handler)


@contextmanager
def log_context(**values: str | None) -> Iterator[None]:
    tokens: dict[str, Token[str | None]] = {}
    try:
        for name, value in values.items():
            context_var = _context_vars.get(name)
            if context_var is None:
                continue
            tokens[name] = context_var.set(value)
        yield
    finally:
        for name, token in tokens.items():
            _context_vars[name].reset(token)
