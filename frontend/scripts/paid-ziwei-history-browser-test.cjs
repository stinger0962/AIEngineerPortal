// Synthetic charts/history only. No model, narration, payment, or external calls.
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const {chromium}=require(process.env.QA_PLAYWRIGHT||'playwright');
const {astro}=require('iztro');
const base=new URL(process.env.QA_BASE_URL||'http://127.0.0.1:3001');
if(base.protocol!=='http:'||!['127.0.0.1','localhost','[::1]'].includes(base.hostname)||base.pathname!=='/'||base.username||base.password||base.search||base.hash)throw Error('HTTP loopback required');
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return{promise,resolve};};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  for(const width of [390,1440]){
   const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
   let listFails=false,detailFails=false,hold=null,heldSeen=false;
   const unexpected=[],errors=[];
   const chart=astro.bySolar('1990-1-1',0,'男',true,'zh-CN');
   const profiles=[1,2].map(id=>({id,name:`History Profile ${id}`,relation:'self',gender:'male',birth_date:'1990-01-01',birth_time_index:0,is_lunar_input:false,is_leap_month:false,chart_json:chart,persona:'sage',created_at:null,updated_at:null}));
   await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
    if(url.pathname.startsWith('/api/')){
     assert.equal(request.method(),'GET');assert.equal(request.headers()['x-paid-client'],'1');assert.equal(request.headers()['x-device-id'],undefined);
     if(url.pathname==='/api/v1/account/session')return json({authenticated:true,enabled:true,account_id:1});
     if(url.pathname==='/api/v1/ziwei/profiles')return json(profiles);
     const profile=url.pathname.match(/^\/api\/v1\/ziwei\/profiles\/(\d+)\/conversations$/);
     if(profile)return listFails?json({},503):json([{id:Number(profile[1])*10,scenario:'natal',title:`Saved ${profile[1]}`,created_at:null},{id:Number(profile[1])*10+1,scenario:'natal',title:`Alternate ${profile[1]}`,created_at:null}]);
     const conversation=url.pathname.match(/^\/api\/v1\/ziwei\/conversations\/(\d+)\/messages$/);
     if(conversation){
      const id=Number(conversation[1]),fail=detailFails,wasHeld=!!hold&&Number(conversation[1])===10;
      if(hold&&id===10){const waiting=hold;heldSeen=true;await waiting.promise;}
      try{return await json(fail?{}:[{id:id*100,role:'assistant',content:wasHeld?`Held private chat ${id}`:`Private saved chat ${id}`,chart_context_json:{},created_at:null}],fail?503:200);}catch{return;}
     }
     unexpected.push(url.pathname);return route.abort();
    }
    if(url.origin!==base.origin){unexpected.push(url.origin);return route.abort();}
    return route.continue();
   });
   const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
   const input=page.getByPlaceholder('向解盘师提问……（Enter 发送，Shift+Enter 换行）');
   const openHistory=()=>page.getByRole('button',{name:'历史会话',exact:true}).click();
   const row=id=>page.getByRole('button',{name:`打开历史会话 ${id} ${id%10===0?'Saved':'Alternate'} ${Math.floor(id/10)}`,exact:true});
   const waitHeld=async()=>{for(let i=0;i<100&&!heldSeen;i++)await page.waitForTimeout(20);assert.equal(heldSeen,true);};
   const switchProfile=id=>page.getByRole('button').filter({has:page.getByText(`History Profile ${id}`,{exact:true})}).click();
   try {
   await page.goto(base.origin+'/ziwei');await input.fill('CURRENT_PRIVATE_DRAFT');
   await page.getByRole('button',{name:'全屏对话',exact:true}).click();
   listFails=true;await openHistory();
   await page.getByRole('alert').filter({hasText:'加载历史会话失败'}).waitFor();
   listFails=false;await page.getByRole('button',{name:'重试加载历史会话',exact:true}).click();await row(10).waitFor();
   // Failed detail leaves the selectable list intact and has its own retry.
   detailFails=true;await row(10).click();await page.getByRole('alert').filter({hasText:'打开会话失败'}).waitFor();
   assert.equal(await row(11).isVisible(),true);
   detailFails=false;await page.getByRole('button',{name:'重试打开会话',exact:true}).click();
   await page.getByText('Private saved chat 10',{exact:true}).waitFor();
   assert.equal(await input.inputValue(),'CURRENT_PRIVATE_DRAFT');
   // Closing during a held detail must preserve the currently displayed chat/draft.
   await openHistory();hold=deferred();heldSeen=false;await row(10).click();await waitHeld();
   await page.getByRole('button',{name:'返回当前对话',exact:true}).click();
   await input.fill('DRAFT_AFTER_CLOSE');hold.resolve();hold=null;await page.waitForTimeout(100);
   await page.getByText('Private saved chat 10',{exact:true}).waitFor();assert.equal(await input.inputValue(),'DRAFT_AFTER_CLOSE');
   assert.equal(await page.getByText('Held private chat 10',{exact:true}).count(),0);
   // Select a newer conversation while the first response is still pending.
   await openHistory();hold=deferred();heldSeen=false;await row(10).click();await waitHeld();
   await row(11).click();await page.getByText('Private saved chat 11',{exact:true}).waitFor();
   hold.resolve();hold=null;await page.waitForTimeout(100);
   assert.equal(await page.getByText('Private saved chat 10',{exact:true}).count(),0);
   // Switching profiles clears loaded chat and prevents late loads crossing identity boundaries.
   await openHistory();hold=deferred();heldSeen=false;await row(10).click();await waitHeld();
   await switchProfile(2);await input.waitFor();hold.resolve();hold=null;await page.waitForTimeout(100);
   assert.equal(await page.getByText('Private saved chat 10',{exact:true}).count(),0);
   assert.equal(await page.getByText('Private saved chat 11',{exact:true}).count(),0);
   assert.equal(await page.getByText('Held private chat 10',{exact:true}).count(),0);
   assert.equal(await input.inputValue(),'');
   await page.getByRole('button',{name:'全屏对话',exact:true}).click();await openHistory();await row(20).click();
   await page.getByText('Private saved chat 20',{exact:true}).waitFor();
   await page.screenshot({path:`/tmp/paid-ziwei-history-${width}.png`,fullPage:true});
   await switchProfile(1);await input.waitFor();assert.equal(await page.getByText('Private saved chat 20',{exact:true}).count(),0);
   assert.deepEqual(unexpected,[]);assert.deepEqual(errors,[]);
   } catch(error) {
    // All page/API content here is synthetic. Do not collect cookies or headers.
    const body=await page.locator('body').innerText().catch(()=>'<body unavailable>');
    await Promise.allSettled([
     page.screenshot({path:`/tmp/paid-ziwei-history-failure-${width}.png`,fullPage:true}),
     fs.writeFile(`/tmp/paid-ziwei-history-failure-${width}.json`,JSON.stringify({width,url:page.url(),failure:String(error),pageErrors:errors,unexpectedRequests:unexpected,body},null,2)),
    ]);
    throw error;
   } finally { hold?.resolve(); await context.close(); }
   console.log(`PASS ${width}px: Ziwei history retry, close/late/selection isolation, preserved draft, clean profile switch`);
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
