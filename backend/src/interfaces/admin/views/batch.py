"""Admin view for Batch model."""

from sqladmin import ModelView

from ....modules.aes.models.submission import Batch
from ..mixins import DataclassModelMixin


class BatchAdmin(DataclassModelMixin, ModelView, model=Batch):
    """Read-only admin view for Batch model."""

    name = "Batch"
    name_plural = "Batches"
    icon = "fa-solid fa-layer-group"
    category = "AES — Correction Records"

    column_list = [Batch.uuid, Batch.municipio_id, Batch.essay_prompt_id, Batch.created_by_user_id, Batch.created_at]
    column_details_list = "__all__"
    column_sortable_list = [Batch.created_at]

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
