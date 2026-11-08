const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '../src');
function load(file) {
  const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 } }).outputText;
  const module = { exports: {} };
  const req = id => {
    if (!id.startsWith('@/') && !id.startsWith('.')) return require(id);
    const target = id.startsWith('@/') ? path.join(root, id.slice(2)) : path.resolve(path.dirname(file), id);
    return load(fs.existsSync(target + '.ts') ? target + '.ts' : target + '.tsx');
  };
  new Function('require', 'module', 'exports', js)(req, module, module.exports);
  return module.exports;
}
(async () => {
 process.env.NEXT_PUBLIC_PRODUCT_MODE = 'paid';
 const a = load(path.join(root, 'lib/product/account.ts'));
 const calls = [];
 global.fetch = async (url, init) => { calls.push({url, init}); return { ok:true, json:async()=>({authenticated:false, enabled:true}) }; };
 assert.deepEqual(await a.accountRequest('/session'), {authenticated:false, enabled:true});
 await a.accountRequest('/challenges', {email:'test@example.test'});
 for (const {init} of calls) { assert.equal(init.credentials,'include'); assert.equal(init.headers['X-Paid-Client'],'1'); assert.equal(init.headers['X-Device-Id'],undefined); assert.equal(init.cache,'no-store'); }
 assert.equal(calls[0].init.method,'GET'); assert.equal(calls[1].init.method,'POST');
 for (const status of [400,401,403,429,503,500]) {
   global.fetch=async()=>({ok:false,status});
   await assert.rejects(a.accountRequest('/verify',{}), Error);
 }
 global.window={dispatchEvent:()=>{}};
 global.sessionStorage={length:1,key:()=>{throw Error('blocked')}};
 assert.doesNotThrow(a.clearPaidRetryState);
 const q = load(path.join(root,'lib/qian/api.ts'));
 global.fetch=async(url,init)=>{assert.equal(init.credentials,'include');assert.equal(init.headers['X-Paid-Client'],'1');assert.equal(init.headers['X-Device-Id'],undefined);return {ok:false,status:401};};
 await assert.rejects(q.qianApi.listReadings(),e=>e.status===401);
 const z = load(path.join(root,'lib/ziwei/api.ts'));
 global.fetch=async(url,init)=>{assert.equal(init.credentials,'include');assert.equal(init.headers['X-Paid-Client'],'1');assert.equal(init.headers['X-Device-Id'],undefined);return {ok:true,json:async()=>[]};};
 assert.deepEqual(await z.ziweiApi.listProfiles(),[]);
 const b=load(path.join(root,'lib/ziwei/billing.ts'));
 await b.createBillingAdapter('/mock',()=>'',async(url,init)=>{assert.equal(init.credentials,'include');assert.equal(init.headers['X-Paid-Client'],'1');assert.equal(init.headers['X-Device-Id'],undefined);return {ok:true,json:async()=>({balance:0})};}).balance();
 console.log('PASS paid accounts: cookie-only transport, failures, storage independence, feature headers');
})().catch(error=>{console.error(error);process.exit(1)});
