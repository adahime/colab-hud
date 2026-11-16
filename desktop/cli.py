"""CLI and desktop launcher entrypoint for COLAB-HUD."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Dict, Optional

from desktop.telemetry import (
    ColabTelemetryStore,
    begin_oauth_flow,
    clear_saved_auth,
    complete_oauth_flow,
    fetch_snapshot,
    launch_interactive_login,
    probe_runtime_hardware,
)


def format_cli_table(snap: Dict[str, Any]) -> str:
    """Format a compact terminal summary for ``--cli`` / ``--watch`` modes."""
    lines = ["=== COLAB-HUD ==="]
    if not snap.get("authenticated"):
        lines.append(f"Status : {snap.get('auth_state')} ({snap.get('error') or 'Not signed in'})")
        lines.append("Action : Run `colab usage` or `colab-hud --login` to authorize.")
        return "\n".join(lines)

    email = snap.get("account_email") or "Signed in"
    lines.append(f"Account: {email}")
    lines.append(f"Balance: {snap.get('balance_cu')} CU")
    lines.append(f"Rate   : {snap.get('rate_cu_hr')} CU/hr")
    if snap.get("est_hours_left") is not None:
        lines.append(f"EstLeft: {snap['est_hours_left']} h")
    lines.append(f"Active : {snap.get('assignments_count', 0)} runtime(s)")

    for rt in snap.get("runtimes") or []:
        lines.append(f"  - [{rt.get('endpoint')}] {rt.get('summary_label')} (kernel={rt.get('kernel_state')})")
        probe = rt.get("probe")
        if probe:
            lines.append(
                f"    GPU={probe.get('gpu_name')} VRAM={probe.get('vram_used_mb')}/{probe.get('vram_total_mb')}MB "
                f"RAM={probe.get('ram_used_gb')}/{probe.get('ram_total_gb')}GB"
            )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="colab-hud", description="Google Colab HUD telemetry & desktop pill")
    parser.add_argument("--json", action="store_true", help="Print JSON telemetry snapshot and exit")
    parser.add_argument("--cli", action="store_true", help="Print terminal summary and exit")
    parser.add_argument("--watch", action="store_true", help="Continuously refresh terminal output")
    parser.add_argument("--probe", action="store_true", help="Probe exact GPU/VRAM/RAM via runtime proxy and exit")
    parser.add_argument("--endpoint", type=str, default=None, help="Target runtime endpoint for --probe")
    parser.add_argument("--force", action="store_true", help="Force temporary kernel probe even if kernel is busy")
    parser.add_argument("--login", action="store_true", help="Launch interactive Colab OAuth sign-in terminal")
    parser.add_argument("--oauth-prompt", action="store_true", help="Run browser-assisted OAuth prompt in current terminal")
    parser.add_argument("--switch-account", action="store_true", help="Clear saved OAuth token and launch sign-in")
    parser.add_argument("--logout", action="store_true", help="Clear saved OAuth token and caches")
    parser.add_argument("--interval", type=float, default=10.0, help="Background poll interval in seconds")
    parser.add_argument("--refresh-ms", type=int, default=1000, help="Desktop pill UI redraw interval in ms")
    parser.add_argument("--alpha", type=float, default=0.94, help="Desktop pill window opacity (0.45-1.0)")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="Initial UI language")
    parser.add_argument("--no-kernel-check", action="store_true", help="Skip /api/kernels check for fastest --json")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.logout:
        result = clear_saved_auth()
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.oauth_prompt:
        import webbrowser

        try:
            flow, auth_url = begin_oauth_flow(switch_account=args.switch_account)
        except Exception as exc:
            print(f"OAuth init failed: {exc}", file=sys.stderr)
            return 1

        print("\n=== COLAB-HUD Google OAuth 授权 ===")
        print("1. 正在尝试为你自动打开浏览器进入 Google 授权页；如未弹出，请复制下方链接打开：")
        print(f"\n   {auth_url}\n")
        webbrowser.open(auth_url)
        print("2. 在网页里选好你要用的 Google 账号并点击 允许。")
        print("3. Google 跳转后会显示一个带复制按钮的页面，把那串授权码 (Authorization code，一般以 4/ 开头) 复制过来。")
        try:
            code = input("\n请在此粘贴授权码后按回车: ").strip()
        except EOFError:
            return 1
        res = complete_oauth_flow(flow, code)
        if res.get("ok"):
            print("授权成功！现在关闭窗口即可，COLAB-HUD 会自动同步余额与配置。")
            if sys.stdin and sys.stdin.isatty():
                try:
                    input("按 Enter 键关闭...")
                except EOFError:
                    pass
            return 0
        print(f"授权失败: {res.get('error')}", file=sys.stderr)
        if sys.stdin and sys.stdin.isatty():
            try:
                input("按 Enter 键关闭...")
            except EOFError:
                pass
        return 1

    if args.login or args.switch_account:
        result = launch_interactive_login(switch_account=args.switch_account)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    if args.probe:
        result = probe_runtime_hardware(endpoint=args.endpoint, force=args.force)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1

    if args.json:
        from desktop.telemetry import FetchOptions

        snap = fetch_snapshot(FetchOptions(check_kernels=not args.no_kernel_check))
        print(json.dumps(snap, ensure_ascii=False))
        return 0

    if args.watch:
        try:
            while True:
                snap = fetch_snapshot()
                print("\033[2J\033[H" + format_cli_table(snap), flush=True)
                time.sleep(max(3.0, args.interval))
        except KeyboardInterrupt:
            return 0

    if args.cli:
        snap = fetch_snapshot()
        print(format_cli_table(snap))
        return 0

    from desktop.hud_pill import ColabHudPill

    store = ColabTelemetryStore(interval_sec=args.interval)
    hud = ColabHudPill(store=store, lang=args.lang, alpha=args.alpha, refresh_ms=args.refresh_ms)
    hud.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
