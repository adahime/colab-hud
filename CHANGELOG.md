# Changelog

## v0.1.0 — Initial Public Release

- Floating Windows desktop HUD pill (`desktop/`) with CLI (`--cli`, `--watch`, `--json`, `--probe`, `--presets`, `--start`, `--stop`, `--stop-all`) and silent `launch.pyw` / `launch.bat` launchers.
- Direct in-pill and side-pane runtime allocation (`POST /tun/m/assign`) covering all 13 official hardware combinations (`CPU`/`T4`/`G4`/`A100`/`H100` Standard & High-RAM, single-shape `L4`, `TPU v5e-1`, `TPU v6e-1`), browser notebook URL jump, and single/all runtime shutdown (`/tun/m/unassign`).
- Native Antigravity 2.0 auxiliary side-pane UI plugin (`plugin/`) backed by Node.js `sidecar_sdk` and cached local Python telemetry.
- Non-blocking keyring credential loader (`google-colab-cli`) with Google `userinfo.email` display and one-click browser-assisted OAuth dialog.
- Live Colab backend polling (`/tun/m/ccu-info` and `/tun/m/assignments`) for Compute Unit balance, hourly burn rate (`CU/hr`), estimated remaining hours, and active runtime shape (`Standard` / `High-RAM`).
- Read-only Jupyter `/api/kernels` inspection plus on-demand cached `nvidia-smi` / `/proc/meminfo` / disk probe via `ColabRuntime`.
- Full `EN / 中文` toggle across both desktop pill and IDE side-pane, plus generated `.ico` assets for desktop shortcuts.
