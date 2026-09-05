import errno
import socket

import pytest
from loguru import logger
from prometheus_client import REGISTRY

from src.modules.aes.metrics import (
    CORRECTION_ATTEMPTS_TOTAL,
    CORRECTION_JOBS_TOTAL,
    CORRECTION_LATENCY_MS,
    CORRECTION_TOKENS,
    start_metrics_server,
)


@pytest.fixture
def captured_logs():
    entries = []
    sink_id = logger.add(lambda message: entries.append(message.record), level="DEBUG", diagnose=False)
    yield entries
    logger.remove(sink_id)


def test_metrics_are_registered_counters_and_histograms():
    CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1").inc()
    assert CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1")._value.get() >= 1

    CORRECTION_TOKENS.labels(provider="mock", model="mock-v1", direction="in").observe(120)
    assert CORRECTION_TOKENS.labels(provider="mock", model="mock-v1", direction="in")._sum.get() >= 120


def test_attempts_counter_increments_by_outcome():
    before = (
        REGISTRY.get_sample_value(
            "aes_correction_attempts_total",
            {"provider": "mock", "model": "mock-v1", "outcome": "retry"},
        )
        or 0.0
    )

    CORRECTION_ATTEMPTS_TOTAL.labels(provider="mock", model="mock-v1", outcome="retry").inc()

    after = REGISTRY.get_sample_value(
        "aes_correction_attempts_total",
        {"provider": "mock", "model": "mock-v1", "outcome": "retry"},
    )
    assert after == before + 1


def test_latency_histogram_buckets_cover_realistic_observations():
    CORRECTION_LATENCY_MS.labels(provider="mock", model="mock-v1").observe(456)

    finite_count = REGISTRY.get_sample_value(
        "aes_correction_latency_ms_bucket",
        {"provider": "mock", "model": "mock-v1", "le": "1000.0"},
    )
    assert finite_count is not None and finite_count >= 1.0


def test_tokens_histogram_buckets_cover_realistic_observations():
    CORRECTION_TOKENS.labels(provider="mock", model="mock-v1", direction="in").observe(1200)

    finite_count = REGISTRY.get_sample_value(
        "aes_correction_tokens_bucket",
        {"provider": "mock", "model": "mock-v1", "direction": "in", "le": "2500.0"},
    )
    assert finite_count is not None and finite_count >= 1.0


def test_start_metrics_server_skips_a_duplicate_bind_and_warns(captured_logs):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    try:
        start_metrics_server(port)
    finally:
        sock.close()

    warnings = [r for r in captured_logs if r["level"].name == "WARNING"]
    assert any("already bound" in r["message"] for r in warnings)


def test_start_metrics_server_reraises_other_os_errors(monkeypatch):
    def _boom(port):
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr("src.modules.aes.metrics.start_http_server", _boom)

    with pytest.raises(OSError, match="Permission denied"):
        start_metrics_server(9464)
