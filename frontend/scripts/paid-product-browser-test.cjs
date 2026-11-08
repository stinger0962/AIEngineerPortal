// Local UI test: all API traffic is mocked and external traffic is blocked.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.QA_PLAYWRIGHT || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:3001';
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw Error('Local server required');
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.QA_CHROMIUM, headless: true, args: ['--no-sandbox'] });
  try {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.pathname === '/api/v1/account/session') return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ authenticated: true, enabled: true, account_id: 1 }) });
        if (url.pathname.startsWith('/api/v1/')) return route.fulfill({ contentType: 'application/json', body: '[]' });
        if (url.origin !== new URL(base).origin) return route.abort();
        return route.continue();
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base);
      await page.getByText('文化探索 · 产品预览').waitFor();
      assert.equal(await page.locator('a[href="/grow"]').count(), 0);
      const door = page.getByRole('link', { name: '紫微斗数 · 入口' }).filter({ visible: true });
      await door.click();
      await page.waitForURL('**/ziwei');
      await page.getByRole('heading', { name: '紫微斗数', exact: true }).waitFor();
      assert.equal(await page.getByText('认领旧档案', { exact: false }).count(), 0);
      await page.goBack();
      await page.getByText('文化探索 · 产品预览').waitFor();
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const explore = page.getByRole('link', { name: '探索 · 更多可能 · 入口' }).filter({ visible: true });
      if (width < 1000) await explore.scrollIntoViewIfNeeded();
      await explore.click();
      await page.waitForURL('**/features');
      await page.getByRole('heading', { name: '探索功能' }).waitFor();
      await page.getByRole('link', { name: /灵签求签.*进入体验/ }).click();
      await page.waitForURL('**/qian');
      await page.getByRole('link', { name: '全部功能', exact: true }).click();
      await page.waitForURL('**/features');
      const response = await page.goto(base + '/settings');
      assert.equal(response.status(), 404);
      assert.deepEqual(errors, []);
      await page.goto(base);
      await page.screenshot({ path: `/tmp/paid-home-${width}.png` });
      console.log(`PASS ${width}px: door navigation, back, reduced motion, catalogue, Qian and portal isolation`);
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
