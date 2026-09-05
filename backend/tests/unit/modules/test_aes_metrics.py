from prometheus_client import REGISTRY

from src.modules.aes.metrics import CORRECTION_ATTEMPTS_TOTAL, CORRECTION_JOBS_TOTAL, CORRECTION_TOKENS


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
