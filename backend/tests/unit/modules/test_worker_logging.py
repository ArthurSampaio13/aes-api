import pytest
from loguru import logger

ESSAY_TEXT = "A minha cidade tem um rio muito bonito que precisa de cuidado."


@pytest.fixture
def captured_logs():
    records = []
    sink_id = logger.add(lambda message: records.append(message.record), level="DEBUG")
    yield records
    logger.remove(sink_id)


@pytest.mark.asyncio
async def test_worker_logs_job_context(captured_logs, correction_job_fixture):
    await correction_job_fixture.run(essay_text=ESSAY_TEXT)

    extras = [record["extra"] for record in captured_logs]
    assert any(extra.get("job_id") for extra in extras)
    assert any(extra.get("provider") == "mock" for extra in extras)
    assert any(extra.get("attempt_number") == 1 for extra in extras)
    assert any(extra.get("outcome") == "success" for extra in extras)


@pytest.mark.asyncio
async def test_worker_never_logs_student_text(captured_logs, correction_job_fixture):
    await correction_job_fixture.run(essay_text=ESSAY_TEXT)

    for record in captured_logs:
        assert ESSAY_TEXT not in record["message"]
        assert ESSAY_TEXT not in str(record["extra"])
