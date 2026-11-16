<div align="center">

<img src="docs/assets/banner.svg" alt="Баннер COLAB-HUD" width="100%" />

<p>
  <strong>Мониторинг модели GPU/TPU, баланса Compute Units и почасового расхода для Google Colab</strong>
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
  <a href="README.de.md">Deutsch</a> ·
  <strong>Русский</strong>
</p>

<p>
  <a href="#overview">Обзор</a> ·
  <a href="#quick-start">Быстрый старт</a> ·
  <a href="#data-sources">Источники данных</a> ·
  <a href="CHANGELOG.md">История изменений</a>
</p>

</div>

---

<div align="center">
  <img src="docs/assets/hud-showcase.svg" alt="Предпросмотр COLAB-HUD" width="100%" />
</div>

---

## <a id="overview"></a>Обзор

**COLAB-HUD** — это лёгкий плавающий виджет для рабочего стола, CLI-утилита и плагин боковой панели Antigravity 2.0 для Google Colab. Он безопасно использует сохранённые учётные данные `google-colab-cli` из системного хранилища ключей без блокировки опроса в `stdin` и отображает активный ускоритель GPU/TPU/CPU, почасовой расход (`CU/hr`), остаток Compute Units, расчётное время работы и привязанный Google-аккаунт.

### Основные возможности

- **Баланс CU, скорость расхода и контроль аккаунта**: Опрашивает `/tun/m/ccu-info` и `/tun/m/assignments`, кэширует `userinfo.email` и сразу показывает, какой аккаунт подключён.
- **Зонд `nvidia-smi` по требованию**: Мгновенно получает тип ускорителя (`T4`/`L4`/`G4`/`A100`/`H100`/TPU/CPU) и профиль (`Standard`/`High-RAM`), в режиме только чтения проверяет `/api/kernels`, а по кнопке **Probe GPU** или флагу `--probe` снимает точную модель GPU, VRAM, RAM, vCPU и диск с кэшированием по endpoint.
- **Удобный вход через браузер**: Автоматически открывает страницу OAuth Google в браузере вместе с окном для вставки кода подтверждения.

---

## <a id="quick-start"></a>Быстрый старт

```bash
uv tool install git+https://github.com/googlecolab/google-colab-cli.git
```

### 1. Плагин боковой панели Antigravity 2.0

```bash
python plugin/install_plugin.py
python plugin/install_plugin.py --uninstall
```

### 2. Плавающий виджет и CLI

```bash
python -m desktop.cli                 # Запуск плавающего виджета
python -m desktop.cli --cli           # Однократный вывод в терминал
python -m desktop.cli --json          # Структурированный вывод JSON
python -m desktop.cli --probe --force # Точный замер GPU / VRAM / RAM
python -m desktop.cli --watch         # Непрерывный мониторинг
```

В Windows можно запускать без окна консоли через `desktop/launch.bat` или `desktop/launch.pyw`.

---

## <a id="data-sources"></a>Источники данных

| Источник | Эндпоинт / Метод | Получаемые данные |
| :--- | :--- | :--- |
| Colab Session API | `GET /tun/m/ccu-info` | Баланс CU, расход в час, число активных инстансов |
| Colab Assignments API | `GET /tun/m/assignments` | Тип ускорителя, конфигурация памяти и прокси-токен |
| Runtime Proxy | `GET {proxy_url}/api/kernels` | Количество ядер и их статус (`idle` / `busy` / `none`) |
| Runtime Probe | `ColabRuntime.execute_code(...)` | Модель GPU по `nvidia-smi`, VRAM, RAM, vCPU и диск |
| Google OAuth2 | `GET /oauth2/v2/userinfo` | Email авторизованного аккаунта |

---

## Лицензия

Распространяется по лицензии [MIT License](LICENSE).
