from __future__ import annotations

import json
from pathlib import Path

from weatherwear.support.common_utils import normalize_text


DATA_DIR = Path(__file__).resolve().parent.parent / "resources" / "geo"


def _load_json_file(filename: str) -> dict:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


RAW_ALIAS_MAP = _load_json_file("city_aliases.json")
COUNTRY_NAME_BY_CODE = _load_json_file("country_names.json")

COMMON_CITY_ALIASES = {normalize_text(key): value for key, value in RAW_ALIAS_MAP.items()}
