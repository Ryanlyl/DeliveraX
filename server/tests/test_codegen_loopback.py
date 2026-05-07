from agents.code_generation.nodes import generate_changes


def test_generate_changes_loopback_repairs_allowed_change_files(monkeypatch) -> None:
    class _FakeLLM:
        available = True

        def complete(self, *, system: str, user: str) -> str:
            return """
{
  "files": [
    {
      "path": "index.html",
      "operation": "Modify",
      "content": "<html></html>",
      "reason": "demo"
    }
  ],
  "notes": []
}
"""

    monkeypatch.setattr("agents.code_generation.nodes.ChatLLM", lambda: _FakeLLM())

    state = {
        "local_only": False,
        "design_markdown": "# demo",
        "repo_context": {},
        "implementation_contract": {
            "change_files": [
                {"path": 'index.html" (Add)', "operation": "Modify", "description": ""},
            ]
        },
        "warnings": [],
        "errors": [],
    }

    result = generate_changes(state)  # type: ignore[arg-type]

    assert result["generated_changes"][0]["path"] == "index.html"
    assert result["implementation_contract"]["change_files"][0]["path"] == "index.html"
    assert any("Loopback auto-fix" in warning for warning in result["warnings"])
