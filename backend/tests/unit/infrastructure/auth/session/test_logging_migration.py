from loguru import logger as loguru_logger

from src.infrastructure.auth.session import manager


def test_session_manager_module_imports_cleanly():
    assert hasattr(manager, "logger")
    assert manager.logger is loguru_logger
