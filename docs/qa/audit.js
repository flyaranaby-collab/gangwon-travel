// 강원 여행 수첩 품질 점검: node audit.js <url> <out.json>
const { chromium } = require('playwright');
const fs = require('fs');
const URL = process.argv[2], OUT = process.argv[3] || 'audit.json';
const AXE = fs.readFileSync(__dirname + '/node_modules/axe-core/axe.min.js', 'utf8');
const TABS = ['places','transit','season','deals','pack','souv','course','favs','coupons','my','more','journal'];
const R = { errors: [], perf: {}, tabs: {}, layout: {}, a11y: {}, flows: {}, net: {} };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function newPage(b, opt = {}) {
  const ctx = await b.newContext({ viewport: opt.vp || { width: 360, height: 780 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, locale: 'ko-KR', ...opt.ctx });
  const p = await ctx.newPage();
  const tag = opt.tag || 'main';
  await ctx.route('https://qa.gangwon.test/**', r => { const f = process.env.QA_FILE || '/home/claude/gangwon/index.html'; r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: fs.readFileSync(f) }); });
  if (!opt.allowSync) await p.route(/(kto_ver\.txt|gmap\.json|owner\.json)/, r => r.abort());
  p.on('framenavigated', f => { if (f === p.mainFrame()) R.errors.push({ tag, type: 'nav', msg: f.url().slice(0, 100) }); });
  p.on('pageerror', e => R.errors.push({ tag, type: 'pageerror', msg: String(e.message).slice(0, 300) }));
  p.on('console', m => { if (m.type() === 'error') { const t = m.text(); if (!/Failed to load resource|net::ERR|ERR_INTERNET|ERR_NAME|403|404/.test(t)) R.errors.push({ tag, type: 'console', msg: t.slice(0, 300) }); } });
  p.on('dialog', d => { R.errors.push({ tag, type: 'dialog', msg: d.type() + ': ' + d.message().slice(0, 120) }); d.dismiss().catch(() => {}); });
  return { ctx, p };
}

async function goTab(p, t) {
  return p.evaluate(async t => {
    const t0 = performance.now();
    const b = document.querySelector(`[data-tab="${t}"]`);
    if (b && b.offsetParent) b.click(); else { state.tab = t; if (typeof setTab === 'function') setTab(t); else render(); }
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const el = document.getElementById('tab-' + t);
    return { ms: Math.round(performance.now() - t0), shown: !!el && !el.hidden, len: el ? el.innerText.length : 0, active: state.tab };
  }, t);
}

async function layoutCheck(p) {
  return p.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const over = [];
    for (const el of document.querySelectorAll('main *, header *, .tabbar *, .bnav *')) {
      if (!el.offsetParent) continue;
      const r = el.getBoundingClientRect();
      if (r.width && r.right > W + 1 && getComputedStyle(el).position !== 'fixed') {
        let a = el.parentElement, clipped = false;
        while (a && a !== document.body) { const s = getComputedStyle(a); if (/(auto|scroll|hidden|clip)/.test(s.overflowX)) { clipped = true; break; } a = a.parentElement; }
        if (!clipped) over.push((el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + [...el.classList].join('.')) + ' ' + Math.round(r.right - W) + 'px "' + (el.innerText || '').trim().slice(0, 20) + '"');
      }
    }
    const small = [];
    for (const el of document.querySelectorAll('button, a[href], input, select, [role=button]')) {
      if (!el.offsetParent) continue;
      const r = el.getBoundingClientRect();
      if (r.width && r.height && (r.height < 24 || r.width < 24)) small.push(el.tagName.toLowerCase() + ' ' + Math.round(r.width) + 'x' + Math.round(r.height) + ' "' + (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 16) + '"');
    }
    const tiny = [];
    for (const el of document.querySelectorAll('main *')) {
      if (!el.offsetParent || !el.childNodes.length) continue;
      const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
      if (!hasText) continue;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < 11) tiny.push(fs + 'px "' + el.textContent.trim().slice(0, 18) + '"');
    }
    return { pageScrollX: document.documentElement.scrollWidth - W, overflow: [...new Set(over)].slice(0, 15), overflowN: over.length, smallTargets: [...new Set(small)].slice(0, 20), smallN: small.length, tinyText: [...new Set(tiny)].slice(0, 10), tinyN: tiny.length };
  });
}

