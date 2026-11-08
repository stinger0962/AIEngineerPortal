// Mocked account UI only: no real codes, mailbox, payments, or backend session.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:3001';
if (!['localhost','127.0.0.1'].includes(new URL(base).hostname)) throw Error('Local server required');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,headless:true,args:['--no-sandbox']});
 try {
  for(const width of [1440,390]){
   let authenticated=false, enabled=true, starts=0, verifies=0, verifyError=400, accountId=1;
   const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
   await context.route('**/*', async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.pathname.startsWith('/api/v1/')){
     assert.equal(req.headers()['x-paid-client'],'1'); assert.equal(req.headers()['x-device-id'],undefined);
     const json=(body,status=200)=>route.fulfill({contentType:'application/json',body:JSON.stringify(body),status});
     if(url.pathname.endsWith('/account/session'))return json({authenticated,enabled,account_id:authenticated?accountId:null});
     if(url.pathname.endsWith('/account/challenges')){starts++;return json({challenge_id:'mock-challenge',expires_in:900});}
     if(url.pathname.endsWith('/account/verify')){verifies++;if(verifyError)return json({},verifyError);authenticated=true;return json({authenticated:true});}
     if(url.pathname.endsWith('/account/logout')||url.pathname.endsWith('/account/logout-all')){authenticated=false;return json({authenticated:false});}
     if(url.pathname.endsWith('/ziwei/profiles'))return json([{id:accountId,name:`Account ${accountId} profile`,relation:'self',gender:'male',birth_date:'1990-01-01',birth_time_index:0,is_lunar_input:false,is_leap_month:false,chart_json:{},persona:'sage',created_at:null,updated_at:null}]);
     return json([]);
    }
    if(url.origin!==new URL(base).origin)return route.abort();
    return route.continue();
   });
   const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto(base+'/ziwei');
   await page.getByRole('heading',{name:'邮箱账号'}).waitFor();
   await page.getByLabel('邮箱',{exact:true}).fill('sample@example.test');
   await page.getByRole('button',{name:'发送验证码',exact:true}).evaluate(button => { button.click(); button.click(); });
   await page.getByLabel('验证码',{exact:true}).waitFor();
   await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
   await page.getByLabel('验证码',{exact:true}).fill('test-code');
   await page.getByRole('button',{name:'验证并登录'}).click();
   await page.getByRole('status').filter({hasText:'验证码无效或已过期'}).waitFor();
   await page.getByRole('button',{name:'更换邮箱 / 重新获取'}).click();
   await page.getByLabel('邮箱',{exact:true}).fill('second@example.test');
   await page.getByRole('button',{name:'发送验证码',exact:true}).click();
   await page.getByLabel('验证码',{exact:true}).fill('test-code'); verifyError=0;
   await page.getByRole('button',{name:'验证并登录'}).click();
   await page.getByRole('heading',{name:'紫微斗数',exact:true}).waitFor();
   assert.equal(starts,2); assert.equal(verifies,2);
   await page.getByText('Account 1 profile',{exact:true}).waitFor();
   await page.evaluate(()=>{sessionStorage.setItem('ziwei-question:1','private old account draft');sessionStorage.setItem('ziwei-request:checkout:test','old retry');});
   accountId=2;
   await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
   await page.getByText('Account 2 profile',{exact:true}).waitFor();
   assert.equal(await page.getByText('Account 1 profile',{exact:true}).count(),0);
   assert.equal(await page.evaluate(()=>sessionStorage.getItem('ziwei-question:1')),null);
   assert.equal(await page.evaluate(()=>sessionStorage.getItem('ziwei-request:checkout:test')),null);
   const secondTab=await context.newPage();await secondTab.goto(base+'/account');
   await secondTab.getByRole('button',{name:'退出此浏览器',exact:true}).click();
   await page.getByRole('button',{name:'发送验证码',exact:true}).waitFor();
   assert.equal(await page.getByText('Account 2 profile',{exact:true}).count(),0);
   await secondTab.close();
   authenticated=true;await page.evaluate(()=>window.dispatchEvent(new Event('pageshow')));
   await page.getByText('Account 2 profile',{exact:true}).waitFor();
   assert.equal(await page.getByText('你的找回码',{exact:true}).count(),0);
   await page.getByRole('link',{name:'账号',exact:true}).click();
   await page.getByRole('button',{name:'退出所有浏览器',exact:true}).click();
   await page.getByRole('button',{name:'发送验证码',exact:true}).waitFor();
   enabled=false; await page.reload();
   await page.getByRole('status').filter({hasText:'邮箱登录尚未开放'}).waitFor();
   assert.equal(await page.getByRole('button',{name:'发送验证码',exact:true}).count(),0);
   assert.deepEqual(errors,[]);
   console.log(`PASS ${width}px: gated features, invalid code, restart, sign in, cross-tab switch/logout, logout-all and disabled state`);
   await context.close();
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
