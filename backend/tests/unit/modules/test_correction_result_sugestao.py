from src.modules.aes.models.correction import CorrectionResult
from src.modules.aes.schemas.submission import JobResultRead


def test_correction_result_carries_sugestao_acionavel():
    result = CorrectionResult(
        municipio_id=1,
        correction_job_id="00000000-0000-0000-0000-000000000001",
        correction_attempt_id="00000000-0000-0000-0000-000000000002",
        scores={},
        feedback="Bom texto.",
        sugestao_acionavel="Revise a conclusão para retomar a tese.",
    )
    assert result.sugestao_acionavel == "Revise a conclusão para retomar a tese."


def test_job_result_read_exposes_sugestao_acionavel():
    payload = JobResultRead(
        scores={},
        feedback="Bom texto.",
        sugestao_acionavel="Revise a conclusão para retomar a tese.",
        requires_teacher_review=True,
    )
    assert payload.sugestao_acionavel == "Revise a conclusão para retomar a tese."
