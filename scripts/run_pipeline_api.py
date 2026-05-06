from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


def _post(url: str, obj: dict, *, timeout: float) -> dict:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str, *, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--repo-path", required=True)
    p.add_argument("--requirement-file", required=True)
    p.add_argument("--provider", default="deepseek")
    p.add_argument("--name", default="sc04_r0_fix_codegen")
    p.add_argument(
        "--test-stage-local-only",
        action="store_true",
        help="Force test stage to run with provider=local (skips E2E and marks succeeded).",
    )
    p.add_argument("--poll-seconds", type=int, default=240)
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    repo = str(Path(args.repo_path))
    requirement = Path(args.requirement_file).read_text(encoding="utf-8")

    stage_overrides: dict = {}
    if args.test_stage_local_only:
        stage_overrides["test"] = {"provider": "local", "local_only": True, "use_real_llm": False}

    pipeline = _post(
        f"{base}/api/pipelines",
        {
            "name": args.name,
            "provider": args.provider,
            "requirement": requirement,
            "repo_path": repo,
            "stage_overrides": stage_overrides,
        },
        timeout=30,
    )
    pid = pipeline["id"]
    run = _post(f"{base}/api/pipelines/{pid}/start", {"repo_path": repo}, timeout=30)
    rid = run["id"]
    print(f"pipelineId={pid}")
    print(f"runId={rid}")

    approved: set[str] = set()
    deadline = time.time() + max(5, int(args.poll_seconds))
    tick = 0
    while time.time() < deadline:
        tick += 1
        r = _get(f"{base}/api/pipelines/{pid}/runs/{rid}", timeout=30)
        st = r.get("status")
        cur = r.get("current_stage_id")
        nxt = r.get("next_stage_id")
        fail = r.get("failed_stage_id")
        print(f"t={tick} status={st} current={cur} next={nxt} failed={fail}")

        if st == "pending_approval" and cur in {"requirements", "solution", "review"} and cur not in approved:
            _post(
                f"{base}/api/pipelines/{pid}/stages/{cur}/approve",
                {"reviewer": "api", "comment": "ok", "continue_pipeline": True},
                timeout=30,
            )
            approved.add(cur)
            print(f"approved_{cur}")

        if st in {"failed", "succeeded", "terminated", "cancelled", "rejected"}:
            break

        time.sleep(1)


if __name__ == "__main__":
    main()

