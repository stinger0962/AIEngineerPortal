// Offline history transport and malformed-data regression, no real APIs.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
const js=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/lib/ziwei/api.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
function load(paid){let invalid=0;const mod={exports:{}};new Function('require','module','exports',js)(id=>{
 if(id.endsWith('product/config'))return{paidProduct:paid};
 if(id.endsWith('product/account'))return{paidRequestHeaders:()=>paid?{'X-Paid-Client':'1'}:{},paidRequestOptions:()=>paid?{credentials:'include'}:{},invalidatePaidSession:()=>{invalid++;}};
 if(id.endsWith('lib/api'))return{API_BASE:'/api/v1'};
 if(id.endsWith('deviceId'))return{getDeviceId:()=> 'synthetic-device'};
 if(id==='./retry-keys')return{retryKeys:{}};
 throw Error(id);
},mod,mod.exports);return{api:mod.exports.ziweiApi,get invalid(){return invalid;}};}
(async()=>{
 const conversation={id:1,title:'Saved',scenario:'natal',created_at:null};
 const message={id:2,role:'assistant',content:'saved text',chart_context_json:{segments:[{text:'saved',commands:[{type:'overview'}]}]},created_at:null};
 for(const paid of [true,false]){
  const r=load(paid),signal=new AbortController().signal;
  global.fetch=async(url,options)=>{
   assert.equal(options.signal,signal);assert.equal(options.cache,'no-store');
   assert.equal(options.credentials,paid?'include':undefined);assert.equal(options.headers['X-Paid-Client'],paid?'1':undefined);
   assert.equal(options.headers['X-Device-Id'],paid?undefined:'synthetic-device');
   return{ok:true,json:async()=>url.endsWith('/messages')?[message]:[conversation]};
  };
  assert.deepEqual(await r.api.listConversations(1,signal),[conversation]);assert.deepEqual(await r.api.listMessages(1,signal),[message]);
  global.fetch=()=>{throw Error('Invalid ids must not request');};
  for(const id of [0,-1,1.5,NaN,Infinity,'1']){
   await assert.rejects(r.api.listConversations(id),e=>e.status===400);await assert.rejects(r.api.listMessages(id),e=>e.status===400);
  }
  for(const rows of [null,{},[null],[{...conversation,title:{}}],[{...conversation,id:0}],[{...conversation,created_at:4}]]){
   global.fetch=async()=>({ok:true,json:async()=>rows});await assert.rejects(r.api.listConversations(1),e=>e.status===502);
  }
  for(const rows of [null,{},[null],[{...message,content:{}}],[{...message,role:'system'}],[{...message,chart_context_json:null}],
   [{...message,chart_context_json:{segments:[{text:'x',commands:[{type:'unknown'}]}]}}],
   [{...message,chart_context_json:{camera_commands:[{type:'explain_term',term:'missing explanation'}]}}]]){
   global.fetch=async()=>({ok:true,json:async()=>rows});await assert.rejects(r.api.listMessages(1),e=>e.status===502);
  }
  for(const status of [401,404,503]){
   global.fetch=async()=>({ok:false,status,headers:new Headers(),json:async()=>({detail:'synthetic'})});
   await assert.rejects(r.api.listMessages(1),e=>e.status===status);
  }
  assert.equal(r.invalid,1);
 }
 console.log('PASS Ziwei history: abort/no-store/identity, malformed list/messages/context, IDs and HTTP failures');
})().catch(e=>{console.error(e);process.exitCode=1;});
