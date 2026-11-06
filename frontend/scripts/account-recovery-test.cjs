// Offline behavior checks; no network or external services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '../src');
const modules = new Map();
function load(file) {
  if (modules.has(file)) return modules.get(file);
  const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 } }).outputText;
  const module = { exports: {} };
  const req = id => {
    if (!id.startsWith('@/') && !id.startsWith('.')) return require(id);
    const target = id.startsWith('@/') ? path.join(root, id.slice(2)) : path.resolve(path.dirname(file), id);
    return load(fs.existsSync(target + '.ts') ? target + '.ts' : target + '.tsx');
  };
  new Function('require', 'module', 'exports', js)(req, module, module.exports);
  modules.set(file, module.exports);
  return module.exports;
}
(async () => {
  global.window = {};
  let stored = 'device-valid';
  global.localStorage = { getItem: () => stored, setItem: (_, value) => { stored = value; } };
  const account = load(path.join(root, 'lib/ziwei/account.ts'));
  const api = load(path.join(root, 'lib/ziwei/api.ts')).ziweiApi;
  const billing = load(path.join(root, 'lib/ziwei/billing.ts'));
  assert.equal(account.recoveryEnabled, false);
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url, init });
    assert.equal(init.credentials, 'include');
    assert.equal(init.headers['X-Recovery-Client'], '1');
    assert.ok(!url.includes('device-valid'));
    return { ok: true, json: async () => [], headers: { get: () => null } };
  };
  for (const value of ['device-valid', 'device with spaces', 'dévice', 'bad\nheader', '中文', 'x'.repeat(65), '\u0000', '']) {
    stored = value;
    const safe = account.recoveryDeviceId();
    assert.ok(safe.length <= 64 && /^[\x20-\x7e\x80-\xff]*$/.test(safe));
    await account.accountRequest('/session');
    await api.listProfiles();
    await billing.createBillingAdapter('/mock', account.recoveryDeviceId, global.fetch).balance();
    assert.equal(calls.at(-1).init.headers['X-Device-Id'], safe);
    if (value) assert.equal(stored, value, 'do not overwrite old identity');
  }
  global.localStorage = { getItem: () => { throw new Error('storage disabled'); } };
  await account.accountRequest('/challenges', { email: 'test@example.test', purpose: 'recover' });
  assert.equal(calls.at(-1).init.headers['X-Device-Id'], '');
  assert.equal(calls.at(-1).init.method, 'POST');
  for (const status of [400, 401, 409, 429, 503]) {
    global.fetch = async () => ({ ok: false, status });
    await assert.rejects(account.accountRequest('/verify', { code: 'fake', challenge_id: 'fake' }));
  }
  console.log('PASS: recovery defaults, cookies/custom headers, corrupt/missing/unavailable storage, no identity overwrite/URL credentials, API error handling');
})().catch(error => { console.error(error); process.exit(1); });
