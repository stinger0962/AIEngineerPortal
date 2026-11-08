// Synthetic loopback-only SSE failures; no real API/model/payment requests.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = new URL(process.env.QA_BASE_URL || 'http://127.0.0.1:3001');
if (base.protocol !== 'http:' || !['127.0.0.1','localhost','[::1]'].includes(base.hostname) || base.pathname !== '/' || base.search || base.hash || base.username || base.password) throw Error('HTTP loopback required');
const frame = event => `data: ${JSON.stringify(event)}\n\n`;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,headless:true,args:['--no-sandbox']});
 try {
  for(const failure of ['eof','error','network']) {
   const context=await browser.newContext({reducedMotion:'reduce'});
   let attempts=0, historyReads=0;
   const unexpected=[];
   await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    const json=body=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
    if(url.pathname==='/api/v1/account/session')return json({authenticated:true,enabled:true,account_id:1});
    if(url.pathname==='/api/v1/qian/readings'){historyReads++;return json([]);}
    if(url.pathname==='/api/v1/qian/oracle/stream'){
     attempts++;
     if(failure==='network')return route.abort('failed');
     const body=frame({type:'sign',sign:{id:7,grade:'上签',title:'测试',palace:'测试',poetry:'测试。',meaning:'测试',holy:'测试'}})+frame({type:'text',delta:'PARTIAL_RESULT_MUST_NOT_APPEAR'})+(failure==='error'?frame({type:'error'}):'');
     return route.fulfill({contentType:'text/event-stream',body});
    }
    if(url.origin!==base.origin || url.pathname.startsWith('/api/')){unexpected.push(url.href);return route.abort();}
    return route.continue();
   });
   const page=await context.newPage();
   await page.goto(base.origin+'/qian');
   const question=page.getByPlaceholder('写下你想问的事，例如「这段时间的事业」……');
   await question.fill('保留这个问题');
   await page.getByRole('button',{name:'摇 签',exact:true}).click();
   await page.getByRole('alert').filter({hasText:'请先查看历史记录'}).waitFor();
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent==='摇 签'&&!b.disabled));
   assert.equal(await question.inputValue(),'保留这个问题');
   assert.equal(await page.getByText('PARTIAL_RESULT_MUST_NOT_APPEAR',{exact:true}).count(),0);
   await page.waitForTimeout(300);
   assert.equal(attempts,1,'Never automatically retry uncertain generation');
   assert.ok(historyReads>=1);
   assert.deepEqual(unexpected,[]);
   console.log(`PASS Qian ${failure}: visible uncertainty, cleared partial answer, retained draft, unlocked UI, no automatic retry`);
   await context.close();
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
