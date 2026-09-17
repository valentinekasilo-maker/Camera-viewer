"""
ANDRO-Vision Launcher
=====================
One-click launcher for the ANDRO-Vision AI Camera System.
Handles environment checks, dependency installation, service startup,
health verification, and automatic browser launch.

Usage:
    python launcher.py          # normal launch
    python launcher.py --dev    # force dev mode (default)
    python launcher.py --log    # verbose logging to console
"""

import ctypes
import json
import logging
import msvcrt
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration — derived from project inspection
# ---------------------------------------------------------------------------

APP_NAME = "ANDRO-Vision"
APP_VERSION = "1.0"

# Ports used by the project (confirmed from run_server.py and vite.config.ts)
BACKEND_PORT = 5000
FRONTEND_PORT = 5173
GO2RTC_PORT = 1984

BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/version"
FRONTEND_HEALTH_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
BROWSER_URL = f"http://127.0.0.1:{FRONTEND_PORT}"

# Timeouts (seconds)
BACKEND_START_TIMEOUT = 60
FRONTEND_START_TIMEOUT = 60
HEALTH_POLL_INTERVAL = 1.5

# Minimum required runtime versions
MIN_PYTHON_MAJOR = 3
MIN_PYTHON_MINOR = 11
MIN_NODE_MAJOR = 18

# Single-instance lock file
LOCK_FILE = Path(tempfile.gettempdir()) / "andro_vision_launcher.lock"


# ---------------------------------------------------------------------------
# Resolve project root (works both from script and from PyInstaller EXE)
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the project root directory regardless of launch location."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller EXE — CameraApp.exe lives directly in the project root
        return Path(sys.executable).parent
    else:
        # Running as a plain Python script inside installer/
        return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
LOGS_DIR = PROJECT_ROOT / "logs"
WEB_DIR = PROJECT_ROOT / "web"
BACKEND_ENTRY = PROJECT_ROOT / "run_server.py"


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool = False) -> logging.Logger:
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / "launcher.log"

    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(level=logging.DEBUG, format=fmt, datefmt=datefmt, handlers=handlers)
    return logging.getLogger("launcher")


logger: logging.Logger | None = None


# ---------------------------------------------------------------------------
# Console output — ANSI colors for Windows 10+
# ---------------------------------------------------------------------------

RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _enable_ansi() -> None:
    """Enable ANSI escape codes in Windows console."""
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def _print_header() -> None:
    _enable_ansi()
    print()
    print(f"{BOLD}{CYAN}{'=' * 54}{RESET}")
    print(f"{BOLD}{CYAN}  {APP_NAME} — AI Camera System{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 54}{RESET}")
    print(f"{DIM}  Project: {PROJECT_ROOT}{RESET}")
    print(f"{DIM}  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 54}{RESET}")
    print()


def step_ok(msg: str) -> None:
    print(f"  {GREEN}[✓]{RESET} {msg}")
    if logger:
        logger.info("OK: %s", msg)


def step_info(msg: str) -> None:
    print(f"  {CYAN}[→]{RESET} {msg}")
    if logger:
        logger.info("%s", msg)


def step_warn(msg: str) -> None:
    print(f"  {YELLOW}[!]{RESET} {msg}")
    if logger:
        logger.warning("%s", msg)


def step_fail(msg: str) -> None:
    print(f"  {RED}[✗]{RESET} {msg}")
    if logger:
        logger.error("%s", msg)


def fatal(msg: str, detail: str = "", hint: str = "") -> None:
    """Print a fatal error and exit."""
    print()
    print(f"{RED}{BOLD}  FATAL ERROR{RESET}")
    print(f"  {RED}{msg}{RESET}")
    if detail:
        print(f"  {DIM}{detail}{RESET}")
    if hint:
        print()
        print(f"  {YELLOW}What to do:{RESET}")
        print(f"  {hint}")
    print()
    if logger:
        logger.critical("FATAL: %s | %s | %s", msg, detail, hint)
    input("  Press Enter to close...")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------

_lock_handle = None  # Windows file handle for single-instance lock


