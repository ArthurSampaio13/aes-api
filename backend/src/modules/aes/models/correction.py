import uuid as uuid_pkg
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ....infrastructure.database.models import TimestampMixin, UUIDMixin
from ....infrastructure.database.session import Base


class CorrectionJob(Base, UUIDMixin, TimestampMixin):
    """The unit of async work: one Submission processed under one provider/model condition."""

    __tablename__ = "correction_jobs"

    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    submission_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, ForeignKey("submissions.uuid"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)


class CorrectionAttempt(Base, UUIDMixin, TimestampMixin):
    """One try at correcting a job — the full execution-history row required for TCC traceability."""

    __tablename__ = "correction_attempts"

    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    correction_job_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, ForeignKey("correction_jobs.uuid"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    rubric_version: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    inference_params: Mapped[dict[str, Any]] = mapped_column(JSONB, default_factory=dict)
    tokens_in: Mapped[int | None] = mapped_column(Integer, default=None)
    tokens_out: Mapped[int | None] = mapped_column(Integer, default=None)
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    raw_response_ref: Mapped[str | None] = mapped_column(String(500), default=None)
    validation_errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    code_version: Mapped[str | None] = mapped_column(String(100), default=None)


class CorrectionResult(Base, UUIDMixin, TimestampMixin):
    """The accepted correction output for a job — always references the CorrectionAttempt that produced it."""

    __tablename__ = "correction_results"

    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    correction_job_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID, ForeignKey("correction_jobs.uuid"), nullable=False, unique=True
    )
    correction_attempt_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, ForeignKey("correction_attempts.uuid"), nullable=False)
    scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    requires_teacher_review: Mapped[bool] = mapped_column(default=True, server_default="true")
