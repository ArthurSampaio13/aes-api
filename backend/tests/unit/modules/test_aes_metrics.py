from prometheus_client import REGISTRY

from src.modules.aes.metrics import (
    CORRECTION_ATTEMPTS_TOTAL,
    CORRECTION_JOBS_TOTAL,
    CORRECTION_LATENCY_MS,
    CORRECTION_TOKENS,
)


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
