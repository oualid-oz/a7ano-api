import json
import logging
import sys
from datetime import UTC, datetime
from logging.config import dictConfig
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "ip_address": getattr(record, "ip_address", None),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in self._reserved_keys():
                log_record[key] = value
        return json.dumps(log_record, default=self._json_default)

    @staticmethod
    def _reserved_keys() -> set[str]:
        return {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "request_id",
            "ip_address",
        }

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


class StandardFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.request_id = getattr(record, "request_id", None)
        record.ip_address = getattr(record, "ip_address", None)

        method = getattr(record, "method", None)
        path = getattr(record, "path", None)
        status_code = getattr(record, "status_code", None)
        duration_ms = getattr(record, "duration_ms", None)

        if method and path and status_code is not None:
            dur = f" ({duration_ms:.0f}ms)" if duration_ms is not None else ""
            record.msg = f"{method} {path} → {status_code}{dur}"
            record.args = ()

        return super().format(record)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "ip_address"):
            record.ip_address = None
        return True


def _build_file_handler() -> TimedRotatingFileHandler:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    today = datetime.now(UTC).strftime("%Y%m%d")
    log_path = log_dir / f"log-{today}.log"
    handler = TimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",
        interval=1,
        backupCount=30,
        utc=True,
        encoding="utf-8",
    )
    handler.suffix = "log-%Y%m%d.log"
    handler.namer = lambda name: name
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())
    return handler


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "context": {
                    "()": f"{__name__}.ContextFilter",
                },
            },
            "formatters": {
                "json": {
                    "()": f"{__name__}.JsonFormatter",
                },
                "standard": {
                    "()": f"{__name__}.StandardFormatter",
                    "format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "standard" if settings.debug else "json",
                    "filters": ["context"],
                },
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["console"],
            },
            "loggers": {
                "uvicorn": {"level": "WARNING"},
                "uvicorn.access": {"level": "CRITICAL", "propagate": False},
                "uvicorn.error": {"level": "WARNING"},
                "sqlalchemy": {"level": "WARNING"},
                "sqlalchemy.engine": {"level": "WARNING"},
                "sqlalchemy.engine.Engine": {"level": "CRITICAL", "propagate": False},
                "sqlalchemy.dialects": {"level": "WARNING"},
                "sqlalchemy.pool": {"level": "WARNING"},
                "app.audit.service": {"level": "INFO"},
                "app.memos.service": {"level": "INFO"},
                "app.notifications.service": {"level": "INFO"},
                "app.permissions.service": {"level": "INFO"},
                "app.projects.service": {"level": "INFO"},
                "app.scheduling.service": {"level": "INFO"},
                "app.tasks.service": {"level": "INFO"},
                "app.teams.service": {"level": "INFO"},
                "app.users.service": {"level": "INFO"},
                "app.vault.service": {"level": "INFO"},
            },
        }
    )

    logging.getLogger().addHandler(_build_file_handler())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
