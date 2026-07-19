import uuid

from src.modules.aes.models.submission import Batch, Submission


def test_batch_links_prompt_and_creator():
    batch = Batch(municipio_id=1, essay_prompt_id=uuid.uuid4(), created_by_user_id=42)
    assert batch.created_by_user_id == 42
    assert batch.uuid is not None


def test_submission_defaults_raw_text_to_none():
    submission = Submission(municipio_id=1, batch_id=uuid.uuid4(), input_type="image", original_ref="s3://bucket/key.png")
    assert submission.raw_text is None
    assert submission.input_type == "image"
