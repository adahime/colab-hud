<div align="center">

<img src="docs/assets/banner.svg" alt="COLAB-HUD バナー" width="100%" />

<p>
  <strong>Google Colab 向け GPU/TPU 詳細モデル・Compute Units 残高・時間単価リアルタイム監視 HUD</strong>
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
  <strong>日本語</strong> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.ru.md">Русский</a>
</p>

<p>
  <a href="#overview">概要</a> ·
  <a href="#quick-start">クイックスタート</a> ·
  <a href="#data-sources">データソース</a> ·
  <a href="CHANGELOG.md">変更履歴</a>
</p>

</div>

---

<div align="center">
  <img src="docs/assets/hud-showcase.svg" alt="COLAB-HUD プレビュー" width="100%" />
</div>

---

## <a id="overview"></a>概要

**COLAB-HUD** は、Google Colab 向けの軽量なデスクトップフローティングピル、CLI ツール、および Antigravity 2.0 サイドペインプラグインです。`google-colab-cli` が OS キーリングに保存した OAuth2 認証情報を標準入力待ちでブロックせずに再利用し、稼働中の GPU/TPU/CPU 構成、1 時間あたりの消費レート（`CU/hr`）、Compute Units 残高、推定残り稼働時間、接続中の Google アカウントメールアドレスをリアルタイムに表示します。

### 主な機能

- **CU 残高・時間単価・アカウント識別**：`/tun/m/ccu-info` と `/tun/m/assignments` を取得し、残高・時間消費レート・推定残り稼働時間・稼働 VM 数に加え、キャッシュした `userinfo.email` を表示してアカウント取り違えを防止します。
- **オンデマンド `nvidia-smi` 詳細プローブ**：割り当て情報からアクセラレータ（`T4`/`L4`/`G4`/`A100`/`H100`/TPU/CPU）とマシン形状（`Standard`/`High-RAM`）を即時取得し、Jupyter `/api/kernels` を読み取り専用で確認します。**Probe GPU** または `--probe` 実行時のみ、`nvidia-smi` による正確な GPU 型番・VRAM・GPU 使用率・RAM・vCPU・ディスク使用量を取得し、エンドポイント単位でキャッシュします。
- **非ブロッキング認証 & ブラウザ連携ダイアログ**：バックグラウンド更新中はプロンプト停止せず状態を返し、ログインやアカウント切替時にはブラウザで認証ページを自動起動します。
- **デスクトップピル・CLI・IDE サイドペイン**：展開時にタスクバーを避けて上方向へ自動補正する Tkinter ピル（`launch.bat` / `launch.pyw`）と、IDE テーマに自動追従する `sidecar_sdk` パネルを備えています。

---

## <a id="quick-start"></a>クイックスタート

### 前提条件

```bash
uv tool install git+https://github.com/googlecolab/google-colab-cli.git
```

### 1. Antigravity 2.0 サイドペインプラグイン

`~/.gemini/config/plugins/colab-hud` へインストールし、Antigravity の Plugins マネージャーで `colab-hud` を有効化します：

```bash
python plugin/install_plugin.py
# アンインストール
python plugin/install_plugin.py --uninstall
```

### 2. デスクトップフローティングピル & CLI

```bash
python -m desktop.cli                 # デスクトップピルを起動
python -m desktop.cli --cli           # 現在の状態を1回出力
python -m desktop.cli --json          # JSON スナップショット出力
python -m desktop.cli --probe --force # アクティブランタイムの詳細 GPU を計測
python -m desktop.cli --watch         # 定期ウォッチ出力
```

Windows では `desktop/launch.bat` または `desktop/launch.pyw` からコンソールウィンドウなしで起動できます。

---

## <a id="data-sources"></a>データソース

| ソース | エンドポイント / 手段 | 取得内容 |
| :--- | :--- | :--- |
| Colab Session API | `GET /tun/m/ccu-info` | CU 残高・時間消費レート・アクティブ割り当て数 |
| Colab Assignments API | `GET /tun/m/assignments` | 割り当て済みアクセラレータ・マシン形状・プロキシ情報 |
| Runtime Proxy | `GET {proxy_url}/api/kernels` | 既存カーネル数および状態（`idle` / `busy` / `none`） |
| Runtime Probe | `ColabRuntime.execute_code(...)` | `nvidia-smi` GPU 名・VRAM・GPU 使用率・RAM・vCPU・ディスク |
| Google OAuth2 | `GET /oauth2/v2/userinfo` | 接続中の Google アカウントメール |

---

## ライセンス

[MIT License](LICENSE) の下で公開されています。
