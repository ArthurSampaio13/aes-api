"""Proves tenant isolation holds at the database level, not just in application code."""

import pytest
from faker import Faker
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.auth.utils import get_password_hash
from src.infrastructure.database.tenancy import set_tenant_context
from src.modules.aes.models.correction import CorrectionJob
from src.modules.aes.models.essay_prompt import EssayPrompt
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.aes.models.submission import Batch, Submission
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
from src.modules.aes.storage import ObjectStorage
from src.modules.aes.worker import process_correction_job
from src.modules.municipio.models import Municipio
from src.modules.user.models import User


class _FakeS3Client:
    def __init__(self):
        self.put_calls: list[dict] = []

    async def put_object(self, Bucket, Key, Body, ContentType):
        self.put_calls.append({"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.integration
async def test_rls_blocks_cross_tenant_read_even_without_app_filter(rls_db: AsyncSession):
    municipio_a = Municipio(nome="Municipio A")
    municipio_b = Municipio(nome="Municipio B")
    rls_db.add_all([municipio_a, municipio_b])
    await rls_db.commit()

    await set_tenant_context(rls_db, municipio_id=municipio_a.id, is_superuser=False)
    await rls_db.execute(
        text("INSERT INTO rubrics (municipio_id, version, criteria) VALUES (:mid, 1, '{}'::jsonb)"),
        {"mid": municipio_a.id},
    )
    await rls_db.commit()

    await set_tenant_context(rls_db, municipio_id=municipio_b.id, is_superuser=False)
    result = await rls_db.execute(text("SELECT * FROM rubrics WHERE municipio_id = :mid"), {"mid": municipio_a.id})
    assert result.fetchall() == []

    result = await rls_db.execute(text("SELECT * FROM rubrics"))
    assert result.fetchall() == []

    await set_tenant_context(rls_db, municipio_id=None, is_superuser=True)
    result = await rls_db.execute(text("SELECT * FROM rubrics"))
    assert len(result.fetchall()) == 1


@pytest.mark.integration
async def test_worker_sets_tenant_context_and_completes_job_under_rls(rls_db: AsyncSession):
    municipio = Municipio(nome="Worker RLS Test")
    rls_db.add(municipio)
    await rls_db.commit()

    await set_tenant_context(rls_db, municipio_id=municipio.id, is_superuser=False)

    fake = Faker()
    user = User(
        name=fake.name(),
        username=f"u{fake.random_int(10000, 99999)}",
        email=fake.email(),
        hashed_password=get_password_hash("Password123!"),
        is_superuser=False,
    )
    rls_db.add(user)
    await rls_db.flush()

    rubric = Rubric(
        version=1,
        criteria={c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA},
        municipio_id=municipio.id,
    )
    template = PromptTemplate(version=1, template_text="Corrija: {essay_text}", municipio_id=municipio.id)
    rls_db.add_all([rubric, template])
    await rls_db.flush()
    essay_prompt = EssayPrompt(
        municipio_id=municipio.id,
        titulo="Teste",
        enunciado="Escreva sobre...",
        ano_escolar="9",
        genero_textual="dissertativo-argumentativo",
        rubric_id=rubric.id,
        prompt_template_id=template.id,
    )
    rls_db.add(essay_prompt)
    await rls_db.flush()

    batch = Batch(municipio_id=municipio.id, essay_prompt_id=essay_prompt.uuid, created_by_user_id=user.id)
    rls_db.add(batch)
    await rls_db.flush()
    submission = Submission(
        municipio_id=municipio.id, batch_id=batch.uuid, input_type="text", original_ref="", raw_text="Um texto de teste."
    )
    rls_db.add(submission)
    await rls_db.flush()
    job = CorrectionJob(
        municipio_id=municipio.id, submission_id=submission.uuid, provider="mock", model="mock-v1", status="pending"
    )
    rls_db.add(job)
    await rls_db.commit()

    await rls_db.execute(text("SELECT set_config('app.municipio_id', '', true)"))
    await rls_db.execute(text("SELECT set_config('app.is_superuser', 'false', true)"))

    await process_correction_job(
        job_id=str(job.uuid),
        municipio_id=municipio.id,
        db=rls_db,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client()),
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    refetched = (await rls_db.execute(select(CorrectionJob).where(CorrectionJob.uuid == job.uuid))).scalar_one()
    assert refetched.status == "done"


@pytest.mark.integration
async def test_transaction_scoped_context_is_wiped_by_a_real_commit(rls_db_real_commits: AsyncSession):
    await set_tenant_context(rls_db_real_commits, municipio_id=123, is_superuser=False)
    before = (await rls_db_real_commits.execute(text("SELECT current_setting('app.municipio_id', true)"))).scalar()
    await rls_db_real_commits.commit()
    after = (await rls_db_real_commits.execute(text("SELECT current_setting('app.municipio_id', true)"))).scalar()

    assert before == "123"
    assert after in (None, "")


@pytest.mark.integration
async def test_worker_survives_real_commits_and_completes_job_under_rls(rls_db_real_commits: AsyncSession):
    municipio = Municipio(nome="Worker RLS Real Commit Test")
    rls_db_real_commits.add(municipio)
    await rls_db_real_commits.commit()

    await set_tenant_context(rls_db_real_commits, municipio_id=municipio.id, is_superuser=False)

    fake = Faker()
    user = User(
        name=fake.name(),
        username=f"u{fake.random_int(10000, 99999)}",
        email=fake.email(),
        hashed_password=get_password_hash("Password123!"),
        is_superuser=False,
    )
    rls_db_real_commits.add(user)
    await rls_db_real_commits.flush()

    rubric = Rubric(
        version=1,
        criteria={c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA},
        municipio_id=municipio.id,
    )
    template = PromptTemplate(version=1, template_text="Corrija: {essay_text}", municipio_id=municipio.id)
    rls_db_real_commits.add_all([rubric, template])
    await rls_db_real_commits.flush()
    essay_prompt = EssayPrompt(
        municipio_id=municipio.id,
        titulo="Teste",
        enunciado="Escreva sobre...",
        ano_escolar="9",
        genero_textual="dissertativo-argumentativo",
        rubric_id=rubric.id,
        prompt_template_id=template.id,
    )
    rls_db_real_commits.add(essay_prompt)
    await rls_db_real_commits.flush()

    batch = Batch(municipio_id=municipio.id, essay_prompt_id=essay_prompt.uuid, created_by_user_id=user.id)
    rls_db_real_commits.add(batch)
    await rls_db_real_commits.flush()
    submission = Submission(
        municipio_id=municipio.id, batch_id=batch.uuid, input_type="text", original_ref="", raw_text="Um texto de teste."
    )
    rls_db_real_commits.add(submission)
    await rls_db_real_commits.flush()
    job = CorrectionJob(
        municipio_id=municipio.id, submission_id=submission.uuid, provider="mock", model="mock-v1", status="pending"
    )
    rls_db_real_commits.add(job)
    await rls_db_real_commits.commit()

    await rls_db_real_commits.execute(text("SELECT set_config('app.municipio_id', '', true)"))
    await rls_db_real_commits.execute(text("SELECT set_config('app.is_superuser', 'false', true)"))

    await process_correction_job(
        job_id=str(job.uuid),
        municipio_id=municipio.id,
        db=rls_db_real_commits,
        provider=MockProvider(),
        ocr_provider=MockOCRProvider(),
        object_storage=ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client()),
        prompt_text="Corrija: {essay_text}",
        prompt_version=1,
        rubric_version=1,
    )

    await set_tenant_context(rls_db_real_commits, municipio_id=municipio.id, is_superuser=False)
    refetched = (await rls_db_real_commits.execute(select(CorrectionJob).where(CorrectionJob.uuid == job.uuid))).scalar_one()
    assert refetched.status == "done"
