from typing import Any

import pytest
from loguru import logger

from src.modules.aes.providers.base import ProviderResponse
from tests.unit.modules.test_correction_worker import _RaisingProvider

ESSAY_TEXT = "A minha cidade tem um rio muito bonito que precisa de cuidado."


class _LeakyValidationErrorProvider:
    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        try:
            raise ValueError(f"model produced invalid output for essay: {essay_text}")
        except Exception as exc:
            return ProviderResponse(
                raw_text="",
                structured=None,
                tokens_in=0,
                tokens_out=0,
                latency_ms=1,
                validation_error=str(exc),
                validation_error_type=type(exc).__name__,
            )


@pytest.fixture
def captured_logs():
    entries = []

    def _sink(message):
        entries.append({"record": message.record, "rendered": str(message)})

    sink_id = logger.add(_sink, level="DEBUG", diagnose=False)
    yield entries
    logger.remove(sink_id)


def _assert_no_essay_leak(captured_logs):
    for entry in captured_logs:
        record = entry["record"]
        assert ESSAY_TEXT not in record["message"]
        assert ESSAY_TEXT not in str(record["extra"])
        assert ESSAY_TEXT not in str(record["exception"])
        assert ESSAY_TEXT not in entry["rendered"]


@pytest.mark.asyncio
async def test_worker_logs_job_context(captured_logs, correction_job_fixture):
    await correction_job_fixture.run(essay_text=ESSAY_TEXT)

    extras = [entry["record"]["extra"] for entry in captured_logs]
    assert any(extra.get("job_id") for extra in extras)
    assert any(extra.get("provider") == "mock" for extra in extras)
    assert any(extra.get("attempt_number") == 1 for extra in extras)
    assert any(extra.get("outcome") == "success" for extra in extras)


@pytest.mark.asyncio
async def test_worker_never_logs_student_text(captured_logs, correction_job_fixture):
    await correction_job_fixture.run(essay_text=ESSAY_TEXT)

    _assert_no_essay_leak(captured_logs)


@pytest.mark.asyncio
async def test_worker_never_logs_student_text_on_unhandled_error(captured_logs, correction_job_fixture):
    municipio, job = await correction_job_fixture.build(raw_text=ESSAY_TEXT)

    with pytest.raises(RuntimeError, match="provider exploded"):
        await correction_job_fixture.process(municipio, job, provider=_RaisingProvider())

    levels = [entry["record"]["level"].name for entry in captured_logs]
    assert "ERROR" in levels
    _assert_no_essay_leak(captured_logs)


@pytest.mark.asyncio
async def test_worker_never_logs_essay_text_embedded_in_provider_validation_error(captured_logs, correction_job_fixture):
    await correction_job_fixture.run(essay_text=ESSAY_TEXT, provider=_LeakyValidationErrorProvider())

    _assert_no_essay_leak(captured_logs)
