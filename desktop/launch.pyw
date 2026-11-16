"""Windowless Windows entrypoint for COLAB-HUD desktop pill."""

import os
import sys
from pathlib import Path


def _ensure_paths() -> None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    uv_site = Path.home() / "AppData" / "Roaming" / "uv" / "tools" / "google-colab-cli" / "Lib" / "site-packages"
    if uv_site.is_dir() and str(uv_site) not in sys.path:
        sys.path.insert(0, str(uv_site))


if __name__ == "__main__":
    _ensure_paths()
    os.chdir(str(Path(__file__).resolve().parent.parent))
    from desktop.cli import main

    raise SystemExit(main([]))
