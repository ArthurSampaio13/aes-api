"""Admin view for Rubric model."""

from sqladmin import ModelView

from ....modules.aes.models.rubric import Rubric
from ..mixins import DataclassModelMixin


class RubricAdmin(DataclassModelMixin, ModelView, model=Rubric):
    """Admin view for Rubric model."""

    name = "Rubric"
    name_plural = "Rubrics"
    icon = "fa-solid fa-list-check"
    category = "AES"

    column_list = [Rubric.id, Rubric.version, Rubric.municipio_id]
    column_details_list = "__all__"
    column_sortable_list = [Rubric.id, Rubric.version]

    can_create = True
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
