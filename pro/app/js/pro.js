/* P0-2 강원 수첩 Pro: 상태(gn_pro) · Paywall 모달(#proModal) · 멤버십 카드 · QA 구독 토글
 * 실결제는 없다. '테스트 모드'로 Pro 를 켜고 끄며 잠금/해제 흐름과 전환 퍼널을 검증한다.
 * 무료 유지: 장소 탐색·지도·1개 여행 일정·오프라인 열람·기본 경비 입력(CSV 포함)
 * Pro 전용: ① 여행 수첩 2개 이상 ② 스마트 코스 하루 무료 횟수 초과·다일 일괄 ③ 경비 엑셀(.xlsx)+요약 리포트 ④ 추천 가게 광고 숨김
 */
var PRO_KEY = "gn_pro";
var PRO_CFG = (window.GW_CONFIG && window.GW_CONFIG.BIZ && window.GW_CONFIG.BIZ.PRO) || { plans:{}, smartCourseFreePerDay:2, freeTrips:1 };
var PRO_TIERS = ["free", "pass7", "annual"];
function proState(){
  var s = null;
  try { s = JSON.parse(localStorage.getItem(PRO_KEY) || "null"); } catch(_) {}
  if (!s || typeof s !== "object" || PRO_TIERS.indexOf(s.tier) < 0) s = { tier:"free", active:false, expiresAt:null, testMode:true };
  if (s.active && s.expiresAt && new Date(s.expiresAt) < new Date()) s = { tier:"free", active:false, expiresAt:null, testMode:!!s.testMode, expired:true };
  return s;
}
function proTier(){ var s = proState(); return s.active ? s.tier : "free"; }
function isPro(){ return proTier() !== "free"; }
function proBadge(){ return isPro() ? "" : `<span class="probadge" aria-label="Pro 전용">PRO</span>`; }
function proPlanName(t){ var p = PRO_CFG.plans[t]; return t === "free" ? "무료" : (p ? p.name : t); }
function proPrice(t){ var p = PRO_CFG.plans[t]; return p ? p.price.toLocaleString("ko-KR") + "원" : ""; }
function setProTier(tier, trigger){
  if (PRO_TIERS.indexOf(tier) < 0) tier = "free";
  var from = proTier(), plan = PRO_CFG.plans[tier];
  var s = tier === "free" ? { tier:"free", active:false, expiresAt:null, testMode:true }
    : { tier:tier, active:true, expiresAt:new Date(Date.now() + (plan ? plan.days : 7) * 864e5).toISOString(), testMode:true };
  try { localStorage.setItem(PRO_KEY, JSON.stringify(s)); } catch(_) {}
  trackEvent("pro_toggle_change", { fromTier:from, toTier:tier, trigger:trigger || "qa_toggle" });
  proApplyUi();
  return s;
}
// Pro 상태가 바뀌면 광고 숨김·잠금 배지를 바로 반영한다
function proApplyUi(){
  document.body.classList.toggle("is-pro", isPro());
  try { render(); } catch(_) {}
}
var PAYWALL = { trigger:"", surface:"", plan:"annual", msg:"" };
var PAYWALL_COPY = {
  multi_trip: "여행 수첩을 2개 이상 만들려면 Pro 가 필요해요.",
  smart_course: "오늘 무료 스마트 코스를 모두 썼어요. Pro 는 무제한·다일 일괄 코스를 지원해요.",
  xlsx: "경비 엑셀 저장과 분류별 요약 리포트는 Pro 기능이에요. CSV 저장은 무료예요.",
  ad_free: "Pro 를 켜면 추천 가게 광고가 숨겨져요.",
  guide: "강원 수첩 Pro 혜택을 확인해 보세요."
};
var PRO_PLAN_DESC = {
  pass7: { sub:"한 번 여행에 가볍게", tag:"" },
  annual: { sub:"1년 내내 모든 여행", tag:"추천" }
};
function paywallHtml(){
  var P = PRO_CFG.plans, on = isPro();
  var row = function(k, free, pro){ return `<tr><td>${esc(k)}</td><td>${free}</td><td>${pro}</td></tr>`; };
  return `<div class="redeem-card procard" role="dialog" aria-modal="true" aria-labelledby="proTitle">
    <div class="prohead"><span class="probadge big">PRO</span><h2 id="proTitle">강원 수첩 Pro</h2>
      <p class="prolead">${esc(PAYWALL_COPY[PAYWALL.trigger] || PAYWALL_COPY.guide)}</p>
      <p class="meta">기본 탐색·지도·오프라인 열람은 계속 무료예요.</p></div>
    <div class="wrap"><table class="protable"><thead><tr><th>기능</th><th>무료</th><th>Pro</th></tr></thead><tbody>
      ${row("장소 탐색·지도·오프라인 열람", "✓", "✓")}
      ${row("여행 수첩(일정)", "1개", "무제한")}
      ${row("스마트 맞춤 코스", "하루 " + PRO_CFG.smartCourseFreePerDay + "회", "무제한 · 다일 일괄")}
      ${row("경비 기록 · CSV", "✓", "✓")}
      ${row("경비 엑셀(.xlsx) · 요약 리포트", "—", "✓")}
      ${row("추천 가게 광고", "보임", "숨김")}
    </tbody></table></div>
    <div class="proplans" role="group" aria-label="플랜 선택">${["pass7", "annual"].filter(function(t){ return P[t]; }).map(function(t){
      var d = PRO_PLAN_DESC[t] || {}, sel = PAYWALL.plan === t;
      return `<button type="button" class="proplan" data-proplan="${t}" aria-pressed="${sel}">
        <span class="pptop"><b>${esc(proPlanName(t))}</b>${d.tag ? `<em class="pptag">${esc(d.tag)}</em>` : ""}<span class="ppchk" aria-hidden="true">${sel ? "✓" : ""}</span></span>
        <strong class="ppprice">${esc(proPrice(t))}</strong>
        ${d.sub ? `<small>${esc(d.sub)}</small>` : ""}</button>`; }).join("")}</div>
    <p class="meta prodisc">실제 결제는 아직 연결되지 않았어요. 지금은 테스트 모드로만 체험할 수 있어요.</p>
    ${PAYWALL.msg ? `<p class="okline">${esc(PAYWALL.msg)}</p>` : ""}
    <div class="redeem-row">
      ${on ? `<button class="btn" type="button" data-proact="close">닫기</button>`
           : `<button class="btn" type="button" data-proact="test" id="proTestOn">테스트 모드: Pro 바로 체험 켜기</button><button class="btn ghost" type="button" data-proact="close">나중에</button>`}
    </div></div>`;
}
function openPaywall(trigger, surface){
  closePaywall();
  PAYWALL.trigger = trigger || "guide"; PAYWALL.surface = surface || ""; PAYWALL.msg = "";
  var box = document.createElement("div"); box.id = "proModal"; box.className = "redeem-scrim promodal";
  box.innerHTML = paywallHtml();
  box.addEventListener("click", function(e){
    e.stopPropagation();
    var pl = e.target.closest("[data-proplan]"), a = e.target.closest("[data-proact]");
    if (pl){ PAYWALL.plan = pl.dataset.proplan; trackEvent("pro_plan_select", { plan:PAYWALL.plan, trigger:PAYWALL.trigger, surface:PAYWALL.surface }); box.innerHTML = paywallHtml(); return; }
    if (a && a.dataset.proact === "test"){ setProTier(PAYWALL.plan, PAYWALL.trigger); PAYWALL.msg = proPlanName(PAYWALL.plan) + " 테스트 모드를 켰어요."; box.innerHTML = paywallHtml(); return; }
    if ((a && a.dataset.proact === "close") || e.target === box) closePaywall();
  });
  box.addEventListener("keydown", function(e){ if (e.key === "Escape") closePaywall(); });
  document.body.appendChild(box);
  trackEvent("paywall_view", { trigger:PAYWALL.trigger, surface:PAYWALL.surface });
  var f = box.querySelector('[data-proplan][aria-pressed="true"]') || box.querySelector("[data-proplan]"); if (f) f.focus({ preventScroll:true });
}
function closePaywall(){ var b = document.getElementById("proModal"); if (b) b.remove(); }
// 잠긴 기능 진입: Pro 면 true, 아니면 Paywall 을 열고 false
function requirePro(trigger, surface){ if (isPro()) return true; openPaywall(trigger, surface); return false; }
// 마이페이지 상단 멤버십 카드 + 개발/QA 용 구독 상태 전환 토글
function proMemberCardHtml(){
  var s = proState(), t = proTier(), exp = s.active && s.expiresAt ? new Date(s.expiresAt) : null;
  return `<section class="procard-my${t !== "free" ? " on" : ""}" aria-label="멤버십" data-pos="M1">
    <div class="pmhead"><span class="probadge big">PRO</span><div><span class="meta">내 멤버십</span><b>${esc(proPlanName(t))}</b>
      ${exp ? `<small>만료일 ${esc(exp.getFullYear() + "-" + String(exp.getMonth() + 1).padStart(2, "0") + "-" + String(exp.getDate()).padStart(2, "0"))}</small>` : `<small>핵심 기능은 계속 무료예요</small>`}</div></div>
    ${t === "free" ? `<button class="btn" type="button" data-paywall="guide">Pro 혜택 보기</button>` : `<p class="okline">Pro 혜택 사용 중 · 광고 숨김 · 무제한 스마트 코스</p>`}
    <div class="qa"><span class="meta">개발/QA 용 구독 상태 (테스트 모드)</span>
      <span class="seg" role="group" aria-label="구독 상태 전환">${PRO_TIERS.map(function(k){ return `<button type="button" data-protier="${k}" aria-pressed="${k === t}">${esc(proPlanName(k))}</button>`; }).join("")}</span></div>
  </section>`;
}
document.addEventListener("click", function(e){
  var p = e.target.closest("[data-paywall]"); if (p){ openPaywall(p.dataset.paywall, "button"); return; }
  var q = e.target.closest("[data-protier]"); if (q && !e.target.closest("#proModal")){ setProTier(q.dataset.protier, "qa_toggle"); return; }
});
// ③ 경비 엑셀 내보내기는 Pro. CSV 는 무료. (main.js 의 경비 처리보다 먼저 가로챈다)
document.addEventListener("click", function(e){
  var b = e.target.closest("[data-exp]"); if (!b) return;
  var a = b.dataset.exp, n = 0;
  try { n = EXP.list.length; } catch(_) {}
  if (a === "xlsx" && !isPro()){ e.stopImmediatePropagation(); e.preventDefault(); openPaywall("xlsx", "expense"); return; }
  if (a === "xlsx" || a === "csv") trackEvent("expense_export", { format:a, itemCount:n });
}, true);
document.addEventListener("DOMContentLoaded", function(){ document.body.classList.toggle("is-pro", isPro()); });
