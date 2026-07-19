"""Admin view for Submission model."""

from sqladmin import ModelView

from ....modules.aes.models.submission import Submission
from ..mixins import DataclassModelMixin


class SubmissionAdmin(DataclassModelMixin, ModelView, model=Submission):
    """Read-only admin view for Submission model."""

    name = "Submission"
    name_plural = "Submissions"
    icon = "fa-solid fa-file-lines"
    category = "AES — Correction Records"

    column_list = [Submission.uuid, Submission.batch_id, Submission.municipio_id, Submission.input_type]
    column_details_list = "__all__"
    column_sortable_list = [Submission.created_at]

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
