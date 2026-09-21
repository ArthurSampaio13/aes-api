"""Repetir a correção das mesmas redações é o que sustenta teste-reteste.

Duas coisas precisam existir para as k execuções serem analisáveis: a redação tem identidade estável entre execuções, e
cada execução se identifica.
"""

import pytest
from sqlalchemy import select

from src.modules.aes.models.correction import CorrectionJob
from src.modules.aes.models.submission import Submission
from src.modules.aes.schemas.submission import BatchSubmitRequest
from src.modules.aes.service import AesService
from src.modules.aes.storage import ObjectStorage
from src.modules.common.exceptions import ResourceNotFoundError, ValidationError

from .test_aes_service_image_batch import _FakeS3Client, _seed_essay_prompt


def _storage() -> ObjectStorage:
    return ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())


async def _submit_two(db_session, test_user, nome: str, labels: list[str] | None = None, run_label: str | None = None):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, nome)
    service = AesService()
    batch_id, job_ids = await service.submit_image_batch(
        essay_prompt_uuid=essay_prompt_uuid,
        images=[(b"jpeg-um", "image/jpeg"), (b"jpeg-dois", "image/jpeg")],
        provider="mock",
        model="mock-v1",
        user_id=test_user["id"],
        municipio_id=test_user["municipio_id"],
        db=db_session,
        object_storage=_storage(),
        labels=labels,
        run_label=run_label,
    )
    return service, batch_id, job_ids


@pytest.mark.asyncio
async def test_the_first_run_can_name_itself_at_upload(db_session, test_user):
    """Deixar a primeira execução sem rótulo obriga a análise a supor que nulo é run-1."""
    _, _, job_ids = await _submit_two(db_session, test_user, "Primeira execucao", run_label="run-1")

    jobs = (await db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid.in_(job_ids)))).scalars().all()
    assert {j.run_label for j in jobs} == {"run-1"}


@pytest.mark.asyncio
async def test_image_batch_records_the_label_of_each_essay(db_session, test_user):
    _, batch_id, _ = await _submit_two(db_session, test_user, "Rotulos", labels=["aluno-01", "aluno-02"])

    submissions = (
        (await db_session.execute(select(Submission).where(Submission.batch_id == batch_id).order_by(Submission.created_at)))
        .scalars()
        .all()
    )
    assert [s.source_label for s in submissions] == ["aluno-01", "aluno-02"]


@pytest.mark.asyncio
async def test_text_batch_carries_the_same_two_labels(db_session, test_user):
    """A suíte de perturbação envia texto; o rastro dela não pode ser pior que o das imagens."""
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Lote de texto")
    service = AesService()

    batch_id, job_ids = await service.submit_batch(
        BatchSubmitRequest(
            essay_prompt_uuid=essay_prompt_uuid,
            texts=["Primeiro texto.", "Segundo texto."],
            labels=["redacao-01", "redacao-02"],
            run_label="run-1",
            provider="mock",
            model="mock-v1",
        ),
        user_id=test_user["id"],
        municipio_id=test_user["municipio_id"],
        db=db_session,
    )

    submissions = (
        (await db_session.execute(select(Submission).where(Submission.batch_id == batch_id).order_by(Submission.created_at)))
        .scalars()
        .all()
    )
    assert [s.source_label for s in submissions] == ["redacao-01", "redacao-02"]
    jobs = (await db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid.in_(job_ids)))).scalars().all()
    assert {j.run_label for j in jobs} == {"run-1"}


@pytest.mark.asyncio
async def test_text_batch_rejects_a_label_list_that_does_not_match_the_texts(db_session, test_user):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Texto desalinhado")

    with pytest.raises(ValidationError):
        await AesService().submit_batch(
            BatchSubmitRequest(
                essay_prompt_uuid=essay_prompt_uuid,
                texts=["Primeiro texto.", "Segundo texto."],
                labels=["redacao-01"],
                provider="mock",
                model="mock-v1",
            ),
            user_id=test_user["id"],
            municipio_id=test_user["municipio_id"],
            db=db_session,
        )

    submissions = (
        (await db_session.execute(select(Submission).where(Submission.municipio_id == test_user["municipio_id"])))
        .scalars()
        .all()
    )
    assert submissions == []


