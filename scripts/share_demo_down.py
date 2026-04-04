from __future__ import annotations

import argparse
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
TUNNEL_PID_FILE = RUNTIME_ROOT / "tunnel.pid"
SHARE_INFO_FILE = RUNTIME_ROOT / "share-demo.json"
APP_EVENTS = LOG_ROOT / "app.events.jsonl"
DEV_DOWN_SCRIPT = ROOT / "scripts" / "dev_down.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stop the Cloudflare demo share tunnel for WeatherWear.")
    parser.add_argument("--stop-app", action="store_true", help="Also stop the local WeatherWear app after closing the tunnel.")
    return parser.parse_args()


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
    except SystemError:
        return False
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
    except ProcessLookupError:
        return


def stop_managed_process(pid_file: Path, *, name: str) -> None:
    pid = read_pid(pid_file)
    if pid is None:
        print(f"- {name}: 未发现运行中的进程")
        return
    if process_alive(pid):
        kill_process_tree(pid)
        print(f"- {name}: 已停止 ({pid})")
    else:
        print(f"- {name}: 进程已不存在 ({pid})")
    pid_file.unlink(missing_ok=True)


def append_runtime_event() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": "launcher.share_stopped",
        "level": "info",
        "message": "WeatherWear public share tunnel stopped.",
        "payload": {},
    }
    with APP_EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    print("正在停止 WeatherWear 公网分享 ...")
    stop_managed_process(TUNNEL_PID_FILE, name="cloudflared tunnel")
    SHARE_INFO_FILE.unlink(missing_ok=True)
    append_runtime_event()
    print(f"- 分享信息已移除: {SHARE_INFO_FILE}")
    if args.stop_app:
        print("- 同时停止本机 WeatherWear ...")
        completed = subprocess.run([sys.executable, str(DEV_DOWN_SCRIPT)], cwd=str(ROOT))
        return int(completed.returncode)
    print("公网分享已关闭，本机 WeatherWear 仍可继续使用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