def acquire_single_instance_lock() -> bool:
    """
    Attempt to acquire a per-process lock file.
    Returns True if this is the only instance, False otherwise.
    """
    global _lock_handle
    try:
        lock_fd = open(LOCK_FILE, "w", encoding="utf-8")
        try:
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            lock_fd.write(str(os.getpid()))
            lock_fd.flush()
            _lock_handle = lock_fd
            return True
        except OSError:
            lock_fd.close()
            return False
    except Exception:
        # If locking fails for any reason, allow startup
        return True


def release_single_instance_lock() -> None:
    global _lock_handle
    if _lock_handle:
        try:
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            _lock_handle.close()
        except Exception:
            pass
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Port utilities
# ---------------------------------------------------------------------------

def is_port_in_use(port: int) -> bool:
    """Return True if the given TCP port has something listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def http_get_ok(url: str, timeout: float = 3.0) -> bool:
    """Return True if an HTTP GET to url returns a 2xx/3xx status."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 400
    except Exception:
        return False


def wait_for_url(url: str, timeout: float, label: str) -> bool:
    """Poll url until it responds or timeout expires. Returns True on success."""
    deadline = time.monotonic() + timeout
    dots = 0
    while time.monotonic() < deadline:
        if http_get_ok(url):
            return True
        dots += 1
        if dots % 4 == 0:
            print(f"\r  {CYAN}[→]{RESET} Waiting for {label}{'.' * (dots // 4 % 4 + 1)}   ", end="", flush=True)
        time.sleep(HEALTH_POLL_INTERVAL)
    print()
    return False


# ---------------------------------------------------------------------------
# Runtime detection
# ---------------------------------------------------------------------------

