from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / ".runtime"
LOG_ROOT = RUNTIME_ROOT / "logs"
API_PID_FILE = RUNTIME_ROOT / "api.pid"
WEB_PID_FILE = RUNTIME_ROOT / "web.pid"
PORTS_FILE = RUNTIME_ROOT / "ports.json"
APP_EVENTS = LOG_ROOT / "app.events.jsonl"


def read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        path.unlink(missing_ok=True)
        return None


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return
    try:
        os.killpg(pid, signal.SIGTERM)
        time.sleep(0.5)
    except ProcessLookupError:
        return


def stop_managed_process(pid_file: Path, *, name: str) -> None:
    pid = read_pid(pid_file)
    if pid is None:
        print(f"- {name}: 未发现 PID 文件")
        return
    if process_alive(pid):
        kill_process_tree(pid)
        print(f"- {name}: 已停止进程树 ({pid})")
    else:
        print(f"- {name}: 进程已不存在 ({pid})")
    pid_file.unlink(missing_ok=True)


def append_runtime_event() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": "launcher.stopped",
        "level": "info",
        "message": "WeatherWear stopped by Python launcher.",
        "payload": {},
    }
    with APP_EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    print("正在停止 WeatherWear ...")
    stop_managed_process(API_PID_FILE, name="api")
    stop_managed_process(WEB_PID_FILE, name="web")
    PORTS_FILE.unlink(missing_ok=True)
    append_runtime_event()
    print(f"- 端口清单已移除: {PORTS_FILE}")
    print("WeatherWear 已停止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
