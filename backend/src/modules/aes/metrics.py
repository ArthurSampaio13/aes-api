"""Prometheus metrics for correction jobs and LLM token usage — see spec section 4."""

import errno

from loguru import logger
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
    """Bind the metrics HTTP server, tolerating a same-process re-bind of the same port.

    A restart of this worker process can re-fire ``WORKER_STARTUP`` while the previous bind is
    still being torn down. Any other bind failure (wrong permissions, unsupported address family,
    a second worker subprocess still competing for the port) is a real misconfiguration and stays loud.
    """
    try:
        start_http_server(port)
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        logger.warning(f"metrics port {port} already bound, skipping duplicate bind")
