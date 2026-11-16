<div align="center">

<img src="docs/assets/banner.svg" alt="COLAB-HUD Banner" width="100%" />

<p>
  <strong>Echtzeit-Monitor für GPU/TPU-Modell, Compute-Units-Guthaben und stündliche Verbrauchsrate in Google Colab</strong>
</p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square" alt="License: MIT" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3b82f6?style=flat-square" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Node.js-22%2B%20sidecar_sdk-06b6d4?style=flat-square" alt="Node.js 22+ sidecar_sdk" />
  <img src="https://img.shields.io/badge/Auth-google--colab--cli%20Keyring-f9ab00?style=flat-square" alt="google-colab-cli Keyring" />
  <img src="https://img.shields.io/badge/UI-EN%20%2F%20%E4%B8%AD%E6%96%87-6366f1?style=flat-square" alt="EN / 中文" />
  <img src="https://img.shields.io/badge/Docs-8%20Languages-ec4899?style=flat-square" alt="8 Languages" />
</p>

<p>
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <strong>Deutsch</strong> ·
  <a href="README.ru.md">Русский</a>
</p>

<p>
  <a href="#overview">Überblick</a> ·
  <a href="#quick-start">Schnellstart</a> ·
  <a href="#data-sources">Datenquellen</a> ·
  <a href="CHANGELOG.md">Änderungsprotokoll</a>
</p>

</div>

---

<div align="center">
  <img src="docs/assets/hud-showcase.svg" alt="COLAB-HUD Vorschau" width="100%" />
</div>

---

## <a id="overview"></a>Überblick

**COLAB-HUD** ist ein schlankes schwebendes Desktop-HUD, CLI-Tool und Antigravity-2.0-Seitenleisten-Plugin für Google Colab. Es nutzt die vorhandenen OAuth2-Anmeldedaten von `google-colab-cli` im System-Schlüsselbund ohne blockierende `stdin`-Abfragen, um aktive GPU/TPU/CPU-Zuweisungen, den Stundenverbrauch (`CU/hr`), das Restguthaben, die geschätzte Restlaufzeit und die verbundene E-Mail-Adresse anzuzeigen.

### Hauptfunktionen

- **CU-Guthaben, Stundensatz & Kontoprüfung**: Fragt `/tun/m/ccu-info` und `/tun/m/assignments` ab und zeigt die zwischengespeicherte Google-E-Mail (`userinfo.email`), um Konto-Verwechslungen sofort zu erkennen.
- **Bedarfsgesteuerte `nvidia-smi`-Abfrage**: Liest Beschleuniger (`T4`/`L4`/`G4`/`A100`/`H100`/TPU/CPU) und Profil (`Standard`/`High-RAM`) direkt aus, prüft `/api/kernels` schreibgeschützt und erfasst bei **Probe GPU** oder `--probe` genaues GPU-Modell, VRAM, RAM, vCPU und Festplattenbelegung.
- **Unterbrechungsfreie OAuth-Hilfe**: Öffnet die Google-Anmeldung automatisch im Standardbrowser mit einem kompakten Code-Eingabedialog.

---

## <a id="quick-start"></a>Schnellstart

```bash
uv tool install git+https://github.com/googlecolab/google-colab-cli.git
```

### 1. Antigravity 2.0 Seitenleisten-Plugin

```bash
python plugin/install_plugin.py
python plugin/install_plugin.py --uninstall
```

### 2. Desktop-Pill & CLI

```bash
python -m desktop.cli                 # Schwebendes HUD starten
python -m desktop.cli --cli           # Einmalige Terminal-Ausgabe
python -m desktop.cli --json          # Strukturierte JSON-Ausgabe
python -m desktop.cli --probe --force # GPU / VRAM / RAM direkt abfragen
python -m desktop.cli --watch         # Laufende Aktualisierung
```

Unter Windows einfach `desktop/launch.bat` oder `desktop/launch.pyw` starten.

---

## <a id="data-sources"></a>Datenquellen

| Quelle | Endpunkt / Schnittstelle | Abgerufene Daten |
| :--- | :--- | :--- |
| Colab Session API | `GET /tun/m/ccu-info` | CU-Guthaben, Stundenrate, aktive Zuweisungen |
| Colab Assignments API | `GET /tun/m/assignments` | Beschleuniger, VM-Form und Proxy-Informationen |
| Runtime Proxy | `GET {proxy_url}/api/kernels` | Kernel-Anzahl und Status (`idle` / `busy` / `none`) |
| Runtime Probe | `ColabRuntime.execute_code(...)` | `nvidia-smi` GPU-Name, VRAM, RAM, vCPU und Speicherplatz |
| Google OAuth2 | `GET /oauth2/v2/userinfo` | Verbundene Google-Konto-E-Mail |

---

## Lizenz

Veröffentlicht unter der [MIT License](LICENSE).
