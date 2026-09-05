"""Prometheus metrics for correction jobs and LLM token usage — see spec section 4."""

from prometheus_client import Counter, Histogram, start_http_server

CORRECTION_JOBS_TOTAL = Counter("aes_correction_jobs_total", "Correction jobs by final status", ["status", "provider", "model"])
CORRECTION_TOKENS = Histogram(
    "aes_correction_tokens",
    "LLM tokens per attempt, by provider/model/direction",
    ["provider", "model", "direction"],
    buckets=(100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000),
)
CORRECTION_LATENCY_MS = Histogram(
    "aes_correction_latency_ms",
    "LLM call latency in milliseconds, by provider/model",
    ["provider", "model"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000),
)
CORRECTION_ATTEMPTS_TOTAL = Counter(
    "aes_correction_attempts_total", "Correction attempts by outcome", ["provider", "model", "outcome"]
)


def start_metrics_server(port: int = 9464) -> None:
    """Bind the metrics HTTP server, tolerating the port already being held.

    Taskiq's process manager fires ``WORKER_STARTUP`` in every worker subprocess sharing this
    pod's network namespace; only the first one to call this needs to actually bind the port.
    """
    try:
        start_http_server(port)
    except OSError:
        pass
