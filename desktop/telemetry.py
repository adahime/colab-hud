"""Colab telemetry, non-blocking credential verification, and hardware probing.

Reads the official ``google-colab-cli`` keyring credentials without ever falling
through to an interactive stdin prompt during background polling, queries
``/tun/m/ccu-info`` and ``/tun/m/assignments``, checks live Jupyter kernel
state via the runtime proxy, and optionally probes exact GPU/VRAM/RAM specs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


CACHE_DIR = Path.home() / ".cache" / "colab-hud"
EMAIL_CACHE_PATH = CACHE_DIR / "account_cache.json"
PROBE_CACHE_PATH = CACHE_DIR / "probe_cache.json"

UV_TOOL_SCRIPTS_DIR = Path.home() / "AppData" / "Roaming" / "uv" / "tools" / "google-colab-cli" / "Scripts"
UV_TOOL_SITE_PACKAGES = Path.home() / "AppData" / "Roaming" / "uv" / "tools" / "google-colab-cli" / "Lib" / "site-packages"
LOCAL_BIN_DIR = Path.home() / ".local" / "bin"

PROBE_PYTHON_SNIPPET = r"""
import json, os, shutil, subprocess

info = {
    "gpu_name": None,
    "gpu_count": 0,
    "vram_used_mb": None,
    "vram_total_mb": None,
    "gpu_util_pct": None,
    "driver_version": None,
    "cuda_version": None,
    "cpu_count": os.cpu_count(),
    "ram_total_gb": None,
    "ram_used_gb": None,
    "disk_total_gb": None,
    "disk_used_gb": None,
}

try:
    total, used, _ = shutil.disk_usage("/")
    info["disk_total_gb"] = round(total / (1024 ** 3), 2)
    info["disk_used_gb"] = round(used / (1024 ** 3), 2)
except Exception:
    pass

try:
    mem = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.split(":", 1)
            if len(parts) == 2:
                val = parts[1].strip().split()[0]
                mem[parts[0].strip()] = int(val)
    if "MemTotal" in mem:
        total_kb = mem["MemTotal"]
        avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
        info["ram_total_gb"] = round(total_kb / (1024 ** 2), 2)
        info["ram_used_gb"] = round(max(0, total_kb - avail_kb) / (1024 ** 2), 2)
except Exception:
    pass

