const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '../src');
const modules = new Map();
function load(file) {
  if (modules.has(file)) return modules.get(file).exports;
  const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 } }).outputText;
  const module = { exports: {} };
  modules.set(file,module);
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
 await b.createBillingAdapter('/mock',()=>'',async(url,init)=>{assert.equal(init.credentials,'include');assert.equal(init.headers['X-Paid-Client'],'1');assert.equal(init.headers['X-Device-Id'],undefined);return {ok:true,json:async()=>({balance:0,mode:"test",packs:[]})};}).balance();
 const order={order_id:1,status:'pending',pack:'small',credits:10,amount_cents:100,currency:'usd',created_at:'2026-01-01T00:00:00Z'};
 for(const body of [{mode:'live',orders:[order]},{mode:'test',orders:[{...order,status:'refunded'}]},{mode:'test',orders:[{...order,order_id:-1}]},{mode:'test',orders:null}]) {
   const adapter=b.createBillingAdapter('/mock',()=>'',async()=>({ok:true,json:async()=>body}));
   await assert.rejects(adapter.orders());
 }
 const history=b.createBillingAdapter('/mock',()=>'',async(url,init)=>{assert.equal(url,'/mock/billing/orders?limit=10');assert.equal(init.credentials,'include');return {ok:true,json:async()=>({mode:'test',orders:[order]})};});
 assert.deepEqual(await history.orders(),[order]);
 const narration=load(path.join(root,'lib/ziwei/narration.ts'));
 let speech=0, invalidated=0, ttsCalls=0;
 narration.BrowserNarration.prototype.speak=async()=>{speech++;};
 global.window={dispatchEvent:event=>{if(event.type==='paid-session-invalid')invalidated++;}};
 global.fetch=async(url,init)=>{ttsCalls++;assert.equal(init.credentials,'include');assert.equal(init.headers['X-Paid-Client'],'1');assert.equal(init.headers['X-Device-Id'],undefined);assert.equal(init.cache,'no-store');return {ok:false,status:503};};
 const voice=new narration.CloudNarration();
 await voice.speak('测试语音');await voice.speak('再次测试');
 assert.equal(ttsCalls,1);assert.equal(speech,2);
 global.fetch=async()=>({ok:false,status:401});
 await new narration.CloudNarration().speak('不能在会话过期后继续播放');
 assert.equal(invalidated,1);assert.equal(speech,2);
 const stored=new Map([['paid-session-account','1'],['ziwei-question:3','private old question'],['ziwei-selected-profile','3'],['ziwei-request:checkout','old'],['unrelated','keep']]);
 global.sessionStorage={get length(){return stored.size;},key:i=>[...stored.keys()][i],getItem:key=>stored.get(key)??null,setItem:(key,value)=>stored.set(key,value),removeItem:key=>stored.delete(key)};
 const retries=load(path.join(root,'lib/ziwei/retry-keys.ts')).retryKeys;
 retries.get('checkout:old',{pack:'p10'});
 a.syncPaidAccountSession(1);
 assert.equal(stored.get('ziwei-question:3'),'private old question');
 a.syncPaidAccountSession(2);
 assert.equal(stored.has('ziwei-question:3'),false);assert.equal(stored.has('ziwei-selected-profile'),false);assert.equal(stored.has('ziwei-request:checkout'),false);assert.equal(stored.get('unrelated'),'keep');
 assert.equal(retries.peek('checkout:old'),undefined);
 stored.set('ziwei-question:3','current question');a.syncPaidAccountSession(2);
 assert.equal(stored.get('ziwei-question:3'),'current question');
 a.syncPaidAccountSession(null);assert.equal(stored.has('ziwei-question:3'),false);
 process.env.NEXT_PUBLIC_PRODUCT_MODE='portal'; modules.clear();
 const portalNarration=load(path.join(root,'lib/ziwei/narration.ts'));
 let portalFallback=0;
 portalNarration.BrowserNarration.prototype.speak=async()=>{portalFallback++;};
 global.fetch=async(url,init)=>{assert.equal(init.credentials,undefined);assert.equal(init.headers['X-Paid-Client'],undefined);return {ok:false,status:401};};
 await new portalNarration.CloudNarration().speak('门户保持原有回退');
 assert.equal(portalFallback,1);
 console.log('PASS paid accounts: cookie-only transport, failures, storage independence, feature headers');
})().catch(error=>{console.error(error);process.exit(1)});
