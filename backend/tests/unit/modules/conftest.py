import pytest


@pytest.fixture(autouse=True)
def set_openrouter_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-for-provider-tests")
