from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / ".runtime"
LOG_ROOT = RUNTIME_ROOT / "logs"
TOOLS_ROOT = RUNTIME_ROOT / "tools"
STATE_ROOT = RUNTIME_ROOT / "state"
PORTS_FILE = RUNTIME_ROOT / "ports.json"
TUNNEL_PID_FILE = RUNTIME_ROOT / "tunnel.pid"
SHARE_INFO_FILE = RUNTIME_ROOT / "share-demo.json"
APP_EVENTS = LOG_ROOT / "app.events.jsonl"
TUNNEL_LOG_FILE = LOG_ROOT / "tunnel.log"
DEV_UP_SCRIPT = ROOT / "scripts" / "dev_up.py"
API_PID_FILE = RUNTIME_ROOT / "api.pid"
FRONTEND_DIST_INDEX = ROOT / "frontend" / "dist" / "index.html"
PUBLIC_URL_PATTERN = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expose the local WeatherWear demo through Cloudflare Quick Tunnel.")
    parser.add_argument("--api-port", type=int, default=8000, help="Preferred API port when starting WeatherWear.")
    parser.add_argument("--web-port", type=int, default=5173, help="Preferred frontend port when starting WeatherWear.")
    parser.add_argument("--timeout", type=int, default=90, help="Startup timeout in seconds. Default: 90")
    parser.add_argument("--skip-npm-install", action="store_true", help="Skip npm install when dev_up starts the app.")
    parser.add_argument("--open-browser", action="store_true", help="Open the local WeatherWear page after startup.")
    parser.add_argument(
        "--cloudflared-path",
        default="",
        help="Optional explicit path to cloudflared. Defaults to looking up cloudflared in PATH.",
    )
    return parser.parse_args()


