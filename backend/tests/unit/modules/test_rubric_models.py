from src.modules.aes.models.rubric import PromptTemplate, Rubric

FIXED_CRITERIA = ["adequacao_tema", "estrutura_textual", "coesao_coerencia", "adequacao_ling", "vocabulario"]


def test_rubric_stores_criteria_json():
    rubric = Rubric(
        municipio_id=None,
        version=1,
        criteria={c: {"descricao": c, "peso": 0.2, "escala_max": 5} for c in FIXED_CRITERIA},
    )
    assert set(rubric.criteria.keys()) == set(FIXED_CRITERIA)


def test_prompt_template_is_versioned_text():
    template = PromptTemplate(municipio_id=7, version=1, template_text="Corrija a redação a seguir: {essay_text}")
    assert template.version == 1
    assert "{essay_text}" in template.template_text
