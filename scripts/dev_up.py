from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"
RUNTIME_ROOT = ROOT / ".runtime"
LOG_ROOT = RUNTIME_ROOT / "logs"
STATE_ROOT = RUNTIME_ROOT / "state"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
API_PID_FILE = RUNTIME_ROOT / "api.pid"
WEB_PID_FILE = RUNTIME_ROOT / "web.pid"
PORTS_FILE = RUNTIME_ROOT / "ports.json"
APP_EVENTS = LOG_ROOT / "app.events.jsonl"


def resolve_esbuild_binary() -> str:
    if os.name != "nt":
        return ""
    candidates = [
        FRONTEND_ROOT / "node_modules" / "@esbuild" / "win32-x64" / "esbuild.exe",
        FRONTEND_ROOT / "node_modules" / "@esbuild" / "win32-ia32" / "esbuild.exe",
        FRONTEND_ROOT / "node_modules" / "@esbuild" / "win32-arm64" / "esbuild.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start WeatherWear locally with a cross-platform launcher.")
    parser.add_argument("--api-port", type=int, default=8000, help="Preferred API port. Default: 8000")
    parser.add_argument("--web-port", type=int, default=5173, help="Preferred frontend port. Default: 5173")
    parser.add_argument("--timeout", type=int, default=60, help="Service startup timeout in seconds. Default: 60")
    parser.add_argument("--skip-npm-install", action="store_true", help="Skip npm install even if node_modules is missing.")
    parser.add_argument("--open-browser", action="store_true", help="Open the frontend URL after startup.")
    return parser.parse_args()


def ensure_runtime_dirs() -> None:
    for path in (RUNTIME_ROOT, LOG_ROOT, STATE_ROOT):
        path.mkdir(parents=True, exist_ok=True)


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


def write_env_map(path: Path, values: dict[str, str]) -> None:
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    rendered: list[str] = []
    for raw_line in existing_lines:
        if "=" in raw_line and not raw_line.lstrip().startswith("#"):
            key = raw_line.split("=", 1)[0].strip()
            if key in remaining:
                rendered.append(f"{key}={remaining.pop(key)}")
                continue
        rendered.append(raw_line)
    for key, value in remaining.items():
        rendered.append(f"{key}={value}")
    path.write_text("\n".join(rendered).rstrip() + "\n", encoding="utf-8")


def ensure_env_file() -> dict[str, str]:
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            ENV_FILE.write_text("", encoding="utf-8")
    values = read_env_map(ENV_FILE)
    changed = False
    if not values.get("WEATHERWEAR_DEV_PIN", "").strip():
        values["WEATHERWEAR_DEV_PIN"] = "".join(str(os.urandom(1)[0] % 10) for _ in range(6))
        changed = True
    if not values.get("WEATHERWEAR_SESSION_SECRET", "").strip():
        values["WEATHERWEAR_SESSION_SECRET"] = os.urandom(24).hex()
        changed = True
    if changed:
        write_env_map(ENV_FILE, values)
    return values


def detect_python_dependencies() -> None:
    missing: list[str] = []
    for module_name in ("fastapi", "pydantic", "requests", "dotenv"):
        try:
            __import__(module_name)
        except Exception:
            missing.append(module_name)
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            f"Missing Python dependencies: {joined}\n"
            f"Please install them first, e.g.:\n"
            f"  py -3 -m venv .venv\n"
            f"  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )


