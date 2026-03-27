from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"
DEFAULT_REPORT_PATH = ROOT / ".runtime" / "validation-report.json"
STEP_LABELS = {
    "core_python_tests": "Core Python tests",
    "knowledge_validation": "Knowledge validation",
    "retrieval_evaluation": "Retrieval evaluation",
    "frontend_build": "Frontend build",
}
FAILURE_HINTS = {
    "core_python_tests": "Check failing backend unit tests first; this usually points to a regression in the main query flow.",
    "knowledge_validation": "Run scripts/check_fashion_knowledge.py directly to inspect schema or locale alignment issues.",
    "retrieval_evaluation": "Review retrieval expectations and fallback behavior; a knowledge edit may have shifted the top hits.",
    "frontend_build": "Check TypeScript errors, Vite build output, or local npm cache permissions.",
}
CORE_TEST_MODULES = [
    "tests.test_observability",
    "tests.test_fashion_knowledge",
    "tests.test_knowledge_admin",
    "tests.test_llm_support",
    "tests.test_fashion_agent",
    "tests.test_coordinator",
    "tests.test_api_server",
]


def _npm_executable() -> str:
    for candidate in ("npm.cmd", "npm"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("npm executable not found in PATH.")


def _step(name: str, command: list[str], cwd: Path) -> dict[str, Any]:
    env = None
    if cwd == FRONTEND_ROOT:
        env = dict(os.environ)
        env["npm_config_cache"] = str(FRONTEND_ROOT / ".npm-cache")
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "display_command": " ".join(_display_token(item) for item in command),
        "display_cwd": _display_path(cwd),
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _print_step_result(result: dict[str, Any], *, verbose: bool = False) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    label = STEP_LABELS.get(result["name"], result["name"])
    print(f"[{status}] {label}")
    print(f"  cwd: {result.get('display_cwd', result['cwd'])}")
    print(f"  cmd: {result.get('display_command', ' '.join(result['command']))}")
    if (verbose or not result["ok"]) and result["stdout"].strip():
        print("  --- stdout ---")
        _write_console_block(result["stdout"])
    if (verbose or not result["ok"]) and result["stderr"].strip():
        print("  --- stderr ---")
        _write_console_block(result["stderr"])


def _write_console_block(text: str) -> None:
    output = text.rstrip() + "\n"
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        print(output, end="")
        return
    buffer.write(output.encode(encoding, errors="replace"))


def _display_path(value: str | Path) -> str:
    path = Path(value) if not isinstance(value, Path) else value
    try:
        resolved = path.resolve()
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except Exception:
        text = str(path)
        return text.replace("\\", "/")


def _display_token(value: str) -> str:
    if not value:
        return value
    if any(sep in value for sep in ("\\", "/")):
        return _display_path(value)
    return value


def build_validation_summary(steps: list[dict[str, Any]], *, report_path: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for step in steps:
        items.append(
            {
                "name": step["name"],
                "label": STEP_LABELS.get(step["name"], step["name"]),
                "ok": step["ok"],
                "status": "PASS" if step["ok"] else "FAIL",
                "hint": "" if step["ok"] else FAILURE_HINTS.get(step["name"], ""),
            }
        )

    passed_count = sum(1 for item in items if item["ok"])
    failed_items = [item for item in items if not item["ok"]]
    headline = (
        f"Validation passed ({passed_count}/{len(items)} steps)"
        if not failed_items
        else f"Validation failed ({len(failed_items)} of {len(items)} steps)"
    )
    return {
        "headline": headline,
        "report_path": _display_path(report_path),
        "items": items,
        "next_action": failed_items[0]["hint"] if failed_items else "All validation steps passed.",
    }


def _print_human_summary(summary: dict[str, Any]) -> None:
    print(f"[summary] {summary['headline']}")
    for item in summary["items"]:
        print(f"  {item['status']} {item['label']}")
        if item["hint"]:
            print(f"    note: {item['hint']}")
    print(f"  report: {summary['report_path']}")
    if summary["next_action"]:
        print(f"  next: {summary['next_action']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single validation pass for WeatherWear.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Write the validation summary to this JSON path.")
    parser.add_argument("--skip-frontend-build", action="store_true", help="Skip the frontend production build step.")
    parser.add_argument("--verbose", action="store_true", help="Print stdout / stderr for all steps, not only failed ones.")
    args = parser.parse_args()

    steps: list[dict[str, Any]] = [
        _step(
            "core_python_tests",
            [sys.executable, "-m", "unittest", *CORE_TEST_MODULES, "-v"],
            ROOT,
        ),
        _step(
            "knowledge_validation",
            [sys.executable, "scripts/check_fashion_knowledge.py"],
            ROOT,
        ),
        _step(
            "retrieval_evaluation",
            [
                sys.executable,
                "scripts/evaluate_retrieval.py",
                "--cases",
                "weatherwear/resources/evaluation/retrieval_cases.sample.json",
                "--fail-on-check",
            ],
            ROOT,
        ),
    ]

    if not args.skip_frontend_build:
        steps.append(
            _step(
                "frontend_build",
                [_npm_executable(), "run", "build"],
                FRONTEND_ROOT,
            )
        )

    overall_ok = all(step["ok"] for step in steps)
    payload = {
        "ok": overall_ok,
        "step_count": len(steps),
        "passed_count": sum(1 for step in steps if step["ok"]),
        "failed_count": sum(1 for step in steps if not step["ok"]),
        "steps": steps,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload["summary"] = build_validation_summary(steps, report_path=report_path)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_human_summary(payload["summary"])
    for step in steps:
        _print_step_result(step, verbose=args.verbose)

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
