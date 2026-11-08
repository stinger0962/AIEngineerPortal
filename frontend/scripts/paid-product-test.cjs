// Offline routing/rendering contracts. No backend, payment, or email service.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const root = path.resolve(__dirname, '../src');
function load(file) {
  const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 } }).outputText;
  const module = { exports: {} };
  const req = id => {
    if (id === 'next/navigation') return { usePathname: () => '/ziwei', useRouter: () => ({}), notFound: () => { throw Error('404'); } };
    if (id === 'next/link') return ({ children, href, ...props }) => React.createElement('a', { ...props, href }, children);
    if (!id.startsWith('@/') && !id.startsWith('.')) return require(id);
    const target = id.startsWith('@/') ? path.join(root, id.slice(2)) : path.resolve(path.dirname(file), id);
    return load(fs.existsSync(target + '.ts') ? target + '.ts' : target + '.tsx');
  };
  new Function('require', 'module', 'exports', js)(req, module, module.exports);
  return module.exports;
}
for (const mode of ['portal', 'paid']) {
  process.env.NEXT_PUBLIC_PRODUCT_MODE = mode;
  const c = load(path.join(root, 'lib/product/config.ts'));
  assert.equal(c.paidProduct, mode === 'paid');
  for (const p of ['/', '/features', '/ziwei', '/qian', '/ziwei/opengraph-image']) assert.equal(c.isPaidProductPath(p), true);
  for (const p of ['/grow', '/settings', '/toolkits', '/ziweievil', '/xuan', '/api/v1/projects']) assert.equal(c.isPaidProductPath(p), false);
  assert.equal(new Set(c.paidFeatures.map(f => f.id)).size, c.paidFeatures.length);
  const Home = load(path.join(root, 'components/home/folding-screen-hub.tsx')).default;
  const html = renderToStaticMarkup(React.createElement(Home));
  assert.match(html, /screen-door/);
  if (mode === 'paid') {
    for (const href of ['/ziwei', '/qian', '/features']) assert.ok(html.includes(`href="${href}"`));
    for (const href of ['/grow', '/toolkits', '/xuan']) assert.ok(!html.includes(`href="${href}"`));
    const Catalogue = load(path.join(root, 'app/features/page.tsx')).default;
    const catalogue = renderToStaticMarkup(React.createElement(Catalogue));
    assert.match(catalogue, /真实付费尚未开放/);
    for (const feature of c.paidFeatures) {
      assert.ok(feature.purpose && feature.preparation);
      assert.ok(catalogue.includes(`了解${feature.label}`));
      assert.ok(catalogue.includes(feature.purpose));
    }
    assert.equal((catalogue.match(/<article/g) || []).length, c.paidFeatures.length);
    const Panel = load(path.join(root, 'components/product/account-panel.tsx')).PaidAccountPanel;
    const initial = renderToStaticMarkup(React.createElement(Panel));
    assert.ok(!initial.includes('type="email"'), 'No email entry before account availability is known');
    assert.match(initial, /正在确认账号是否开放/);
    const Shell = load(path.join(root, 'components/layout/domain-shell.tsx')).DomainShell;
    const shell = renderToStaticMarkup(React.createElement(Shell, { config: {wordmark:'方寸',accent:'#7c5cf0',bg:'#fff',links:[{href:'/ziwei',label:'紫微'}]} }, 'content'));
    assert.match(shell, /aria-current="page"/);
    assert.match(shell, /href="#paid-main"/);
    assert.match(shell, /aria-label="产品导航"/);
  } else {
    for (const href of ['/grow', '/toolkits', '/xuan']) assert.ok(html.includes(`href="${href}"`));
  }
  console.log(`PASS ${mode}: homepage and route contracts`);
}
console.log('PASS fresh product does not import PR #19 recovery/migration');
assert.ok(!fs.readFileSync(path.join(root, 'app/ziwei/page.tsx'), 'utf8').includes('AccountPanel'));
