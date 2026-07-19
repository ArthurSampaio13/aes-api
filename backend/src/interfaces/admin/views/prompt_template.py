"""Admin view for PromptTemplate model."""

from sqladmin import ModelView

from ....modules.aes.models.rubric import PromptTemplate
from ..mixins import DataclassModelMixin


class PromptTemplateAdmin(DataclassModelMixin, ModelView, model=PromptTemplate):
    """Admin view for PromptTemplate model."""

    name = "Prompt Template"
    name_plural = "Prompt Templates"
    icon = "fa-solid fa-file-lines"
    category = "AES"

    column_list = [PromptTemplate.id, PromptTemplate.version, PromptTemplate.municipio_id]
    column_details_list = "__all__"
    column_sortable_list = [PromptTemplate.id, PromptTemplate.version]

    can_create = True
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
