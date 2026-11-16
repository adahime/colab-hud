<div align="center">

<img src="docs/assets/banner.svg" alt="COLAB-HUD 배너" width="100%" />

<p>
  <strong>Google Colab 용 실시간 GPU/TPU 상세 모델, Compute Units 잔액 및 시간당 소모율 모니터</strong>
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
  <strong>한국어</strong> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.ru.md">Русский</a>
</p>

<p>
  <a href="#overview">개요</a> ·
  <a href="#quick-start">빠른 시작</a> ·
  <a href="#data-sources">데이터 소스</a> ·
  <a href="CHANGELOG.md">변경 로그</a>
</p>

</div>

---

<div align="center">
  <img src="docs/assets/hud-showcase.svg" alt="COLAB-HUD 미리보기" width="100%" />
</div>

---

## <a id="overview"></a>개요

**COLAB-HUD**는 Google Colab용 경량 데스크톱 플로팅 필, CLI 도구 및 Antigravity 2.0 사이드 패널 플러그인입니다. OS 키링에 저장된 `google-colab-cli` OAuth2 자격 증명을 백그라운드 폴링 중 `stdin` 대기 없이 안전하게 사용하여 활성 GPU/TPU/CPU 사양, 시간당 Compute Units 소모율(`CU/hr`), 남은 잔액, 예상 잔여 시간 및 연결된 Google 계정 이메일을 표시합니다.

### 주요 기능

- **CU 잔액, 소모율 및 연결 계정 확인**: `/tun/m/ccu-info`와 `/tun/m/assignments`를 폴링하여 잔액, 시간당 소모율, 예상 사용 가능 시간, 활성 인스턴스 수 및 캐시된 `userinfo.email`을 표시합니다.
- **요청 시 `nvidia-smi` 정밀 프로브**: 백엔드 할당 정보에서 가속기(`T4`/`L4`/`G4`/`A100`/`H100`/TPU/CPU)와 머신 사양(`Standard`/`High-RAM`)을 즉시 읽고 Jupyter `/api/kernels`를 읽기 전용으로 확인합니다. **Probe GPU** 또는 `--probe` 실행 시에만 정확한 GPU 모델명, VRAM, RAM, vCPU 및 디스크 사용량을 수집해 엔드포인트별로 캐시합니다.
- **논블로킹 키링 인증 및 브라우저 OAuth 창**: 미인증 상태에서도 폴링이 멈추지 않으며, 로그인/계정 전환 시 브라우저 인증 페이지를 자동으로 엽니다.
- **데스크톱 플로팅 필, CLI 및 IDE 사이드 패널**: 확장 시 작업 표시줄 위로 자동 배치되는 Tkinter 창(`launch.bat` / `launch.pyw`)과 라이트/다크 테마를 자동 동기화하는 `sidecar_sdk` 패널을 제공합니다.

---

## <a id="quick-start"></a>빠른 시작

```bash
uv tool install git+https://github.com/googlecolab/google-colab-cli.git
```

### 1. Antigravity 2.0 사이드 패널 플러그인

```bash
python plugin/install_plugin.py
# 제거
python plugin/install_plugin.py --uninstall
```

### 2. 데스크톱 플로팅 필 & CLI

```bash
python -m desktop.cli                 # 플로팅 필 실행
python -m desktop.cli --cli           # 터미널 요약 출력
python -m desktop.cli --json          # JSON 스냅샷 출력
python -m desktop.cli --probe --force # 활성 런타임 GPU/RAM 프로브
python -m desktop.cli --watch         # 실시간 모니터링
```

Windows에서는 `desktop/launch.bat` 또는 `desktop/launch.pyw`를 더블클릭해 콘솔 창 없이 실행할 수 있습니다.

---

## <a id="data-sources"></a>데이터 소스

| 소스 | 엔드포인트 / 인터페이스 | 수집 데이터 |
| :--- | :--- | :--- |
| Colab Session API | `GET /tun/m/ccu-info` | CU 잔액, 시간당 소모율, 활성 할당 수 |
| Colab Assignments API | `GET /tun/m/assignments` | 할당된 가속기, 머신 형태(`Standard`/`High-RAM`), 프록시 토큰 |
| Runtime Proxy | `GET {proxy_url}/api/kernels` | 실행 중인 커널 수 및 상태(`idle`/`busy`/`none`) |
| Runtime Probe | `ColabRuntime.execute_code(...)` | `nvidia-smi` GPU 모델명, VRAM, GPU 사용률, RAM, vCPU, 디스크 |
| Google OAuth2 | `GET /oauth2/v2/userinfo` | 현재 인증된 Google 계정 이메일 |

---

## 라이선스

[MIT License](LICENSE)에 따라 배포됩니다.
