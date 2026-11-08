// Local-only mocked UI checks. Never contacts a payment provider or real API.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = new URL(process.env.QA_BASE_URL || 'http://127.0.0.1:3001');
if (base.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname)
    || base.username || base.password || base.search || base.hash || base.pathname !== '/') throw Error('HTTP loopback origin required');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.QA_CHROMIUM, headless: true, args: ['--no-sandbox'] });
  try {
    for (const width of [320, 390, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
      let balanceFails = false, serverStatus = 'pending', statusMode = 'test', accountId = 1, ordersMode = 'test', ordersEmpty = false, ordersFail = false;
      let balanceReads = 0, orderReads = 0;
      let delayNextStatus = false, releaseStatus, statusStarted;
      const unexpected = [], errors = [];
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
        if (url.pathname.startsWith('/api/')) {
          assert.equal(request.method(), 'GET', 'Credit discovery must not mutate billing');
          assert.equal(request.headers()['x-paid-client'], '1');
          assert.equal(request.headers()['x-device-id'], undefined);
          if (url.pathname === '/api/v1/account/session') return json({ authenticated: true, enabled: true, account_id: accountId });
          if (url.pathname === '/api/v1/billing/balance') {
            balanceReads++;
            if (balanceFails) return json({}, 503);
            // Even an enabled server must not override the frontend's default-off opt-in.
            return json({ mode: 'test', balance: accountId === 1 ? 17 : 29, paid_enabled: true, require_credits: true, currency: 'usd', packs: [{ key: 'small', label: '测试小包', credits: 10, amount_cents: 100, currency: 'usd' }] });
          }
          if (url.pathname === '/api/v1/billing/orders') {
            orderReads++;
            if (ordersFail) return json({}, 503);
            if (ordersEmpty) return json({ mode: 'test', orders: [] });
            return json({ mode: ordersMode, orders: [{ order_id: accountId === 1 ? 123 : 456, status: 'pending', pack: 'small', credits: 10, amount_cents: 100, currency: 'usd', created_at: '2026-01-01T00:00:00Z' }] });
          }
          if (url.pathname === '/api/v1/billing/orders/123') {
            const body = {mode: statusMode, status: serverStatus};
            if (delayNextStatus) {
              delayNextStatus = false;
              await new Promise(resolve => { releaseStatus = resolve; statusStarted(); });
            }
            return json(body);
          }
          unexpected.push(`${request.method()} ${url.pathname}`);
          return route.abort();
        }
        if (url.origin !== base.origin) { unexpected.push(url.origin); return route.abort(); }
        return route.continue();
      });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base.origin + '/credits?paid=1&order_id=123');
      await page.getByRole('heading', { name: '点数与订单', exact: true, level: 1 }).waitFor();
      await page.getByRole('heading', { name: '最近测试订单', exact: true }).waitFor();
      await page.getByText('订单 #123', { exact: true }).waitFor();
      await page.getByText('可用点数：17', { exact: true }).waitFor();
      await page.getByRole('status').filter({ hasText: '测试付款待确认' }).waitFor();
      assert.equal(await page.getByText('测试付款已确认，点数已入账。', { exact: true }).count(), 0, 'Return URL alone is not evidence of payment');
      for (const button of await page.getByRole('button', { name: /测试购买|充值|支付/ }).all()) {
        assert.equal(await button.isEnabled(), false, 'Default frontend build must not offer checkout');
      }
      const retry = page.getByRole('button', { name: '刷新余额与付款状态', exact: true });
      // Older pending responses must not overwrite a newer paid confirmation.
      delayNextStatus = true;
      const started = new Promise(resolve => { statusStarted = resolve; });
      await retry.click();
      await started;
      serverStatus = 'paid';
      await retry.click();
      await page.getByText('测试付款已确认，点数已入账。', { exact: true }).waitFor();
      const late = page.waitForResponse(response => response.url().endsWith('/billing/orders/123'));
      releaseStatus(); await late;
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert.equal(await page.getByText('测试付款已确认，点数已入账。', { exact: true }).count(), 1);
      balanceFails = true;
      await retry.click();
      await page.getByRole('alert').filter({ hasText: '余额暂不可用' }).waitFor();
      balanceFails = false;
      await retry.click();
      await page.getByRole('alert').filter({ hasText: '余额暂不可用' }).waitFor({ state: 'hidden' });
      // A live-mode response cannot be treated as verified test payment.
      statusMode = 'live';
      await page.goto(base.origin + '/credits?paid=1&order_id=123');
      await page.getByRole('alert').filter({ hasText: '付款状态暂无法确认' }).waitFor();
      assert.equal(await page.getByText('测试付款已确认，点数已入账。', { exact: true }).count(), 0);
      statusMode = 'test'; serverStatus = 'failed';
      await retry.click();
      await page.getByRole('status').filter({ hasText: '测试付款失败' }).waitFor();
      serverStatus = 'pending';
      await page.goto(base.origin + '/credits?canceled=1&order_id=123');
      await page.getByRole('status').filter({ hasText: '这不代表服务器订单已取消' }).waitFor();
      // Account changes must re-mount the entire private view, not retain a prior balance.
      await page.goto(base.origin + '/credits');
      await page.getByText('订单 #123', { exact: true }).waitFor();
      accountId = 2;
      await page.evaluate(() => window.dispatchEvent(new Event('focus')));
      await page.getByText('可用点数：29', { exact: true }).waitFor();
      assert.equal(await page.getByText('可用点数：17', { exact: true }).count(), 0);
      await page.getByText('订单 #456', { exact: true }).waitFor();
      assert.equal(await page.getByText('订单 #123', { exact: true }).count(), 0);
      ordersMode = 'live';
      await page.getByRole('button', { name: '刷新订单', exact: true }).click();
      await page.getByRole('alert').filter({ hasText: '订单暂不可用' }).waitFor();
      assert.equal(await page.getByText('订单 #456', { exact: true }).count(), 0);
      ordersMode = 'test';
      await page.getByRole('button', { name: '刷新订单', exact: true }).click();
      await page.getByText('订单 #456', { exact: true }).waitFor();
      ordersFail = true;
      await page.getByRole('button', { name: '刷新订单', exact: true }).click();
      await page.getByRole('alert').filter({ hasText: '订单暂不可用' }).waitFor();
      ordersFail = false; ordersEmpty = true;
      await page.getByRole('button', { name: '刷新订单', exact: true }).click();
      await page.getByText('暂无测试订单。不会仅因浏览此页创建订单。', { exact: true }).waitFor();
      ordersEmpty = false;
      await page.getByRole('button', { name: '刷新订单', exact: true }).click();
      await page.getByText('订单 #456', { exact: true }).waitFor();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      assert.equal(overflow, false, `Horizontal overflow at ${width}px`);
      await page.screenshot({ path: `/tmp/paid-credits-${width}.png`, fullPage: true });
      assert.ok(balanceReads > 0 && orderReads > 0);
      assert.deepEqual(unexpected, []);
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}px: server-truth returns, failed/cancelled states, balance retry, account isolation, default checkout off`);
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
