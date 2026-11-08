const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const source = fs.readFileSync(path.join(__dirname, '../src/lib/qian/api.ts'), 'utf8');
const js = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
const mod = {exports:{}};
new Function('require','module','exports',js)(id => {
  if(id.endsWith('product/config')) return {paidProduct:true};
  if(id.endsWith('product/account')) return {paidRequestHeaders:()=>({'X-Paid-Client':'1'}),paidRequestOptions:()=>({credentials:'include'}),invalidatePaidSession:()=>{}};
  if(id.endsWith('deviceId')) return {getDeviceId:()=>''};
  if(id.endsWith('lib/api')) return {API_BASE:'/api/v1'};
  throw Error(id);
},mod,mod.exports);
const frame = event => `data: ${JSON.stringify(event)}\r\n\r\n`;
async function run(chunks, signal) {
  global.fetch=async()=>({ok:true,body:new ReadableStream({start(c){for(const chunk of chunks)c.enqueue(new TextEncoder().encode(chunk));c.close();}})});
  const calls=[];
  const handlers=Object.fromEntries(['Sign','Text','Camera','Done','Error'].map(name=>['on'+name,()=>calls.push(name)]));
  await mod.exports.qianApi.streamOracle({question:'synthetic'},handlers,signal);
  return calls;
}
(async()=>{
  assert.deepEqual(await run([]),['Error']);
  assert.deepEqual(await run([frame({type:'sign',sign:{}}),frame({type:'text',delta:'partial'})]),['Sign','Text','Error']);
  assert.deepEqual(await run(['data: {"type":"do']),['Error']);
  assert.deepEqual(await run(['data: null\n\ndata: garbage\n\n']),['Error']);
  const success=frame({type:'text',delta:'done'})+frame({type:'done'});
  assert.deepEqual(await run([success.slice(0,8),success.slice(8)]),['Text','Done']);
  assert.deepEqual(await run([frame({type:'error'}),frame({type:'done'}),frame({type:'error'})]),['Error']);
  assert.deepEqual(await run([frame({type:'done'}),frame({type:'text',delta:'late'})]),['Done']);
  const controller=new AbortController();controller.abort();
  assert.deepEqual(await run([],controller.signal),[]);
  console.log('PASS Qian terminal SSE: truncated/empty/malformed, split frames, duplicate terminals, abort');
})().catch(e=>{console.error(e);process.exit(1)});
