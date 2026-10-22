// Local Chromium UI regression suite. Every API response is mocked; external requests are blocked.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.QA_PLAYWRIGHT || 'playwright');
const {astro} = require('iztro');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:3100';
if (!['localhost','127.0.0.1'].includes(new URL(base).hostname)) throw Error('Local server required');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({reducedMotion:'reduce',viewport:{width:1440,height:1100}});
 const requests=[], errors=[];
 let balance=1, status='pending', oracle='busy', release;
 await context.addInitScript(()=>localStorage.setItem('ziwei-audio-hint','1'));
 await context.route('**/*',async route=>{
  const req=route.request(), url=new URL(req.url());
  if(url.origin!==new URL(base).origin)return route.abort();
  if(!url.pathname.startsWith('/api/v1/'))return route.continue();
  requests.push({path:url.pathname,headers:req.headers(),body:req.postDataJSON()});
  const json=(data,code=200)=>route.fulfill({status:code,contentType:'application/json',body:JSON.stringify(data)});
  if(url.pathname.endsWith('/billing/balance'))return json({balance,paid_enabled:true,require_credits:true,mode:'test',currency:'cny',packs:[{key:'p10',label:'QA 10',credits:10,amount_cents:990}]});
  if(url.pathname.includes('/billing/orders/'))return json({order_id:123,status,mode:'test'});
  if(url.pathname.endsWith('/oracle/stream')){
   if(oracle==='hold')await new Promise(r=>release=r);
   if(oracle==='done'){balance=0;return route.fulfill({contentType:'text/event-stream',body:'data: {"type":"text","delta":"Mock reading."}\n\ndata: {"type":"done","conversation_id":77,"meta":{}}\n\n'});}
   return json({detail:{code:'billing_busy',retryable:true,retry_after_seconds:2}},503);
  }
  if(url.pathname==='/api/v1/ziwei/profiles')return json([{id:1,name:'QA Profile',relation:'self',gender:'male',birth_date:'1990-01-01',birth_time_index:0,is_lunar_input:false,is_leap_month:false,chart_json:astro.bySolar('1990-1-1',0,'男',true,'zh-CN'),persona:'sage',created_at:null,updated_at:null}]);
  if(url.pathname.endsWith('/conversations'))return json([{id:77,scenario:'natal',title:'QA prior conversation',created_at:null}]);
  if(url.pathname.endsWith('/messages'))return json([]);
  return json({});
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base+'/ziwei');
  const panel=page.getByRole('region',{name:'紫微测试点数'});
  await panel.getByText('可用点数：1',{exact:true}).waitFor();
  await page.evaluate(()=>history.pushState({},'','/ziwei?paid=1&order_id=123'));
  await panel.getByText(/测试付款待确认/).waitFor();
  assert.equal(await panel.getByRole('button',{name:/测试购买/}).isDisabled(),true);
  status='paid';balance=11;
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
  await panel.getByText(/测试付款已确认/).waitFor();
  await panel.getByText('可用点数：11',{exact:true}).waitFor();
  console.log('PASS browser: search navigation, pageshow refresh, pending/paid server confirmation');
  const input=page.getByPlaceholder('向解盘师提问……（Enter 发送，Shift+Enter 换行）');
  await input.waitFor();
  await page.getByRole('button',{name:'全屏对话',exact:true}).click();
  await page.getByRole('button',{name:'历史会话',exact:true}).click();
  await page.getByText('QA prior conversation',{exact:true}).click();
  await input.fill('Question A');oracle='hold';
  await page.getByRole('button',{name:'问',exact:true}).click();
  await page.waitForFunction(()=>Object.keys(sessionStorage).some(k=>k.startsWith('ziwei-request:oracle:')));
  await input.fill('Newer draft B');
  for(let i=0;!release && i<100;i++)await new Promise(r=>setTimeout(r,10));
  assert.ok(release);oracle='busy';release();
  await page.getByRole('alert').filter({hasText:'点数服务暂时繁忙'}).waitFor();
  assert.equal(await input.inputValue(),'Newer draft B');
  const first=requests.filter(r=>r.path.endsWith('/oracle/stream')).at(-1);
  assert.equal(first.body.conversation_id,77);
  await page.reload();await input.waitFor();
  assert.equal(await input.inputValue(),'Newer draft B');
  await page.getByRole('button',{name:'重试未完成的问题：Question A',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'点数服务暂时繁忙'}).waitFor();
  const retry=requests.filter(r=>r.path.endsWith('/oracle/stream')).at(-1);
  assert.deepEqual(retry.body,first.body);
  assert.equal(retry.headers['idempotency-key'],first.headers['idempotency-key']);
  assert.equal(await input.inputValue(),'Newer draft B');
  console.log('PASS browser: newer draft survives failure; reload preserves pending conversation/payload/key');
  oracle='done';await page.getByRole('button',{name:'重试未完成的问题：Question A',exact:true}).click();
  await panel.getByText('可用点数：0',{exact:true}).waitFor();
  assert.equal(await input.inputValue(),'Newer draft B');assert.deepEqual(errors,[]);
  console.log('PASS browser: successful retry refreshes credit, preserves draft, no page exceptions');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