def detect_npm() -> str:
    for candidate in ("npm.cmd", "npm"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SystemExit("npm was not found in PATH. Please install Node.js 18+ first.")


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def find_free_port(preferred: int, *, upper_bound: int) -> int:
    for port in range(preferred, upper_bound + 1):
        if not is_port_open(port):
            return port
    raise RuntimeError(f"Could not find a free port in range {preferred}-{upper_bound}.")


def read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
        return int(value)
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


def kill_process_tree(pid: int, *, name: str) -> None:
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
        kill_process_tree(pid, name=name)
    pid_file.unlink(missing_ok=True)


def ensure_frontend_dependencies(npm_executable: str, *, skip_install: bool) -> None:
    node_modules = FRONTEND_ROOT / "node_modules"
    if node_modules.exists() or skip_install:
        return
    env = dict(os.environ)
    env["npm_config_cache"] = str(FRONTEND_ROOT / ".npm-cache")
    completed = subprocess.run(
        [npm_executable, "install"],
        cwd=str(FRONTEND_ROOT),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise SystemExit("npm install failed. Please run it manually inside frontend/.")


def start_process(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    pid_file: Path,
    env: dict[str, str],
) -> subprocess.Popen[str]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = 0
    kwargs: dict[str, object] = {
        "cwd": str(cwd),
        "env": env,
        "stdout": stdout_path.open("w", encoding="utf-8"),
        "stderr": stderr_path.open("w", encoding="utf-8"),
        "text": True,
    }
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creationflags
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    pid_file.write_text(str(process.pid), encoding="utf-8")
    return process


def wait_for_port(port: int, *, name: str, timeout: int, pid_file: Path, stderr_path: Path) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(port):
            return
        pid = read_pid(pid_file)
        if pid is None or not process_alive(pid):
            error_tail = ""
            if stderr_path.exists():
                error_tail = "\n".join(stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()[-20:])
            raise SystemExit(f"{name} exited before becoming ready on port {port}.\n{error_tail}".rstrip())
        time.sleep(0.4)
    raise SystemExit(f"{name} did not become ready on port {port} within {timeout} seconds.")


def runtime_mode(env_values: dict[str, str]) -> str:
    has_weather = bool(env_values.get("OPENWEATHER_API_KEY", "").strip())
    has_llm = all(
        env_values.get(key, "").strip()
        for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_ID")
    )
    if not has_weather and not has_llm:
        return "demo / degraded（未配置 OpenWeather，LLM 也可能走兜底）"
    if not has_weather:
        return "mixed / degraded（LLM 可用，天气走 demo 或 degraded）"
    if not has_llm:
        return "partial / fallback（天气在线，LLM 或 embedding 可能走兜底）"
    return "full（在线天气 + 模型能力已配置）"


def write_ports_manifest(*, api_port: int, web_port: int) -> None:
    payload = {
        "api": {"port": api_port, "url": f"http://127.0.0.1:{api_port}"},
        "web": {"port": web_port, "url": f"http://127.0.0.1:{web_port}"},
    }
    PORTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_runtime_event(event_type: str, message: str, payload: dict[str, object]) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": event_type,
        "level": "info",
        "message": message,
        "payload": payload,
    }
    with APP_EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    ensure_runtime_dirs()
    env_values = ensure_env_file()
    detect_python_dependencies()
    npm_executable = detect_npm()
    ensure_frontend_dependencies(npm_executable, skip_install=args.skip_npm_install)

    stop_managed_process(API_PID_FILE, name="api")
    stop_managed_process(WEB_PID_FILE, name="web")

    api_port = find_free_port(args.api_port, upper_bound=max(args.api_port + 50, 8050))
    web_port = find_free_port(args.web_port, upper_bound=max(args.web_port + 50, 5205))

    api_env = dict(os.environ)
    api_env["WEATHERWEAR_API_PORT"] = str(api_port)

    web_env = dict(os.environ)
    web_env["WEATHERWEAR_API_PORT"] = str(api_port)
    web_env["WEATHERWEAR_API_URL"] = f"http://127.0.0.1:{api_port}"
    web_env["WEATHERWEAR_OPEN_BROWSER"] = "1" if args.open_browser else "0"
    web_env["npm_config_cache"] = str(FRONTEND_ROOT / ".npm-cache")
    esbuild_binary = resolve_esbuild_binary()
    if esbuild_binary:
        web_env["ESBUILD_BINARY_PATH"] = esbuild_binary

    api_process = start_process(
        command=[sys.executable, "-m", "weatherwear.api.server"],
        cwd=ROOT,
        stdout_path=LOG_ROOT / "api.out.log",
        stderr_path=LOG_ROOT / "api.err.log",
        pid_file=API_PID_FILE,
        env=api_env,
    )
    wait_for_port(
        api_port,
        name="WeatherWear API",
        timeout=args.timeout,
        pid_file=API_PID_FILE,
        stderr_path=LOG_ROOT / "api.err.log",
    )

    web_process = start_process(
        command=[npm_executable, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(web_port), "--strictPort"],
        cwd=FRONTEND_ROOT,
        stdout_path=LOG_ROOT / "web.out.log",
        stderr_path=LOG_ROOT / "web.err.log",
        pid_file=WEB_PID_FILE,
        env=web_env,
    )
    try:
        wait_for_port(
            web_port,
            name="WeatherWear frontend",
            timeout=args.timeout,
            pid_file=WEB_PID_FILE,
            stderr_path=LOG_ROOT / "web.err.log",
        )
    except Exception:
        if process_alive(api_process.pid):
            stop_managed_process(API_PID_FILE, name="api")
        raise

    write_ports_manifest(api_port=api_port, web_port=web_port)
    append_runtime_event(
        "launcher.started",
        "WeatherWear started with Python launcher.",
        {
            "api_port": api_port,
            "web_port": web_port,
            "mode": runtime_mode(env_values),
        },
    )

    if args.open_browser:
        webbrowser.open(f"http://127.0.0.1:{web_port}", new=2)

    print("WeatherWear 已启动。")
    print(f"- 前端地址: http://127.0.0.1:{web_port}")
    print(f"- API 地址: http://127.0.0.1:{api_port}")
    print(f"- 运行模式: {runtime_mode(env_values)}")
    print(f"- 开发者 PIN: {env_values.get('WEATHERWEAR_DEV_PIN', '').strip() or '请查看 .env'}")
    print(f"- 停止命令: {sys.executable} scripts/dev_down.py")
    print(f"- 日志目录: {LOG_ROOT}")
    print(f"- PID 文件: {API_PID_FILE.name}, {WEB_PID_FILE.name}")
    _ = web_process
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