def find_python() -> tuple[str, tuple[int, int]] | None:
    """
    Return (python_executable, (major, minor)) for the best Python found,
    or None if not found / version too old.
    """
    candidates = [sys.executable, "python", "python3", "py"]
    for cand in candidates:
        try:
            result = subprocess.run(
                [cand, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(".")
                major, minor = int(parts[0]), int(parts[1])
                if (major, minor) >= (MIN_PYTHON_MAJOR, MIN_PYTHON_MINOR):
                    return cand, (major, minor)
        except Exception:
            continue
    return None


def find_node() -> tuple[str, int] | None:
    """Return (node_executable, major_version) or None."""
    node_exe = shutil.which("node")
    if not node_exe:
        return None
    try:
        result = subprocess.run(
            [node_exe, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            version_str = result.stdout.strip().lstrip("v")
            major = int(version_str.split(".")[0])
            if major >= MIN_NODE_MAJOR:
                return node_exe, major
    except Exception:
        pass
    return None


def find_npm() -> str | None:
    """Return npm executable path or None."""
    return shutil.which("npm")


# ---------------------------------------------------------------------------
# Dependency & environment checks
# ---------------------------------------------------------------------------

def check_python(python_exe: str, project_root: Path) -> None:
    """Verify required Python packages are available."""
    required_packages = ["uvicorn", "fastapi", "peewee", "cv2", "numpy", "yaml"]
    missing = []
    for pkg in required_packages:
        result = subprocess.run(
            [python_exe, "-c", f"import {pkg}"],
            capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            missing.append(pkg)

    if missing:
        step_warn(f"Missing Python packages: {', '.join(missing)}")
        step_info("Installing missing Python packages...")
        pip_names = {
            "cv2": "opencv-python-headless",
            "yaml": "PyYAML",
        }
        to_install = [pip_names.get(p, p) for p in missing]
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "--quiet"] + to_install,
            capture_output=False, timeout=120,
        )
        if result.returncode != 0:
            fatal(
                "Failed to install required Python packages.",
                f"Packages: {', '.join(to_install)}",
                "Run: pip install " + " ".join(to_install),
            )
        step_ok("Python packages installed")
    else:
        step_ok("All required Python packages available")


def check_frontend_deps() -> None:
    """Install frontend npm dependencies if node_modules is missing or incomplete."""
    node_modules = WEB_DIR / "node_modules"
    package_lock = WEB_DIR / "package-lock.json"

    if node_modules.exists() and (node_modules / ".package-lock.json").exists():
        step_ok("Frontend node_modules already installed")
        return

    step_info("Installing frontend dependencies (npm install)...")
    npm = find_npm()
    if not npm:
        fatal("npm not found in PATH.", hint="Install Node.js from https://nodejs.org/")

    log_path = LOGS_DIR / "npm_install.log"
    with open(log_path, "w", encoding="utf-8") as log_f:
        result = subprocess.run(
            [npm, "install"],
            cwd=str(WEB_DIR),
            stdout=log_f,
            stderr=log_f,
            timeout=300,
        )

    if result.returncode != 0:
        fatal(
            "npm install failed for the frontend.",
            f"See log: {log_path}",
            "Run 'npm install' inside the 'web/' directory manually.",
        )
    step_ok("Frontend dependencies installed")


def ensure_config_files(project_root: Path) -> None:
    """Create required config files from examples if they are missing."""
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        step_warn(".env file created from .env.example — edit it to add your GEMINI_API_KEY")
    elif env_file.exists():
        step_ok(".env configuration present")
    else:
        step_warn("No .env file found — some AI features may be unavailable")

    config_file = project_root / "config" / "config.yml"
    config_example = project_root / "config" / "config.yml.example"
    if not config_file.exists() and config_example.exists():
        shutil.copy(config_example, config_file)
        step_warn("config.yml created from example — review camera settings")
    elif config_file.exists():
        step_ok("config.yml present")

    # Ensure required directories exist
    for d in ["logs", "config/camera_snapshots", "config/identities"]:
        (project_root / d).mkdir(parents=True, exist_ok=True)


def check_go2rtc() -> None:
    """Check go2rtc binary exists (it is started by the backend automatically)."""
    go2rtc_bin = PROJECT_ROOT / "go2rtc_bin" / "go2rtc.exe"
    if go2rtc_bin.exists():
        step_ok("go2rtc binary found")
    else:
        step_warn("go2rtc binary not found — live camera streaming may be unavailable")


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

class ManagedProcess:
    """Wrapper around a subprocess that logs output to a file."""

    def __init__(self, name: str, cmd: list[str], cwd: Path, log_path: Path, env: dict | None = None):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.log_path = log_path
        self.env = env
        self.proc: subprocess.Popen | None = None
        self._log_file = None

    def start(self) -> None:
        self._log_file = open(self.log_path, "w", encoding="utf-8")
        env = {**os.environ, **(self.env or {})}

        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        self.proc = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            stdout=self._log_file,
            stderr=self._log_file,
            env=env,
            creationflags=creation_flags,
        )
        if logger:
            logger.info("Started %s (PID %s): %s", self.name, self.proc.pid, " ".join(self.cmd))

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            if logger:
                logger.info("Stopping %s (PID %s)...", self.name, self.proc.pid)
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            except Exception:
                pass
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass

    def get_exit_code(self) -> int | None:
        if self.proc:
            return self.proc.poll()
        return None


# ---------------------------------------------------------------------------
# Main launcher flow
# ---------------------------------------------------------------------------

_processes: list[ManagedProcess] = []


def shutdown_all() -> None:
    """Terminate all managed processes cleanly."""
    print()
    step_info("Shutting down services...")
    for proc in reversed(_processes):
        if proc.is_running():
            step_info(f"Stopping {proc.name}...")
            proc.stop()
    release_single_instance_lock()
    step_ok("All services stopped. Goodbye.")
    print()


def main() -> None:
    global logger

    verbose = "--log" in sys.argv
    logger = setup_logging(verbose)

    _print_header()

    # ------------------------------------------------------------------
    # 1. Single-instance check
    # ------------------------------------------------------------------
    if not acquire_single_instance_lock():
        # Another launcher is running — check if services are already up
        print(f"  {YELLOW}[!]{RESET} Another launcher instance is already running.")
        if is_port_in_use(FRONTEND_PORT):
            step_ok("Application already running — opening browser...")
            webbrowser.open(BROWSER_URL)
            input("  Press Enter to close this window...")
            sys.exit(0)
        else:
            step_warn("Previous launcher may have crashed. Proceeding anyway...")

    # ------------------------------------------------------------------
    # 2. Environment checks
    # ------------------------------------------------------------------
    print(f"  {BOLD}Checking environment...{RESET}\n")

    # OS
    step_ok(f"Operating System: Windows {platform.version()}")

    # Python
    python_info = find_python()
    if not python_info:
        fatal(
            f"Python {MIN_PYTHON_MAJOR}.{MIN_PYTHON_MINOR}+ not found.",
            "The backend requires Python 3.11 or newer.",
            f"Download from: https://www.python.org/downloads/\n"
            f"  Install Python and make sure to check 'Add to PATH'.",
        )
    python_exe, (py_major, py_minor) = python_info
    step_ok(f"Python {py_major}.{py_minor} found: {python_exe}")

    # Node.js
    node_info = find_node()
    if not node_info:
        fatal(
            f"Node.js {MIN_NODE_MAJOR}+ not found.",
            "The frontend requires Node.js 18 or newer.",
            "Download from: https://nodejs.org/en/download\n"
            "  Install Node.js and restart this launcher.",
        )
    node_exe, node_major = node_info
    step_ok(f"Node.js {node_major} found: {node_exe}")

    npm_exe = find_npm()
    if not npm_exe:
        fatal("npm not found in PATH.", hint="npm comes bundled with Node.js — reinstall Node.js.")
    step_ok(f"npm found: {npm_exe}")

    # ------------------------------------------------------------------
    # 3. Config & directories
    # ------------------------------------------------------------------
    print()
    print(f"  {BOLD}Checking project configuration...{RESET}\n")
    ensure_config_files(PROJECT_ROOT)

    # go2rtc binary
    check_go2rtc()

    # ------------------------------------------------------------------
    # 4. Python packages
    # ------------------------------------------------------------------
    print()
    print(f"  {BOLD}Checking backend dependencies...{RESET}\n")
    check_python(python_exe, PROJECT_ROOT)

    # ------------------------------------------------------------------
    # 5. Frontend deps
    # ------------------------------------------------------------------
    print()
    print(f"  {BOLD}Checking frontend dependencies...{RESET}\n")
    check_frontend_deps()

    # ------------------------------------------------------------------
    # 6. Port conflict detection
    # ------------------------------------------------------------------
    print()
    print(f"  {BOLD}Checking ports...{RESET}\n")

    backend_already_running = False
    frontend_already_running = False

    if is_port_in_use(BACKEND_PORT):
        if http_get_ok(BACKEND_HEALTH_URL):
            step_ok(f"Backend already running on port {BACKEND_PORT} — reusing")
            backend_already_running = True
        else:
            fatal(
                f"Port {BACKEND_PORT} is occupied by another process.",
                "This port is required for the ANDRO-Vision backend.",
                f"Find and close the process using port {BACKEND_PORT}, then relaunch.",
            )

    if is_port_in_use(FRONTEND_PORT):
        if http_get_ok(FRONTEND_HEALTH_URL):
            step_ok(f"Frontend already running on port {FRONTEND_PORT} — reusing")
            frontend_already_running = True
        else:
            fatal(
                f"Port {FRONTEND_PORT} is occupied by another process.",
                "This port is required for the ANDRO-Vision frontend dev server.",
                f"Find and close the process using port {FRONTEND_PORT}, then relaunch.",
            )

    if not backend_already_running:
        step_ok(f"Port {BACKEND_PORT} available for backend")
    if not frontend_already_running:
        step_ok(f"Port {FRONTEND_PORT} available for frontend")

    # ------------------------------------------------------------------
    # 7. Start backend
    # ------------------------------------------------------------------
    if not backend_already_running:
        print()
        print(f"  {BOLD}Starting backend...{RESET}\n")

        backend_env = {"PYTHONPATH": str(PROJECT_ROOT)}
        backend_log = LOGS_DIR / "backend.log"

        backend_proc = ManagedProcess(
            name="Backend (FastAPI)",
            cmd=[python_exe, str(BACKEND_ENTRY)],
            cwd=PROJECT_ROOT,
            log_path=backend_log,
            env=backend_env,
        )
        backend_proc.start()
        _processes.append(backend_proc)

        step_info(f"Backend starting... (log: logs/backend.log)")

        print(f"\r  {CYAN}[→]{RESET} Waiting for backend on port {BACKEND_PORT}...", end="", flush=True)
        if not wait_for_url(BACKEND_HEALTH_URL, BACKEND_START_TIMEOUT, "backend"):
            print()
            # Check if process exited early
            exit_code = backend_proc.get_exit_code()
            if exit_code is not None:
                fatal(
                    f"Backend process exited unexpectedly (code {exit_code}).",
                    f"See logs/backend.log for details.",
                    "Check that all Python dependencies are installed and config/config.yml is valid.",
                )
            else:
                fatal(
                    f"Backend did not respond within {BACKEND_START_TIMEOUT}s.",
                    "The process is running but not accepting connections.",
                    "Check logs/backend.log for errors.",
                )
        print()
        step_ok(f"Backend ready on http://127.0.0.1:{BACKEND_PORT}")

    # ------------------------------------------------------------------
    # 8. Start frontend
    # ------------------------------------------------------------------
    if not frontend_already_running:
        print()
        print(f"  {BOLD}Starting frontend...{RESET}\n")

        frontend_log = LOGS_DIR / "frontend.log"
        frontend_proc = ManagedProcess(
            name="Frontend (Vite dev)",
            cmd=[npm_exe, "run", "dev"],
            cwd=WEB_DIR,
            log_path=frontend_log,
        )
        frontend_proc.start()
        _processes.append(frontend_proc)

        step_info("Frontend dev server starting... (log: logs/frontend.log)")

        print(f"\r  {CYAN}[→]{RESET} Waiting for frontend on port {FRONTEND_PORT}...", end="", flush=True)
        if not wait_for_url(FRONTEND_HEALTH_URL, FRONTEND_START_TIMEOUT, "frontend"):
            print()
            exit_code = frontend_proc.get_exit_code()
            if exit_code is not None:
                fatal(
                    f"Frontend process exited unexpectedly (code {exit_code}).",
                    "See logs/frontend.log for details.",
                    "Try running 'npm run dev' inside the 'web/' directory manually.",
                )
            else:
                fatal(
                    f"Frontend did not respond within {FRONTEND_START_TIMEOUT}s.",
                    "The Vite dev server is running but not accepting connections.",
                    "Check logs/frontend.log for errors.",
                )
        print()
        step_ok(f"Frontend ready on http://127.0.0.1:{FRONTEND_PORT}")

    # ------------------------------------------------------------------
    # 9. Open browser
    # ------------------------------------------------------------------
    print()
    step_info(f"Opening browser: {BROWSER_URL}")
    time.sleep(0.5)
    webbrowser.open(BROWSER_URL)

    # ------------------------------------------------------------------
    # 10. Keep alive
    # ------------------------------------------------------------------
    print()
    print(f"  {GREEN}{BOLD}Application ready.{RESET}")
    print()
    print(f"  {DIM}Backend:  http://127.0.0.1:{BACKEND_PORT}{RESET}")
    print(f"  {DIM}Frontend: http://127.0.0.1:{FRONTEND_PORT}{RESET}")
    print(f"  {DIM}Logs:     {LOGS_DIR}{RESET}")
    print()
    print(f"  {YELLOW}Press Ctrl+C to stop all services and exit.{RESET}")
    print()

    try:
        while True:
            # Check if any managed process died unexpectedly
            for proc in _processes:
                if not proc.is_running():
                    exit_code = proc.get_exit_code()
                    step_fail(f"{proc.name} stopped unexpectedly (exit code {exit_code})")
                    if logger:
                        logger.error("%s stopped unexpectedly with exit code %s", proc.name, exit_code)
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_all()


if __name__ == "__main__":
    main()
