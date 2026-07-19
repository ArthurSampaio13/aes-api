from loguru import logger as loguru_logger

from src.modules.api_keys import service


def test_api_keys_service_module_imports_cleanly():
    assert hasattr(service, "logger")
    assert service.logger is loguru_logger
