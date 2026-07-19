import json

from pydantic_ai import ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart

from src.modules.aes.providers._pydantic_ai_support import extract_raw_output_text


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
