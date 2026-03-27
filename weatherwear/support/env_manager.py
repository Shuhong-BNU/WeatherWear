from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values


_PLAIN_ENV_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_./:@-]+$")


class EnvManager:
    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self._ensure_env_file_exists()

    def _ensure_env_file_exists(self) -> None:
        if not self.env_file.exists():
            self.env_file.touch()

    def read_env(self) -> dict[str, str]:
        if not self.env_file.exists():
            return {}

        loaded = dotenv_values(self.env_file, encoding="utf-8")
        return {
            key: value
            for key, value in loaded.items()
            if key and value is not None
        }

    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        runtime_value = os.getenv(key)
        if runtime_value is not None:
            return runtime_value
        return self.read_env().get(key, default)

    def apply_changes(
        self,
        *,
        updates: dict[str, str],
        deletions: list[str] | None = None,
    ) -> bool:
        try:
            env_vars = self.read_env()
            env_vars.update(updates)
            for key in deletions or []:
                env_vars.pop(key, None)
            return self._write_env(env_vars)
        except Exception as exc:
            print(f"更新环境变量失败: {exc}")
            return False

    def _write_env(self, env_vars: dict[str, str]) -> bool:
        try:
            with open(self.env_file, "w", encoding="utf-8") as handle:
                for key, value in env_vars.items():
                    handle.write(f"{key}={self._serialize_value(value)}\n")
            return True
        except Exception as exc:
            print(f"写入 .env 文件失败: {exc}")
            return False

    def _serialize_value(self, value: str) -> str:
        text = str(value)
        if text == "":
            return ""
        if _PLAIN_ENV_VALUE_PATTERN.fullmatch(text):
            return text
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'


env_manager = EnvManager()