def ensure_runtime_dirs() -> None:
    for path in (RUNTIME_ROOT, LOG_ROOT, TOOLS_ROOT, STATE_ROOT):
        path.mkdir(parents=True, exist_ok=True)


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
        return
    if process_alive(pid):
        kill_process_tree(pid)
        print(f"- 已停止 {name} 进程 ({pid})")
    pid_file.unlink(missing_ok=True)


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def read_ports_manifest() -> dict[str, object] | None:
    if not PORTS_FILE.exists():
        return None
    try:
        payload = json.loads(PORTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    api = payload.get("api") if isinstance(payload, dict) else None
    web = payload.get("web") if isinstance(payload, dict) else None
    if not isinstance(api, dict) or not isinstance(web, dict):
        return None
    api_port = int(api.get("port") or 0)
    web_port = int(web.get("port") or 0)
    if api_port <= 0:
        return None
    if not is_port_open(api_port):
        return None
    if web_port > 0 and is_port_open(web_port):
        return payload
    if FRONTEND_DIST_INDEX.exists():
        payload["web"] = {
            "port": api_port,
            "url": f"http://127.0.0.1:{api_port}",
            "source": "bundled",
        }
        return payload
    return payload


def detect_cloudflared(explicit_path: str) -> str:
    if explicit_path:
        candidate = Path(explicit_path).expanduser()
        if candidate.exists():
            return str(candidate)
        raise SystemExit(f"找不到 cloudflared：{candidate}")
    bundled_candidates = [
        TOOLS_ROOT / "cloudflared.exe",
        TOOLS_ROOT / "cloudflared",
    ]
    for candidate in bundled_candidates:
        if candidate.exists():
            return str(candidate)
    for executable in ("cloudflared.exe", "cloudflared"):
        resolved = shutil.which(executable)
        if resolved:
            return resolved
    raise SystemExit(
        "未检测到 cloudflared。请先安装 Cloudflare Tunnel 客户端，再重新运行本脚本。\n"
        "安装后确保 `cloudflared` 命令在 PATH 中可用。"
    )


def ensure_weatherwear_running(args: argparse.Namespace) -> dict[str, object]:
    manifest = read_ports_manifest()
    if manifest:
        return manifest
    if FRONTEND_DIST_INDEX.exists():
        api_port = args.api_port
        if not is_port_open(api_port):
            api_env = dict(os.environ)
            api_env["WEATHERWEAR_API_PORT"] = str(api_port)
            kwargs: dict[str, object] = {
                "cwd": str(ROOT),
                "stdout": (LOG_ROOT / "api.out.log").open("w", encoding="utf-8"),
                "stderr": (LOG_ROOT / "api.err.log").open("w", encoding="utf-8"),
                "text": True,
                "env": api_env,
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                kwargs["start_new_session"] = True
            process = subprocess.Popen([sys.executable, "-m", "weatherwear.api.server"], **kwargs)
            API_PID_FILE.write_text(str(process.pid), encoding="utf-8")
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                if is_port_open(api_port):
                    break
                if not process_alive(process.pid):
                    raise SystemExit("WeatherWear API 启动失败，无法继续创建公网分享链接。")
                time.sleep(0.4)
            else:
                raise SystemExit("WeatherWear API 在超时时间内没有就绪。")
        manifest = {
            "api": {"port": api_port, "url": f"http://127.0.0.1:{api_port}"},
            "web": {"port": api_port, "url": f"http://127.0.0.1:{api_port}", "source": "bundled"},
        }
        PORTS_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
    command = [
        sys.executable,
        str(DEV_UP_SCRIPT),
        "--api-port",
        str(args.api_port),
        "--web-port",
        str(args.web_port),
        "--timeout",
        str(args.timeout),
    ]
    if args.skip_npm_install:
        command.append("--skip-npm-install")
    if args.open_browser:
        command.append("--open-browser")
    completed = subprocess.run(command, cwd=str(ROOT))
    if completed.returncode != 0:
        raise SystemExit("WeatherWear 启动失败，无法继续创建公网分享链接。")
    manifest = read_ports_manifest()
    if not manifest:
        raise SystemExit("WeatherWear 已尝试启动，但未能读取有效的端口清单。")
    return manifest


def extract_public_url(log_text: str) -> str | None:
    matches = PUBLIC_URL_PATTERN.findall(log_text)
    if not matches:
        return None
    return matches[-1]


def launch_tunnel(cloudflared_path: str, local_url: str, timeout: int) -> str:
    stop_managed_process(TUNNEL_PID_FILE, name="cloudflared tunnel")
    SHARE_INFO_FILE.unlink(missing_ok=True)
    TUNNEL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    TUNNEL_LOG_FILE.write_text("", encoding="utf-8")
    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            raise SystemExit("未找到 powershell.exe，无法在 Windows 上启动 cloudflared。")
        escaped_exe = cloudflared_path.replace("'", "''")
        escaped_log = str(TUNNEL_LOG_FILE.resolve()).replace("'", "''")
        escaped_url = local_url.replace("'", "''")
        ps_command = (
            f"$exe = '{escaped_exe}'; "
            f"$log = '{escaped_log}'; "
            f"$proc = Start-Process -FilePath $exe "
            f"-ArgumentList @('tunnel','--loglevel','debug','--logfile',$log,'--url','{escaped_url}') "
            "-PassThru -WindowStyle Hidden; "
            "Write-Output $proc.Id"
        )
        completed = subprocess.run(
            [powershell, "-NoProfile", "-Command", ps_command],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise SystemExit(f"Cloudflare Tunnel 启动失败。\n{completed.stderr}".rstrip())
        pid_text = (completed.stdout or "").strip().splitlines()
        if not pid_text or not pid_text[-1].strip().isdigit():
            raise SystemExit("Cloudflare Tunnel 启动失败，未能获取进程 PID。")
        tunnel_pid = int(pid_text[-1].strip())
    else:
        kwargs: dict[str, object] = {
            "cwd": str(ROOT),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "text": True,
            "start_new_session": True,
        }
        process = subprocess.Popen(
            [
                cloudflared_path,
                "tunnel",
                "--loglevel",
                "debug",
                "--logfile",
                str(TUNNEL_LOG_FILE.resolve()),
                "--url",
                local_url,
            ],
            **kwargs,
        )
        tunnel_pid = process.pid
    TUNNEL_PID_FILE.write_text(str(tunnel_pid), encoding="utf-8")

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not process_alive(tunnel_pid):
            log_text = TUNNEL_LOG_FILE.read_text(encoding="utf-8", errors="replace") if TUNNEL_LOG_FILE.exists() else ""
            raise SystemExit(f"Cloudflare Tunnel 启动失败。\n{log_text}".rstrip())
        log_text = TUNNEL_LOG_FILE.read_text(encoding="utf-8", errors="replace") if TUNNEL_LOG_FILE.exists() else ""
        public_url = extract_public_url(log_text)
        if public_url:
            return public_url
        time.sleep(0.5)
    stop_managed_process(TUNNEL_PID_FILE, name="cloudflared tunnel")
    raise SystemExit("Cloudflare Tunnel 在超时时间内没有返回公网链接。")


def read_env_map(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value
    return values


def runtime_mode() -> str:
    env_values = read_env_map(ROOT / ".env")
    has_weather = bool(env_values.get("OPENWEATHER_API_KEY", "").strip())
    has_llm = all(env_values.get(key, "").strip() for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID"))
    if not has_weather and not has_llm:
        return "demo / degraded（未配置 OpenWeather，LLM 也可能走兜底）"
    if not has_weather:
        return "mixed / degraded（LLM 可用，天气走 demo 或 degraded）"
    if not has_llm:
        return "partial / fallback（天气在线，LLM 或 embedding 可能走兜底）"
    return "full（在线天气 + 模型能力已配置）"


def write_share_info(*, local_web_url: str, local_api_url: str, public_url: str, web_port: int, api_port: int) -> None:
    payload = {
        "public_url": public_url,
        "local_web_url": local_web_url,
        "local_api_url": local_api_url,
        "web_port": web_port,
        "api_port": api_port,
        "runtime_mode": runtime_mode(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    SHARE_INFO_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_runtime_event(public_url: str, local_web_url: str, local_api_url: str) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": "launcher.shared",
        "level": "info",
        "message": "WeatherWear public share tunnel started.",
        "payload": {
            "public_url": public_url,
            "local_web_url": local_web_url,
            "local_api_url": local_api_url,
        },
    }
    with APP_EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    ensure_runtime_dirs()
    cloudflared_path = detect_cloudflared(args.cloudflared_path)
    manifest = ensure_weatherwear_running(args)

    api = manifest["api"]
    web = manifest["web"]
    assert isinstance(api, dict)
    assert isinstance(web, dict)
    api_port = int(api["port"])
    web_port = int(web["port"])
    local_api_url = f"http://127.0.0.1:{api_port}"
    local_web_url = f"http://127.0.0.1:{web_port}"

    print("正在启动 Cloudflare Quick Tunnel ...")
    public_url = launch_tunnel(cloudflared_path, local_web_url, args.timeout)
    write_share_info(
        local_web_url=local_web_url,
        local_api_url=local_api_url,
        public_url=public_url,
        web_port=web_port,
        api_port=api_port,
    )
    append_runtime_event(public_url, local_web_url, local_api_url)

    print("WeatherWear 共享链接已就绪。")
    print(f"- 本机前端: {local_web_url}")
    print(f"- 本机 API:  {local_api_url}")
    print(f"- 公网链接: {public_url}")
    print(f"- 当前模式: {runtime_mode()}")
    print(f"- Tunnel PID: {TUNNEL_PID_FILE}")
    print(f"- 分享信息: {SHARE_INFO_FILE}")
    print(f"- Tunnel 日志: {TUNNEL_LOG_FILE}")
    print(f"- 停止分享: {sys.executable} scripts/share_demo_down.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