@pytest.mark.asyncio
async def test_image_batch_without_labels_leaves_them_null(db_session, test_user):
    _, batch_id, _ = await _submit_two(db_session, test_user, "Sem rotulos")

    submissions = (await db_session.execute(select(Submission).where(Submission.batch_id == batch_id))).scalars().all()
    assert [s.source_label for s in submissions] == [None, None]


@pytest.mark.asyncio
async def test_image_batch_rejects_a_label_list_that_does_not_match_the_images(db_session, test_user):
    """Rótulo trocado é pior que rótulo nenhum: junta execuções de redações diferentes."""
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Rotulos desalinhados")

    with pytest.raises(ValidationError):
        await AesService().submit_image_batch(
            essay_prompt_uuid=essay_prompt_uuid,
            images=[(b"jpeg-um", "image/jpeg"), (b"jpeg-dois", "image/jpeg")],
            provider="mock",
            model="mock-v1",
            user_id=test_user["id"],
            municipio_id=test_user["municipio_id"],
            db=db_session,
            object_storage=_storage(),
            labels=["aluno-01"],
        )

    submissions = (
        (await db_session.execute(select(Submission).where(Submission.municipio_id == test_user["municipio_id"])))
        .scalars()
        .all()
    )
    assert submissions == []


@pytest.mark.asyncio
async def test_recorrecting_a_batch_reuses_the_submissions_instead_of_creating_new_ones(db_session, test_user):
    """Sem isso, cada execução transcreveria de novo e mediria OCR junto com correção."""
    service, batch_id, primeiros_jobs = await _submit_two(db_session, test_user, "Reexecucao")
    antes = {s.uuid for s in (await db_session.execute(select(Submission))).scalars().all()}

    _, novos_jobs = await service.recorrect_batch(
        batch_id=str(batch_id),
        run_label="run-2",
        provider="mock",
        model="mock-v1",
        municipio_id=test_user["municipio_id"],
        db=db_session,
    )

    depois = {s.uuid for s in (await db_session.execute(select(Submission))).scalars().all()}
    assert depois == antes
    assert len(novos_jobs) == 2
    assert not set(novos_jobs) & set(primeiros_jobs)

    jobs = (await db_session.execute(select(CorrectionJob).where(CorrectionJob.uuid.in_(novos_jobs)))).scalars().all()
    assert {j.run_label for j in jobs} == {"run-2"}
    assert {j.submission_id for j in jobs} == antes


@pytest.mark.asyncio
async def test_recorrecting_an_unknown_batch_is_not_found(db_session, test_user):
    service, _, _ = await _submit_two(db_session, test_user, "Lote inexistente")

    with pytest.raises(ResourceNotFoundError):
        await service.recorrect_batch(
            batch_id="0c1cf2c4-0000-4000-8000-000000000000",
            run_label="run-2",
            provider="mock",
            model="mock-v1",
            municipio_id=test_user["municipio_id"],
            db=db_session,
        )


@pytest.mark.asyncio
async def test_manifest_carries_the_essay_label_and_the_run_label(db_session, test_user):
    """O manifesto é o dado da análise: sem os dois rótulos não se junta redação com execução."""
    service, batch_id, _ = await _submit_two(db_session, test_user, "Manifesto", labels=["aluno-01", "aluno-02"])
    await service.recorrect_batch(
        batch_id=str(batch_id),
        run_label="run-2",
        provider="mock",
        model="mock-v1",
        municipio_id=test_user["municipio_id"],
        db=db_session,
    )

    manifesto = await service.get_batch_manifest(str(batch_id), db_session)

    assert len(manifesto["jobs"]) == 4
    assert {j["source_label"] for j in manifesto["jobs"]} == {"aluno-01", "aluno-02"}
    assert {j["run_label"] for j in manifesto["jobs"]} == {None, "run-2"}
    por_redacao: dict[str, set[str | None]] = {}
    for job in manifesto["jobs"]:
        por_redacao.setdefault(job["source_label"], set()).add(job["run_label"])
    assert por_redacao == {"aluno-01": {None, "run-2"}, "aluno-02": {None, "run-2"}}