async function axe(p, label) {
  await p.addScriptTag({ content: AXE });
  const r = await p.evaluate(async () => {
    const res = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] }, resultTypes: ['violations'] });
    return res.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, ex: v.nodes.slice(0, 3).map(n => n.target.join(' ') + ' | ' + (n.failureSummary || '').split('\n')[1]?.slice(0, 90)) }));
  });
  R.a11y[label] = r;
}

// 화면 안 버튼을 모두 눌러 본다(외부 링크·삭제·초기화·다운로드는 제외)
async function clickAll(p, t) {
  return p.evaluate(async t => {
    const panel = document.getElementById('tab-' + t);
    const errs = []; let n = 0, dead = 0; const deadList = [];
    window.__err = []; const oe = e => window.__err.push(String(e.message || e)); window.addEventListener('error', oe);
    window.confirm = () => false; window.alert = () => {}; window.prompt = () => null;
    const sel = 'button, [data-detail], [data-near], [role=button], .chipbtn, summary';
    const skip = /삭제|초기화|지우기|비우기|로그아웃|내보내기|저장하기|다운로드|엑셀|CSV|백업|복원|올리기|토큰|위치|내 주변|km/;
    const seen = new Set();
    for (let pass = 0; pass < 2; pass++) {
      const btns = [...panel.querySelectorAll(sel)].filter(b => b.offsetParent && !b.disabled && !skip.test(b.innerText || '') && !b.closest('a[target=_blank]'));
      for (const b of btns.slice(0, 80)) {
        const key = (b.innerText || b.getAttribute('aria-label') || '').trim().slice(0, 30) + '|' + [...b.attributes].map(a => a.name + '=' + a.value).join(',').slice(0, 80);
        if (seen.has(key)) continue; seen.add(key);
        if (!document.body.contains(b)) continue;
        const before = document.body.innerHTML.length + '|' + location.hash + '|' + (document.getElementById('subPage')?.hidden) + '|' + document.activeElement?.tagName + '|' + b.getAttribute('aria-pressed') + '|' + b.getAttribute('aria-expanded') + '|' + (b.closest('details')?.open);
        const errN = window.__err.length;
        try { b.click(); } catch (e) { errs.push(key + ' → ' + e.message); }
        n++;
        await new Promise(r => setTimeout(r, 30));
        if (window.__err.length > errN) errs.push(key + ' → ' + window.__err.slice(errN).join('; '));
        const after = document.body.innerHTML.length + '|' + location.hash + '|' + (document.getElementById('subPage')?.hidden) + '|' + document.activeElement?.tagName + '|' + b.getAttribute('aria-pressed') + '|' + b.getAttribute('aria-expanded') + '|' + (b.closest('details')?.open);
        if (before === after && b.tagName !== 'SUMMARY') { dead++; if (deadList.length < 12) deadList.push(key.split('|')[0] || key); }
        // 상세 화면이 열렸으면 닫고 원래 탭으로
        const sp = document.getElementById('subPage'); if (sp && !sp.hidden) closeSub();
        const so = document.getElementById('searchOv'); if (so && !so.hidden) closeSearch();
        const zb = document.getElementById('zoomBox'); if (zb && !zb.hidden) zb.hidden = true;
        if (state.tab !== t) { state.tab = t; render(); document.querySelectorAll('.panel').forEach(x => x.hidden = x.id !== 'tab-' + t); }
      }
    }
    window.removeEventListener('error', oe);
    return { clicked: n, errors: errs, noVisibleChange: dead, noChangeEx: deadList };
  }, t);
}

