import importlib

from taskiq_aio_sqs import SQSBroker

from src.infrastructure.config.enums import TaskiqBrokerType
from src.infrastructure.config.settings import get_settings
from src.infrastructure.taskiq import brokers as brokers_module


def test_sqs_is_a_supported_broker_type():
    assert TaskiqBrokerType.SQS == "sqs"


def test_create_default_broker_dispatches_to_sqs_factory(monkeypatch):
    monkeypatch.setenv("TASKIQ_BROKER_TYPE", "sqs")
    monkeypatch.setenv("TASKIQ_SQS_QUEUE_URL", "http://localhost:4566/000000000000/correction-jobs")
    get_settings.cache_clear()
    importlib.reload(brokers_module)
    try:
        assert isinstance(brokers_module.default_broker, SQSBroker)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        importlib.reload(brokers_module)
