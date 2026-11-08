// Deterministic fake-clock/speech/audio/transport tests. No browser or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const source = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../src/lib/ziwei/narration.ts'), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
function rig({ paid = true } = {}) {
  let now = 0, id = 0, invalidated = 0, speechCancels = 0;
  const timers = new Map(), requests = [], speeches = [], audios = [], urls = [], revoked = [];
  let transport = () => new Promise(() => {}), play = () => Promise.resolve();
  const speech = { getVoices: () => [], cancel: () => { speechCancels++; }, speak: utterance => speeches.push(utterance) };
  const context = {
    exports: {}, AbortController, DOMException, Promise,
    window: { speechSynthesis: speech },
    SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } },
    setTimeout: (fn, delay) => { const token = ++id; timers.set(token, { fn, at: now + delay }); return token; },
    clearTimeout: token => timers.delete(token),
    fetch: (url, options) => { requests.push({ url, options }); return transport(url, options); },
    URL: { createObjectURL: () => { const url = `blob:fake-${urls.length}`; urls.push(url); return url; }, revokeObjectURL: url => revoked.push(url) },
    Audio: class { constructor(url) { this.url = url; this.pauses = 0; audios.push(this); } play() { return play(this); } pause() { this.pauses++; } },
    require: name => {
      if (name.endsWith('/product/config')) return { paidProduct: paid };
      if (name.endsWith('/product/account')) return { paidRequestHeaders: () => paid ? { 'X-Paid-Client': '1' } : {}, paidRequestOptions: () => paid ? { credentials: 'include' } : {}, invalidatePaidSession: () => { invalidated++; } };
      if (name === '@/lib/api') return { API_BASE: '/api/v1' };
      if (name === './text') return { stripMarkdown: text => text };
      throw Error(`Unexpected import ${name}`);
    },
  };
  vm.runInNewContext(source, context);
  return {
    ...context.exports, timers, requests, speeches, audios, urls, revoked, speech,
    get invalidated() { return invalidated; }, get speechCancels() { return speechCancels; },
    transport(fn) { transport = fn; }, playback(fn) { play = fn; },
    utterance(fn) { context.SpeechSynthesisUtterance = fn; },
    audioConstructor(fn) { context.Audio = fn; },
    revoke(fn) { context.URL.revokeObjectURL = fn; },
    async advance(ms) {
      const end = now + ms;
      while (true) {
        const next = [...timers.entries()].filter(([, v]) => v.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        now = next[1].at; timers.delete(next[0]); next[1].fn(); await flush();
      }
      now = end; await flush();
    },
  };
}
const track = promise => { const result = { done: false }; promise.then(() => { result.done = true; }); return result; };
const ok = () => ({ ok: true, status: 200, blob: async () => ({ fake: 'audio' }) });
const endSpeech = async r => { r.speeches.at(-1)?.onend?.(); await flush(); };

