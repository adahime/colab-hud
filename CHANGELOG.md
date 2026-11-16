# Changelog

## v0.1.0 — Initial Public Release

- Floating Windows desktop HUD pill (`desktop/`) with CLI (`--cli`, `--watch`, `--json`, `--probe`) and silent `launch.pyw` / `launch.bat` launchers.
- Native Antigravity 2.0 auxiliary side-pane UI plugin (`plugin/`) backed by Node.js `sidecar_sdk` and cached local Python telemetry.
- Non-blocking keyring credential loader (`google-colab-cli`) with Google `userinfo.email` display and one-click browser-assisted OAuth dialog.
- Live Colab backend polling (`/tun/m/ccu-info` and `/tun/m/assignments`) for Compute Unit balance, hourly burn rate (`CU/hr`), estimated remaining hours, and active runtime shape (`Standard` / `High-RAM`).
- Read-only Jupyter `/api/kernels` inspection plus on-demand cached `nvidia-smi` / `/proc/meminfo` / disk probe via `ColabRuntime`.
- Full `EN / 中文` toggle across both desktop pill and IDE side-pane, plus generated `.ico` assets for desktop shortcuts.
