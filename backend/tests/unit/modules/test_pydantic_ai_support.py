import json

from pydantic_ai import ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart

from src.modules.aes.providers._pydantic_ai_support import extract_raw_output_text, split_prompt_for_caching


def test_extract_raw_output_text_reads_tool_call_args():
    messages = [
        ModelRequest(parts=[UserPromptPart(content="corrija isto")]),
        ModelResponse(parts=[ToolCallPart(tool_name="final_result", args={"feedback": "ok"})]),
    ]
    assert json.loads(extract_raw_output_text(messages)) == {"feedback": "ok"}


def test_extract_raw_output_text_reads_plain_text_when_no_tool_call():
    messages = [
        ModelRequest(parts=[UserPromptPart(content="corrija isto")]),
        ModelResponse(parts=[TextPart(content="resposta livre")]),
    ]
    assert extract_raw_output_text(messages) == "resposta livre"


def test_extract_raw_output_text_returns_empty_string_when_no_model_response():
    messages = [ModelRequest(parts=[UserPromptPart(content="corrija isto")])]
    assert extract_raw_output_text(messages) == ""


def test_split_prompt_for_caching_separates_prefix_from_essay():
    instructions, user_content = split_prompt_for_caching("Corrija: {essay_text}", "texto do aluno")
    assert instructions == "Corrija: "
    assert user_content == "texto do aluno"


def test_split_prompt_for_caching_handles_missing_placeholder():
    instructions, user_content = split_prompt_for_caching("sem placeholder", "texto do aluno")
    assert instructions == "sem placeholder"
    assert user_content == "texto do aluno"


def test_split_prompt_for_caching_handles_text_after_placeholder():
    instructions, user_content = split_prompt_for_caching("Antes {essay_text} depois", "texto")
    assert instructions == "Antes "
    assert user_content == "texto depois"
