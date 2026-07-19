"""Admin view for Municipio model."""

from sqladmin import ModelView

from ....modules.municipio.models import Municipio
from ..mixins import DataclassModelMixin


class MunicipioAdmin(DataclassModelMixin, ModelView, model=Municipio):
    """Admin view for Municipio model."""

    name = "Município"
    name_plural = "Municípios"
    icon = "fa-solid fa-city"
    category = "AES"

    column_list = [Municipio.id, Municipio.nome, Municipio.monthly_token_budget]
    column_details_list = "__all__"
    column_searchable_list = [Municipio.nome]
    column_sortable_list = [Municipio.id, Municipio.nome]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
