# COLAB-HUD Plugin

Antigravity 2.0 auxiliary side-pane plugin showing real-time Google Colab telemetry:
- Connected Google account email
- Compute Unit (CU) balance & estimated remaining runtime hours
- Hourly burn rate (`CU/hr`) & active assignment count
- Active GPU / TPU / CPU hardware tier + on-demand `nvidia-smi` exact model, VRAM, RAM, and disk probe
- One-click Desktop Pill launch (`Launch Pill`)

## Installation

```powershell
python plugin/install_plugin.py
```

Then enable `colab-hud` in the Antigravity Plugins Manager.
