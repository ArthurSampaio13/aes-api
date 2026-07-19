from loguru import logger as loguru_logger

from src.infrastructure.security import production_validator


def test_production_validator_module_imports_cleanly():
    assert hasattr(production_validator, "logger")
    assert production_validator.logger is loguru_logger
