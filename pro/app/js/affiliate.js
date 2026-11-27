/* P0-1 멀티 제휴 예약 링크
 * OWNER.biz.partner.{stay,ticket,car} = [{ id, name, tpl, badge, enabled, affId }]
 * - 예전 단일 문자열(partner.stay = "https://...{q}...")도 그대로 동작한다(제휴 링크로 간주, 맨 앞에 표시).
 * - 운영자가 아무것도 정하지 않았으면 js/config.js 의 GW_CONFIG.BIZ.AFFILIATE.partners 를 쓴다.
 * - 제휴 ID 가 없거나 "YOUR_..." placeholder 면 제휴 파라미터를 빼고 일반 검색으로 연결하며 affiliate_mode 를 "fallback" 으로 기록한다.
 */
var AFF_CFG = (window.GW_CONFIG && window.GW_CONFIG.BIZ && window.GW_CONFIG.BIZ.AFFILIATE) || { utm:{ source:"gw_note", medium:"app" }, partners:{} };
var AFF_CATS = { stay:"숙소", ticket:"티켓·체험", car:"렌터카" };
var affRealId = function(v){ v = String(v == null ? "" : v).trim(); return !!v && !/^YOUR_/i.test(v); };
function affNorm(x, i, cat){
  x = x && typeof x === "object" ? x : {};
  return { id:String(x.id || (cat + "-" + i)).replace(/[^\w-]/g, "").slice(0, 30) || (cat + "-" + i), name:String(x.name || "제휴 예약").slice(0, 30),
    tpl:String(x.tpl || ""), badge:String(x.badge || "").slice(0, 12), enabled:x.enabled !== false, affId:String(x.affId == null ? "" : x.affId) };
}
// 지금 쓰는 파트너 목록(운영자 설정 → 기본 설정)
function affPartners(cat, all){
  var B = (typeof OWNER !== "undefined" && OWNER.biz && OWNER.biz.partner) || {}, v = B[cat], out;
  if (Array.isArray(v)) out = v.map(function(x, i){ return affNorm(x, i, cat); });
  else {
    out = (AFF_CFG.partners[cat] || []).map(function(x, i){ return affNorm(x, i, cat); });
    if (typeof v === "string" && /^https:\/\//.test(v))   // 하위 호환: 예전 단일 제휴 링크 틀
      out.unshift({ id:"legacy", name:"제휴 예약", tpl:v, badge:"", enabled:true, affId:"__legacy__" });
  }
  return all ? out : out.filter(function(x){ return x.enabled && /^https:\/\//.test(x.tpl); });
}
// 링크 만들기: {q} 치환, 제휴 ID 처리, UTM 자동 부착
function affUrl(pt, cat, q, targetId){
  var mode = pt.affId === "__legacy__" || affRealId(pt.affId) ? "partner" : "fallback", u;
  try {
    u = new URL(pt.tpl.split("{q}").join(encodeURIComponent(String(q || ""))));
    if (u.protocol !== "https:") throw 0;
    var drop = [];
    u.searchParams.forEach(function(val, key){ if (val.indexOf("{affId}") >= 0) drop.push([key, val]); });
    drop.forEach(function(kv){ if (mode === "partner" && pt.affId !== "__legacy__") u.searchParams.set(kv[0], kv[1].split("{affId}").join(pt.affId)); else u.searchParams.delete(kv[0]); });
    u.searchParams.set("utm_source", AFF_CFG.utm.source || "gw_note");
    u.searchParams.set("utm_medium", AFF_CFG.utm.medium || "app");
    u.searchParams.set("utm_campaign", cat);
    if (targetId) u.searchParams.set("utm_content", String(targetId).slice(0, 60));
    return { href:u.href, mode:mode };
  } catch(_) {
    return { href:"https://search.naver.com/search.naver?query=" + encodeURIComponent(String(q || "") + " 예약"), mode:"fallback" };
  }
}
// 링크 묶음 데이터: 활성 파트너가 하나도 없으면 안전한 네이버 검색 하나로 대신한다
function affLinks(cat, q, targetId, surface){
  var list = affPartners(cat);
  if (!list.length) list = [{ id:"search", name:"예약 검색", tpl:"https://search.naver.com/search.naver?query={q}", badge:"", enabled:true, affId:"" }];
  return list.map(function(pt, i){ var r = affUrl(pt, cat, q, targetId);
    return { label:pt.name, badge:pt.badge, href:r.href, mode:r.mode, primary:i === 0, aff:[cat, pt.id, r.mode, targetId || "", surface || ""].join("|") }; });
}
function affLinksHtml(cat, q, targetId, surface){
  return affLinks(cat, q, targetId, surface).map(function(l){
    return `<a class="afflink${l.primary ? " primary" : ""}" href="${esc(safeUrl(l.href))}" target="_blank" rel="noopener sponsored" data-aff="${esc(l.aff)}">${REV}${esc(l.label)}${l.badge ? `<small class="affbadge">${esc(l.badge)}</small>` : ""}<span aria-hidden="true">↗</span></a>`; }).join("");
}
// 클릭 계측: affiliate_click + 기존 trackRev 집계(운영 탭 '수익 링크 클릭')
document.addEventListener("click", function(e){
  var a = e.target.closest("[data-aff]"); if (!a) return;
  var f = String(a.dataset.aff).split("|"), region = "";
  try { var p = byId(f[3]) || (typeof LODGING !== "undefined" && LODGING.find(function(l){ return l.id === f[3]; })); region = p ? p.region : state.region; } catch(_) {}
  trackEvent("affiliate_click", { category:f[0], partner:f[1], mode:f[2], targetId:f[3], region:region, isPro:isPro(), surface:f[4] });
  try { trackRev(f[0] + ":" + (f[3] || f[1])); } catch(_) {}
});
// 교통 탭 하단: 렌터카 비교 + 교통 패스
function transitAffHtml(){
  var town = state.region === "all" ? "강원" : REG[state.region].q;
  return `<section class="taxi affbox" data-pos="D5" aria-label="렌터카와 교통 패스">
    <div><div class="eyebrow">RENT-A-CAR · PASS</div><h3>${esc(town)} 렌터카 · 교통 패스</h3>
      <p>역·터미널에서 렌터카를 빌리거나 열차 패스로 아끼는 방법이에요. 여러 곳 가격을 비교해 보세요.</p></div>
    <nav class="links afflinks" aria-label="렌터카 예약 비교">${affLinksHtml("car", town + "역", "car-" + state.region, "transit_car")}</nav>
    <nav class="links afflinks" aria-label="교통 패스">
      <a class="afflink" href="${esc(naver("코레일 내일로 패스"))}" target="_blank" rel="noopener" data-aff="${esc(["pass", "korail-pass", "fallback", "pass-" + state.region, "transit_pass"].join("|"))}">코레일 패스(내일로)<span aria-hidden="true">↗</span></a>
      <a class="afflink" href="${esc(naver(town + " 시티투어 버스 예약"))}" target="_blank" rel="noopener" data-aff="${esc(["pass", "citytour", "fallback", "pass-" + state.region, "transit_pass"].join("|"))}">시티투어 예약<span aria-hidden="true">↗</span></a>
    </nav>
    <p class="meta">제휴 링크를 통해 예약하면 앱 운영에 도움이 되는 수수료를 받을 수 있어요. 가격은 각 예약처에서 다시 확인하세요.</p>
  </section>`;
}
// 운영자 수익 설정(bizManager) 안의 '제휴 예약 링크' 편집기
var AFFED = { msg:"" };
function affEnsureOwned(cat){
  var B = OWNER.biz.partner;
  if (!Array.isArray(B[cat])) B[cat] = affPartners(cat, true).map(function(x){ return Object.assign({}, x); });
  return B[cat];
}
function affManagerHtml(){
  var sample = { stay:"강릉 호텔", ticket:"아르떼뮤지엄 강릉", car:"강릉역" };
  return `<h3>3. 제휴 예약 링크 (파트너별)</h3>
    <p class="meta">링크 틀의 {q} 에 장소 이름, {affId} 에 제휴 ID 가 들어가요. 제휴 ID 가 비었거나 YOUR_ 로 시작하면 제휴 파라미터 없이 일반 검색으로 연결돼요(fallback). utm_source=gw_note 등 추적 값은 자동으로 붙어요.</p>
    ${Object.keys(AFF_CATS).map(function(cat){ var list = affPartners(cat, true);
      return `<div class="affcat"><h4>${esc(AFF_CATS[cat])}</h4>${list.map(function(pt, i){ var r = affUrl(pt, cat, sample[cat], "preview");
        return `<div class="affrow">
          <label class="pmday"><input type="checkbox" data-affed="${cat}:${i}:enabled" ${pt.enabled ? "checked" : ""}> 링크 사용</label>
          <label>파트너 이름<input data-affed="${cat}:${i}:name" value="${esc(pt.name)}"></label>
          <label>표시 배지<input data-affed="${cat}:${i}:badge" value="${esc(pt.badge)}" placeholder="예: 최저가"></label>
          <label>제휴 ID<input data-affed="${cat}:${i}:affId" value="${esc(pt.affId === "__legacy__" ? "" : pt.affId)}" placeholder="YOUR_ID"></label>
          <label class="wide">링크 틀<input data-affed="${cat}:${i}:tpl" value="${esc(pt.tpl)}" placeholder="https://제휴사/search?q={q}&amp;aid={affId}"></label>
          <p class="meta wide">미리보기 (${esc(r.mode)}): <a href="${esc(safeUrl(r.href))}" target="_blank" rel="noopener">${esc(r.href.slice(0, 120))}</a> <button class="linkbtn" type="button" data-affdel="${cat}:${i}">빼기</button></p>
        </div>`; }).join("")}
        <button class="btn ghost" type="button" data-affadd="${cat}">${esc(AFF_CATS[cat])} 파트너 추가</button></div>`; }).join("")}
    ${AFFED.msg ? `<p class="okline">${esc(AFFED.msg)}</p>` : ""}`;
}
function affChanged(msg){ AFFED.msg = msg || "제휴 링크 설정을 바꿨어요. ‘저장하고 공개’로 반영하세요."; try { bizRefresh(); } catch(_) {} try { renderOps(); } catch(_) {} }
document.addEventListener("change", function(e){
  var k = e.target.dataset && e.target.dataset.affed; if (!k) return;
  var p = k.split(":"), list = affEnsureOwned(p[0]), it = list[+p[1]]; if (!it) return;
  if (p[2] === "enabled") it.enabled = e.target.checked;
  else if (p[2] === "tpl"){ var v = e.target.value.trim(); if (v && !/^https:\/\//.test(v)){ AFFED.msg = "링크 틀은 https:// 로 시작해야 해요."; renderOps(); return; } it.tpl = v; }
  else it[p[2]] = e.target.value.trim();
  affChanged();
});
document.addEventListener("click", function(e){
  var add = e.target.closest("[data-affadd]"), del = e.target.closest("[data-affdel]");
  if (add){ var l = affEnsureOwned(add.dataset.affadd); l.push({ id:add.dataset.affadd + "-" + Date.now().toString(36), name:"새 파트너", tpl:"https://", badge:"", enabled:false, affId:"" }); affChanged("파트너를 추가했어요. 링크 틀을 넣고 ‘사용’을 켜세요."); }
  if (del){ var q = del.dataset.affdel.split(":"), L = affEnsureOwned(q[0]); L.splice(+q[1], 1); affChanged("파트너를 뺐어요."); }
});
function affStatus(cat){ var l = affPartners(cat); var n = l.filter(function(x){ return x.affId === "__legacy__" || affRealId(x.affId); }).length;
  return n ? ("제휴 " + n + "곳 연결 · 전체 " + l.length + "곳") : ("제휴 ID 미설정 · 일반 검색 " + l.length + "곳"); }
