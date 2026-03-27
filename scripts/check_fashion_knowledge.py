from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from weatherwear.services.knowledge_admin import summarize_knowledge_base, validate_knowledge_base
from weatherwear.services.fashion_knowledge import rebuild_vector_indexes


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WeatherWear fashion knowledge files and optionally rebuild indexes.")
    parser.add_argument("--locale", action="append", dest="locales", help="Only validate the given locale, can be used multiple times.")
    parser.add_argument("--rebuild-index", action="store_true", help="Also rebuild local vector cache / Chroma index metadata.")
    parser.add_argument("--force", action="store_true", help="Force rebuilding indexes by clearing cached metadata first.")
    args = parser.parse_args()

    locales = args.locales or None
    validation = validate_knowledge_base(locales)
    summary = summarize_knowledge_base(locales)
    payload: dict[str, object] = {
        "validation": validation,
        "summary": summary,
    }
    if args.rebuild_index:
        payload["rebuild"] = rebuild_vector_indexes(locales, force=args.force)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if validation.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
