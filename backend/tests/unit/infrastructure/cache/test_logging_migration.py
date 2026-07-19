from loguru import logger as loguru_logger

from src.infrastructure.cache import decorator


def test_cache_decorator_module_imports_cleanly():
    assert hasattr(decorator, "logger")
    assert decorator.logger is loguru_logger
