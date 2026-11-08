// Synthetic owner-scoped history only. External traffic, generation, and TTS blocked.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = new URL(process.env.QA_BASE_URL || 'http://127.0.0.1:3001');
if (base.protocol !== 'http:' || !['127.0.0.1','localhost','[::1]'].includes(base.hostname) || base.pathname !== '/' || base.username || base.password || base.search || base.hash) throw Error('HTTP loopback origin required');
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
(async () => {
 const browser = await chromium.launch({ executablePath: process.env.QA_CHROMIUM, headless: true, args: ['--no-sandbox'] });
 try {
  for (const width of [320,390,1440]) {
   const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
   let listFails = false, empty = false, detailStatus = 200, hold = null, heldSeen = false;
   const unexpected = [], errors = [], requests = [];
   const waitForHeld = async page => {
    for(let i=0;i<100&&!heldSeen;i++) await page.waitForTimeout(20);
    assert.equal(heldSeen,true,'Expected detail request did not arrive');
   };
   const rows = Array.from({ length: 6 }, (_, i) => ({ id: 101+i, sign_id: 7+i, question: `已保存问题 ${i+1} ${'x'.repeat(120)}`, grade: '上签', device: '—', created_at: '2026-01-01T00:00:00Z' }));
   await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    const json = (body,status=200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname.startsWith('/api/')) {
     requests.push(`${request.method()} ${url.pathname}`);
     assert.equal(request.method(),'GET'); assert.equal(request.headers()['x-paid-client'],'1'); assert.equal(request.headers()['x-device-id'],undefined);
     if (url.pathname === '/api/v1/account/session') return json({ authenticated:true,enabled:true,account_id:1 });
     if (url.pathname === '/api/v1/qian/readings') return listFails ? json({},503) : json(empty ? [] : rows);
     const match = url.pathname.match(/^\/api\/v1\/qian\/readings\/(\d+)$/);
     if (match) {
      const id=Number(match[1]), status=detailStatus;
      if (hold && id===101) { const waiting=hold; heldSeen=true; await waiting.promise; }
      try { return await json(status===200 ? { id, sign_id:id-94, grade:'上签', question:`完整保存问题 ${id}`, response:`SAVED_ANSWER_${id} <script>DO_NOT_EXECUTE</script>`,context_json:{},created_at:'2026-01-01T00:00:00Z' } : {},status); }
      catch { return; } // Cancellation may abort the held route before release.
     }
     unexpected.push(url.pathname); return route.abort();
    }
    if(url.origin!==base.origin){unexpected.push(url.origin);return route.abort();}
    return route.continue();
   });
   const page=await context.newPage(); page.on('pageerror', e=>errors.push(e.message));
   await page.goto(base.origin+'/qian');
   const question=page.getByPlaceholder('写下你想问的事，例如「这段时间的事业」……');
   await question.fill('CURRENT_DRAFT_KEEP');
   const row = id => page.getByRole('button',{name:`查看第${id-94}签记录 ${id}`,exact:true});
   await row(101).waitFor();
   assert.equal(await row(106).count(),0);
   await page.getByRole('button',{name:'展开全部记录',exact:true}).click(); await row(106).waitFor();
   const detail=page.getByRole('region',{name:'灵签历史详情',exact:true});
   await row(101).focus(); await page.keyboard.press('Enter');
   await detail.getByText('SAVED_ANSWER_101 <script>DO_NOT_EXECUTE</script>',{exact:true}).waitFor();
   assert.equal(await detail.locator('script').count(),0);
   assert.equal(await question.inputValue(),'CURRENT_DRAFT_KEEP');
   assert.equal(await page.getByRole('heading',{name:'已保存的解签内容',exact:true}).evaluate(e=>e===document.activeElement),true);
   await page.getByRole('button',{name:'关闭详情',exact:true}).click(); await detail.waitFor({state:'hidden'});
   assert.equal(await row(101).evaluate(e=>e===document.activeElement),true);
   // Closing in-flight detail cannot reopen it after a late response.
   hold=deferred();heldSeen=false;
   await row(101).click(); await detail.getByText('读取历史详情中…',{exact:true}).waitFor();
   await waitForHeld(page);
   await page.getByRole('button',{name:'关闭详情',exact:true}).click();
   hold.resolve();hold=null;await page.waitForTimeout(100);
   assert.equal(await detail.count(),0);
   // A newer selection wins even when an older response arrives later.
   hold=deferred();heldSeen=false;await row(101).click();
   await waitForHeld(page);
   await row(102).click();await detail.getByText('SAVED_ANSWER_102 <script>DO_NOT_EXECUTE</script>',{exact:true}).waitFor();
   hold.resolve();hold=null;await page.waitForTimeout(100);
   assert.equal(await detail.getByText('SAVED_ANSWER_101 <script>DO_NOT_EXECUTE</script>',{exact:true}).count(),0);
   for (const status of [404,503]) {
    detailStatus=status;await row(103).click();
    await detail.getByText(status===404?'记录不存在或已不可访问。':'历史详情暂不可用，请重试。',{exact:true}).waitFor();
    detailStatus=200;await detail.getByRole('button',{name:'重试读取详情',exact:true}).click();
    await detail.getByText('SAVED_ANSWER_103 <script>DO_NOT_EXECUTE</script>',{exact:true}).waitFor();
   }
   await page.getByRole('button',{name:'关闭详情',exact:true}).click();
   listFails=true;await page.getByRole('button',{name:'刷新历史记录',exact:true}).click();
   await page.getByText('历史记录暂不可用，请刷新重试。',{exact:true}).waitFor();
   assert.equal(await page.getByText('暂无已保存的灵签记录。',{exact:true}).count(),0);
   listFails=false;empty=true;await page.getByRole('button',{name:'刷新历史记录',exact:true}).click();
   await page.getByText('暂无已保存的灵签记录。',{exact:true}).waitFor();
   empty=false;await page.getByRole('button',{name:'刷新历史记录',exact:true}).click();await row(101).waitFor();
   await row(101).click();await detail.getByText('SAVED_ANSWER_101 <script>DO_NOT_EXECUTE</script>',{exact:true}).waitFor();
   assert.equal(await question.inputValue(),'CURRENT_DRAFT_KEEP');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false);
   await page.screenshot({path:`/tmp/paid-qian-history-${width}.png`,fullPage:true});
   assert.deepEqual(unexpected,[]);assert.deepEqual(errors,[]);
   assert.ok(requests.every(x=>!x.includes('/oracle')&&!x.includes('/tts')));
   await context.close();console.log(`PASS ${width}px: read-only saved details, text safety, keyboard/close, retry, stale/cancel guards, preserved draft`);
  }
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
