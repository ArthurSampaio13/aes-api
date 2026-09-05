import sqladmin

from src.interfaces.admin.views import (
    EssayPromptAdmin,
    MunicipioAdmin,
    PromptTemplateAdmin,
    RubricAdmin,
    register_admin_views,
)
from src.modules.aes.models.essay_prompt import EssayPrompt
from src.modules.aes.models.rubric import PromptTemplate, Rubric
from src.modules.municipio.models import Municipio


def test_municipio_admin_targets_municipio_model():
    assert MunicipioAdmin.model is Municipio


def test_rubric_admin_targets_rubric_model():
    assert RubricAdmin.model is Rubric


def test_prompt_template_admin_targets_prompt_template_model():
    assert PromptTemplateAdmin.model is PromptTemplate


def test_essay_prompt_admin_targets_essay_prompt_model():
    assert EssayPromptAdmin.model is EssayPrompt


def test_register_admin_views_includes_aes_config_views():
    admin = sqladmin.Admin.__new__(sqladmin.Admin)
    admin._views = []
    admin.add_view = lambda view: admin._views.append(view)

    register_admin_views(admin)

    registered_models = {v.model for v in admin._views}
    assert Municipio in registered_models
    assert Rubric in registered_models
    assert PromptTemplate in registered_models
    assert EssayPrompt in registered_models
