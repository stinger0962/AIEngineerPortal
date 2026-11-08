// Offline transport/shape checks. No network, credentials, or provider calls.
const assert=require('node:assert/strict');
const fs=require('node:fs'), path=require('node:path'), ts=require('typescript');
const js=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/lib/qian/api.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
function load(paid){
 let invalidated=0;const mod={exports:{}};
 new Function('require','module','exports',js)(id=>{
  if(id.endsWith('product/config'))return{paidProduct:paid};
  if(id.endsWith('product/account'))return{paidRequestHeaders:()=>paid?{'X-Paid-Client':'1'}:{},paidRequestOptions:()=>paid?{credentials:'include'}:{},invalidatePaidSession:()=>{invalidated++;}};
  if(id.endsWith('deviceId'))return{getDeviceId:()=> 'synthetic-device'};
  if(id.endsWith('lib/api'))return{API_BASE:'/api/v1'};
  throw Error(id);
 },mod,mod.exports);
 return{api:mod.exports.qianApi,get invalidated(){return invalidated;}};
}
(async()=>{
 const detail={id:7,sign_id:3,grade:'上签',question:'full saved question',response:'saved partial answer',context_json:{},created_at:null};
 for(const paid of [true,false]){
  const r=load(paid),controller=new AbortController();let calls=0;
  global.fetch=async(url,options)=>{
   calls++;assert.equal(options.cache,'no-store');assert.equal(options.signal,controller.signal);
   assert.equal(options.credentials,paid?'include':undefined);
   assert.equal(options.headers['X-Paid-Client'],paid?'1':undefined);
   assert.equal(options.headers['X-Device-Id'],paid?undefined:'synthetic-device');
   return{ok:true,json:async()=>url.endsWith('/7')?detail:[detail]};
  };
  assert.deepEqual(await r.api.getReading(7,controller.signal),detail);
  assert.deepEqual(await r.api.listReadings(controller.signal),[detail]);assert.equal(calls,2);
  global.fetch=async()=>{throw Error('invalid ids must never fetch');};
  for(const id of [0,-1,1.5,NaN,Infinity,Number.MAX_SAFE_INTEGER+1,'7'])await assert.rejects(r.api.getReading(id),e=>e.status===400);
  for(const body of [null,[],{}, {...detail,id:8},{...detail,question:{}},{...detail,response:null},{...detail,sign_id:0},{...detail,grade:{}},{...detail,created_at:[]}]){
   global.fetch=async()=>({ok:true,json:async()=>body});await assert.rejects(r.api.getReading(7),e=>e.status===502);
  }
  for(const body of [null,{},[null],[{...detail,id:0}],[{...detail,question:{}}],[{...detail,grade:null}],[{...detail,created_at:5}]]){
   global.fetch=async()=>({ok:true,json:async()=>body});await assert.rejects(r.api.listReadings(),e=>e.status===502);
  }
  for(const status of [401,404,503]){
   global.fetch=async()=>({ok:false,status});await assert.rejects(r.api.getReading(7),e=>e.status===status);
  }
  assert.equal(r.invalidated,1);
 }
 console.log('PASS Qian history API: paid cookie/legacy identity, no-store/abort, id validation, malformed rows/details, explicit failures');
})().catch(error=>{console.error(error);process.exitCode=1;});
