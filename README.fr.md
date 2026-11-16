<div align="center">

<img src="docs/assets/banner.svg" alt="Bannière COLAB-HUD" width="100%" />

<p>
  <strong>Moniteur temps réel du modèle GPU/TPU, du solde de Compute Units et du taux de consommation horaire pour Google Colab</strong>
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
  <strong>Français</strong> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.ru.md">Русский</a>
</p>

<p>
  <a href="#overview">Présentation</a> ·
  <a href="#quick-start">Démarrage rapide</a> ·
  <a href="#data-sources">Sources de données</a> ·
  <a href="CHANGELOG.md">Historique</a>
</p>

</div>

---

<div align="center">
  <img src="docs/assets/hud-showcase.svg" alt="Aperçu COLAB-HUD" width="100%" />
</div>

---

## <a id="overview"></a>Présentation

**COLAB-HUD** est un widget flottant de bureau, un outil CLI et une extension de panneau latéral Antigravity 2.0 pour Google Colab. Il réutilise vos identifiants OAuth2 `google-colab-cli` stockés dans le trousseau système sans jamais bloquer l'interrogation sur `stdin`, pour afficher le matériel GPU/TPU/CPU actif, le taux de consommation (`CU/hr`), le solde restant, l'autonomie estimée et l'adresse Google connectée.

### Fonctionnalités clés

- **Solde CU, débit horaire et compte connecté** : Interroge `/tun/m/ccu-info` et `/tun/m/assignments`, et met en cache `userinfo.email` afin d'éviter toute confusion entre comptes Google.
- **Sonde matérielle `nvidia-smi` à la demande** : Affiche l'accélérateur (`T4`/`L4`/`G4`/`A100`/`H100`/TPU/CPU) et le profil (`Standard` / `High-RAM`) immédiatement, vérifie `/api/kernels` en lecture seule et récupère le modèle GPU exact, la VRAM, la RAM, les vCPU et l'espace disque lorsque vous lancez **Probe GPU** ou `--probe`.
- **Authentification fluide sans blocage** : Ouvre automatiquement la page de consentement Google dans votre navigateur avec une fenêtre dédiée pour coller le code d'autorisation.

---

## <a id="quick-start"></a>Démarrage rapide

```bash
uv tool install git+https://github.com/googlecolab/google-colab-cli.git
```

### 1. Plugin Antigravity 2.0

```bash
python plugin/install_plugin.py
python plugin/install_plugin.py --uninstall
```

### 2. Widget bureau & CLI

```bash
python -m desktop.cli                 # Lancer la pilule flottante
python -m desktop.cli --cli           # Résumé terminal unique
python -m desktop.cli --json          # Sortie JSON structurée
python -m desktop.cli --probe --force # Sonder GPU / VRAM / RAM exacts
python -m desktop.cli --watch         # Surveillance continue
```

Sous Windows, double-cliquez sur `desktop/launch.bat` ou `desktop/launch.pyw`.

---

## <a id="data-sources"></a>Sources de données

| Source | Endpoint / Interface | Données récupérées |
| :--- | :--- | :--- |
| Colab Session API | `GET /tun/m/ccu-info` | Solde CU, consommation horaire, instances actives |
| Colab Assignments API | `GET /tun/m/assignments` | Accélérateur, profil mémoire et jeton proxy |
| Runtime Proxy | `GET {proxy_url}/api/kernels` | Nombre et état des noyaux (`idle` / `busy` / `none`) |
| Runtime Probe | `ColabRuntime.execute_code(...)` | Modèle GPU `nvidia-smi`, VRAM, RAM, vCPU et disque |
| Google OAuth2 | `GET /oauth2/v2/userinfo` | Email du compte autorisé |

---

## Licence

Publié sous licence [MIT License](LICENSE).