(async () => {
  // Header and body stalls share one deadline, each falling back once without retry.
  for (const phase of ['headers', 'body']) {
    const r = rig(), late = deferred();
    r.transport(() => phase === 'headers' ? late.promise : Promise.resolve({ ok: true, blob: () => late.promise }));
    const voice = new r.CloudNarration(), done = track(voice.speak('timeout'));
    await flush(); await r.advance(14999);
    assert.equal(r.speeches.length, 0); assert.equal(done.done, false);
    await r.advance(1);
    assert.equal(r.requests[0].options.signal.aborted, true);
    assert.equal(r.speeches.length, 1); assert.equal(r.requests.length, 1);
    await endSpeech(r); assert.equal(done.done, true);
    late.resolve(phase === 'headers' ? ok() : {}); await flush();
    assert.equal(r.audios.length, 0); assert.equal(r.urls.length, 0); assert.equal(r.timers.size, 0);
    assert.equal(r.requests[0].options.credentials, 'include');
    assert.equal(r.requests[0].options.headers['X-Paid-Client'], '1');
  }
  // Cancel hangs immediately, ignores late transport/body completions, and never speaks fallback.
  for (const phase of ['headers', 'body']) {
    const r = rig(), late = deferred();
    r.transport(() => phase === 'headers' ? late.promise : Promise.resolve({ ok: true, blob: () => late.promise }));
    const voice = new r.CloudNarration(), done = track(voice.speak('cancel'));
    await flush(); voice.cancel(); await flush();
    assert.equal(done.done, true); assert.equal(r.requests[0].options.signal.aborted, true);
    late.resolve(phase === 'headers' ? ok() : {}); await flush(); await r.advance(60000);
    assert.equal(r.speeches.length, 0); assert.equal(r.audios.length, 0); assert.equal(r.timers.size, 0);
  }
  // Playback that never ends (including unresolved play()) times out and releases exactly one URL.
  for (const playHangs of [false, true]) {
    const r = rig(); r.transport(async () => ok());
    if (playHangs) r.playback(() => new Promise(() => {}));
    const done = track(new r.CloudNarration().speak('playback hang')); await flush();
    await r.advance(30000);
    assert.equal(r.speeches.length, 1); assert.equal(r.audios[0].pauses, 1);
    assert.deepEqual(r.revoked, r.urls); assert.equal(r.audios[0].onended, null);
    await r.advance(30000); assert.equal(done.done, true); assert.equal(r.timers.size, 0);
  }
  // Browser speech itself is bounded even when its callbacks never arrive.
  {
    const r = rig(), voice = new r.BrowserNarration(), done = track(voice.speak('browser hang'));
    await r.advance(29999); assert.equal(done.done, false);
    await r.advance(1); assert.equal(done.done, true); assert.equal(r.timers.size, 0);
    assert.equal(r.speeches[0].onend, null); assert.ok(r.speechCancels >= 2);
    const old = track(voice.speak('first')); const latest = track(voice.speak('second')); await flush();
    assert.equal(old.done, true); assert.equal(latest.done, false);
    voice.cancel(); await flush(); assert.equal(latest.done, true); assert.equal(r.timers.size, 0);
  }
  // Browser API exceptions must not reject/strand the reading queue.
  {
    const r = rig();
    r.speech.getVoices = () => { throw Error('voice list unavailable'); };
    r.speech.cancel = () => { throw Error('cancel unavailable'); };
    r.speech.speak = () => { throw Error('speech unavailable'); };
    const done = track(new r.BrowserNarration().speak('browser failure')); await flush();
    assert.equal(done.done, true); assert.equal(r.timers.size, 0);
  }
  {
    const r = rig(); r.utterance(class { constructor() { throw Error('constructor unavailable'); } });
    const done = track(new r.BrowserNarration().speak('constructor failure')); await flush();
    assert.equal(done.done, true); assert.equal(r.timers.size, 0);
  }
  {
    const r = rig(); r.speech.cancel = () => { throw Error('cancel unavailable'); };
    const done = track(new r.BrowserNarration().speak('timeout despite failed browser cancel'));
    await r.advance(30000); assert.equal(done.done, true); assert.equal(r.timers.size, 0);
  }
  // Successful/error/rejected playback and explicit cancellation all release resources.
  for (const outcome of ['ended', 'error', 'rejected', 'cancel']) {
    const r = rig(); r.transport(async () => ok());
    if (outcome === 'rejected') r.playback(() => Promise.reject(Error('denied')));
    const voice = new r.CloudNarration(), done = track(voice.speak(outcome)); await flush();
    if (outcome === 'ended') r.audios[0].onended();
    if (outcome === 'error') r.audios[0].onerror();
    if (outcome === 'cancel') voice.cancel();
    await flush();
    const fallback = outcome === 'error' || outcome === 'rejected';
    assert.equal(r.speeches.length, Number(fallback));
    if (fallback) await endSpeech(r);
    assert.equal(done.done, true); assert.deepEqual(r.revoked, r.urls); assert.equal(r.revoked.length, 1);
    assert.equal(r.timers.size, 0); assert.equal(r.requests.length, 1);
  }
  for (const phase of ['fetch', 'body', 'audio-constructor']) {
    const r = rig();
    r.transport(() => phase === 'fetch' ? Promise.reject(Error('network')) : Promise.resolve(
      phase === 'body' ? { ok: true, blob: async () => { throw Error('body'); } } : ok()));
    if (phase === 'audio-constructor') r.audioConstructor(class { constructor() { throw Error('audio unavailable'); } });
    const done = track(new r.CloudNarration().speak('failure')); await flush();
    assert.equal(r.requests.length, 1); assert.equal(r.speeches.length, 1);
    await endSpeech(r); assert.equal(done.done, true); assert.deepEqual(r.revoked, r.urls); assert.equal(r.timers.size, 0);
  }
  // Host cleanup failures cannot strand playback or cancel promises.
  for (const outcome of ['ended', 'error', 'cancel', 'timeout']) {
    const r = rig(); r.transport(async () => ok());
    let revokeAttempts = 0;
    r.revoke(() => { revokeAttempts++; throw Error('revoke unavailable'); });
    const voice = new r.CloudNarration(), done = track(voice.speak('cleanup exceptions')); await flush();
    r.audios[0].pause = () => { throw Error('pause unavailable'); };
    if (outcome === 'ended') r.audios[0].onended();
    if (outcome === 'error') r.audios[0].onerror();
    if (outcome === 'cancel') voice.cancel();
    if (outcome === 'timeout') await r.advance(30000);
    await flush();
    if (outcome === 'error' || outcome === 'timeout') await endSpeech(r);
    assert.equal(done.done, true); assert.equal(revokeAttempts, 1); assert.equal(r.timers.size, 0);
    voice.cancel(); assert.equal(revokeAttempts, 1);
  }
  // Older requests cannot overwrite or cancel newer audio on the same narrator.
  {
    const r = rig(), late = deferred(); let calls = 0;
    r.transport(() => ++calls === 1 ? late.promise : Promise.resolve(ok()));
    const voice = new r.CloudNarration(), old = track(voice.speak('old')); await flush();
    const current = track(voice.speak('new')); await flush();
    assert.equal(old.done, true); assert.equal(r.audios.length, 1);
    late.resolve(ok()); await flush(); assert.equal(r.audios.length, 1); assert.equal(r.audios[0].pauses, 0);
    r.audios[0].onended(); await flush(); assert.equal(current.done, true); assert.equal(r.timers.size, 0);
  }
  // Replacing active playback removes its handlers; stale browser callbacks cannot stop the replacement.
  {
    const r = rig(); r.transport(async () => ok());
    const voice = new r.CloudNarration(), old = track(voice.speak('old')); await flush();
    const staleEnd = r.audios[0].onended;
    const current = track(voice.speak('new')); await flush(); staleEnd(); await flush();
    assert.equal(old.done, true); assert.equal(current.done, false); assert.equal(r.audios[1].pauses, 0);
    voice.cancel(); await flush(); assert.equal(current.done, true); assert.deepEqual(r.revoked, r.urls);
    assert.equal(r.speeches.length, 0); assert.equal(r.timers.size, 0);
  }
  // Paid expiry never speaks private fallback; missing provider disables future cloud attempts.
  for (const status of [401, 503, 500]) {
    const r = rig(); r.transport(async () => ({ ok: false, status }));
    const voice = new r.CloudNarration(), first = track(voice.speak('first')); await flush();
    assert.equal(r.invalidated, status === 401 ? 1 : 0);
    assert.equal(r.speeches.length, status === 401 ? 0 : 1);
    if (status !== 401) await endSpeech(r);
    assert.equal(first.done, true);
    const second = track(voice.speak('second')); await flush();
    assert.equal(r.requests.length, status === 503 ? 1 : 2);
    voice.cancel(); await flush(); assert.equal(second.done, true); assert.equal(r.timers.size, 0);
  }
  // Portal still falls back on 401 rather than invalidating a nonexistent paid session.
  {
    const r = rig({ paid: false }); r.transport(async () => ({ ok: false, status: 401 }));
    const done = track(new r.CloudNarration().speak('portal')); await flush();
    assert.equal(r.invalidated, 0); assert.equal(r.speeches.length, 1);
    assert.equal(r.requests[0].options.credentials, undefined);
    assert.equal(r.requests[0].options.headers['X-Paid-Client'], undefined);
    await endSpeech(r); assert.equal(done.done, true); assert.equal(r.timers.size, 0);
  }
  console.log('PASS narration reliability: request/body/playback/speech deadlines, cancellation, overlap, late completions, URL cleanup, paid expiry, no provider retry');
})().catch(error => { console.error(error); process.exitCode = 1; });
