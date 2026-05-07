from agents.code_generation.design_parser import parse_technical_design


def test_parse_technical_design_accepts_string_change_files() -> None:
    markdown = """
## 11. Implementation Contract

```yaml
implementation_contract:
  objective: "demo"
  repo_root: "demo-repo"
  must_read_files:
    - "index.html"
  change_files:
    - "index.html"
  api_changes: []
  state_changes: []
  test_commands: []
  acceptance_checks: []
  constraints: []
```
"""
    contract, _metadata, warnings = parse_technical_design(markdown)
    assert warnings == []
    assert contract["change_files"] == [
        {
            "path": "index.html",
            "operation": "Modify",
            "description": "",
        }
    ]


def test_parse_technical_design_derives_must_read_files_from_string_change_files() -> None:
    markdown = """
## 11. Implementation Contract

```yaml
implementation_contract:
  objective: "demo"
  repo_root: "demo-repo"
  change_files:
    - "src/app.ts"
    - "src/view.ts"
  api_changes: []
  state_changes: []
  test_commands: []
  acceptance_checks: []
  constraints: []
```
"""
    contract, _metadata, _warnings = parse_technical_design(markdown)
    assert contract["must_read_files"] == ["src/app.ts", "src/view.ts"]


def test_parse_technical_design_cleans_change_file_operation_suffix() -> None:
    markdown = """
## 11. Implementation Contract

```yaml
implementation_contract:
  objective: "demo"
  repo_root: "demo-repo"
  change_files:
    - "\\"index.html\\" (Add)"
    - "src/app.ts (Modify)"
  api_changes: []
  state_changes: []
  test_commands: []
  acceptance_checks: []
  constraints: []
```
"""
    contract, _metadata, _warnings = parse_technical_design(markdown)
    assert contract["change_files"] == [
        {"path": "index.html", "operation": "Add", "description": ""},
        {"path": "src/app.ts", "operation": "Modify", "description": ""},
    ]
