from src.modules.aes.metrics import CORRECTION_JOBS_TOTAL, CORRECTION_TOKENS


def test_metrics_are_registered_counters_and_histograms():
    CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1").inc()
    assert CORRECTION_JOBS_TOTAL.labels(status="done", provider="mock", model="mock-v1")._value.get() >= 1

    CORRECTION_TOKENS.labels(provider="mock", model="mock-v1", direction="in").observe(120)
    assert CORRECTION_TOKENS.labels(provider="mock", model="mock-v1", direction="in")._sum.get() >= 120
