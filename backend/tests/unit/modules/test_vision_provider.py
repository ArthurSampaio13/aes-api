import pytest
from pydantic_ai import BinaryContent, RequestUsage
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.modules.aes.providers.vision import TRANSCRIPTION_PROMPT, VisionOCRProvider
from src.modules.common.exceptions import TranscriptionQualityError


def test_construction_succeeds_without_the_key_in_the_process_environment(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")
    assert provider.model_id == "openrouter:modelo/teste"


PDF_BYTES = b"%PDF-1.4 conteudo"
PNG_BYTES = b"\x89PNG\r\n\x1a\n conteudo"
JPEG_BYTES = b"\xff\xd8\xff\xe0 conteudo"


def _capturing_model(capturado: dict):
    def responder(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        capturado["messages"] = messages
        capturado["settings"] = info.model_settings
        payload = {"texto": "  Primeira linha.\nSegunda linha.\n", "transcricao_completa": True, "trechos_ilegiveis": 0}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])

    return FunctionModel(responder)


def _modelo_de_transcricao(sequencia: list[dict], chamadas: list):
    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        chamadas.append(messages)
        payload = sequencia[min(len(chamadas) - 1, len(sequencia) - 1)]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])

    return FunctionModel(responder)


def _partes_do_pedido(capturado: dict) -> list:
    partes = []
    for message in capturado["messages"]:
        for part in getattr(message, "parts", []):
            conteudo = getattr(part, "content", None)
            if isinstance(conteudo, list):
                partes += conteudo
    return partes


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "media_type"),
    [(PDF_BYTES, "application/pdf"), (PNG_BYTES, "image/png"), (JPEG_BYTES, "image/jpeg")],
)
async def test_media_type_comes_from_the_magic_bytes(data: bytes, media_type: str):
    capturado: dict = {}
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model(capturado)):
        await provider.extract_text(image_bytes=data)

    binarias = [p for p in _partes_do_pedido(capturado) if isinstance(p, BinaryContent)]
    assert len(binarias) == 1
    assert binarias[0].media_type == media_type
    assert binarias[0].data == data


@pytest.mark.asyncio
async def test_returns_the_transcription_stripped():
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model({})):
        result = await provider.extract_text(image_bytes=PNG_BYTES)

    assert result.text == "Primeira linha.\nSegunda linha."


@pytest.mark.asyncio
async def test_the_prompt_that_reaches_the_model_forbids_fixing_the_student_spelling():
    capturado: dict = {}
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model(capturado)):
        await provider.extract_text(image_bytes=PNG_BYTES)

    assert TRANSCRIPTION_PROMPT in _partes_do_pedido(capturado)
    assert "sem corrigir ortografia" in TRANSCRIPTION_PROMPT


@pytest.mark.asyncio
async def test_transcription_is_deterministic_and_denies_provider_data_collection():
    capturado: dict = {}
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model(capturado)):
        await provider.extract_text(image_bytes=PNG_BYTES)

    assert capturado["settings"]["temperature"] == 0.0
    assert capturado["settings"]["openrouter_provider"]["data_collection"] == "deny"
    assert capturado["settings"]["seed"] == 42


@pytest.mark.asyncio
async def test_transcricao_incompleta_provoca_segunda_chamada_ao_modelo():
    chamadas: list = []
    sequencia = [
        {"texto": "tres palavras so", "transcricao_completa": False, "trechos_ilegiveis": 0},
        {"texto": " ".join(["palavra"] * 60), "transcricao_completa": True, "trechos_ilegiveis": 0},
    ]
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_modelo_de_transcricao(sequencia, chamadas)):
        resultado = await provider.extract_text(image_bytes=PNG_BYTES)

    assert len(chamadas) == 2
    assert resultado.transcricao_completa is True
    assert [e["veredito"] for e in resultado.meta["guardrail_events"]] == ["retry", "allow"]


@pytest.mark.asyncio
async def test_transcricao_persistentemente_incompleta_levanta_erro_de_dominio():
    chamadas: list = []
    sequencia = [{"texto": "curto", "transcricao_completa": False, "trechos_ilegiveis": 0}]
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_modelo_de_transcricao(sequencia, chamadas)):
        with pytest.raises(TranscriptionQualityError):
            await provider.extract_text(image_bytes=PNG_BYTES)


@pytest.mark.asyncio
async def test_falha_de_qualidade_carrega_o_uso_real_das_chamadas_ja_feitas():
    """As chamadas ao modelo que resultaram em erro de qualidade ja foram pagas.

    O erro tem que carregar esse uso consigo, para o worker gravar o rastro antes de propagar a falha; sem isso a
    submissao fica sem nenhum registro da tentativa.
    """
    chamadas: list = []

    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        chamadas.append(messages)
        payload = {"texto": "curto", "transcricao_completa": False, "trechos_ilegiveis": 0}
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, payload)],
            usage=RequestUsage(input_tokens=500, output_tokens=100),
        )

    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=FunctionModel(responder)):
        with pytest.raises(TranscriptionQualityError) as excinfo:
            await provider.extract_text(image_bytes=PNG_BYTES)

    partial_meta = excinfo.value.partial_meta
    assert partial_meta["model"] == "openrouter:modelo/teste"
    assert partial_meta["tokens_in"] == 500 * len(chamadas)
    assert partial_meta["tokens_out"] == 100 * len(chamadas)


@pytest.mark.asyncio
async def test_transcricao_curta_e_perguntada_uma_vez_e_a_reafirmacao_passa():
    """O guard de contagem de palavras é estadual: pergunta uma vez, aceita a repetição.

    Duas chamadas ao modelo, e a redação curta do aluno sobrevive.
    """
    chamadas: list = []
    sequencia = [{"texto": "Eu gosto de jogar bola.", "transcricao_completa": True, "trechos_ilegiveis": 0}]
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_modelo_de_transcricao(sequencia, chamadas)):
        resultado = await provider.extract_text(image_bytes=PNG_BYTES)

    assert len(chamadas) == 2
    assert resultado.text == "Eu gosto de jogar bola."
    assert [e["veredito"] for e in resultado.meta["guardrail_events"]] == ["retry", "allow"]


@pytest.mark.asyncio
async def test_meta_da_transcricao_registra_modelo_tokens_e_retries():
    chamadas: list = []
    sequencia = [{"texto": " ".join(["palavra"] * 60), "transcricao_completa": True, "trechos_ilegiveis": 0}]
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_modelo_de_transcricao(sequencia, chamadas)):
        resultado = await provider.extract_text(image_bytes=PNG_BYTES)

    assert resultado.meta["model"] == "openrouter:modelo/teste"
    assert resultado.meta["model_retries"] == 0
    assert resultado.meta["palavras"] == 60
