from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from weatherwear.services.knowledge_admin import default_retrieval_cases, evaluate_retrieval_cases, load_payloads_from_path


def _load_cases(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return default_retrieval_cases()

    payload = load_payloads_from_path(path)
    if payload:
        return payload

    raw_payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw_payload, dict) and isinstance(raw_payload.get("cases"), list):
        return [item for item in raw_payload["cases"] if isinstance(item, dict)]
    raise ValueError("Evaluation cases file must be a JSON array, JSONL objects, or an object with a cases array.")


def _print_pretty(payload: dict[str, Any]) -> None:
    print(
        f"[summary] cases={payload['case_count']} checked={payload['checked_case_count']} "
        f"passed={payload['passed_case_count']} failed={payload['failed_case_count']}"
    )
    if payload["check_count"]:
        print(
            f"[checks] total={payload['check_count']} "
            f"passed={payload['passed_check_count']} failed={payload['failed_check_count']}"
        )

    for case in payload["cases"]:
        status = "PASS" if case["passed"] else ("FAIL" if case["passed"] is False else "INFO")
        print(f"[{status}] {case['name']} mode={case['retrieval_mode']} vector={case['vector_leg_status']}")
        print(f"  top hits: {', '.join(case['top_hit_ids']) or '(none)'}")
        if case["vector_leg_skipped_reason"]:
            print(f"  vector note: {case['vector_leg_skipped_reason']}")
        for check in case["checks"]:
            marker = "ok" if check["ok"] else "x"
            print(f"  [{marker}] {check['name']} expected={check['expected']} actual={check['actual']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline retrieval evaluation cases for WeatherWear fashion knowledge.")
    parser.add_argument("--cases", help="Load evaluation cases from a JSON / JSONL file.")
    parser.add_argument("--output", help="Write JSON result to a file.")
    parser.add_argument("--pretty", action="store_true", help="Print a human-friendly summary instead of raw JSON.")
    parser.add_argument("--fail-on-check", action="store_true", help="Return a non-zero exit code when any expectation check fails.")
    args = parser.parse_args()

    payload = evaluate_retrieval_cases(_load_cases(args.cases))

    if args.output:
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.pretty:
        _print_pretty(payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.fail_on_check and payload["failed_check_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
