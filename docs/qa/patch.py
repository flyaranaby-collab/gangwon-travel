"""강원 여행 수첩 QA 수정 (2026-11-14). 원본: /home/claude/gangwon/index.html"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/gangwon/index.html'
s = open(P, encoding='utf-8').read()
def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:90])
    s = s.replace(a, b)

# ── P0 보안: 외부 데이터(구글 지도·관광공사)의 이름·주소·사진 주소를 화면에 넣기 전에 정리 ──
rep('const stripTags = v => String(v||"").replace(/<br\\s*\\/?>/gi," ").replace(/<[^>]+>/g,"").replace(/\\s+/g," ").trim();',
    '''const stripTags = v => String(v||"").replace(/<br\\s*\\/?>/gi," ").replace(/<[^>]+>/g,"").replace(/[<>`]/g,"").replace(/"/g,"'").replace(/\\s+/g," ").trim();
// 외부 자료(구글 지도·관광공사)는 누구나 이름을 바꿀 수 있으니, 화면에 넣기 전에 태그·따옴표를 없앤다(스크립트 실행 차단)
const cleanTxt = v => String(v ?? "").replace(/[<>`]/g, "").replace(/"/g, "'").replace(/[\\u0000-\\u001f]/g, " ").trim();
const cleanUrl = v => /^https:\\/\\/[^\\s"'<>`]+$/i.test(String(v||"")) ? String(v) : "";
const cleanId = v => String(v ?? "").replace(/[^\\w-]/g, "");''')
rep('return { id:"kto-"+it.contentid, source:"kto", region, name:stripTags(it.title), cat:ktoCat(it),',
    'return { id:"kto-"+cleanId(it.contentid), source:"kto", region, name:stripTags(it.title), cat:ktoCat(it),')
rep('area:(String(it.addr1||"").split(" ")[1]||REG[region].name).replace(/(시|군)$/,""), lat, lng, img:it.firstimage||"",',
    'area:cleanTxt((String(it.addr1||"").split(" ")[1]||REG[region].name).replace(/(시|군)$/,"")), lat, lng, img:cleanUrl(it.firstimage),')
rep('return { id:"kto-"+it.contentid, source:"kto", region, name:stripTags(it.title), type:"숙박", area:(String(it.addr1||"").split(" ")[1]||"").replace(/(시|군)$/,"") || REG[region].name,',
    'return { id:"kto-"+cleanId(it.contentid), source:"kto", region, name:stripTags(it.title), type:"숙박", area:cleanTxt((String(it.addr1||"").split(" ")[1]||"").replace(/(시|군)$/,"")) || REG[region].name,')
rep('function gmapToPlace(it){\n  let cat = it.cat; const nm = String(it.name||"").trim();',
    'function gmapToPlace(it){\n  let cat = it.cat; const nm = cleanTxt(it.name);\n  it = { ...it, id:cleanId(it.id), area:cleanTxt(it.area), city:cleanTxt(it.city), addr:cleanTxt(it.addr), type:cleanTxt(it.type), tags:(Array.isArray(it.tags)?it.tags:[]).map(cleanTxt) };')

# ── P1: 쓰는 도중 화면이 저절로 새로고침되지 않게 ──
rep('''    if (PM.dirty || PM.busy || PM.edit || HOTED.open){ OSYNC.pending = true; renderOps(); return; }
    location.reload();''', '''    if (PM.dirty || PM.busy || PM.edit || HOTED.open){ OSYNC.pending = true; renderOps(); return; }
    softReload();''')
rep('if (!force && !(PM.dirty || PM.busy || PM.edit || HOTED.open)) location.reload();', 'if (!force && !(PM.dirty || PM.busy || PM.edit || HOTED.open)) softReload();')
rep('if (!(PM.dirty || PM.busy || PM.edit || HOTED.open)) location.reload();', 'if (!(PM.dirty || PM.busy || PM.edit || HOTED.open)) softReload();')

# ── P2 성능: 보이는 화면만 그리고, 숨은 화면은 열 때 그린다 ──
rep('function render(){ renderTop(); renderPlaces(); renderTransitTab(); renderSeasonTab(); renderSouvTab(); renderCourse(); renderDeals(); renderOps(); renderPack(); renderJournal(); renderFavs(); renderCouponBook(); renderMy(); renderMore(); refreshDetail(); }',
'''// 예전엔 탭 13개를 매번 모두 다시 그려 휴대폰에서 한 번 누를 때 0.5초쯤 걸렸다. 지금은 보이는 탭만 그리고, 나머지는 열 때 그린다.
function panelR(){ return { places:()=>renderPlaces(), transit:()=>renderTransitTab(), season:()=>renderSeasonTab(), souv:()=>renderSouvTab(), course:()=>renderCourse(), deals:()=>renderDeals(), ops:()=>renderOps(), pack:()=>renderPack(), journal:()=>renderJournal(), favs:()=>renderFavs(), coupons:()=>renderCouponBook(), my:()=>renderMy(), more:()=>renderMore() }; }
var PANEL_DIRTY;   // 아직 안 그린 탭(var: 스크립트 앞쪽에서 불려도 안전)
function ensurePanel(t){ const R = panelR(); if (PANEL_DIRTY && PANEL_DIRTY.has(t) && R[t]){ PANEL_DIRTY.delete(t); R[t](); draftRestore(); } }
function render(){ PANEL_DIRTY = PANEL_DIRTY || new Set(); const R = panelR(); renderTop(); for (const t in R){ if (t===state.tab){ PANEL_DIRTY.delete(t); R[t](); } else PANEL_DIRTY.add(t); } refreshDetail(); draftRestore(); }''')
rep('''  ["places","transit","season","course","deals","pack","souv","journal","ops","favs","coupons","my","more"].forEach(t=>document.getElementById("tab-"+t).hidden = t!==state.tab);
''', '''  ["places","transit","season","course","deals","pack","souv","journal","ops","favs","coupons","my","more"].forEach(t=>document.getElementById("tab-"+t).hidden = t!==state.tab);
  if (typeof ensurePanel === "function") ensurePanel(state.tab);
''')

# ── P1: 쓰던 글(후기·쿠폰·문의·AI 코스·경비 메모)을 화면이 바뀌거나 앱을 다시 켜도 지키기 ──
rep('// ───────── 뒤로 가기: 탭·검색을 방문 기록으로 남겨,', '''// ───────── 쓰던 글 지키기 ─────────
// 다른 탭에 갔다 오거나 화면이 새로 그려져도, 저장 전 입력이 지워지지 않게 한다. 저장(제출)하면 지운다.
const DRAFT_IDS = ["revText","cpTitle","cpNote","cpTitle2","cpNote2","aiText","inqPlace","inqContact","inqMsg","exAmt","exMemo"];
const DRAFT_KEEP = new Set(["revText","aiText","inqMsg","exMemo","cpNote","cpNote2"]);   // 앱을 껐다 켜도 남길 것(연락처는 저장하지 않음)
var DRAFT = (()=>{ try { return JSON.parse(localStorage.getItem("gw_drafts") || "{}") || {}; } catch(_) { return {}; } })();
const draftSave = () => { try { const k = {}; for (const id in DRAFT) if (DRAFT_KEEP.has(id)) k[id] = DRAFT[id]; localStorage.setItem("gw_drafts", JSON.stringify(k)); } catch(_) {} };
document.addEventListener("input", e=>{ const t = e.target; if (!t || !DRAFT_IDS.includes(t.id)) return;
  DRAFT[t.id] = { v:t.value, ctx: t.id==="revText" ? state.revPick : "" }; draftSave(); }, true);
document.addEventListener("submit", e=>{ const f = e.target; if (!f || !f.querySelectorAll) return;
  f.querySelectorAll("input,textarea").forEach(x=>{ if (DRAFT[x.id]) delete DRAFT[x.id]; }); draftSave(); }, true);
function draftRestore(){
  if (!DRAFT) return;
  for (const id in DRAFT){ const el = document.getElementById(id), d = DRAFT[id]; if (!el || !d || el === document.activeElement) continue;
    if (id==="revText" && d.ctx !== state.revPick) continue;   // 다른 장소를 고르면 그 장소 후기를 보여 준다
    if (el.value !== d.v) el.value = d.v; }
}
// ───────── 새 정보가 도착하면: 아직 아무것도 안 눌렀으면 바로, 쓰는 중이면 알림만 ─────────
var UX = { touched:false, reload:false };
["pointerdown","keydown","input"].forEach(ev=>addEventListener(ev, ()=>{ UX.touched = true; }, { capture:true, passive:true }));
function gwNote(html, id){
  let n = document.getElementById(id); if (!n){ n = document.createElement("div"); n.id = id; n.className = "gwnote"; n.setAttribute("role","status"); document.body.appendChild(n); }
  n.innerHTML = html; n.hidden = !html; return n;
}
function softReload(){
  const busy = UX.touched || !document.getElementById("subPage").hidden || !document.getElementById("searchOv").hidden;
  if (!busy){ location.reload(); return; }
  if (UX.reload) return; UX.reload = true;
  gwNote(`<span>새 장소 정보가 도착했어요.</span><button type="button" class="btn" data-gwreload>지금 반영</button><button type="button" class="btn ghost" data-gwlater aria-label="나중에 반영">나중에</button>`, "gwUpd");
}
document.addEventListener("click", e=>{
  if (e.target.closest("[data-gwreload]")) location.reload();
  else if (e.target.closest("[data-gwlater]")) gwNote("", "gwUpd");   // 다음에 앱을 열면 저절로 반영돼요
});
// ───────── 인터넷이 끊기면 알려 주기(수첩 내용은 그대로 볼 수 있음) ─────────
function netNote(){ gwNote(navigator.onLine === false ? `<span>📴 인터넷이 끊겼어요. 저장된 수첩은 그대로 볼 수 있고, 지도·예매·날씨 같은 바깥 연결은 다시 연결되면 돼요.</span><button type="button" class="btn ghost" data-netx aria-label="알림 닫기">닫기</button>` : "", "gwNet"); }
addEventListener("offline", netNote); addEventListener("online", netNote);
document.addEventListener("click", e=>{ if (e.target.closest("[data-netx]")) gwNote("", "gwNet"); });
// ───────── 뒤로 가기: 탭·검색을 방문 기록으로 남겨,''')
rep('if (t.id==="revPlace"){ pickReview(t.value); renderJournal(); }', 'if (t.id==="revPlace"){ pickReview(t.value); renderJournal(); draftRestore(); }')
rep('initRuntime();\nsetLang(LANG);', 'initRuntime();\nsetLang(LANG);\ndraftRestore(); netNote();', 1)

# 별점 버튼: 화면 읽기 프로그램이 선택 상태를 알 수 있게
rep('''`<button type="button" data-star="${i}" class="${i<=state.revStar?"on":""}" aria-label="${i}점">★</button>`''',
    '''`<button type="button" data-star="${i}" class="${i<=state.revStar?"on":""}" aria-label="${i}점" aria-pressed="${i===state.revStar}">★</button>`''')
rep('document.querySelectorAll(".stars button").forEach(b=>b.classList.toggle("on", +b.dataset.star<=state.revStar)); return;',
    'document.querySelectorAll(".stars button").forEach(b=>{ b.classList.toggle("on", +b.dataset.star<=state.revStar); b.setAttribute("aria-pressed", +b.dataset.star===state.revStar); }); return;')

# ── P1: 문의 — 보낼 수 없는 화면이면 쓰기 전에 미리 알려 주고, 길이 제한 ──
rep('''      <input id="inqPlace" placeholder="가게·장소 이름" value="${esc(i.place)}" required aria-label="가게·장소 이름">
      <input id="inqContact" placeholder="연락처(전화·이메일, 선택)" aria-label="연락처">''',
'''      <input id="inqPlace" placeholder="가게·장소 이름" value="${esc(i.place)}" required maxlength="80" aria-label="가게·장소 이름">
      <input id="inqContact" placeholder="연락처(전화·이메일, 선택)" maxlength="80" autocomplete="off" aria-label="연락처">''')
rep('''<textarea id="inqMsg" placeholder="문의 내용이나 바뀐 정보(영업시간·휴무·가격 등)를 적어 주세요." required aria-label="내용">''',
    '''${!RT.db && !isLocal ? `<p class="notice">이 화면에서는 문의를 바로 보낼 수 없어요. 웹 수첩(claude.ai)에 로그인해서 열면 보낼 수 있어요.</p>` : ""}
    <textarea id="inqMsg" placeholder="문의 내용이나 바뀐 정보(영업시간·휴무·가격 등)를 적어 주세요." required maxlength="2000" aria-label="내용">''')

# ── P2 디자인·접근성 CSS ──
rep('.trainbox .trtoggle { width: 100%; justify-content: center; margin-top: 4px; }\n</style>', '''.trainbox .trtoggle { width: 100%; justify-content: center; margin-top: 4px; }
/* ── 품질 점검(2026-11-14): 누르기 쉬운 크기 · 글자 대비 · 작은 화면 넘침 ── */
.panel .links a, .subpage .links a { display: inline-flex; align-items: center; min-height: 36px; }
.panel button, .subpage button { min-height: 32px; }
.review .meta button { padding: 4px 8px; }
.panel input[type=checkbox], .subpage input[type=checkbox] { width: 20px; height: 20px; flex: none; }
.stars button { min-width: 36px; min-height: 40px; }
.panel select, .subpage select, .cbar input, .revform select { max-width: 100%; min-width: 0; }
.cbar > *, .course > *, .maptools > * { min-width: 0; }
.maptools { flex-wrap: wrap; }
:root { --muted: #5b6477; }
:root:not([data-theme="dark"]) { --brass: #76592b; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --muted: #98a1b2; --brass: #d4b37a; } }
:root[data-theme="dark"] { --muted: #98a1b2; --brass: #d4b37a; }
.hero .seg button[aria-pressed=true] { background: #2b6aa3; }
.bnav button.on { color: #2b6aa3; }
.sitemc em, .ticket .tstamp, .expamt.need { color: #a84b1b; }
.ticket .tstamp { border-color: #a84b1b; }
.ctour .ctlive { color: #15803d; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .bnav button.on { color: #8cc0ee; } :root:not([data-theme="light"]) .sitemc em, :root:not([data-theme="light"]) .expamt.need { color: #f0a070; } :root:not([data-theme="light"]) .ctour .ctlive { color: #6ee7a0; } :root:not([data-theme="light"]) .ctour .ctas { background: var(--sea-soft); color: var(--ink); } :root:not([data-theme="light"]) .opsbar .danger { color: var(--bad); } }
:root[data-theme="dark"] .bnav button.on { color: #8cc0ee; } :root[data-theme="dark"] .sitemc em, :root[data-theme="dark"] .expamt.need { color: #f0a070; } :root[data-theme="dark"] .ctour .ctlive { color: #6ee7a0; } :root[data-theme="dark"] .ctour .ctas { background: var(--sea-soft); color: var(--ink); } :root[data-theme="dark"] .opsbar .danger { color: var(--bad); }
.gwnote { position: fixed; left: 12px; right: 12px; bottom: calc(70px + env(safe-area-inset-bottom, 0px)); z-index: 60; max-width: 560px; margin: 0 auto; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 12px; background: #1d3150; color: #fff; font-size: 14px; box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.gwnote span { flex: 1 1 200px; }
.gwnote .btn { min-height: 36px; padding: 6px 12px; font-size: 13px; }
.gwnote .btn.ghost { color: #fff; border-color: rgba(255,255,255,.5); background: transparent; }
#gwNet { bottom: calc(132px + env(safe-area-inset-bottom, 0px)); }
.gwnote[hidden] { display: none; }
.panel button.tag, .subpage button.tag { min-width: 32px; padding: 2px 4px; }
.leg a { display: inline-flex; align-items: center; min-height: 32px; }
</style>''')
# ── P2 성능: 추천 정렬·날짜 계산을 한 번만 ──
rep("""function tripDays(){
  let s = new Date(state.date+"T00:00:00");""", """var TRIPDAYS_MEMO = null;   // 같은 날짜면 다시 계산하지 않는다(장소마다 휴무 확인할 때 수천 번 불림)
function tripDays(){
  const key = state.date + "|" + state.dateEnd;
  if (TRIPDAYS_MEMO && TRIPDAYS_MEMO.key === key) return TRIPDAYS_MEMO.days.slice();
  const days = tripDaysCalc(); TRIPDAYS_MEMO = { key, days }; return days.slice();
}
function tripDaysCalc(){
  let s = new Date(state.date+"T00:00:00");""")
rep("""const autoHot = () => regionPlaces().filter(p=>status(p).cls!=="closed")
  .sort((a,b)=>b.who[state.who]-a.who[state.who] || (!!photoFor(b)-!!photoFor(a)) || a.name.localeCompare(b.name));""",
"""var KO_COLL = new Intl.Collator();   // localeCompare와 같은 순서, 훨씬 빠름
const autoHot = () => regionPlaces().filter(p=>status(p).cls!=="closed")
  .map(p=>[p, (p.who && p.who[state.who]) || 0, photoFor(p) ? 1 : 0])
  .sort((a,b)=>b[1]-a[1] || b[2]-a[2] || (KO_COLL || (KO_COLL = new Intl.Collator())).compare(a[0].name, b[0].name)).map(x=>x[0]);""")
open(P, 'w', encoding='utf-8').write(s)
print('patched', P)
