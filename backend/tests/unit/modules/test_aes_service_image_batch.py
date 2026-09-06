import pytest
from sqlalchemy import select

from src.modules.aes.models.essay_prompt import EssayPrompt
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.aes.models.submission import Batch, Submission
from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.service import AesService
from src.modules.aes.storage import ObjectStorage
from src.modules.common.exceptions import ValidationError
from src.modules.municipio.models import Municipio


class _FakeS3Client:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    async def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def _seed_essay_prompt(db_session, test_user, nome: str) -> str:
    municipio = Municipio(nome=nome)
    db_session.add(municipio)
    await db_session.commit()
    test_user["municipio_id"] = municipio.id

    rubric = Rubric(
        version=1,
        criteria={c: {"descricao": c, "peso": 0.2, "escala_max": 10} for c in FIXED_CRITERIA},
        municipio_id=municipio.id,
    )
    template = PromptTemplate(version=1, template_text="Corrija: {essay_text}", municipio_id=municipio.id)
    db_session.add_all([rubric, template])
    await db_session.flush()
    essay_prompt = EssayPrompt(
        municipio_id=municipio.id,
        titulo="Teste",
        enunciado="Escreva sobre...",
        ano_escolar="9",
        genero_textual="dissertativo-argumentativo",
        rubric_id=rubric.id,
        prompt_template_id=template.id,
    )
    db_session.add(essay_prompt)
    await db_session.commit()
    return str(essay_prompt.uuid)


@pytest.mark.asyncio
async def test_submit_image_batch_creates_one_submission_and_job_per_image(db_session, test_user):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Image Batch Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    service = AesService()
    batch_id, job_ids = await service.submit_image_batch(
        essay_prompt_uuid=essay_prompt_uuid,
        images=[(b"jpeg-bytes", "image/jpeg"), (b"png-bytes", "image/png")],
        provider="mock",
        model="mock-v1",
        user_id=test_user["id"],
        municipio_id=test_user["municipio_id"],
        db=db_session,
        object_storage=storage,
    )

    assert len(job_ids) == 2
    submissions = (await db_session.execute(select(Submission).where(Submission.batch_id == batch_id))).scalars().all()
    assert len(submissions) == 2
    for submission in submissions:
        assert submission.input_type == "image"
        assert submission.raw_text is None
        assert submission.original_ref.startswith(f"submissions/{submission.uuid}/original.")


@pytest.mark.asyncio
async def test_submit_image_batch_accepts_single_page_pdf(db_session, test_user):
    """Redacao escaneada costuma sair em PDF de uma folha; o Textract sincrono le esse formato."""
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Pdf Batch Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    service = AesService()
    batch_id, job_ids = await service.submit_image_batch(
        essay_prompt_uuid=essay_prompt_uuid,
        images=[(b"%PDF-1.4 bytes", "application/pdf")],
        provider="mock",
        model="mock-v1",
        user_id=test_user["id"],
        municipio_id=test_user["municipio_id"],
        db=db_session,
        object_storage=storage,
    )

    assert len(job_ids) == 1
    submission = (await db_session.execute(select(Submission).where(Submission.batch_id == batch_id))).scalars().one()
    assert submission.input_type == "image"
    assert submission.original_ref.endswith(".pdf")


@pytest.mark.asyncio
async def test_submit_image_batch_rejects_empty_image_list(db_session, test_user):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Empty Batch Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    service = AesService()
    with pytest.raises(ValidationError):
        await service.submit_image_batch(
            essay_prompt_uuid=essay_prompt_uuid,
            images=[],
            provider="mock",
            model="mock-v1",
            user_id=test_user["id"],
            municipio_id=test_user["municipio_id"],
            db=db_session,
            object_storage=storage,
        )

    batches = (await db_session.execute(select(Batch).where(Batch.municipio_id == test_user["municipio_id"]))).scalars().all()
    assert len(batches) == 0


@pytest.mark.asyncio
async def test_submit_image_batch_rejects_unsupported_content_type(db_session, test_user):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Bad Content Type Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    service = AesService()
    with pytest.raises(ValidationError):
        await service.submit_image_batch(
            essay_prompt_uuid=essay_prompt_uuid,
            images=[(b"not-an-image", "image/gif")],
            provider="mock",
            model="mock-v1",
            user_id=test_user["id"],
            municipio_id=test_user["municipio_id"],
            db=db_session,
            object_storage=storage,
        )

    batches = (await db_session.execute(select(Batch).where(Batch.municipio_id == test_user["municipio_id"]))).scalars().all()
    assert len(batches) == 0


@pytest.mark.asyncio
async def test_submit_image_batch_rejects_more_than_fifty_images(db_session, test_user):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Too Many Images Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    service = AesService()
    with pytest.raises(ValidationError):
        await service.submit_image_batch(
            essay_prompt_uuid=essay_prompt_uuid,
            images=[(b"jpeg-bytes", "image/jpeg")] * 51,
            provider="mock",
            model="mock-v1",
            user_id=test_user["id"],
            municipio_id=test_user["municipio_id"],
            db=db_session,
            object_storage=storage,
        )

    batches = (await db_session.execute(select(Batch).where(Batch.municipio_id == test_user["municipio_id"]))).scalars().all()
    assert len(batches) == 0


@pytest.mark.asyncio
async def test_submit_image_batch_rejects_oversized_image(db_session, test_user):
    essay_prompt_uuid = await _seed_essay_prompt(db_session, test_user, "Oversized Image Test")
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: _FakeS3Client())

    service = AesService()
    oversized = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ValidationError):
        await service.submit_image_batch(
            essay_prompt_uuid=essay_prompt_uuid,
            images=[(oversized, "image/jpeg")],
            provider="mock",
            model="mock-v1",
            user_id=test_user["id"],
            municipio_id=test_user["municipio_id"],
            db=db_session,
            object_storage=storage,
        )

    batches = (await db_session.execute(select(Batch).where(Batch.municipio_id == test_user["municipio_id"]))).scalars().all()
    assert len(batches) == 0
