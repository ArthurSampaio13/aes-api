import uuid

from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult


def test_correction_job_defaults():
    job = CorrectionJob(municipio_id=1, submission_id=uuid.uuid4(), provider="mock", model="mock-v1", status="pending")
    assert job.max_attempts == 3


def test_correction_attempt_records_token_usage():
    attempt = CorrectionAttempt(
        municipio_id=1,
        correction_job_id=uuid.uuid4(),
        attempt_number=1,
        provider="mock",
        model="mock-v1",
        prompt_version=1,
        rubric_version=1,
        inference_params={"temperature": 0.0},
        tokens_in=120,
        tokens_out=340,
        latency_ms=800,
        outcome="success",
    )
    assert attempt.tokens_in == 120
    assert attempt.error_message is None


def test_correction_result_requires_teacher_review_by_default():
    result = CorrectionResult(
        municipio_id=1,
        correction_job_id=uuid.uuid4(),
        correction_attempt_id=uuid.uuid4(),
        scores={"adequacao_tema": {"nota": 4, "justificativa": "..."}},
        feedback="Bom desenvolvimento do tema.",
    )
    assert result.requires_teacher_review is True
