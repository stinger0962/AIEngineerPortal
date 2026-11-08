// Real browser -> same-origin proxy -> FastAPI -> disposable SQLite.
// Only delivery is injected: codes stay in the private temporary QA outbox.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = 'http://127.0.0.1:3002';
const outbox = path.join(process.env.PAID_QA_DIR,'outbox.jsonl');
const mail = email => fs.readFileSync(outbox,'utf8').trim().split('\n').map(JSON.parse).filter(x=>x.email===email).at(-1);
const options = {headers:{'X-Paid-Client':'1','Origin':base}};
async function api(context, method, route, data) {
 const response = await context.request[method](base+'/api/v1/'+route,{...options,...(data?{data}:{})});
 assert.equal(response.headers()['x-paid-qa-run'],process.env.PAID_QA_RUN);
 return response;
}
async function login(context,page,email,invalid=false) {
 await page.goto(base+'/account');
 await page.getByLabel('邮箱',{exact:true}).fill(email);
 await page.getByRole('button',{name:'发送验证码',exact:true}).click();
 await page.getByLabel('验证码',{exact:true}).waitFor();
 // Returning from another email tab must preserve the challenge.
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 if(invalid){
  await page.getByLabel('验证码',{exact:true}).fill('not-valid');
  await page.getByRole('button',{name:'验证并登录'}).click();
  await page.getByRole('status').filter({hasText:'验证码无效或已过期'}).waitFor();
 }
 const code=mail(email).code;
 await page.getByLabel('验证码',{exact:true}).fill(code);
 await page.getByRole('button',{name:'验证并登录'}).click();
 await page.getByRole('button',{name:'退出此浏览器',exact:true}).waitFor();
 const cookie=(await context.cookies()).find(c=>c.name==='paid_session_local');
 assert.ok(cookie);assert.equal(cookie.httpOnly,true);assert.equal(cookie.sameSite,'Strict');
 assert.equal(cookie.path,'/');assert.equal(cookie.domain,'127.0.0.1');
 assert.equal(await page.evaluate(()=>document.cookie.includes('paid_session')),false);
 assert.equal((await api(context,'get','account/session')).status(),200);
 assert.equal(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}).includes('paid_session')),false);
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,headless:true,args:['--no-sandbox']});
 try{
  for(const width of [1440,390]){
   const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
   // No response mocking. Abort external page requests, including accidental third parties.
   await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   assert.equal((await api(context,'get','ziwei/profiles')).status(),401);
   const email=`account-${width}@example.test`;
   await login(context,page,email,true);
   const original=(await (await api(context,'get','account/session')).json()).account_id;
   const profile=await api(context,'post','ziwei/profiles',{name:`Private ${width}`,gender:'female',birth_date:'1990-01-01',birth_time_index:1});
   assert.equal(profile.status(),200);
   const profileId=(await profile.json()).id;
   await page.goto(base+'/ziwei');await page.getByText(`Private ${width}`,{exact:true}).waitFor();
   assert.equal((await api(context,'get','qian/readings')).status(),200);
   // Server authorization, not UI state, rejects a missing CSRF header and evil Origin.
   assert.equal((await context.request.post(base+'/api/v1/account/logout',{data:{}})).status(),403);
   assert.equal((await context.request.post(base+'/api/v1/account/logout',{headers:{'X-Paid-Client':'1',Origin:'https://evil.example'},data:{}})).status(),403);
   const second=await browser.newContext(); const secondPage=await second.newPage();
   await second.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
   await login(second,secondPage,`other-${width}@example.test`);
   assert.deepEqual(await (await api(second,'get','ziwei/profiles')).json(),[]);
   assert.equal((await api(second,'get',`ziwei/profiles/${profileId}`)).status(),404);
   await secondPage.getByRole('button',{name:'退出此浏览器',exact:true}).click();
   await secondPage.getByRole('button',{name:'发送验证码',exact:true}).waitFor();
   await login(second,secondPage,email);
   assert.equal((await (await api(second,'get','account/session')).json()).account_id,original);
   assert.equal((await api(context,'get','ziwei/profiles')).status(),401);
   await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
   await page.getByRole('heading',{name:'邮箱账号'}).waitFor();
   assert.equal(await page.getByText(`Private ${width}`,{exact:true}).count(),0);
   assert.equal((await (await api(second,'get','ziwei/profiles')).json())[0].id,profileId);
   await secondPage.getByRole('button',{name:'退出所有浏览器',exact:true}).click();
   await secondPage.getByRole('button',{name:'发送验证码',exact:true}).waitFor();
   assert.equal((await api(second,'get','ziwei/profiles')).status(),401);
   assert.equal((await second.cookies()).some(c=>c.name==='paid_session_local'),false);
   assert.deepEqual(errors,[]);
   await second.close();await context.close();
   console.log(`PASS ${width}px real API: email verification, cookie, account isolation, returning account, revocation and logout`);
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
