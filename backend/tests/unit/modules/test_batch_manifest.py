import json
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select

from src.modules.aes.models.submission import Submission
from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate, ProviderResponse
from src.modules.aes.schemas.manifest import AttemptManifest, JobManifest
from src.modules.aes.service import AesService
from src.modules.common.exceptions import ResourceNotFoundError


def test_schema_do_manifesto_exige_as_condicoes_de_reproducao():
    assert {"submission_id", "transcription", "attempts", "result"} <= set(JobManifest.model_fields)
    assert {
        "model",
        "served_provider",
        "prompt_version",
        "rubric_version",
        "code_version",
        "inference_params",
        "cache_read_tokens",
        "cost_usd",
        "guardrail_events",
    } <= set(AttemptManifest.model_fields)


@pytest.mark.asyncio
async def test_manifesto_traz_uma_linha_por_job_com_as_condicoes(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    await correction_job_fixture.process(municipio, job)

    db_session = correction_job_fixture.db_session
    submission = (await db_session.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalars().one()

    manifesto = await AesService().get_batch_manifest(str(submission.batch_id), db_session)

    assert manifesto["batch_id"] == str(submission.batch_id)
    assert len(manifesto["jobs"]) == 1
    linha = manifesto["jobs"][0]
    assert linha["status"] == "done"
    assert linha["attempts"][0]["prompt_version"] == 1
    assert linha["attempts"][0]["rubric_version"] == 1
    assert linha["attempts"][0]["inference_params"]
    assert linha["result"]["scores"]
    assert linha["result"]["requires_teacher_review"] is True


class _ProviderComCustoDecimal:
    model_id = "openrouter:modelo/teste"

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        return ProviderResponse(
            raw_text="{}",
            structured=CorrectionCandidate.model_validate(
                {
                    "scores": {c: {"nota": 7, "justificativa": f"ok {c}"} for c in FIXED_CRITERIA},
                    "feedback": "ok",
                    "sugestao_acionavel": "revise",
                }
            ),
            tokens_in=100,
            tokens_out=20,
            latency_ms=10,
            cache_read_tokens=900,
            cache_write_tokens=50,
            cost_usd=Decimal("0.00012345"),
            served_provider="anthropic",
            model_retries=1,
            guardrail_events=[{"guard": "citacoes", "veredito": "retry", "motivo": "citacao ausente: x"}],
        )


@pytest.mark.asyncio
async def test_manifesto_serializa_decimal_uuid_e_vereditos_de_guardrail_como_json(correction_job_fixture):
    municipio, job = await correction_job_fixture.build()
    await correction_job_fixture.process(municipio, job, provider=_ProviderComCustoDecimal())

    db_session = correction_job_fixture.db_session
    submission = (await db_session.execute(select(Submission).where(Submission.uuid == job.submission_id))).scalars().one()

    manifesto = await AesService().get_batch_manifest(str(submission.batch_id), db_session)

    json.dumps(manifesto)
    attempt = manifesto["jobs"][0]["attempts"][0]
    assert attempt["cost_usd"] == "0.00012345"
    assert attempt["cache_read_tokens"] == 900
    assert attempt["cache_write_tokens"] == 50
    assert attempt["served_provider"] == "anthropic"
    assert attempt["guardrail_events"][0]["guard"] == "citacoes"
    assert isinstance(manifesto["batch_id"], str)
    assert isinstance(manifesto["jobs"][0]["job_id"], str)


@pytest.mark.asyncio
async def test_manifesto_de_batch_inexistente_levanta_not_found(correction_job_fixture):
    with pytest.raises(ResourceNotFoundError):
        await AesService().get_batch_manifest("00000000-0000-0000-0000-000000000000", correction_job_fixture.db_session)
