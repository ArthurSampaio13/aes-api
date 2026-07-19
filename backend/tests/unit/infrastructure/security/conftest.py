import logging

import pytest
from loguru import logger


class _PropagateHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        logging.getLogger(record.name).handle(record)


@pytest.fixture(autouse=True)
def _propagate_loguru_to_caplog():
    sink_id = logger.add(_PropagateHandler(), format="{message}")
    yield
    logger.remove(sink_id)
