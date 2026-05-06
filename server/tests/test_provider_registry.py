from __future__ import annotations

from api_server.providers.registry import list_provider_public, provider_registry


def test_provider_registry_contains_openai_and_deepseek(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    registry = provider_registry()
    assert "openai" in registry
    assert "deepseek" in registry

    providers = list_provider_public()
    by_id = {item["id"]: item for item in providers}

    assert by_id["openai"]["kind"] == "openai-compatible"
    assert by_id["deepseek"]["kind"] == "openai-compatible"

    assert by_id["openai"]["configured"] is False
    assert by_id["deepseek"]["configured"] is False


def test_provider_registry_marks_anthropic_unavailable() -> None:
    registry = provider_registry()
    assert "anthropic" in registry
    assert registry["anthropic"].available is False