nvidia_smi = shutil.which("nvidia-smi")
if nvidia_smi:
    try:
        out = subprocess.check_output(
            [
                nvidia_smi,
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,driver_version",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        ).strip()
        rows = [r.strip() for r in out.splitlines() if r.strip()]
        if rows:
            info["gpu_count"] = len(rows)
            cols = [c.strip() for c in rows[0].split(",")]
            if len(cols) >= 5:
                info["gpu_name"] = cols[0]
                info["vram_used_mb"] = float(cols[1]) if cols[1] not in ("N/A", "[N/A]") else None
                info["vram_total_mb"] = float(cols[2]) if cols[2] not in ("N/A", "[N/A]") else None
                info["gpu_util_pct"] = float(cols[3]) if cols[3] not in ("N/A", "[N/A]") else None
                info["driver_version"] = cols[4] if cols[4] not in ("N/A", "[N/A]") else None
    except Exception:
        pass

print("__COLAB_HUD_PROBE__" + json.dumps(info))
""".strip()


def bootstrap_colab_cli() -> bool:
    """Ensure ``colab_cli`` and its dependencies are importable."""
    try:
        import colab_cli  # noqa: F401
        return True
    except ImportError:
        pass

    if UV_TOOL_SITE_PACKAGES.is_dir():
        site_str = str(UV_TOOL_SITE_PACKAGES)
        if site_str not in sys.path:
            sys.path.insert(0, site_str)
        try:
            import colab_cli  # noqa: F401
            return True
        except ImportError:
            pass
    return False


def find_colab_executable() -> Optional[str]:
    """Locate the official ``colab`` CLI executable."""
    candidates = [
        LOCAL_BIN_DIR / ("colab.exe" if os.name == "nt" else "colab"),
        UV_TOOL_SCRIPTS_DIR / ("colab.exe" if os.name == "nt" else "colab"),
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return shutil.which("colab")


def find_tool_python(gui: bool = False) -> str:
    """Locate the ``google-colab-cli`` Python interpreter, falling back to ``sys.executable``."""
    name = ("pythonw.exe" if gui else "python.exe") if os.name == "nt" else "python"
    candidate = UV_TOOL_SCRIPTS_DIR / name
    if candidate.is_file():
        return str(candidate)
    return sys.executable


def _read_json_file(path: Path) -> Dict[str, Any]:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _write_json_file(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _token_fingerprint(token_json: str) -> str:
    return hashlib.sha256(token_json.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _extract_token_json() -> Tuple[Optional[str], bool]:
    """Return ``(token_json, from_legacy_file)`` from OS keyring or legacy file."""
    bootstrap_colab_cli()
    from colab_cli import auth as colab_auth

    token_json: Optional[str] = None
    try:
        token_json = colab_auth._get_token_from_keyring()
    except Exception:
        token_json = None

    if token_json:
        return token_json, False

    legacy_path = Path(colab_auth.LEGACY_TOKEN_PATH)
    if legacy_path.is_file():
        try:
            return legacy_path.read_text(encoding="utf-8"), True
        except Exception:
            return None, True

    return None, False


def load_cached_credentials() -> Tuple[Optional[Any], str, Optional[str], Optional[str]]:
    """Load and refresh saved OAuth credentials without prompting stdin.

    Returns ``(credentials, auth_state, error_message, fingerprint)``.
    ``auth_state`` is one of ``"ok"``, ``"unauthenticated"``, ``"expired"``, ``"error"``.
    """
    if not bootstrap_colab_cli():
        return None, "error", "google-colab-cli package not found", None

    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2.credentials import Credentials
    from colab_cli import auth as colab_auth

    token_json, from_legacy = _extract_token_json()
    if not token_json:
        return None, "unauthenticated", "Not signed in to Google Colab CLI", None

    try:
        token_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(token_data)
    except Exception as exc:
        return None, "expired", f"Corrupted saved token: {exc}", None

    needs_save = from_legacy
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
                needs_save = True
            except Exception as exc:
                return None, "expired", f"OAuth refresh failed: {exc}", None
        else:
            return None, "expired", "Saved OAuth token expired without refresh token", None

    updated_json = token_json
    if needs_save:
        try:
            updated_json = creds.to_json()
            colab_auth._save_token_to_keyring(updated_json)
            if from_legacy:
                colab_auth._remove_legacy_token()
        except Exception:
            pass

    return creds, "ok", None, _token_fingerprint(updated_json)


def clear_saved_auth() -> Dict[str, Any]:
    """Delete saved Colab CLI OAuth token and HUD caches so user can switch accounts."""
    removed_keyring = False
    removed_legacy = False

    if bootstrap_colab_cli():
        import keyring
        from colab_cli import auth as colab_auth

        try:
            keyring.delete_password(colab_auth.KEYRING_SERVICE_NAME, colab_auth.KEYRING_USERNAME)
            removed_keyring = True
        except Exception:
            pass

        legacy = Path(colab_auth.LEGACY_TOKEN_PATH)
        if legacy.is_file():
            try:
                legacy.unlink()
                removed_legacy = True
            except Exception:
                pass

    for path in (EMAIL_CACHE_PATH, PROBE_CACHE_PATH):
        if path.is_file():
            try:
                path.unlink()
            except Exception:
                pass

    return {
        "ok": True,
        "removed_keyring": removed_keyring,
        "removed_legacy": removed_legacy,
    }


def _load_oauth_client_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the official ``google-colab-cli`` OAuth client configuration."""
    bootstrap_colab_cli()
    from importlib import resources

    cfg_path = config_path or os.path.expanduser("~/.colab-cli-oauth-config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    config_resource = resources.files("colab_cli").joinpath("oauth_config.json")
    if config_resource.is_file():
        return json.loads(config_resource.read_text(encoding="utf-8"))

    raise FileNotFoundError("Could not locate Colab CLI oauth_config.json")


def begin_oauth_flow(switch_account: bool = False) -> Tuple[Any, str]:
    """Build Google's official OAuth2 flow and authorization URL."""
    if not bootstrap_colab_cli():
        raise RuntimeError("google-colab-cli package not found")

    if switch_account:
        clear_saved_auth()

    from google_auth_oauthlib.flow import InstalledAppFlow
    from colab_cli import auth as colab_auth

    client_config = _load_oauth_client_config()
    flow = InstalledAppFlow.from_client_config(client_config, colab_auth.PUBLIC_SCOPES)
    flow.redirect_uri = colab_auth.REMOTE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(prompt="consent", token_usage="remote")
    return flow, auth_url


def complete_oauth_flow(flow: Any, code: str) -> Dict[str, Any]:
    """Exchange Google's authorization code for tokens and persist into OS keyring."""
    cleaned = (code or "").strip()
    if not cleaned:
        return {"ok": False, "error": "Authorization code is empty"}

    bootstrap_colab_cli()
    from colab_cli import auth as colab_auth

    try:
        flow.oauth2session.scope = None
        token = flow.fetch_token(code=cleaned)
        flow.oauth2session.scope = token.get("scope")
        creds = flow.credentials
        colab_auth._save_token_to_keyring(creds.to_json())
        colab_auth._remove_legacy_token()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def launch_interactive_login(switch_account: bool = False) -> Dict[str, Any]:
    """Open a console helper that launches Google OAuth in the browser and reads the code."""
    tool_py = find_tool_python(gui=False)
    py_root = str(Path(__file__).resolve().parent.parent)

    if switch_account:
        clear_saved_auth()

    args = [tool_py, "-m", "desktop.cli", "--oauth-prompt"]
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{py_root}{os.pathsep}{existing}" if existing else py_root

    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(args, cwd=py_root, env=env, creationflags=creationflags)
        return {"ok": True, "launched": tool_py}

    subprocess.Popen(args, cwd=py_root, env=env)
    return {"ok": True, "launched": tool_py}


def _resolve_account_email(session: Any, fingerprint: Optional[str]) -> Optional[str]:
    if not fingerprint:
        return None

    cache = _read_json_file(EMAIL_CACHE_PATH)
    if cache.get("fingerprint") == fingerprint and cache.get("email"):
        return str(cache["email"])

    try:
        resp = session.get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=4)
        if resp.ok:
            email = resp.json().get("email")
            if email:
                _write_json_file(
                    EMAIL_CACHE_PATH,
                    {"fingerprint": fingerprint, "email": email, "updated_ms": int(time.time() * 1000)},
                )
                return str(email)
    except Exception:
        pass
    return None


def format_runtime_summary(accelerator: str, variant: str, shape_label: str) -> str:
    """Format a concise hardware label from backend assignment metadata."""
    acc = (accelerator or "NONE").upper()
    var = (variant or "DEFAULT").upper()

    if acc == "NONE" or var == "DEFAULT":
        hw = "CPU"
    elif var == "TPU" or acc.startswith("V"):
        tpu_map = {"V5E1": "TPU v5e-1", "V6E1": "TPU v6e-1", "V28": "TPU v2-8"}
        hw = tpu_map.get(acc, f"TPU {acc}")
    else:
        hw = f"{acc} GPU"

    if shape_label and shape_label.lower() != "standard":
        return f"{hw} · {shape_label}"
    return hw


def _inspect_proxy_kernels(proxy_url: str, proxy_token: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Read-only HTTP check of ``/api/kernels`` on an active runtime proxy."""
    if not proxy_url or not proxy_token:
        return None, None, None

    import requests

    url = f"{proxy_url.rstrip('/')}/api/kernels"
    headers = {
        "X-Colab-Client-Agent": "colab-cli",
        "X-Colab-Runtime-Proxy-Token": proxy_token,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=3.5)
        if not resp.ok:
            return None, None, None
        kernels = resp.json()
        if not isinstance(kernels, list):
            return None, None, None
        if not kernels:
            return 0, "none", None

        idle_id: Optional[str] = None
        states = []
        for item in kernels:
            state = str(item.get("execution_state") or "unknown")
            states.append(state)
            if state == "idle" and idle_id is None:
                idle_id = item.get("id")

        agg_state = "idle" if "idle" in states else ("busy" if "busy" in states else states[0])
        return len(kernels), agg_state, idle_id
    except Exception:
        return None, None, None


def _load_probe_cache() -> Dict[str, Any]:
    return _read_json_file(PROBE_CACHE_PATH)


def _save_probe_cache(endpoint: str, probe_data: Dict[str, Any]) -> None:
    cache = _load_probe_cache()
    cache[endpoint] = probe_data
    # Keep at most 16 most recent endpoint probe entries.
    if len(cache) > 16:
        ordered = sorted(cache.items(), key=lambda kv: kv[1].get("probed_at_ms", 0), reverse=True)
        cache = dict(ordered[:16])
    _write_json_file(PROBE_CACHE_PATH, cache)


def _extract_probe_json(outputs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    marker = "__COLAB_HUD_PROBE__"
    for item in outputs:
        text = item.get("text")
        if not text and isinstance(item.get("data"), dict):
            text = item["data"].get("text/plain")
        if not text:
            continue
        for line in str(text).splitlines():
            if marker in line:
                payload = line.split(marker, 1)[1].strip()
                return json.loads(payload)
    return None


@dataclass
class FetchOptions:
    check_kernels: bool = True
    include_email: bool = True


def fetch_snapshot(options: Optional[FetchOptions] = None) -> Dict[str, Any]:
    """Fetch current Colab CU balance, hourly rate, and active VM configurations."""
    opts = options or FetchOptions()
    now_ms = int(time.time() * 1000)
    colab_exe = find_colab_executable()

    base: Dict[str, Any] = {
        "authenticated": False,
        "auth_state": "unauthenticated",
        "account_email": None,
        "timestamp_ms": now_ms,
        "balance_cu": None,
        "rate_cu_hr": None,
        "assignments_count": 0,
        "est_hours_left": None,
        "runtimes": [],
        "colab_cli_found": bool(colab_exe),
        "error": None,
    }

    creds, auth_state, err_msg, fingerprint = load_cached_credentials()
    if creds is None:
        base["auth_state"] = auth_state
        base["error"] = err_msg
        return base

    from google.auth.transport.requests import AuthorizedSession
    from colab_cli.client import Client, ColabRequestError, Prod, shape_display_label

    session = AuthorizedSession(creds)
    client = Client(Prod(), session)

    if opts.include_email:
        base["account_email"] = _resolve_account_email(session, fingerprint)

    try:
        usage = client.get_consumption_user_info()
        assignments = client.list_assignments()
    except ColabRequestError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        base["auth_state"] = "auth_error" if status in (401, 403) else "error"
        base["error"] = f"Colab API error ({status}): {exc}" if status else str(exc)
        return base
    except Exception as exc:
        base["auth_state"] = "error"
        base["error"] = str(exc)
        return base

    probe_cache = _load_probe_cache()
    runtimes: List[Dict[str, Any]] = []

    for item in assignments:
        acc_val = getattr(item.accelerator, "value", str(item.accelerator))
        var_name = getattr(item.variant, "name", str(item.variant))
        shape_label = shape_display_label(item.machine_shape)
        proxy = item.runtime_proxy_info
        proxy_url = getattr(proxy, "url", "") if proxy else ""
        proxy_token = getattr(proxy, "token", "") if proxy else ""
        expires_s = getattr(proxy, "token_expires_in_seconds", None) if proxy else None

        k_count, k_state, idle_kid = (
            _inspect_proxy_kernels(proxy_url, proxy_token) if opts.check_kernels else (None, None, None)
        )

        runtimes.append(
            {
                "endpoint": item.endpoint,
                "accelerator": acc_val,
                "variant": var_name,
                "machine_shape": shape_label,
                "summary_label": format_runtime_summary(acc_val, var_name, shape_label),
                "proxy_url": proxy_url,
                "token_expires_in_s": expires_s,
                "kernels_count": k_count,
                "kernel_state": k_state,
                "idle_kernel_id": idle_kid,
                "probe": probe_cache.get(item.endpoint),
            }
        )

    balance = float(usage.paid_compute_units_balance)
    rate = float(usage.consumption_rate_hourly)
    est_hours = round(balance / rate, 2) if rate > 0 else None

    base.update(
        {
            "authenticated": True,
            "auth_state": "ok",
            "balance_cu": round(balance, 3),
            "rate_cu_hr": round(rate, 3),
            "assignments_count": int(usage.assignments_count),
            "est_hours_left": est_hours,
            "runtimes": runtimes,
            "error": None,
        }
    )
    return base


def probe_runtime_hardware(endpoint: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    """Execute a brief read-only hardware probe on an active Colab assignment."""
    creds, auth_state, err_msg, _ = load_cached_credentials()
    if creds is None:
        return {"ok": False, "auth_state": auth_state, "error": err_msg or "Not authenticated"}

    from google.auth.transport.requests import AuthorizedSession
    from colab_cli.client import Client, Prod
    from colab_cli.runtime import ColabRuntime

    session = AuthorizedSession(creds)
    client = Client(Prod(), session)

    try:
        assignments = client.list_assignments()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    if not assignments:
        return {"ok": False, "error": "No active Colab runtime assignment found"}

    target = None
    if endpoint:
        target = next((a for a in assignments if a.endpoint == endpoint), None)
    if target is None:
        # Prefer GPU/TPU runtime when multiple exist.
        gpu_first = sorted(
            assignments,
            key=lambda a: 0 if getattr(a.accelerator, "value", "NONE") != "NONE" else 1,
        )
        target = gpu_first[0]

    proxy = target.runtime_proxy_info
    if not proxy or not proxy.url or not proxy.token:
        return {"ok": False, "endpoint": target.endpoint, "error": "Missing runtime proxy token"}

    k_count, k_state, idle_kid = _inspect_proxy_kernels(proxy.url, proxy.token)
    if k_count and k_state == "busy" and not idle_kid and not force:
        return {
            "ok": False,
            "endpoint": target.endpoint,
            "busy": True,
            "error": "Existing kernel is busy; pass force=True to probe in a temporary kernel",
        }

    spawned_temp = idle_kid is None
    rt = ColabRuntime(proxy.url, proxy.token, kernel_id=idle_kid)
    try:
        outputs = rt.execute_code(PROBE_PYTHON_SNIPPET, allow_stdin=False, timeout=20.0)
        parsed = _extract_probe_json(outputs)
        if not parsed:
            return {"ok": False, "endpoint": target.endpoint, "error": "Probe produced no JSON payload"}
        parsed["probed_at_ms"] = int(time.time() * 1000)
        parsed["endpoint"] = target.endpoint
        _save_probe_cache(target.endpoint, parsed)
        return {"ok": True, "endpoint": target.endpoint, "probe": parsed}
    except Exception as exc:
        return {"ok": False, "endpoint": target.endpoint, "error": str(exc)}
    finally:
        try:
            rt.stop(shutdown_kernel=bool(spawned_temp and force))
        except Exception:
            pass


class ColabTelemetryStore:
    """Thread-safe poller holding the latest Colab telemetry snapshot."""

    def __init__(self, interval_sec: float = 10.0) -> None:
        self.interval_sec = max(3.0, float(interval_sec))
        self._lock = threading.Lock()
        self._snapshot: Optional[Dict[str, Any]] = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def add_listener(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners.append(cb)

    def get_snapshot(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._snapshot) if self._snapshot is not None else None

    def refresh_now(self) -> Dict[str, Any]:
        snap = fetch_snapshot()
        with self._lock:
            self._snapshot = snap
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(snap)
            except Exception:
                pass
        return snap

    def trigger_refresh(self) -> None:
        self._wake_event.set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="colab-hud-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_now()
            self._wake_event.wait(timeout=self.interval_sec)
            self._wake_event.clear()
