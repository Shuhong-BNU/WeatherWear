from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from weatherwear.services import fashion_knowledge as knowledge
from weatherwear.services.knowledge_admin import (
    load_payloads_from_path,
    normalize_knowledge_payloads,
    validate_knowledge_payloads,
    write_payloads_to_jsonl,
)


def _resolve_locale(payloads: list[dict[str, object]], cli_locale: str | None) -> str:
    if cli_locale:
        return cli_locale

    locales = {str(item.get("locale", "") or "").strip() for item in payloads if isinstance(item, dict)}
    locales.discard("")
    if len(locales) == 1:
        return next(iter(locales))
    if not locales:
        raise ValueError("Input payloads do not contain locale; please pass --locale.")
    raise ValueError(f"Input payloads contain multiple locales: {sorted(locales)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize, validate, and optionally import WeatherWear fashion knowledge entries.")
    parser.add_argument("--input", required=True, help="Input knowledge file (.json or .jsonl).")
    parser.add_argument("--output", help="Output JSONL path. Defaults to the locale knowledge file.")
    parser.add_argument("--locale", help="Override locale for normalization and validation.")
    parser.add_argument("--append", action="store_true", help="Append to the output file after validating the merged result.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate and print the merged result summary.")
    args = parser.parse_args()

    incoming_payloads = load_payloads_from_path(args.input)
    locale = _resolve_locale(incoming_payloads, args.locale)
    normalized_incoming = normalize_knowledge_payloads(incoming_payloads, locale=locale)

    output_path = Path(args.output) if args.output else knowledge.knowledge_file_for_locale(locale)
    existing_payloads = load_payloads_from_path(output_path) if args.append and output_path.exists() else []
    merged_payloads = [*existing_payloads, *normalized_incoming] if args.append else normalized_incoming
    validation = validate_knowledge_payloads(merged_payloads, locale=locale)

    payload: dict[str, object] = {
        "ok": validation["ok"],
        "locale": locale,
        "input_path": str(Path(args.input).resolve()),
        "output_path": str(output_path.resolve()),
        "append": args.append,
        "validate_only": args.validate_only,
        "existing_count": len(existing_payloads),
        "incoming_count": len(incoming_payloads),
        "merged_count": len(merged_payloads),
        "normalized_incoming_count": sum(1 for raw, normalized in zip(incoming_payloads, normalized_incoming) if raw != normalized),
        "validation": validation,
    }

    if args.validate_only or not validation["ok"]:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if validation["ok"] else 1

    written = write_payloads_to_jsonl(output_path, merged_payloads)
    payload["written_count"] = written
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
