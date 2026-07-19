"""Prometheus metrics for correction jobs and LLM token usage — see spec section 4."""

from prometheus_client import Counter, Histogram

CORRECTION_JOBS_TOTAL = Counter("aes_correction_jobs_total", "Correction jobs by final status", ["status", "provider", "model"])
CORRECTION_TOKENS = Histogram(
    "aes_correction_tokens", "LLM tokens per attempt, by provider/model/direction", ["provider", "model", "direction"]
)
CORRECTION_LATENCY_MS = Histogram(
    "aes_correction_latency_ms", "LLM call latency in milliseconds, by provider/model", ["provider", "model"]
)
