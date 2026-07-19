"""Admin view for EssayPrompt model."""

from sqladmin import ModelView

from ....modules.aes.models.essay_prompt import EssayPrompt
from ..mixins import DataclassModelMixin


class EssayPromptAdmin(DataclassModelMixin, ModelView, model=EssayPrompt):
    """Admin view for EssayPrompt model."""

    name = "Essay Prompt"
    name_plural = "Essay Prompts"
    icon = "fa-solid fa-pen-to-square"
    category = "AES"

    column_list = [EssayPrompt.uuid, EssayPrompt.titulo, EssayPrompt.ano_escolar, EssayPrompt.municipio_id]
    column_details_list = "__all__"
    column_searchable_list = [EssayPrompt.titulo]
    column_sortable_list = [EssayPrompt.titulo, EssayPrompt.ano_escolar]

    can_create = True
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
