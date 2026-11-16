"""Floating desktop HUD pill for Google Colab hardware, burn rate, and CU balance."""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox
from typing import Any, Dict, List, Optional

from desktop.telemetry import (
    ColabTelemetryStore,
    begin_oauth_flow,
    clear_saved_auth,
    complete_oauth_flow,
    probe_runtime_hardware,
)


PALETTE = {
    "BG_PILL": "#18181b",
    "BG_CARD": "#27272a",
    "BG_BTN": "#303036",
    "BORDER": "#3f3f46",
    "FG_MAIN": "#f4f4f5",
    "FG_MUTED": "#a1a1aa",
    "FG_DIM": "#71717a",
    "OK": "#22c55e",
    "WARN": "#eab308",
    "CRIT": "#ef4444",
    "ACCENT": "#3b82f6",
    "LIVE": "#06b6d4",
}

UI_FONT = "Microsoft YaHei UI"
MONO_FONT = "Consolas"

LANG_PACK = {
    "zh": {
        "title": "COLAB-HUD",
        "no_cli": "未找到 colab-cli",
        "need_login": "COLAB-HUD · 未登录 (右键授权)",
        "expired": "COLAB-HUD · 授权过期 (右键重登)",
        "api_err": "COLAB-HUD · 连接异常",
        "connecting": "COLAB-HUD · 读取中...",
        "idle_pill": "待机 · {bal} CU",
        "active_pill": "{hw} · {rate}/h · {bal} CU",
        "acct": "账号",
        "acct_unknown": "已授权 (未知邮箱)",
        "acct_none": "尚未授权 Google Colab 账号",
        "balance": "当前点数余额",
        "rate": "每小时消耗费率",
        "est": "预计剩余可用",
        "vms": "活跃实例数",
        "hw_title": "当前配置与硬件型号",
        "no_vm": "当前没有运行中的 Colab 实例（仅登录待机，0 消耗）",
        "probe_pending": "未探测精确型号 — 点击下方「探测显卡」获取",
        "probing": "正在通过代理探测硬件...",
        "updated": "更新于 {ts}",
        "btn_refresh": "刷新",
        "btn_probe": "探测显卡",
        "btn_login": "授权/切号",
        "menu_expand": "展开 / 收起详情",
        "menu_refresh": "立即刷新",
        "menu_probe": "探测精确显卡 (nvidia-smi)",
        "menu_login": "授权登录 Colab",
        "menu_switch": "切换 Google 账号",
        "menu_top": "置顶显示",
        "menu_pin": "锁定位置",
        "menu_lang": "切换语言 (中文 / EN)",
        "menu_alpha": "透明度",
        "menu_interval": "刷新间隔",
        "menu_exit": "退出",
        "probe_err_title": "探测失败",
    },
    "en": {
        "title": "COLAB-HUD",
        "no_cli": "colab-cli missing",
        "need_login": "COLAB-HUD · Sign in (Right-click)",
        "expired": "COLAB-HUD · Token expired",
        "api_err": "COLAB-HUD · API error",
        "connecting": "COLAB-HUD · Loading...",
        "idle_pill": "IDLE · {bal} CU",
        "active_pill": "{hw} · {rate}/h · {bal} CU",
        "acct": "Account",
        "acct_unknown": "Signed in",
        "acct_none": "No Colab OAuth token saved",
        "balance": "CU Balance",
        "rate": "Burn Rate",
        "est": "Est. Left",
        "vms": "Active VMs",
        "hw_title": "Active Runtime Hardware",
        "no_vm": "No running Colab runtime (idle, 0 CU/hr)",
        "probe_pending": "Exact model unprobed — click Probe GPU below",
        "probing": "Probing runtime hardware...",
        "updated": "Updated {ts}",
        "btn_refresh": "Refresh",
        "btn_probe": "Probe GPU",
        "btn_login": "Sign In / Switch",
        "menu_expand": "Expand / Collapse",
        "menu_refresh": "Refresh Now",
        "menu_probe": "Probe Exact GPU (nvidia-smi)",
        "menu_login": "Sign In to Colab",
        "menu_switch": "Switch Google Account",
        "menu_top": "Always on Top",
        "menu_pin": "Pin Position",
        "menu_lang": "Language (EN / 中文)",
        "menu_alpha": "Opacity",
        "menu_interval": "Refresh Interval",
        "menu_exit": "Exit",
        "probe_err_title": "Probe Failed",
    },
}


