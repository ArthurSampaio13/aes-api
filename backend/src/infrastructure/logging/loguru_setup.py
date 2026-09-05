"""Loguru-based logging setup — replaces the stdlib-logging infrastructure this module used to hold."""

import contextvars
import sys
import uuid
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from loguru import logger

from ..config.settings import EnvironmentOption, get_settings

if TYPE_CHECKING:
    from loguru import Record

_configured = False
_configuration_lock = Lock()

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id")

_DEV_FORMAT = (
    "<green>{time:HH:mm:ss}</green> <level>{level: <8}</level> "
    "<cyan>{name}</cyan> [<magenta>{extra[correlation_id]}</magenta>] - <level>{message}</level>"
)
_STRUCTURED_FORMAT = (
    '{time:YYYY-MM-DD HH:mm:ss} level={level} module={name} correlation_id={extra[correlation_id]} message="{message}"'
)


def set_correlation_id(correlation_id: str) -> None:
    _correlation_id_var.set(correlation_id)


def get_correlation_id() -> str | None:
    try:
        return _correlation_id_var.get()
    except LookupError:
        return None


def generate_correlation_id() -> str:
    return str(uuid.uuid4())


def _patch_correlation_id(record: "Record") -> None:
    record["extra"]["correlation_id"] = get_correlation_id() or "no-correlation"


logger.configure(patcher=_patch_correlation_id)


def configure_logging() -> None:
    global _configured
    with _configuration_lock:
        if _configured:
            return

        settings = get_settings()
        logger.remove()

        if settings.ENVIRONMENT == EnvironmentOption.DEVELOPMENT:
            if settings.LOG_CONSOLE_ENABLED:
                level = "DEBUG" if settings.LOG_DEVELOPMENT_VERBOSE else settings.LOG_LEVEL
                logger.add(sys.stdout, format=_DEV_FORMAT, level=level, colorize=True, diagnose=False)
        elif settings.ENVIRONMENT == EnvironmentOption.STAGING:
            if settings.LOG_CONSOLE_ENABLED:
                logger.add(sys.stdout, format=_STRUCTURED_FORMAT, level=settings.LOG_LEVEL, colorize=False, diagnose=False)
        elif settings.ENVIRONMENT == EnvironmentOption.PRODUCTION:
            if settings.LOG_CONSOLE_ENABLED:
                level = "WARNING" if settings.LOG_PRODUCTION_OPTIMIZE else settings.LOG_LEVEL
                logger.add(sys.stdout, serialize=True, level=level, diagnose=False)
        else:
            if settings.LOG_CONSOLE_ENABLED:
                logger.add(sys.stdout, format=_DEV_FORMAT, level=settings.LOG_LEVEL, colorize=True, diagnose=False)

        if settings.LOG_FILE_ENABLED:
            Path(settings.LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
            is_production = settings.ENVIRONMENT == EnvironmentOption.PRODUCTION
            logger.add(
                settings.LOG_FILE_PATH,
                format=_STRUCTURED_FORMAT if not is_production else "{message}",
                serialize=is_production,
                level="DEBUG",
                rotation=settings.LOG_FILE_MAX_SIZE,
                retention=settings.LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
                diagnose=False,
            )

        _configured = True
        logger.info(f"Logging configured for {settings.ENVIRONMENT.value} environment")
