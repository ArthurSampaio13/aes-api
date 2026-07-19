"""Admin views for CorrectionJob, CorrectionAttempt, and CorrectionResult models."""

from sqladmin import ModelView

from ....modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from ..mixins import DataclassModelMixin


class CorrectionJobAdmin(DataclassModelMixin, ModelView, model=CorrectionJob):
    """Read-only admin view for CorrectionJob model."""

    name = "Correction Job"
    name_plural = "Correction Jobs"
    icon = "fa-solid fa-gears"
    category = "AES — Correction Records"

    column_list = [
        CorrectionJob.uuid,
        CorrectionJob.municipio_id,
        CorrectionJob.submission_id,
        CorrectionJob.provider,
        CorrectionJob.model,
        CorrectionJob.status,
    ]
    column_details_list = "__all__"
    column_searchable_list = [CorrectionJob.status, CorrectionJob.provider]
    column_sortable_list = [CorrectionJob.created_at, CorrectionJob.status]

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True


class CorrectionAttemptAdmin(DataclassModelMixin, ModelView, model=CorrectionAttempt):
    """Read-only admin view for CorrectionAttempt model — the TCC traceability record."""

    name = "Correction Attempt"
    name_plural = "Correction Attempts"
    icon = "fa-solid fa-clock-rotate-left"
    category = "AES — Correction Records"

    column_list = [
        CorrectionAttempt.uuid,
        CorrectionAttempt.correction_job_id,
        CorrectionAttempt.attempt_number,
        CorrectionAttempt.provider,
        CorrectionAttempt.model,
        CorrectionAttempt.outcome,
        CorrectionAttempt.tokens_in,
        CorrectionAttempt.tokens_out,
    ]
    column_details_list = "__all__"
    column_searchable_list = [CorrectionAttempt.outcome, CorrectionAttempt.provider]
    column_sortable_list = [CorrectionAttempt.created_at, CorrectionAttempt.attempt_number]

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True


class CorrectionResultAdmin(DataclassModelMixin, ModelView, model=CorrectionResult):
    """Read-only admin view for CorrectionResult model."""

    name = "Correction Result"
    name_plural = "Correction Results"
    icon = "fa-solid fa-clipboard-check"
    category = "AES — Correction Records"

    column_list = [
        CorrectionResult.uuid,
        CorrectionResult.correction_job_id,
        CorrectionResult.requires_teacher_review,
    ]
    column_details_list = "__all__"
    column_sortable_list = [CorrectionResult.created_at]

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