def _fmt_cu(val: Optional[float]) -> str:
    if val is None:
        return "--"
    if abs(val) >= 100:
        return f"{val:.1f}"
    return f"{val:.2f}"


def _fmt_hours(hours: Optional[float], lang: str) -> str:
    if hours is None:
        return "--"
    if hours >= 100:
        return f"{hours:.0f}h" if lang == "en" else f"{hours:.0f} 小时"
    return f"{hours:.1f}h" if lang == "en" else f"{hours:.1f} 小时"


def _compact_gpu_tag(rt: Dict[str, Any]) -> str:
    probe = rt.get("probe") or {}
    gpu_name = probe.get("gpu_name")
    vram_mb = probe.get("vram_total_mb")
    if gpu_name:
        short = (
            gpu_name.replace("NVIDIA ", "")
            .replace("Tesla ", "")
            .replace("-SXM4-", " ")
            .replace("-PCIE-", " ")
        )
        if vram_mb and "GB" not in short.upper():
            gb = round(float(vram_mb) / 1024)
            return f"{short.split()[0]} {gb}G"
        return short[:16]
    return str(rt.get("summary_label") or rt.get("accelerator") or "VM")


def _json_sig(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


class ColabHudPill:
    """Frameless floating pill + expandable breakdown card for Google Colab."""

    def __init__(
        self,
        store: ColabTelemetryStore,
        lang: str = "zh",
        alpha: float = 0.94,
        refresh_ms: int = 1000,
    ) -> None:
        self.store = store
        self.lang = lang if lang in LANG_PACK else "zh"
        self.alpha = max(0.45, min(1.0, float(alpha)))
        self.refresh_ms = max(400, int(refresh_ms))

        self.expanded = False
        self.always_on_top = True
        self.pinned = False
        self.probing = False
        self._drag_origin: Optional[tuple[int, int]] = None
        self._pre_expand_y: Optional[int] = None
        self._last_snap: Optional[Dict[str, Any]] = None
        self._last_rendered_key: Optional[tuple[Any, ...]] = None
        self._last_data_sig: Optional[str] = None
        self._last_runtimes_sig: Optional[str] = None
        self._last_dot_color: Optional[str] = None

        self.root = tk.Tk()
        self.root.title("COLAB-HUD")
        self.root.overrideredirect(True)
        self.root.configure(bg=PALETTE["BORDER"])
        self.root.attributes("-topmost", self.always_on_top)
        self.root.attributes("-alpha", self.alpha)

        self._build_ui()
        self._position_default()
        self._bind_events()

    def _tr(self, key: str) -> str:
        return LANG_PACK[self.lang][key]

    def _build_ui(self) -> None:
        self.outer = tk.Frame(self.root, bg=PALETTE["BG_PILL"], padx=10, pady=6)
        self.outer.pack(fill="both", expand=True, padx=1, pady=1)

        # Compact single-line pill row
        self.pill_row = tk.Frame(self.outer, bg=PALETTE["BG_PILL"])
        self.pill_row.pack(fill="x")

        self.dot_canvas = tk.Canvas(
            self.pill_row, width=10, height=10, bg=PALETTE["BG_PILL"], highlightthickness=0
        )
        self.dot_id = self.dot_canvas.create_oval(1, 1, 9, 9, fill=PALETTE["FG_DIM"], outline="")
        self.dot_canvas.pack(side="left", padx=(0, 7))

        self.pill_label = tk.Label(
            self.pill_row,
            text=self._tr("connecting"),
            bg=PALETTE["BG_PILL"],
            fg=PALETTE["FG_MAIN"],
            font=(MONO_FONT, 10, "bold"),
            cursor="fleur",
        )
        self.pill_label.pack(side="left")

        self.chevron = tk.Label(
            self.pill_row,
            text="▾",
            bg=PALETTE["BG_PILL"],
            fg=PALETTE["FG_MUTED"],
            font=(UI_FONT, 10),
            cursor="hand2",
            padx=6,
        )
        self.chevron.pack(side="right")

        # Expandable breakdown card
        self.card = tk.Frame(self.outer, bg=PALETTE["BG_CARD"], padx=10, pady=8)

        self.acct_label = tk.Label(
            self.card,
            text="",
            bg=PALETTE["BG_CARD"],
            fg=PALETTE["FG_MUTED"],
            font=(UI_FONT, 8),
            anchor="w",
        )
        self.acct_label.pack(fill="x", pady=(0, 6))

        self.metrics_grid = tk.Frame(self.card, bg=PALETTE["BG_CARD"])
        self.metrics_grid.pack(fill="x", pady=(0, 6))
        self.metrics_grid.columnconfigure(0, weight=1)
        self.metrics_grid.columnconfigure(1, weight=1)

        self.val_balance = self._make_metric_cell(self.metrics_grid, 0, 0)
        self.val_rate = self._make_metric_cell(self.metrics_grid, 0, 1)
        self.val_est = self._make_metric_cell(self.metrics_grid, 1, 0)
        self.val_vms = self._make_metric_cell(self.metrics_grid, 1, 1)

        tk.Frame(self.card, bg=PALETTE["BORDER"], height=1).pack(fill="x", pady=5)

        self.hw_header = tk.Label(
            self.card,
            text=self._tr("hw_title"),
            bg=PALETTE["BG_CARD"],
            fg=PALETTE["FG_DIM"],
            font=(UI_FONT, 8, "bold"),
            anchor="w",
        )
        self.hw_header.pack(fill="x")

        self.hw_body = tk.Frame(self.card, bg=PALETTE["BG_CARD"])
        self.hw_body.pack(fill="x", pady=(3, 6))

        # Footer action bar
        self.footer = tk.Frame(self.card, bg=PALETTE["BG_CARD"])
        self.footer.pack(fill="x")

        self.updated_label = tk.Label(
            self.footer,
            text="",
            bg=PALETTE["BG_CARD"],
            fg=PALETTE["FG_DIM"],
            font=(UI_FONT, 8),
        )
        self.updated_label.pack(side="left")

        self.btn_login = self._make_chip_button(self.footer, "", self._on_login_click)
        self.btn_login.pack(side="right", padx=(4, 0))

        self.btn_probe = self._make_chip_button(self.footer, "", self._on_probe_click)
        self.btn_probe.pack(side="right", padx=(4, 0))

        self.btn_refresh = self._make_chip_button(self.footer, "", self._on_refresh_click)
        self.btn_refresh.pack(side="right", padx=(4, 0))

        self._apply_button_labels()

    def _make_metric_cell(self, parent: tk.Frame, row: int, col: int) -> Dict[str, tk.Label]:
        box = tk.Frame(parent, bg=PALETTE["BG_PILL"], padx=8, pady=5)
        box.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 4, 0), pady=2)
        title = tk.Label(box, text="", bg=PALETTE["BG_PILL"], fg=PALETTE["FG_DIM"], font=(UI_FONT, 8), anchor="w")
        title.pack(fill="x")
        val = tk.Label(box, text="--", bg=PALETTE["BG_PILL"], fg=PALETTE["FG_MAIN"], font=(MONO_FONT, 10, "bold"), anchor="w")
        val.pack(fill="x")
        return {"title": title, "value": val}

    def _make_chip_button(self, parent: tk.Frame, text: str, command: Any) -> tk.Label:
        btn = tk.Label(
            parent,
            text=text,
            bg=PALETTE["BG_BTN"],
            fg=PALETTE["FG_MAIN"],
            font=(UI_FONT, 8),
            padx=7,
            pady=2,
            cursor="hand2",
        )
        btn.bind("<Button-1>", lambda _e: command())
        return btn

    def _apply_button_labels(self) -> None:
        self.val_balance["title"].config(text=self._tr("balance"))
        self.val_rate["title"].config(text=self._tr("rate"))
        self.val_est["title"].config(text=self._tr("est"))
        self.val_vms["title"].config(text=self._tr("vms"))
        self.hw_header.config(text=self._tr("hw_title"))
        self.btn_refresh.config(text=self._tr("btn_refresh"))
        self.btn_probe.config(text=self._tr("btn_probe"))
        self.btn_login.config(text=self._tr("btn_login"))

    def _position_default(self) -> None:
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        # Sit just above bottom-right so it pairs cleanly above AGY-HUD.
        w = max(260, self.root.winfo_reqwidth())
        x = max(20, sw - w - 24)
        y = max(20, sh - 160)
        self.root.geometry(f"+{x}+{y}")

    def _clamp_vertical_for_card(self) -> None:
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        cur_x = min(max(12, self.root.winfo_x()), max(12, sw - w - 12))
        max_y = max(12, sh - h - 52)
        if self.expanded:
            cur_y = self.root.winfo_y()
            if cur_y > max_y:
                self._pre_expand_y = cur_y
                cur_y = max_y
            self.root.geometry(f"+{cur_x}+{cur_y}")
        else:
            restored_y = self._pre_expand_y if self._pre_expand_y is not None else self.root.winfo_y()
            self._pre_expand_y = None
            cur_y = min(max(12, restored_y), max_y)
            self.root.geometry(f"+{cur_x}+{cur_y}")

    def _bind_events(self) -> None:
        self.root.bind("<Button-3>", self._show_context_menu)
        drag_targets = [self.outer, self.pill_row, self.dot_canvas, self.pill_label]
        for widget in drag_targets:
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<Double-Button-1>", lambda _e: self.toggle_expand())

        self.chevron.bind("<Button-1>", lambda _e: self.toggle_expand())

    def _start_drag(self, event: tk.Event) -> None:
        if self.pinned:
            return
        self._drag_origin = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _on_drag(self, event: tk.Event) -> None:
        if self.pinned or not self._drag_origin:
            return
        dx, dy = self._drag_origin
        self.root.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

    def toggle_expand(self) -> None:
        self.expanded = not self.expanded
        if self.expanded:
            self.card.pack(fill="both", expand=True, pady=(6, 0))
            self.chevron.config(text="▴")
        else:
            self.card.pack_forget()
            self.chevron.config(text="▾")
        self._clamp_vertical_for_card()

    def _toggle_lang(self) -> None:
        self.lang = "en" if self.lang == "zh" else "zh"
        self._apply_button_labels()
        if self._last_snap is not None:
            self._render_snapshot(self._last_snap)

    def _set_alpha(self, val: float) -> None:
        self.alpha = val
        self.root.attributes("-alpha", val)

    def _set_interval(self, seconds: float) -> None:
        self.store.interval_sec = seconds
        self.store.trigger_refresh()

    def _toggle_topmost(self) -> None:
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)

    def _toggle_pin(self) -> None:
        self.pinned = not self.pinned

    def _on_refresh_click(self) -> None:
        threading.Thread(target=self.store.refresh_now, daemon=True).start()

    def _on_login_click(self, switch_account: bool = False) -> None:
        if not switch_account and self._last_snap and self._last_snap.get("authenticated"):
            switch_account = True
        self._open_login_dialog(switch_account=switch_account)

    def _open_login_dialog(self, switch_account: bool = False) -> None:
        try:
            flow, auth_url = begin_oauth_flow(switch_account=switch_account)
        except Exception as exc:
            messagebox.showerror("COLAB-HUD", str(exc))
            return

        webbrowser.open(auth_url)

        win = tk.Toplevel(self.root)
        win.title("COLAB-HUD 授权登录" if self.lang == "zh" else "COLAB-HUD Sign In")
        win.configure(bg=PALETTE["BG_PILL"])
        win.attributes("-topmost", True)
        win.resizable(False, False)

        wrap = tk.Frame(win, bg=PALETTE["BG_PILL"], padx=14, pady=12)
        wrap.pack(fill="both", expand=True)

        guide = (
            "1. 浏览器已自动打开 Google 授权页面，选好你要用的账号点 允许。\n"
            "2. 页面跳转到 Google Cloud SDK 后，点复制按钮拿到授权码 (一般以 4/ 开头)。\n"
            "3. 粘到下方输入框并点 确认授权："
            if self.lang == "zh"
            else "1. Your browser opened Google sign-in — approve access.\n"
            "2. Copy the authorization code shown on the Google landing page.\n"
            "3. Paste the code below and click Confirm:"
        )
        tk.Label(
            wrap,
            text=guide,
            bg=PALETTE["BG_PILL"],
            fg=PALETTE["FG_MAIN"],
            font=(UI_FONT, 9),
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        code_var = tk.StringVar()
        entry = tk.Entry(
            wrap,
            textvariable=code_var,
            bg=PALETTE["BG_CARD"],
            fg=PALETTE["FG_MAIN"],
            insertbackground=PALETTE["FG_MAIN"],
            relief="flat",
            font=(MONO_FONT, 10),
            width=46,
        )
        entry.pack(fill="x", ipady=5, pady=(0, 8))
        entry.focus_set()

        status_lbl = tk.Label(
            wrap,
            text="",
            bg=PALETTE["BG_PILL"],
            fg=PALETTE["WARN"],
            font=(UI_FONT, 8),
            anchor="w",
        )
        status_lbl.pack(fill="x", pady=(0, 6))

        btn_row = tk.Frame(wrap, bg=PALETTE["BG_PILL"])
        btn_row.pack(fill="x")

        def copy_url() -> None:
            win.clipboard_clear()
            win.clipboard_append(auth_url)
            status_lbl.config(
                text="已复制授权链接，可粘贴到任意浏览器打开" if self.lang == "zh" else "Auth URL copied to clipboard",
                fg=PALETTE["LIVE"],
            )

        def submit(_event: Any = None) -> None:
            raw = code_var.get().strip()
            if not raw:
                status_lbl.config(
                    text="请先粘贴授权码" if self.lang == "zh" else "Paste authorization code first",
                    fg=PALETTE["WARN"],
                )
                return
            submit_btn.config(state="disabled")
            status_lbl.config(
                text="正在验证并保存授权..." if self.lang == "zh" else "Verifying authorization code...",
                fg=PALETTE["LIVE"],
            )

            def worker() -> None:
                res = complete_oauth_flow(flow, raw)
                self.root.after(0, lambda: on_done(res))

            threading.Thread(target=worker, daemon=True).start()

        def on_done(res: Dict[str, Any]) -> None:
            if not win.winfo_exists():
                return
            if res.get("ok"):
                win.destroy()
                threading.Thread(target=self.store.refresh_now, daemon=True).start()
            else:
                submit_btn.config(state="normal")
                status_lbl.config(text=str(res.get("error") or "OAuth failed"), fg=PALETTE["CRIT"])

        tk.Button(
            btn_row,
            text="重新打开网页" if self.lang == "zh" else "Open URL",
            command=lambda: webbrowser.open(auth_url),
            bg=PALETTE["BG_BTN"],
            fg=PALETTE["FG_MAIN"],
            relief="flat",
            padx=8,
            pady=4,
            font=(UI_FONT, 8),
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_row,
            text="复制链接" if self.lang == "zh" else "Copy URL",
            command=copy_url,
            bg=PALETTE["BG_BTN"],
            fg=PALETTE["FG_MAIN"],
            relief="flat",
            padx=8,
            pady=4,
            font=(UI_FONT, 8),
            cursor="hand2",
        ).pack(side="left", padx=(6, 0))

        submit_btn = tk.Button(
            btn_row,
            text="确认授权" if self.lang == "zh" else "Confirm",
            command=submit,
            bg=PALETTE["ACCENT"],
            fg=PALETTE["FG_MAIN"],
            relief="flat",
            padx=12,
            pady=4,
            font=(UI_FONT, 8, "bold"),
            cursor="hand2",
        )
        submit_btn.pack(side="right")
        entry.bind("<Return>", submit)

    def _on_probe_click(self) -> None:
        if self.probing:
            return
        snap = self._last_snap
        if not snap or not snap.get("runtimes"):
            return
        self.probing = True
        self.btn_probe.config(fg=PALETTE["LIVE"])

        def worker() -> None:
            res = probe_runtime_hardware(force=True)
            self.probing = False
            self.root.after(0, lambda: self._finish_probe(res))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_probe(self, res: Dict[str, Any]) -> None:
        self.btn_probe.config(fg=PALETTE["FG_MAIN"])
        if res.get("ok"):
            threading.Thread(target=self.store.refresh_now, daemon=True).start()
        elif res.get("error"):
            messagebox.showwarning(self._tr("probe_err_title"), str(res["error"]))

    def _show_context_menu(self, event: tk.Event) -> None:
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=PALETTE["BG_CARD"],
            fg=PALETTE["FG_MAIN"],
            activebackground=PALETTE["ACCENT"],
            activeforeground=PALETTE["FG_MAIN"],
        )
        has_vm = bool(self._last_snap and self._last_snap.get("runtimes"))
        is_authed = bool(self._last_snap and self._last_snap.get("authenticated"))

        menu.add_command(label=self._tr("menu_expand"), command=self.toggle_expand)
        menu.add_command(label=self._tr("menu_refresh"), command=self._on_refresh_click)
        menu.add_command(
            label=self._tr("menu_probe"),
            command=self._on_probe_click,
            state="normal" if has_vm else "disabled",
        )
        menu.add_separator()
        menu.add_command(
            label=self._tr("menu_login"),
            command=lambda: self._open_login_dialog(switch_account=False),
        )
        if is_authed:
            menu.add_command(
                label=self._tr("menu_switch"),
                command=lambda: self._open_login_dialog(switch_account=True),
            )
            menu.add_command(
                label="清除本地授权 / Sign Out" if self.lang == "zh" else "Sign Out",
                command=lambda: (clear_saved_auth(), self._on_refresh_click()),
            )
        menu.add_separator()

        top_var = tk.BooleanVar(value=self.always_on_top)
        pin_var = tk.BooleanVar(value=self.pinned)
        menu.add_checkbutton(label=self._tr("menu_top"), variable=top_var, command=self._toggle_topmost)
        menu.add_checkbutton(label=self._tr("menu_pin"), variable=pin_var, command=self._toggle_pin)
        menu.add_command(label=self._tr("menu_lang"), command=self._toggle_lang)

        alpha_menu = tk.Menu(menu, tearoff=0, bg=PALETTE["BG_CARD"], fg=PALETTE["FG_MAIN"])
        for pct in (100, 94, 85, 70):
            alpha_menu.add_command(label=f"{pct}%", command=lambda v=pct / 100.0: self._set_alpha(v))
        menu.add_cascade(label=self._tr("menu_alpha"), menu=alpha_menu)

        int_menu = tk.Menu(menu, tearoff=0, bg=PALETTE["BG_CARD"], fg=PALETTE["FG_MAIN"])
        for sec in (5, 10, 30, 60):
            int_menu.add_command(label=f"{sec}s", command=lambda s=sec: self._set_interval(float(s)))
        menu.add_cascade(label=self._tr("menu_interval"), menu=int_menu)

        menu.add_separator()
        menu.add_command(label=self._tr("menu_exit"), command=self.close)
        menu.tk_popup(event.x_root, event.y_root)

    def _render_runtimes(self, runtimes: List[Dict[str, Any]]) -> None:
        sig = _json_sig({"lang": self.lang, "runtimes": runtimes})
        if sig == self._last_runtimes_sig:
            return
        self._last_runtimes_sig = sig

        for child in self.hw_body.winfo_children():
            child.destroy()

        if not runtimes:
            tk.Label(
                self.hw_body,
                text=self._tr("no_vm"),
                bg=PALETTE["BG_CARD"],
                fg=PALETTE["FG_MUTED"],
                font=(UI_FONT, 8),
                wraplength=290,
                justify="left",
                anchor="w",
            ).pack(fill="x", pady=2)
            if self.expanded:
                self._clamp_vertical_for_card()
            return

        for rt in runtimes:
            box = tk.Frame(self.hw_body, bg=PALETTE["BG_PILL"], padx=8, pady=5)
            box.pack(fill="x", pady=2)

            k_state = rt.get("kernel_state")
            badge_str = f"[{k_state}]" if k_state and k_state != "none" else ""
            title = f"{rt.get('summary_label', 'Runtime')} {badge_str}".strip()
            tk.Label(
                box,
                text=title,
                bg=PALETTE["BG_PILL"],
                fg=PALETTE["LIVE"],
                font=(MONO_FONT, 9, "bold"),
                anchor="w",
            ).pack(fill="x")

            probe = rt.get("probe")
            if probe:
                details: List[str] = []
                if probe.get("gpu_name"):
                    cnt = probe.get("gpu_count") or 1
                    gpu_str = f"{probe['gpu_name']} (x{cnt})" if cnt > 1 else probe["gpu_name"]
                    details.append(gpu_str)
                if probe.get("vram_total_mb"):
                    used_gb = (probe.get("vram_used_mb") or 0) / 1024
                    tot_gb = probe["vram_total_mb"] / 1024
                    util = probe.get("gpu_util_pct")
                    util_s = f" · GPU {util:.0f}%" if util is not None else ""
                    details.append(f"VRAM {used_gb:.1f}/{tot_gb:.1f} GB{util_s}")
                if probe.get("ram_total_gb"):
                    details.append(
                        f"RAM {probe.get('ram_used_gb', 0):.1f}/{probe['ram_total_gb']:.1f} GB"
                        f" · {probe.get('cpu_count') or '?'} vCPU"
                    )
                if probe.get("disk_total_gb"):
                    details.append(f"Disk {probe.get('disk_used_gb', 0):.1f}/{probe['disk_total_gb']:.1f} GB")
                detail_text = "\n".join(details)
                fg_color = PALETTE["FG_MAIN"]
            else:
                detail_text = self._tr("probe_pending")
                fg_color = PALETTE["FG_DIM"]

            tk.Label(
                box,
                text=detail_text,
                bg=PALETTE["BG_PILL"],
                fg=fg_color,
                font=(UI_FONT, 8),
                justify="left",
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

        if self.expanded:
            self._clamp_vertical_for_card()

    def _set_dot_color(self, color: str) -> None:
        if color != self._last_dot_color:
            self._last_dot_color = color
            self.dot_canvas.itemconfig(self.dot_id, fill=color)

    def _render_snapshot(self, snap: Dict[str, Any]) -> None:
        self._last_snap = snap
        self._last_rendered_key = (snap.get("timestamp_ms"), self.lang)

        ts_ms = snap.get("timestamp_ms")
        if ts_ms:
            clock = time.strftime("%H:%M:%S", time.localtime(ts_ms / 1000))
            self.updated_label.config(text=self._tr("updated").format(ts=clock))

        data_sig = _json_sig({
            "lang": self.lang,
            "authenticated": snap.get("authenticated"),
            "auth_state": snap.get("auth_state"),
            "account_email": snap.get("account_email"),
            "balance_cu": snap.get("balance_cu"),
            "rate_cu_hr": snap.get("rate_cu_hr"),
            "est_hours_left": snap.get("est_hours_left"),
            "assignments_count": snap.get("assignments_count"),
            "runtimes": snap.get("runtimes"),
            "error": snap.get("error"),
        })
        if data_sig == self._last_data_sig:
            return
        self._last_data_sig = data_sig

        auth_state = snap.get("auth_state")
        runtimes = snap.get("runtimes") or []
        bal = snap.get("balance_cu")
        rate = snap.get("rate_cu_hr") or 0.0

        if not snap.get("authenticated"):
            dot_color = PALETTE["WARN"] if auth_state in ("unauthenticated", "expired") else PALETTE["CRIT"]
            msg_key = "expired" if auth_state == "expired" else ("need_login" if auth_state == "unauthenticated" else "api_err")
            self._set_dot_color(dot_color)
            self.pill_label.config(text=self._tr(msg_key), fg=PALETTE["FG_MAIN"])
            self.acct_label.config(text=snap.get("error") or self._tr("acct_none"))
            self.val_balance["value"].config(text="--", fg=PALETTE["FG_DIM"])
            self.val_rate["value"].config(text="--", fg=PALETTE["FG_DIM"])
            self.val_est["value"].config(text="--", fg=PALETTE["FG_DIM"])
            self.val_vms["value"].config(text="0", fg=PALETTE["FG_DIM"])
            self.btn_probe.config(fg=PALETTE["FG_DIM"])
            self._render_runtimes([])
        else:
            email = snap.get("account_email") or self._tr("acct_unknown")
            self.acct_label.config(text=f"{self._tr('acct')}: {email}")

            if runtimes:
                hw_tag = _compact_gpu_tag(runtimes[0])
                if len(runtimes) > 1:
                    hw_tag = f"{hw_tag}+{len(runtimes) - 1}"
                pill_text = self._tr("active_pill").format(hw=hw_tag, rate=_fmt_cu(rate), bal=_fmt_cu(bal))
                if bal is not None and bal <= 5:
                    dot_color = PALETTE["CRIT"]
                elif rate >= 10:
                    dot_color = PALETTE["WARN"]
                else:
                    dot_color = PALETTE["LIVE"]
            else:
                dot_color = PALETTE["OK"]
                pill_text = self._tr("idle_pill").format(bal=_fmt_cu(bal))

            self._set_dot_color(dot_color)
            self.pill_label.config(text=pill_text, fg=PALETTE["FG_MAIN"])

            bal_color = PALETTE["OK"] if (bal or 0) > 20 else (PALETTE["WARN"] if (bal or 0) > 5 else PALETTE["CRIT"])
            rate_color = PALETTE["LIVE"] if rate > 0 else PALETTE["FG_MUTED"]
            self.val_balance["value"].config(text=f"{_fmt_cu(bal)} CU", fg=bal_color)
            self.val_rate["value"].config(text=f"{_fmt_cu(rate)} /hr", fg=rate_color)
            self.val_est["value"].config(text=_fmt_hours(snap.get("est_hours_left"), self.lang), fg=PALETTE["FG_MAIN"])
            self.val_vms["value"].config(text=str(snap.get("assignments_count", len(runtimes))), fg=PALETTE["FG_MAIN"])
            self.btn_probe.config(fg=PALETTE["FG_MAIN"] if runtimes else PALETTE["FG_DIM"])
            self._render_runtimes(runtimes)

    def _poll_ui(self) -> None:
        snap = self.store.get_snapshot()
        if snap is not None:
            key = (snap.get("timestamp_ms"), self.lang)
            if key != self._last_rendered_key:
                self._render_snapshot(snap)
        self.root.after(self.refresh_ms, self._poll_ui)

    def run(self) -> None:
        self.store.start()
        self.root.after(150, self._poll_ui)
        self.root.mainloop()

    def close(self) -> None:
        self.store.stop()
        self.root.destroy()
