from __future__ import annotations

import argparse
import json
from pathlib import Path

from triage import run_triage


def main() -> None:
    p = argparse.ArgumentParser(
        description="Triage CodeTest output: classify failure owner and emit feedback markdown."
    )
    p.add_argument(
        "--code-test-result",
        type=str,
        help="Path to code_test_result.json",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for triage_result.json + feedback_*.md (default: alongside code_test_result.json)",
    )
    args = p.parse_args()
    if not args.code_test_result:
        raise SystemExit("Provide --code-test-result path/to/code_test_result.json")

    result_path = Path(args.code_test_result)
    if not result_path.is_file():
        raise SystemExit(f"Not found: {result_path}")

    out = Path(args.output_dir).resolve() if args.output_dir else None
    triage = run_triage(result_path=result_path, output_dir=out)
    print(json.dumps(triage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
