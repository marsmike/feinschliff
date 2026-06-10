import sys

import pytest

from feinschliff_builder.verify.llm import rubric


def test_client_missing_anthropic_exits_with_friendly_message(monkeypatch):
    rubric._client.cache_clear()
    monkeypatch.setitem(sys.modules, "anthropic", None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(SystemExit, match="anthropic library not installed"):
        rubric._client()


def test_client_missing_api_key_exits_with_friendly_message(monkeypatch):
    pytest.importorskip("anthropic")
    rubric._client.cache_clear()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY not set"):
        rubric._client()
