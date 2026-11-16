import { createHash } from 'node:crypto';
import { execFile, spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { delimiter, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { Response, SidecarApp } from 'sidecar_sdk';

const execFileAsync = promisify(execFile);
const __dirname = dirname(fileURLToPath(import.meta.url));

const CACHE_TTL_MS = 5000;
let cachedSnap = null;
let cachedEtag = '';
let lastFetchMs = 0;
let inFlightSnap = null;

function resolvePythonBin(gui = false) {
  const exe = process.platform === 'win32' ? (gui ? 'pythonw.exe' : 'python.exe') : 'python';
  const uvPy = join(homedir(), 'AppData', 'Roaming', 'uv', 'tools', 'google-colab-cli', 'Scripts', exe);
  if (existsSync(uvPy)) return uvPy;
  return process.platform === 'win32' ? (gui ? 'pythonw' : 'python') : 'python3';
}

function resolvePyRoot() {
  const bundled = join(__dirname, 'py');
  if (existsSync(join(bundled, 'desktop', 'cli.py'))) return bundled;
  return resolve(__dirname, '..', '..', '..');
}

async function runCliJson(args, timeoutMs = 20000) {
  const py = resolvePythonBin(false);
  const pyRoot = resolvePyRoot();
  const existingPath = process.env.PYTHONPATH || '';
  const pythonPath = existingPath ? `${pyRoot}${delimiter}${existingPath}` : pyRoot;

  const { stdout } = await execFileAsync(py, ['-m', 'desktop.cli', ...args], {
    cwd: pyRoot,
    env: {
      ...process.env,
      PYTHONPATH: pythonPath,
      PYTHONIOENCODING: 'utf-8',
    },
    timeout: timeoutMs,
    windowsHide: true,
    maxBuffer: 1024 * 1024,
  });

  const text = (stdout || '').trim();
  if (!text) throw new Error('Empty telemetry output');
  return JSON.parse(text);
}

function computeEtag(snap) {
  const stable = {
    authenticated: snap.authenticated,
    auth_state: snap.auth_state,
    account_email: snap.account_email,
    balance_cu: snap.balance_cu,
    rate_cu_hr: snap.rate_cu_hr,
    assignments_count: snap.assignments_count,
    est_hours_left: snap.est_hours_left,
    runtimes: snap.runtimes,
    error: snap.error,
  };
  return createHash('sha1').update(JSON.stringify(stable)).digest('hex').slice(0, 12);
}

async function getSnapshot(force = false) {
  const now = Date.now();
  if (!force && cachedSnap && now - lastFetchMs < CACHE_TTL_MS) {
    return { snap: cachedSnap, etag: cachedEtag };
  }
  if (inFlightSnap) return inFlightSnap;

  inFlightSnap = (async () => {
    try {
      const snap = await runCliJson(['--json']);
      cachedSnap = snap;
      cachedEtag = computeEtag(snap);
      lastFetchMs = Date.now();
      return { snap: cachedSnap, etag: cachedEtag };
    } finally {
      inFlightSnap = null;
    }
  })();

  return inFlightSnap;
}

const app = new SidecarApp();

app.page('/', () => readFileSync(join(__dirname, 'index.html'), 'utf-8'));
app.page('/styles.css', () => new Response(readFileSync(join(__dirname, 'styles.css'), 'utf-8'), {
  contentType: 'text/css; charset=utf-8',
}));
app.page('/app.js', () => readFileSync(join(__dirname, 'app.js'), 'utf-8'));

app.api('/api/stats', async (data) => {
  const force = data?.force === '1' || data?.force === true;
  const { snap, etag } = await getSnapshot(force);
  if (!force && data?.etag && data.etag === etag) {
    return { unchanged: true, etag, serverTimeMs: Date.now() };
  }
  return { ...snap, unchanged: false, etag, serverTimeMs: Date.now() };
}, 'GET');

app.api('/api/refresh', async () => {
  const { snap, etag } = await getSnapshot(true);
  return { ...snap, unchanged: false, etag, serverTimeMs: Date.now() };
}, 'POST');

app.api('/api/probe', async (data) => {
  const args = ['--probe', '--force'];
  if (data?.endpoint) args.push('--endpoint', String(data.endpoint));
  const res = await runCliJson(args, 30000);
  const refreshed = await getSnapshot(true);
  return { probeResult: res, snapshot: { ...refreshed.snap, etag: refreshed.etag } };
}, 'POST');

app.api('/api/login', async (data) => {
  const flag = data?.switchAccount ? '--switch-account' : '--login';
  const res = await runCliJson([flag], 10000);
  cachedSnap = null;
  lastFetchMs = 0;
  return res;
}, 'POST');

app.api('/api/logout', async () => {
  const res = await runCliJson(['--logout'], 10000);
  const refreshed = await getSnapshot(true);
  return { logout: res, snapshot: { ...refreshed.snap, etag: refreshed.etag } };
}, 'POST');

app.api('/api/desktop-pill', () => {
  const pyRoot = resolvePyRoot();
  const launchPyw = join(pyRoot, 'desktop', 'launch.pyw');
  if (!existsSync(launchPyw)) {
    return { ok: false, error: 'launch.pyw not found' };
  }
  const pyw = resolvePythonBin(true);
  const child = spawn(pyw, [launchPyw], {
    cwd: pyRoot,
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  });
  child.unref();
  return { ok: true };
}, 'POST');

app.run();