(async () => {
  const b = await chromium.launch();
  // 1) 첫 실행 성능
  {
    const { ctx, p } = await newPage(b, { tag: 'cold' });
    const cdp = await ctx.newCDPSession(p); await cdp.send('Performance.enable');
    const t0 = Date.now();
    await p.goto(URL, { waitUntil: 'domcontentloaded' });
    const dcl = Date.now() - t0;
    await p.waitForFunction(() => document.querySelector('#tab-places .card, #tab-places article'), null, { timeout: 30000 });
    const firstCards = Date.now() - t0;
    await p.waitForLoadState('load').catch(() => {});
    const load = Date.now() - t0;
    await sleep(2500);
    const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x => [x.name, x.value]));
    const nav = await p.evaluate(() => { const n = performance.getEntriesByType('navigation')[0]; const res = performance.getEntriesByType('resource'); return { transferKB: Math.round((n.transferSize + res.reduce((a, r) => a + (r.transferSize || 0), 0)) / 1024), htmlKB: Math.round(n.decodedBodySize / 1024), requests: res.length, domNodes: document.getElementsByTagName('*').length, imgs: document.images.length, lazyImgs: [...document.images].filter(i => i.loading === 'lazy').length, imgsNoAlt: [...document.images].filter(i => !i.hasAttribute('alt')).length, fetches: res.filter(r => r.initiatorType === 'fetch').map(r => r.name.replace(/\?.*/, '').split('/').slice(-1)[0]) }; });
    R.perf.cold = { dclMs: dcl, firstCardsMs: firstCards, loadMs: load, jsHeapMB: +(m.JSHeapUsedSize / 1048576).toFixed(1), scriptMs: Math.round(m.ScriptDuration * 1000), layoutMs: Math.round(m.LayoutDuration * 1000), taskMs: Math.round(m.TaskDuration * 1000), ...nav };
    R.layout.home360 = await layoutCheck(p);
    await axe(p, 'home');
    // 2) 탭 전체
    for (const t of TABS) {
      const r = await goTab(p, t);
      await sleep(150);
      r.layout = await layoutCheck(p);
      r.click = await clickAll(p, t);
      R.tabs[t] = r;
    }
    await goTab(p, 'places');
    // 지역 전체 순회
    R.flows.regions = await p.evaluate(async () => {
      const out = [];
      for (const b of [...document.querySelectorAll('#regionChips button')]) { const t0 = performance.now(); b.click(); await new Promise(r => setTimeout(r, 20)); out.push(b.innerText.trim().split('\n')[0] + ':' + Math.round(performance.now() - t0) + 'ms/' + document.querySelectorAll('#tab-places .card, #tab-places article').length); }
      return out;
    });
    // 3) 상세 화면 전부 열기
    R.flows.details = await p.evaluate(async () => {
      const ids = [...new Set([...document.querySelectorAll('[data-detail]')].map(e => e.dataset.detail))];
      const keys = typeof PLACES !== 'undefined' ? PLACES.map(x => 'p:' + x.id) : [];
      let ok = 0, bad = [], slow = [];
      for (const k of [...new Set([...ids, ...keys])]) {
        const [kk, ...rest] = k.split(':'); const id = rest.join(':');
        const t0 = performance.now();
        try { openDetail(kk, id, false); const sp = document.getElementById('subPage'); if (sp && !sp.hidden && document.getElementById('subBody').innerText.length > 20) ok++; else bad.push(k); } catch (e) { bad.push(k + ' ' + e.message); }
        const ms = performance.now() - t0; if (ms > 100) slow.push(k + ' ' + Math.round(ms) + 'ms');
        closeSub();
      }
      return { total: ok + bad.length, ok, bad: bad.slice(0, 20), badN: bad.length, slow: slow.slice(0, 10) };
    });
    await axe(p, 'detail').catch(() => {});
    // 4) 검색
    R.flows.search = await p.evaluate(async () => {
      const out = {};
      document.getElementById('searchBtn').click(); await new Promise(r => setTimeout(r, 100));
      const q = document.getElementById('searchQ');
      for (const w of ['칼국수', '주문진', '경포', 'ㄱ', '<img src=x onerror=alert(1)>', '"><script>alert(1)</script>', '   ', 'a'.repeat(500), '오죽헌', 'xyzxyz없음']) {
        q.value = w; q.dispatchEvent(new Event('input', { bubbles: true })); await new Promise(r => setTimeout(r, 250));
        const res = document.getElementById('searchRes');
        out[w.slice(0, 20)] = { items: res.querySelectorAll('a,button,article,li').length, text: res.innerText.trim().slice(0, 60).replace(/\n/g, ' '), injected: !!res.querySelector('img[src=x], script') };
      }
      return out;
    });
    await p.evaluate(() => closeSearch());
    // 5) 저장 → 재실행 유지
    R.flows.persist = await p.evaluate(() => {
      const fav = document.querySelector('#tab-places [data-fav], #tab-places .fav, #tab-places [aria-label*="찜"]');
      const out = { favBtn: !!fav };
      if (fav) { fav.click(); }
      out.favCountBefore = document.getElementById('favCount')?.innerText;
      const add = document.querySelector('#tab-places [data-add], #tab-places [data-course], #tab-places [aria-label*="일정"]');
      out.addBtn = !!add; if (add) add.click();
      out.courseBefore = document.getElementById('courseCount')?.innerText;
      out.keys = Object.keys(localStorage).length;
      return out;
    });
    await p.reload(); await p.waitForTimeout(1500);
    Object.assign(R.flows.persist, await p.evaluate(() => ({ favCountAfter: document.getElementById('favCount')?.innerText, courseAfter: document.getElementById('courseCount')?.innerText, tabAfterReload: state.tab, hash: location.hash })));
    // 6) 뒤로 가기
    R.flows.back = await p.evaluate(async () => {
      const w = () => new Promise(r => setTimeout(r, 150)); const log = [];
      document.querySelector('.tabs [data-tab="transit"]').click(); await w(); log.push('탭이동:' + state.tab);
      const d = document.querySelector('#tab-transit [data-detail], #tab-places [data-detail]');
      document.querySelector('.tabs [data-tab="places"]').click(); await w();
      const d2 = document.querySelector('#tab-places [data-detail]'); if (d2) { d2.click(); await w(); log.push('상세열림:' + !document.getElementById('subPage').hidden); }
      history.back(); await w(); log.push('뒤로1→상세닫힘:' + document.getElementById('subPage').hidden + ' 탭:' + state.tab);
      history.back(); await w(); log.push('뒤로2→탭:' + state.tab);
      document.getElementById('searchBtn').click(); await w(); log.push('검색열림:' + !document.getElementById('searchOv').hidden);
      history.back(); await w(); log.push('뒤로→검색닫힘:' + document.getElementById('searchOv').hidden);
      return log;
    });
    // 7) 연타
    R.flows.rapid = await p.evaluate(async () => {
      const errN = (window.__err || []).length; const t0 = performance.now();
      const tabs = [...document.querySelectorAll('.tabs [data-tab], .bnav [data-tab]')].filter(b => b.offsetParent);
      for (let i = 0; i < 60; i++) tabs[i % tabs.length].click();
      const d = document.querySelector('#tab-' + state.tab + ' [data-detail]');
      const fav = document.querySelector('[data-fav]'); const before = fav && fav.getAttribute('aria-pressed');
      if (fav) for (let i = 0; i < 9; i++) fav.click();
      return { ms: Math.round(performance.now() - t0), finalTab: state.tab, panelsShown: [...document.querySelectorAll('.panel')].filter(x => !x.hidden).length, favToggledOdd: fav ? before !== fav.getAttribute('aria-pressed') : null };
    });
    // 8) 메모리 - 탭 300회 전환
    R.perf.memory = await p.evaluate(async () => {
      const h0 = performance.memory?.usedJSHeapSize; const tabs = ['places', 'transit', 'season', 'deals', 'pack', 'souv', 'course', 'favs', 'my', 'more'];
      for (let i = 0; i < 300; i++) { const b = document.querySelector(`[data-tab="${tabs[i % tabs.length]}"]`); if (b && b.offsetParent) b.click(); else { state.tab = tabs[i % tabs.length]; render(); } if (i % 20 === 0) await new Promise(r => setTimeout(r, 0)); }
      await new Promise(r => setTimeout(r, 500));
      return { beforeMB: +(h0 / 1048576).toFixed(1), afterMB: +(performance.memory?.usedJSHeapSize / 1048576).toFixed(1), listeners: typeof getEventListeners };
    });
    // 렌더 함수 비용
    R.perf.render = await p.evaluate(() => { const t0 = performance.now(); for (let i = 0; i < 5; i++) render(); return Math.round((performance.now() - t0) / 5) + 'ms/회'; });
    await ctx.close();
  }
  // 9) 오프라인 첫 실행
  {
    const { ctx, p } = await newPage(b, { tag: 'offline' });
    await p.route(/^(?!https:\/\/qa\.gangwon\.test)/, r => { const u = r.request().url(); if (u.startsWith(URL.split('/').slice(0, 3).join('/'))) r.fallback(); else r.abort('internetdisconnected'); });
    const t0 = Date.now();
    await p.goto(URL); await p.waitForTimeout(3000);
    R.net.offline = await p.evaluate(() => ({ cards: document.querySelectorAll('#tab-places .card, #tab-places article').length, notice: (document.body.innerText.match(/(인터넷|오프라인|연결)[^\n]{0,40}/) || [''])[0], brokenImgs: [...document.images].filter(i => i.complete && !i.naturalWidth && i.offsetParent).length, imgsVisible: [...document.images].filter(i => i.offsetParent).length }));
    R.net.offline.ms = Date.now() - t0;
    for (const t of ['transit', 'season']) { await goTab(p, t); }
    R.net.offlineTransit = await p.evaluate(() => (document.getElementById('trainBox')?.innerText || '').slice(0, 120));
    await ctx.close();
  }
  // 10) 느린 3G
  {
    const { ctx, p } = await newPage(b, { tag: 'slow3g' });
    const cdp = await ctx.newCDPSession(p);
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 400, downloadThroughput: 400 * 1024 / 8, uploadThroughput: 400 * 1024 / 8 });
    const t0 = Date.now();
    await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    const dcl = Date.now() - t0;
    await p.waitForFunction(() => document.querySelector('#tab-places .card, #tab-places article'), null, { timeout: 120000 }).catch(() => {});
    R.net.slow3g = { dclMs: dcl, firstCardsMs: Date.now() - t0 };
    await ctx.close();
  }
  // 11) 화면 크기·글자 확대·가로
  for (const [name, vp] of [['w320', { width: 320, height: 640 }], ['zoom150', { width: 240, height: 520 }], ['landscape', { width: 780, height: 360 }], ['tablet', { width: 820, height: 1180 }]]) {
    const { ctx, p } = await newPage(b, { tag: name, vp });
    await p.goto(URL); await p.waitForTimeout(1500);
    const per = {};
    for (const t of ['places', 'transit', 'course', 'my', 'more']) { await goTab(p, t); await sleep(100); const l = await layoutCheck(p); per[t] = { scrollX: l.pageScrollX, overflowN: l.overflowN, ex: l.overflow.slice(0, 4) }; }
    const d = await p.evaluate(() => { const x = document.querySelector('[data-detail]'); if (x) x.click(); return !!x; });
    await sleep(200); const l = await layoutCheck(p); per.detail = { scrollX: l.pageScrollX, overflowN: l.overflowN, ex: l.overflow.slice(0, 4) };
    await p.screenshot({ path: __dirname + `/shot-${name}.png` });
    R.layout[name] = per;
    await ctx.close();
  }
  // 12) 다크 모드 대비
  {
    const { ctx, p } = await newPage(b, { tag: 'dark', ctx: { colorScheme: 'dark' } });
    await p.goto(URL); await p.waitForTimeout(1500);
    await axe(p, 'dark-home');
    await p.screenshot({ path: __dirname + '/shot-dark.png' });
    await ctx.close();
  }
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1));
  await b.close();
  console.log('done', R.errors.length, 'errors');
})().catch(e => { console.error(e); fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); process.exit(1); });
