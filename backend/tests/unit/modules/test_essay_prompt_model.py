from src.modules.aes.models.essay_prompt import EssayPrompt


def test_essay_prompt_carries_support_texts():
    prompt = EssayPrompt(
        municipio_id=1,
        titulo="A importância da leitura",
        enunciado="Escreva um texto dissertativo sobre...",
        ano_escolar="9",
        genero_textual="dissertativo-argumentativo",
        support_texts=[{"titulo": "Texto motivador 1", "conteudo": "..."}],
        rubric_id=1,
        prompt_template_id=1,
    )
    assert prompt.support_texts[0]["titulo"] == "Texto motivador 1"
    assert prompt.uuid is not None
