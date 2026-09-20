import importlib

from taskiq_aio_sqs import SQSBroker

from src.infrastructure.config.enums import TaskiqBrokerType
from src.infrastructure.config.settings import get_settings
from src.infrastructure.taskiq import brokers as brokers_module


def test_sqs_is_a_supported_broker_type():
    assert TaskiqBrokerType.SQS == "sqs"


def test_queue_name_from_url_strips_trailing_slash():
    assert brokers_module._queue_name_from_url("http://localhost:4566/000000000000/correction-jobs/") == "correction-jobs"


def test_queue_name_from_url_handles_no_trailing_slash():
    assert brokers_module._queue_name_from_url("http://localhost:4566/000000000000/correction-jobs") == "correction-jobs"


def test_queue_name_from_url_handles_empty_string():
    assert brokers_module._queue_name_from_url("") == ""


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


def _sqs_env(monkeypatch):
    monkeypatch.setenv("TASKIQ_BROKER_TYPE", "sqs")
    monkeypatch.setenv("TASKIQ_SQS_QUEUE_URL", "http://localhost:4566/000000000000/correction-jobs")


def test_sqs_broker_holds_the_message_longer_than_a_correction_takes(monkeypatch):
    """A correção mede p50 de 65s e até 160s ponta a ponta.

    Com o default de 30s da AWS o SQS torna a mensagem visível no meio da execução e entrega de novo, fazendo o job
    inteiro rodar duas ou três vezes e pagar o modelo cada vez.
    """
    _sqs_env(monkeypatch)
    get_settings.cache_clear()
    importlib.reload(brokers_module)
    try:
        assert brokers_module._create_sqs_broker().visibility_timeout == 900
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        importlib.reload(brokers_module)


def test_sqs_visibility_timeout_is_configurable(monkeypatch):
    _sqs_env(monkeypatch)
    monkeypatch.setenv("TASKIQ_SQS_VISIBILITY_TIMEOUT", "1800")
    get_settings.cache_clear()
    importlib.reload(brokers_module)
    try:
        assert brokers_module._create_sqs_broker().visibility_timeout == 1800
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        importlib.reload(brokers_module)
