// Local-only discovery/accessibility smoke. All account responses are synthetic;
// no real email, credentials, payments, or backend feature requests are used.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:3001';
const origin = new URL(base);
if (origin.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname)
    || origin.username || origin.password || origin.search || origin.hash || origin.pathname !== '/') {
  throw Error('An HTTP loopback origin is required');
}

async function noOverflow(page, width) {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  assert.ok(dimensions.document <= dimensions.viewport + 1 && dimensions.body <= dimensions.viewport + 1,
    `${width}px horizontal overflow: ${JSON.stringify(dimensions)}`);
}

async function tabTo(page, locator) {
  for (let attempt = 0; attempt < 40; attempt++) {
    await page.keyboard.press('Tab');
    if (await locator.evaluate(element => element === document.activeElement)) {
      const focus = await locator.evaluate(element => {
        const style = getComputedStyle(element);
        return style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0
          || style.boxShadow !== 'none';
      });
      assert.ok(focus, 'Keyboard-focused feature link needs a visible focus indicator');
      return;
    }
  }
  assert.fail('Feature link is not reachable by keyboard Tab');
}

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.QA_CHROMIUM, headless: true, args: ['--no-sandbox'] });
  try {
    for (const width of [320, 390, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
      const errors = [], unexpected = [];
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (url.pathname.startsWith('/api/')) {
          if (url.pathname === '/api/v1/account/session' && request.method() === 'GET') {
            await new Promise(resolve => setTimeout(resolve, 250));
            return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ authenticated: false, enabled: false, account_id: null }) });
          }
          unexpected.push(`${request.method()} ${url.pathname}`);
          return route.abort();
        }
        if (url.origin !== origin.origin) {
          unexpected.push(`External request: ${url.origin}`);
          return route.abort();
        }
        return route.continue();
      });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      for (const [name, path] of [['了解紫微斗数', '/ziwei'], ['了解灵签求签', '/qian']]) {
        await page.goto(origin.origin + '/features');
        await page.getByRole('heading', { name: '探索功能', exact: true, level: 1 }).waitFor();
        await page.getByText(/真实付费尚未开放/).first().waitFor();
        const link = page.getByRole('link', { name, exact: true });
        assert.equal(await link.count(), 1);
        assert.equal(await link.getAttribute('href'), path);
        await noOverflow(page, width);
        await page.screenshot({ path: `/tmp/paid-discovery-${width}.png`, fullPage: true });
        await tabTo(page, link);
        await page.keyboard.press('Enter');
        await page.waitForURL(origin.origin + path);
        await page.getByRole('status').filter({ hasText: '邮箱登录尚未开放' }).waitFor();
        assert.equal(await page.locator('input[type="email"]').count(), 0);
        assert.equal(await page.getByRole('button', { name: /支付|购买|充值|发送验证码/ }).count(), 0);
        await noOverflow(page, width);
        // Check a real semantic return link, not browser history.
        await page.locator('a[href="/features"]').last().click();
        await page.getByRole('heading', { name: '探索功能', exact: true }).waitFor();
      }
      await page.addInitScript(() => {
        window.__emailInputSeen = false;
        new MutationObserver(() => {
          if (document.querySelector('input[type="email"]')) window.__emailInputSeen = true;
        }).observe(document, { childList: true, subtree: true });
      });
      await page.goto(origin.origin + '/account');
      await page.getByRole('status').filter({ hasText: '邮箱登录尚未开放' }).waitFor();
      assert.equal(await page.locator('input').count(), 0);
      assert.equal(await page.evaluate(() => window.__emailInputSeen), false, 'Disabled account must not flash email entry while loading');
      assert.equal(await page.getByRole('button', { name: /支付|购买|充值|发送验证码/ }).count(), 0);
      await noOverflow(page, width);
      await page.screenshot({ path: `/tmp/paid-disabled-${width}.png`, fullPage: true });
      await page.locator('a[href="/features"]').last().click();
      await page.getByRole('heading', { name: '探索功能', exact: true }).waitFor();
      assert.deepEqual(unexpected, [], 'Discovery should not contact feature APIs or external services');
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}px: semantic discovery, keyboard links, disabled accounts, return navigation, no overflow`);
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
