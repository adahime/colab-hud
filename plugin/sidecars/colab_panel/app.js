(() => {
  const POLL_MS = 6000;
  const $ = (id) => document.getElementById(id);

  const I18N = {
    zh: {
      langBtn: 'EN',
      pillBtn: '桌面胶囊',
      signIn: '授权登录',
      switchAcct: '切换账号',
      signOut: '退出授权',
      lblBalance: '当前点数余额',
      lblRate: '每小时消耗费率',
      lblRuntimes: '当前配置与精确硬件',
      probe: '探测精确显卡',
      probing: '探测中...',
      refresh: '刷新',
      badgeOk: '运行中',
      badgeIdle: '待机 (0 消耗)',
      badgeUnauth: '未授权',
      badgeErr: '异常',
      noAuthAcct: '尚未授权 Google Colab CLI，请点击右侧按钮完成一次登录',
      authedAcct: (email) => `已连接账号：${email || '已登录'}`,
      estHours: (h) => (h === null || h === undefined ? '待机无消耗' : `约可继续运行 ${h} 小时`),
      activeVms: (n) => `活跃实例：${n} 个`,
      noVms: '当前没有运行中的 Colab 实例（仅登录保持连接，每小时费率为 0）',
      needLoginBody: '请点击上方「授权登录」，在弹出的终端中打开 Google 授权链接并粘贴授权码即可同步数据。',
      unprobedHint: '点击右上角「探测精确显卡」读取 nvidia-smi 型号、显存、内存与磁盘详情',
      gpuExact: '精确显卡型号',
      vram: '显存占用',
      ram: '系统内存 / vCPU',
      disk: '实例磁盘',
      kernel: '内核状态',
      shape: '实例规格',
      updated: (t) => `最后更新 ${t}`,
      loginOpened: '已打开终端窗口，请按提示完成 Google 授权。',
      pillLaunched: '已启动 COLAB-HUD 桌面悬浮胶囊。',
      probeDone: '精确硬件信息探测完成。',
      probeFail: (e) => `探测失败：${e}`,
    },
    en: {
      langBtn: '中文',
      pillBtn: 'Desktop Pill',
      signIn: 'Sign In',
      switchAcct: 'Switch',
      signOut: 'Sign Out',
      lblBalance: 'CU Balance',
      lblRate: 'Hourly Burn Rate',
      lblRuntimes: 'Active Runtime & Hardware',
      probe: 'Probe GPU',
      probing: 'Probing...',
      refresh: 'Refresh',
      badgeOk: 'Active',
      badgeIdle: 'Idle (0/hr)',
      badgeUnauth: 'Not Signed In',
      badgeErr: 'Error',
      noAuthAcct: 'Google Colab CLI is not signed in yet',
      authedAcct: (email) => `Connected: ${email || 'Authorized'}`,
      estHours: (h) => (h === null || h === undefined ? 'No active burn' : `~${h}h remaining`),
      activeVms: (n) => `Active VMs: ${n}`,
      noVms: 'No active Colab VM running (0.00 CU/hr)',
      needLoginBody: 'Click Sign In above to open the official OAuth prompt in a terminal window.',
      unprobedHint: 'Click Probe GPU to inspect exact nvidia-smi model, VRAM, RAM, and disk.',
      gpuExact: 'GPU Model',
      vram: 'VRAM',
      ram: 'System RAM / CPU',
      disk: 'Disk Usage',
      kernel: 'Kernel',
      shape: 'Shape',
      updated: (t) => `Updated ${t}`,
      loginOpened: 'Terminal opened for official Google Colab OAuth sign-in.',
      pillLaunched: 'Launched COLAB-HUD desktop floating pill.',
      probeDone: 'Runtime hardware probed successfully.',
      probeFail: (e) => `Probe failed: ${e}`,
    },
  };

  const state = {
    lang: 'zh',
    etag: '',
    lastSnap: null,
    timer: null,
  };

  try {
    const savedLang = localStorage.getItem('colab_hud_lang');
    if (savedLang === 'en' || savedLang === 'zh') state.lang = savedLang;
  } catch { /* ignore */ }

  function tr() {
    return I18N[state.lang];
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function syncTheme() {
    const rootStyle = getComputedStyle(document.documentElement);
    const bg = rootStyle.getPropertyValue('--background').trim() || rootStyle.getPropertyValue('--vscode-editor-background').trim();
    const match = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (match) {
      const lum = (0.2126 * Number(match[1]) + 0.7152 * Number(match[2]) + 0.0722 * Number(match[3])) / 255;
      document.body.classList.toggle('theme-light', lum > 0.55);
    }
  }

  function showToast(msg) {
    const el = $('toast');
    el.textContent = msg;
    el.classList.remove('hidden');
    clearTimeout(el._hideTimer);
    el._hideTimer = setTimeout(() => el.classList.add('hidden'), 4000);
  }

  async function apiCall(path, method = 'GET', body = null) {
    const fetcher = window.sidecar?.fetch ? window.sidecar.fetch.bind(window.sidecar) : fetch;
    const opts = { method, headers: {} };
    if (body !== null && method !== 'GET') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetcher(path, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function applyStaticLabels() {
    const t = tr();
    $('lang-btn').textContent = t.langBtn;
    $('pill-btn').textContent = t.pillBtn;
    $('lbl-balance').textContent = t.lblBalance;
    $('lbl-rate').textContent = t.lblRate;
    $('lbl-runtimes').textContent = t.lblRuntimes;
    $('probe-btn').textContent = t.probe;
    $('refresh-btn').textContent = t.refresh;
    $('logout-btn').textContent = t.signOut;
  }

  function renderRuntimes(snap) {
    const t = tr();
    const list = $('runtime-list');
    if (!snap.authenticated) {
      list.innerHTML = `<div class="empty-card">${esc(t.needLoginBody)}</div>`;
      return;
    }

    const runtimes = snap.runtimes || [];
    if (!runtimes.length) {
      list.innerHTML = `<div class="empty-card">${esc(t.noVms)}</div>`;
      return;
    }

    list.innerHTML = runtimes.map((rt) => {
      const probe = rt.probe;
      const kState = rt.kernel_state || 'none';
      let bodyHtml = `<div class="runtime-meta" style="margin-top:6px;">${esc(t.unprobedHint)}</div>`;
      if (probe) {
        const vramTxt = probe.vram_total_mb
          ? `${((probe.vram_used_mb || 0) / 1024).toFixed(1)} / ${(probe.vram_total_mb / 1024).toFixed(1)} GB${probe.gpu_util_pct !== null && probe.gpu_util_pct !== undefined ? ` (${probe.gpu_util_pct.toFixed(0)}%)` : ''}`
          : '--';
        const ramTxt = probe.ram_total_gb
          ? `${probe.ram_used_gb ?? 0} / ${probe.ram_total_gb} GB · ${probe.cpu_count || '?'}c`
          : '--';
        const diskTxt = probe.disk_total_gb
          ? `${probe.disk_used_gb ?? 0} / ${probe.disk_total_gb} GB`
          : '--';
        const gpuTitle = probe.gpu_name
          ? `${probe.gpu_name}${probe.gpu_count > 1 ? ` x${probe.gpu_count}` : ''}`
          : rt.summary_label;

        bodyHtml = `
          <div class="specs-grid">
            <div class="spec-item"><div class="spec-k">${esc(t.gpuExact)}</div><div class="spec-v">${esc(gpuTitle)}</div></div>
            <div class="spec-item"><div class="spec-k">${esc(t.vram)}</div><div class="spec-v">${esc(vramTxt)}</div></div>
            <div class="spec-item"><div class="spec-k">${esc(t.ram)}</div><div class="spec-v">${esc(ramTxt)}</div></div>
            <div class="spec-item"><div class="spec-k">${esc(t.disk)}</div><div class="spec-v">${esc(diskTxt)}</div></div>
          </div>
        `;
      }

      return `
        <div class="runtime-card">
          <div class="runtime-top">
            <span class="runtime-model">${esc(rt.summary_label)}</span>
            <span class="runtime-meta">${esc(t.kernel)}: ${esc(kState)} · ${esc(rt.machine_shape || '')}</span>
          </div>
          ${bodyHtml}
        </div>
      `;
    }).join('');
  }

  function render(snap) {
    const t = tr();
    state.lastSnap = snap;
    const badge = $('status-badge');
    const statusText = $('status-text');
    const hasVms = (snap.runtimes || []).length > 0;

    if (!snap.authenticated) {
      const isWarn = snap.auth_state === 'unauthenticated' || snap.auth_state === 'expired';
      badge.className = isWarn ? 'badge warn' : 'badge bad';
      statusText.textContent = isWarn ? t.badgeUnauth : t.badgeErr;
      $('account-text').textContent = snap.error || t.noAuthAcct;
      $('login-btn').textContent = t.signIn;
      $('logout-btn').classList.add('hidden');
      $('val-balance').textContent = '--';
      $('val-rate').textContent = '--';
      $('sub-est').textContent = '--';
      $('sub-vms').textContent = '--';
      $('probe-btn').disabled = true;
    } else {
      badge.className = hasVms ? 'badge live' : 'badge ok';
      statusText.textContent = hasVms ? t.badgeOk : t.badgeIdle;
      $('account-text').textContent = t.authedAcct(snap.account_email);
      $('login-btn').textContent = t.switchAcct;
      $('logout-btn').classList.remove('hidden');

      const bal = snap.balance_cu;
      const rate = snap.rate_cu_hr;
      $('val-balance').textContent = bal !== null && bal !== undefined ? `${Number(bal).toFixed(2)} CU` : '--';
      $('val-balance').style.color = bal > 20 ? 'var(--hud-ok)' : (bal > 5 ? 'var(--hud-warn)' : 'var(--hud-bad)');
      $('val-rate').textContent = rate !== null && rate !== undefined ? `${Number(rate).toFixed(2)} /hr` : '--';
      $('val-rate').style.color = rate > 0 ? 'var(--hud-live)' : 'var(--hud-muted)';
      $('sub-est').textContent = t.estHours(snap.est_hours_left);
      $('sub-vms').textContent = t.activeVms(snap.assignments_count ?? (snap.runtimes || []).length);
      $('probe-btn').disabled = !hasVms;
    }

    renderRuntimes(snap);

    const ts = snap.timestamp_ms ? new Date(snap.timestamp_ms).toLocaleTimeString() : '--';
    $('updated-line').textContent = t.updated(ts);
  }

  async function poll() {
    try {
      const qs = state.etag ? `?etag=${encodeURIComponent(state.etag)}` : '';
      const snap = await apiCall(`/api/stats${qs}`);
      if (snap.etag) state.etag = snap.etag;
      if (!snap.unchanged) render(snap);
    } catch (err) {
      $('status-badge').className = 'badge bad';
      $('status-text').textContent = String(err.message || err);
    } finally {
      state.timer = setTimeout(poll, POLL_MS);
    }
  }

  $('lang-btn').addEventListener('click', () => {
    state.lang = state.lang === 'zh' ? 'en' : 'zh';
    try { localStorage.setItem('colab_hud_lang', state.lang); } catch { /* ignore */ }
    applyStaticLabels();
    if (state.lastSnap) render(state.lastSnap);
  });

  $('refresh-btn').addEventListener('click', async () => {
    try {
      const snap = await apiCall('/api/refresh', 'POST', {});
      if (snap.etag) state.etag = snap.etag;
      render(snap);
    } catch (err) {
      showToast(String(err.message || err));
    }
  });

  $('probe-btn').addEventListener('click', async () => {
    const btn = $('probe-btn');
    btn.disabled = true;
    btn.textContent = tr().probing;
    try {
      const res = await apiCall('/api/probe', 'POST', {});
      if (res.snapshot) {
        if (res.snapshot.etag) state.etag = res.snapshot.etag;
        render(res.snapshot);
      }
      if (res.probeResult?.ok) showToast(tr().probeDone);
      else showToast(tr().probeFail(res.probeResult?.error || 'Unknown'));
    } catch (err) {
      showToast(tr().probeFail(err.message || err));
    } finally {
      btn.textContent = tr().probe;
      btn.disabled = !(state.lastSnap?.runtimes?.length);
    }
  });

  $('login-btn').addEventListener('click', async () => {
    try {
      const switchAccount = Boolean(state.lastSnap?.authenticated);
      await apiCall('/api/login', 'POST', { switchAccount });
      showToast(tr().loginOpened);
    } catch (err) {
      showToast(String(err.message || err));
    }
  });

  $('logout-btn').addEventListener('click', async () => {
    try {
      const res = await apiCall('/api/logout', 'POST', {});
      if (res.snapshot) {
        state.etag = res.snapshot.etag || '';
        render(res.snapshot);
      }
    } catch (err) {
      showToast(String(err.message || err));
    }
  });

  $('pill-btn').addEventListener('click', async () => {
    try {
      await apiCall('/api/desktop-pill', 'POST', {});
      showToast(tr().pillLaunched);
    } catch (err) {
      showToast(String(err.message || err));
    }
  });

  syncTheme();
  applyStaticLabels();
  poll();
})();
