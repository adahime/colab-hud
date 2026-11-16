<div align="center">

<img src="docs/assets/banner.svg" alt="COLAB-HUD Banner" width="100%" />

<p>
  <strong>Live GPU/TPU hardware specs, Compute Unit balance, and hourly burn-rate HUD for Google Colab</strong>
</p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square" alt="License: MIT" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3b82f6?style=flat-square" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Node.js-22%2B%20sidecar_sdk-06b6d4?style=flat-square" alt="Node.js 22+ sidecar_sdk" />
  <img src="https://img.shields.io/badge/Auth-google--colab--cli%20Keyring-f9ab00?style=flat-square" alt="google-colab-cli Keyring" />
  <img src="https://img.shields.io/badge/UI-EN%20%2F%20%E4%B8%AD%E6%96%87-6366f1?style=flat-square" alt="EN / 中文" />
  <img src="https://img.shields.io/badge/Docs-8%20Languages-ec4899?style=flat-square" alt="Docs: 8 Languages" />
</p>

<p>
  <strong>English</strong> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.ru.md">Русский</a>
</p>

<p>
  <a href="#overview">Overview</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#data-sources">Data Sources</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

</div>

---

<div align="center">
  <img src="docs/assets/hud-showcase.svg" alt="COLAB-HUD Desktop Pill and Side-Pane Preview" width="100%" />
</div>

---

## <a id="overview"></a>Overview

**COLAB-HUD** is a lightweight desktop floating pill, CLI utility, and Antigravity 2.0 auxiliary side-pane plugin for Google Colab. It queries official Google Colab backend endpoints using your existing `google-colab-cli` OAuth2 keyring credentials—without blocking background polling on interactive stdin prompts—to monitor active GPU/TPU/CPU assignments, hourly Compute Unit (`CU/hr`) burn rate, remaining balance, estimated hours left, and connected Google account email.

### Key Features

- **Balance, Burn Rate & Active Account**: Polls `/tun/m/ccu-info` and `/tun/m/assignments` to display current Compute Unit balance, live hourly burn rate (`CU/hr`), estimated remaining runtime hours (`balance / rate`), active assignment count, and cached `userinfo.email` so multi-account mismatches are spotted immediately.
- **On-Demand Hardware Probe (`nvidia-smi`)**: Reads assigned accelerator tier and machine shape (`Standard` / `High-RAM`) immediately from backend assignments, checks Jupyter `/api/kernels` execution state read-only (`idle` / `busy` / `none`), and—only when you click **Probe GPU** or run `--probe`—runs a cached read-only hardware check for exact GPU model (e.g. `NVIDIA A100-SXM4-40GB`), VRAM usage, GPU utilization, system RAM, vCPU count, and root disk usage.
- **Safe Non-Blocking Keyring Loader**: Reads and refreshes saved `google-colab-cli` tokens silently during polling (`unauthenticated` / `expired` states are reported cleanly instead of hanging on `input()`). Signing in or switching accounts opens Google's OAuth page in your browser and provides a compact authorization-code dialog.
- **Desktop Floating Pill, CLI & Side-Pane Plugin**: Includes a frameless dark-theme Tkinter pill (`launch.bat` / `launch.pyw`) that automatically clears the Windows taskbar when expanded, JSON/table/watch CLI flags, and an Antigravity side-pane plugin (`sidecars/colab_panel/`) with automatic light/dark theme sync and a one-click button to launch the desktop pill.
- **Zero Duplicate Toolchains**: Automatically locates the `uv`-installed `google-colab-cli` Python environment (`site-packages` / `pythonw.exe`) when launched from system Python or Node.js.

---

## <a id="quick-start"></a>Quick Start

### Prerequisites

Install the official Colab CLI once if you have not already:

```bash
uv tool install git+https://github.com/googlecolab/google-colab-cli.git
```

### 1. Antigravity 2.0 Side-Pane Plugin

Install the self-contained plugin into `~/.gemini/config/plugins/colab-hud`, then enable `colab-hud` in the Antigravity Plugins Manager:

