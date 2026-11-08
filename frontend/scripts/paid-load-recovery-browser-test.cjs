// Read-only synthetic load recovery. Every mutation/provider/external request is forbidden.
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
   let sessionFailure=true, authenticated=false, sessionHold=null, profileFailure=true, profileHold=null, empty=false, profileOverride=undefined;
   let sessionReads=0, profileReads=0;
   const errors=[],unexpected=[];
   const chart=astro.bySolar('1990-1-1',0,'男',true,'zh-CN');
   const profiles=[1,2].map(id=>({id,name:`Recovered Profile ${id}`,relation:'self',gender:'male',birth_date:'1990-01-01',birth_time_index:0,is_lunar_input:false,is_leap_month:false,chart_json:chart,persona:'sage',created_at:null,updated_at:null}));
   await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
    if(url.pathname.startsWith('/api/')){
     if(request.method()!=='GET'){unexpected.push(`${request.method()} ${url.pathname}`);return route.abort();}
     assert.equal(request.headers()['x-paid-client'],'1');assert.equal(request.headers()['x-device-id'],undefined);
     if(url.pathname==='/api/v1/account/session'){
      sessionReads++;const fail=sessionFailure,auth=authenticated,held=sessionHold;
      if(held)await held.promise;
      try{return await json(fail?{}:{authenticated:auth,enabled:true,account_id:auth?1:null},fail?503:200);}catch{return;}
     }
     if(url.pathname==='/api/v1/ziwei/profiles'){
      profileReads++;const fail=profileFailure,body=profileOverride??(empty?[]:profiles),held=profileHold;
      if(held)await held.promise;
      try{return await json(fail?{}:body,fail?503:200);}catch{return;}
     }
     unexpected.push(url.pathname);return route.abort();
    }
    if(url.origin!==base.origin){unexpected.push(url.origin);return route.abort();}
    return route.continue();
   });
   const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
   const absentCreation=async()=>{
    assert.equal(await page.getByRole('button',{name:'新建命主档案',exact:true}).count(),0);
    assert.equal(await page.getByLabel('姓名 / 称呼',{exact:true}).count(),0);
   };
   try{
    await page.goto(base.origin+'/account');
    await page.getByRole('button',{name:'重新检查登录状态',exact:true}).waitFor();
    assert.equal(await page.locator('input[type="email"]').count(),0);
    const originalReads=sessionReads;sessionFailure=false;sessionHold=deferred();
    await page.getByRole('button',{name:'重新检查登录状态',exact:true}).evaluate(button=>{button.click();button.click();});
    await page.getByRole('button',{name:'正在重新检查登录状态…',exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'正在重新检查登录状态…',exact:true}).isDisabled(),true);
    for(let i=0;i<250&&sessionReads===originalReads;i++)await page.waitForTimeout(20);
    assert.equal(sessionReads,originalReads+1,'Repeated retry must not multiply session checks');
    assert.equal(await page.locator('input[type="email"]').count(),0);
    sessionHold.resolve();sessionHold=null;
    await page.getByLabel('邮箱',{exact:true}).fill('UNSENT@example.test');
    assert.equal(await page.getByRole('button',{name:'发送验证码',exact:true}).isEnabled(),true);
    // Valid session and transient failed profile load: never substitute an empty create form.
    authenticated=true;profileHold=deferred();
    await page.goto(base.origin+'/ziwei');
    await page.getByRole('status').filter({hasText:'正在读取档案'}).waitFor();await absentCreation();
    profileHold.resolve();profileHold=null;
    await page.getByRole('alert').filter({hasText:'暂时无法读取档案'}).waitFor();await absentCreation();
    profileFailure=false;
    for(const malformed of [[null],[{...profiles[0],name:{invalid:true}}]]){
     profileOverride=malformed;profileHold=deferred();
     await page.getByRole('button',{name:'重试读取档案',exact:true}).click();
     await page.getByRole('status').filter({hasText:'正在读取档案'}).waitFor();await absentCreation();
     profileHold.resolve();profileHold=null;
     await page.getByRole('alert').filter({hasText:'暂时无法读取档案'}).waitFor();await absentCreation();
    }
    profileOverride=undefined;profileHold=deferred();
    await page.getByRole('button',{name:'重试读取档案',exact:true}).click();
    await page.getByRole('status').filter({hasText:'正在读取档案'}).waitFor();await absentCreation();
    profileHold.resolve();profileHold=null;
    await page.getByText('Recovered Profile 1',{exact:true}).waitFor();
    assert.equal(await page.getByLabel('姓名 / 称呼',{exact:true}).count(),0);
    await page.getByRole('button').filter({has:page.getByText('Recovered Profile 2',{exact:true})}).click();
    const draft=page.getByPlaceholder('向解盘师提问……（Enter 发送，Shift+Enter 换行）');
    await draft.fill('UNSENT recovered draft');assert.equal(await draft.inputValue(),'UNSENT recovered draft');
    await page.screenshot({path:`/tmp/paid-load-recovery-${width}.png`,fullPage:true});
    // A genuinely empty successful read, not a failed read, may reveal creation.
    empty=true;profileHold=deferred();await page.reload();
    await page.getByRole('status').filter({hasText:'正在读取档案'}).waitFor();await absentCreation();
    profileHold.resolve();profileHold=null;
    await page.getByLabel('姓名 / 称呼',{exact:true}).waitFor();
    assert.ok(profileReads>=3);assert.deepEqual(unexpected,[]);assert.deepEqual(errors,[]);
   }catch(error){
    const body=await page.locator('body').innerText().catch(()=>'<unavailable>');
    await Promise.allSettled([page.screenshot({path:`/tmp/paid-load-recovery-failure-${width}.png`,fullPage:true}),fs.writeFile(`/tmp/paid-load-recovery-failure-${width}.json`,JSON.stringify({failure:String(error),errors,unexpected,body},null,2))]);throw error;
   }finally{sessionHold?.resolve();profileHold?.resolve();await context.close();}
   console.log(`PASS ${width}px: read-only account/profile recovery, duplicate retry guard, no premature creation or mutation`);
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
