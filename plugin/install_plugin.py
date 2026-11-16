"""Install or uninstall the COLAB-HUD plugin into ~/.gemini/config/plugins/colab-hud."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PLUGIN_NAME = "colab-hud"


def target_dir() -> Path:
    return Path.home() / ".gemini" / "config" / "plugins" / PLUGIN_NAME


def install_plugin() -> Path:
    plugin_src = Path(__file__).resolve().parent
    project_root = plugin_src.parent
    desktop_src = project_root / "desktop"
    dst = target_dir()

    shutil.copytree(
        plugin_src,
        dst,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("install_plugin.py", "__pycache__", "*.pyc"),
    )

    # Bundle the desktop telemetry/HUD Python modules inside the sidecar so the
    # installed plugin stays self-contained regardless of workspace location.
    bundled_desktop = dst / "sidecars" / "colab_panel" / "py" / "desktop"
    if desktop_src.is_dir():
        shutil.copytree(
            desktop_src,
            bundled_desktop,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "agy_hud.ico"),
        )

    return dst


def uninstall_plugin() -> None:
    dst = target_dir()
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=False)
        print(f"Removed {PLUGIN_NAME} plugin from: {dst}")
    else:
        print(f"Plugin directory not found: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install/uninstall COLAB-HUD plugin")
    parser.add_argument("--uninstall", action="store_true", help="Remove installed plugin")
    args = parser.parse_args()
    if args.uninstall:
        uninstall_plugin()
    else:
        dest = install_plugin()
        print(f"Installed COLAB-HUD plugin to: {dest}")


if __name__ == "__main__":
    main()
