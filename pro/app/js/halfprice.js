/* P0-6 강원 반값여행(평창·영월·횡성) & 정책 혜택 계산기 — 클라이언트 단독.
 * 정책 기준·한도는 시기별로 바뀌므로 화면에 '공식 공고 확인 필수'를 늘 표시한다. 기본값은 js/config.js 의 HALFPRICE.
 */
var HP_CFG = (window.GW_CONFIG && window.GW_CONFIG.BIZ && window.GW_CONFIG.BIZ.HALFPRICE) || { rate:0.5, capPerPerson:100000, capPerTeam:200000, regions:[] };
var HP = (function(){ var d = { region:"pyeongchang", people:2, stay:150000, food:100000, act:50000, res:null };
  try { var s = JSON.parse(localStorage.getItem("gn_halfprice") || "null"); if (s) d = Object.assign(d, s); } catch(_) {} return d; })();
function hpRegion(id){ return HP_CFG.regions.find(function(r){ return r.id === id; }) || HP_CFG.regions[0]; }
function hpCalc(){
  var r = hpRegion(HP.region), people = Math.max(1, Math.min(30, HP.people | 0));
  var spend = [HP.stay, HP.food, HP.act].reduce(function(a, v){ return a + Math.max(0, +v || 0); }, 0);
  var cap = Math.min(HP_CFG.capPerPerson * people, HP_CFG.capPerTeam);
  var raw = Math.round(spend * HP_CFG.rate), refund = r && r.target ? Math.min(raw, cap) : 0;
  return { region:r, people:people, spend:spend, cap:cap, raw:raw, refund:refund, capped:r && r.target && raw > cap };
}
var hpWon = function(n){ return Math.round(n).toLocaleString("ko-KR") + "원"; };
function hpCardHtml(){
  var c = HP.res, appRegion = (hpRegion(HP.region) || {}).app;
  var num = function(id, v, label){ return `<label>${esc(label)}<input id="${id}" type="number" min="0" step="10000" inputmode="numeric" value="${esc(String(v))}"></label>`; };
  return `<section class="hpcard revapp" id="hpCard" data-pos="I0" aria-label="강원 반값여행과 정책 혜택">
    <div class="hphead"><span class="hpbadge">2026~2027 정책</span><h2>강원 반값여행 & 정책 혜택</h2>
      <p>평창·영월·횡성은 여행 경비의 50%를 지역화폐로 돌려받는 반값여행(지역사랑 휴가지원) 시범 대상이에요.</p></div>
    <ul class="hpinfo">
      <li><b>사전승인 필수</b> · 출발 전에 신청하고 승인을 받아야 환급돼요.</li>
      <li><b>예산 소진 주의</b> · 지자체 예산이 떨어지면 일찍 마감될 수 있어요.</li>
      <li><b>디지털 관광주민증</b> · 발급하면 강원 관광지·가게 할인을 받을 수 있어요.</li>
      <li><b>강원 워케이션</b> · 일하며 머무는 여행자에게 숙박비 등을 지원하는 사업이 있어요.</li>
    </ul>
    <div class="cbar" style="margin:0">
      <a class="btn ghost" href="${esc(naver("강원 반값여행 평창 영월 횡성 신청 공고"))}" target="_blank" rel="noopener">공식 공고 확인 ↗</a>
      <a class="btn ghost" href="${esc(naver("디지털 관광주민증 강원"))}" target="_blank" rel="noopener">관광주민증 ↗</a>
      <a class="btn ghost" href="${esc(naver("강원 워케이션 지원"))}" target="_blank" rel="noopener">워케이션 ↗</a>
    </div>
    <form id="hpForm" class="hpform" autocomplete="off">
      <h3>예상 환급액 계산기</h3>
      <label>지역<select id="hpRegion">${HP_CFG.regions.map(function(r){ return `<option value="${esc(r.id)}" ${r.id === HP.region ? "selected" : ""}>${esc(r.name)}${r.target ? " (시범 대상)" : ""}</option>`; }).join("")}</select></label>
      <label>인원<input id="hpPeople" type="number" min="1" max="30" inputmode="numeric" value="${esc(String(HP.people))}"></label>
      ${num("hpStay", HP.stay, "숙박비(원)")}${num("hpFood", HP.food, "식비(원)")}${num("hpAct", HP.act, "체험·입장료(원)")}
      <button class="btn" type="submit">환급액 계산</button>
    </form>
    ${c ? `<div class="hpres" id="hpResult" aria-live="polite">
      ${c.region && c.region.target
        ? `<span class="meta">${esc(c.region.name)} · ${esc(String(c.people))}명 · 예상 경비 ${esc(hpWon(c.spend))}</span><b>예상 환급 ${esc(hpWon(c.refund))}</b>
           <small>${c.capped ? "한도에 걸렸어요. " : ""}50% 환급 · 1인당 한도 ${esc(hpWon(HP_CFG.capPerPerson))}, 팀 최대 ${esc(hpWon(HP_CFG.capPerTeam))} (지역화폐 지급)</small>`
        : `<b>이 지역은 반값여행 시범 대상이 아니에요</b><small>평창·영월·횡성을 골라 보세요. 할인 방법 아래의 지역화폐·쿠폰은 쓸 수 있어요.</small>`}
    </div>` : ""}
    <p class="hpwarn">정책 기준·한도는 시기별로 바뀔 수 있어요. 공식 공고를 꼭 확인하세요. 계산 결과는 참고용 추정이에요.</p>
    <div class="cbar" style="margin:0">
      <button class="btn" type="button" data-hpgo="stay" ${appRegion ? "" : "disabled"}>${REV}이 지역 숙소 예약 비교</button>
      <button class="btn ghost" type="button" data-tab="coupons">쿠폰북 보기</button>
    </div>
  </section>`;
}
// 가볼 곳 지역 칩(A7)에서 평창·정선/영월을 고르면 위에 띄우는 안내 배너
function hpBannerHtml(){
  if (["pyeongchang", "jeongseon"].indexOf(state.region) < 0) return "";
  return `<div class="hpbanner" data-pos="C0"><span>💸 ${esc(regionLabel())} 반값여행 시범 지역 · 경비 50% 지역화폐 환급</span><button class="btn ghost" type="button" data-hpopen="1">환급액 계산하기</button></div>`;
}
function hpRead(){
  var v = function(id){ var el = document.getElementById(id); return el ? el.value : ""; };
  HP.region = v("hpRegion") || HP.region; HP.people = Math.max(1, Math.min(30, parseInt(v("hpPeople"), 10) || 1));
  HP.stay = Math.max(0, +v("hpStay") || 0); HP.food = Math.max(0, +v("hpFood") || 0); HP.act = Math.max(0, +v("hpAct") || 0);
}
function hpPersist(){ try { localStorage.setItem("gn_halfprice", JSON.stringify(HP)); } catch(_) {} }
document.addEventListener("submit", function(e){
  if (e.target.id !== "hpForm") return; e.preventDefault();
  hpRead(); HP.res = hpCalc(); hpPersist();
  trackEvent("halfprice_calc_run", { region:HP.region, people:HP.res.people, estSpend:HP.res.spend, estRefund:HP.res.refund });
  var card = document.getElementById("hpCard"); if (card) card.outerHTML = hpCardHtml();
});
document.addEventListener("change", function(e){ if (e.target.id === "hpRegion"){ hpRead(); hpPersist(); var card = document.getElementById("hpCard"); if (card){ HP.res = null; card.outerHTML = hpCardHtml(); } } });
document.addEventListener("click", function(e){
  var g = e.target.closest("[data-hpgo]"), o = e.target.closest("[data-hpopen]");
  if (o){ var prev0 = state.tab; state.tab = "deals"; navPush(prev0 !== "deals"); render(); keepTabPos();
    setTimeout(function(){ var c = document.getElementById("hpCard"); if (c) c.scrollIntoView({ block:"start" }); }, 60); return; }
  if (!g) return;
  var r = hpRegion(HP.region); if (!r || !r.app) return;
  var prev = state.tab; state.region = r.app; state.cat = "숙소"; state.tab = "places"; save(); navPush(prev !== "places"); render(); keepTabPos();
  trackEvent("region_or_filter_use", { filter:"halfprice_stay", value:r.app });
});
