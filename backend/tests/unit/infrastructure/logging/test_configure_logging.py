from unittest.mock import MagicMock

import pytest

from src.infrastructure.config.settings import EnvironmentOption, Settings
from src.infrastructure.logging import loguru_setup


@pytest.mark.parametrize("environment", list(EnvironmentOption))
def test_configure_logging_disables_diagnose_on_every_sink(environment, monkeypatch, tmp_path):
    calls: list[tuple[object, dict]] = []

    def fake_add(sink, **kwargs):
        calls.append((sink, kwargs))
        return len(calls)

    monkeypatch.setattr(loguru_setup.logger, "add", fake_add)
    monkeypatch.setattr(loguru_setup.logger, "remove", lambda *a, **k: None)
    monkeypatch.setattr(loguru_setup.logger, "info", lambda *a, **k: None)
    monkeypatch.setattr(loguru_setup, "_configured", False)

    settings = MagicMock(spec=Settings)
    settings.ENVIRONMENT = environment
    settings.LOG_CONSOLE_ENABLED = True
    settings.LOG_FILE_ENABLED = True
    settings.LOG_DEVELOPMENT_VERBOSE = True
    settings.LOG_PRODUCTION_OPTIMIZE = True
    settings.LOG_LEVEL = "INFO"
    settings.LOG_FILE_PATH = str(tmp_path / "app.log")
    settings.LOG_FILE_MAX_SIZE = 10485760
    settings.LOG_FILE_BACKUP_COUNT = 5
    monkeypatch.setattr(loguru_setup, "get_settings", lambda: settings)

    loguru_setup.configure_logging()

    assert calls, "configure_logging() never called logger.add — the _configured guard likely short-circuited it"
    for sink, kwargs in calls:
        assert kwargs.get("diagnose") is False, f"sink {sink!r} was added without diagnose=False: {kwargs}"