```bash
python plugin/install_plugin.py
```

To uninstall:

```bash
python plugin/install_plugin.py --uninstall
```

### 2. Standalone Desktop Pill & CLI

Runs independently without touching any Antigravity configuration:

- **Windows (no console window)**: double-click `desktop/launch.bat` or `desktop/launch.pyw`
- **Python GUI / CLI**:

```bash
# Launch desktop floating pill (default: zh, 10s backend poll, 94% opacity)
python -m desktop.cli

# Optional flags: --lang en|zh, --interval 10, --refresh-ms 1000, --alpha 0.94
python -m desktop.cli --lang en --interval 5

# Print one terminal snapshot and exit
python -m desktop.cli --cli

# Output structured JSON snapshot (add --no-kernel-check to skip /api/kernels)
python -m desktop.cli --json

# Probe exact GPU model, VRAM, RAM, vCPU, and disk on the active assignment
python -m desktop.cli --probe --force

# Continuously refresh terminal summary
python -m desktop.cli --watch --interval 10
```

> [!TIP]
> Left-drag the pill bar to reposition (unless pinned), click `▾` or double-click the bar to expand/collapse the card, and **right-click** anywhere on the window to switch **Language (`EN` / `中文`)**, **Sign In / Switch Account**, **Probe Exact GPU**, **Always on Top**, **Pin Position**, **Opacity (`100%`–`70%`)**, or **Refresh Interval (`5s`–`60s`)**.

---

## <a id="data-sources"></a>Data Sources

| Source | Endpoint / Interface | Data Retrieved |
| :--- | :--- | :--- |
| Colab Session API | `GET /tun/m/ccu-info` | Compute Unit balance (`currentBalance`), hourly burn rate (`consumptionRateHourly`), active assignments (`assignmentsCount`) |
| Colab Assignments API | `GET /tun/m/assignments` | Active runtime endpoints, accelerator (`T4` / `L4` / `G4` / `A100` / `H100` / `V5E1` / `V6E1` / `NONE`), variant, machine shape (`Standard` / `High-RAM`), proxy URL/token |
| Runtime Proxy (Read-Only) | `GET {proxy_url}/api/kernels` | Live kernel count and execution state (`idle` / `busy` / `none`) without spawning kernels |
| Runtime Probe (On-Demand) | `ColabRuntime.execute_code(...)` | `nvidia-smi` GPU name, count, VRAM used/total, GPU utilization, `/proc/meminfo` RAM, `os.cpu_count()`, and `/` disk usage |
| Google OAuth2 Userinfo | `GET /oauth2/v2/userinfo` | Signed-in account email (`cached by token fingerprint`) |

---

## Project Structure

```text
colab-hud/
├── desktop/                     # Desktop floating pill, OAuth dialog & CLI
│   ├── telemetry.py             # Keyring loader, Colab API polling, /api/kernels & nvidia-smi probe
│   ├── hud_pill.py              # Tkinter frameless pill, expandable card & OAuth dialog
│   ├── cli.py                   # Entrypoint for GUI / --cli / --json / --watch / --probe
│   ├── launch.pyw               # Silent Windows GUI launcher
│   ├── launch.bat               # Windows double-click batch launcher
│   └── assets/colab_hud.ico     # Desktop shortcut icon
├── plugin/                      # Antigravity 2.0 auxiliary side-pane plugin
│   ├── plugin.json              # Plugin manifest
│   ├── install_plugin.py        # Self-contained installer / uninstaller
│   ├── assets/logo.svg          # Plugin icon
│   └── sidecars/colab_panel/    # sidecar_sdk Node backend (5s cache + ETag) & Webview UI
├── tests/                       # Unit tests covering telemetry, OAuth helpers & CLI
├── docs/assets/                 # SVG banner and preview graphics
├── pyproject.toml
├── CHANGELOG.md
└── LICENSE
```

---

## License

Released under the [MIT License](LICENSE).
