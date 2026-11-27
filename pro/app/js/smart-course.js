/* P0-3 오프라인 '스마트 맞춤 코스' 엔진 — claude.ai 런타임 없이 기기 안에서 바로 코스를 만든다(APK 오류 대체).
 * 규칙: ① 그날 휴무(status(p).cls==="closed") 완전 제외 ② 동행 점수·로컬엄선(CURATED)·우천(rainOk) 가중치
 *       ③ 식당 1~2 + 카페 1 + 명소 1~2 균형 ④ nearestOrder 동선 정렬 + 선택 사유 요약
 * 무료: 하루 2회(gn_smart_quota), 3회차·다일 일괄은 Pro Paywall. Pro 는 무제한.
 */
var SC_THEMES = ["바다", "맛집", "카페", "실내·우천", "로컬엄선", "가성비"];
var SC_BUDGETS = [0, 30000, 50000, 100000];
var SC = (function(){ var d = { pace:3, themes:[], budget:0, kw:"", multi:false };
  try { var s = JSON.parse(localStorage.getItem("gn_smart_prefs") || "null"); if (s && typeof s === "object") d = Object.assign(d, s); } catch(_) {}
  if (!Array.isArray(d.themes)) d.themes = []; d.msg = ""; d.err = ""; d.reasons = []; d.runs = 0; return d; })();
function scSavePrefs(){ try { localStorage.setItem("gn_smart_prefs", JSON.stringify({ pace:SC.pace, themes:SC.themes, budget:SC.budget, kw:SC.kw, multi:SC.multi })); } catch(_) {} }
function scQuota(){ var q = null; try { q = JSON.parse(localStorage.getItem("gn_smart_quota") || "null"); } catch(_) {}
  return q && q.d === todayISO ? q : { d:todayISO, n:0 }; }
function scUse(){ var q = scQuota(); q.n++; try { localStorage.setItem("gn_smart_quota", JSON.stringify(q)); } catch(_) {} return q.n; }
function scLeft(){ return Math.max(0, (PRO_CFG.smartCourseFreePerDay || 2) - scQuota().n); }
var scKind = function(p){ return p.cat === "맛집" ? "food" : p.cat === "카페" ? "cafe" : "sight"; };
var scHas = function(p, re){ return re.test([p.name, p.sig, p.area, p.cat].concat(p.tags || []).join(" ")); };
function scRainOk(p){ try { ensureWx(); } catch(_) {} return !!((p.weather && (p.weather.rainOk || p.weather.indoor)) || (p.tags || []).indexOf("실내") >= 0 || p.cat === "카페" || p.cat === "맛집"); }
// 한 날짜의 코스를 만든다. exclude: 다른 날에 이미 넣은 장소
function smartCourse(opt){
  opt = opt || {};
  var themes = opt.themes || [], pace = opt.pace === 5 ? 5 : 3, bus = state.mode === "bus", budget = +opt.budget || 0;
  var st = startPt(), region = state.region === "all" ? (st.region || "gangneung") : state.region;
  var kws = String(opt.kw || "").split(/[\s,·]+/).map(function(s){ return s.trim(); }).filter(function(s){ return s.length >= 2; });
  var exclude = opt.exclude || new Set();
  var pool = PLACES.filter(function(p){ return (p.region === region || (Array.isArray(p.also) && p.also.indexOf(region) >= 0)) && p.lat && p.cat !== "숙소" && !exclude.has(p.id) && !(typeof isBar === "function" && isBar(p)); });
  var closed = pool.filter(function(p){ return status(p).cls === "closed"; });
  var cands = pool.filter(function(p){ return status(p).cls !== "closed"; });
  var score = function(p){
    var s = ((p.who && p.who[state.who]) || 1) * 1.5, cost = (META[p.id] || {}).cost || 0;
    if (CURATED[p.id]) s += 2.5;
    if (p.source) s -= 0.8;
    try { if (photoFor(p)) s += 0.6; } catch(_) {}
    if (themes.indexOf("바다") >= 0 && (p.cat === "바다" || scHas(p, /바다|해변|해수욕|항구|오션/))) s += 3;
    if (themes.indexOf("맛집") >= 0 && p.cat === "맛집") s += 2;
    if (themes.indexOf("카페") >= 0 && p.cat === "카페") s += 2;
    if (themes.indexOf("실내·우천") >= 0) s += scRainOk(p) ? 2.5 : -6;
    if (themes.indexOf("로컬엄선") >= 0 && (CURATED[p.id] || (p.tags || []).indexOf("현지인맛집") >= 0)) s += 3;
    if (themes.indexOf("가성비") >= 0) s += cost <= 10000 ? 2 : cost > 20000 ? -2 : 0;
    kws.forEach(function(k){ if (scHas(p, new RegExp(k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"))) s += 4; });
    if (bus) s += isCarFree(p) ? 2 : -1.5;
    return s;
  };
  var scored = cands.map(function(p){ return { p:p, s:score(p), k:scKind(p), c:(META[p.id] || {}).cost || 0 }; }).sort(function(a, b){ return b.s - a.s; });
  var slots = pace === 5 ? ["sight", "food", "cafe", "sight", "food"] : ["sight", "food", "cafe"];
  var pick = [], spent = 0, per = bus ? 0.6 : 0.25, reach = bus ? 8 : 25;
  var fits = function(x){ return !budget || spent + x.c <= budget; };
  // 첫 장소(기준점): 명소 중 상위권(다시 누르면 순서를 바꿔 다른 코스)
  var top = scored.filter(function(x){ return x.k === "sight" && fits(x) && x.s > -3; }).slice(0, 3);
  if (!top.length) top = scored.filter(fits).slice(0, 3);
  if (!top.length) return { ids:[], reasons:[], closed:closed.length };
  var anchor = top[(opt.seed || 0) % top.length]; pick.push(anchor); spent += anchor.c;
  slots.slice(1).forEach(function(kind){
    var last = pick[pick.length - 1].p, used = new Set(pick.map(function(x){ return x.p.id; }));
    var best = null, bv = -1e9;
    scored.forEach(function(x){
      if (used.has(x.p.id) || x.k !== kind || !fits(x)) return;
      var d = km(anchor.p, x.p); if (d > reach) return;
      var v = x.s - per * km(last, x.p); if (v > bv){ bv = v; best = x; } });
    if (!best) scored.forEach(function(x){ if (used.has(x.p.id) || !fits(x)) return; var d = km(anchor.p, x.p); if (d > reach) return; var v = x.s - per * km(last, x.p); if (v > bv){ bv = v; best = x; } });
    if (best){ pick.push(best); spent += best.c; }
  });
  var ids = nearestOrder(pick.map(function(x){ return x.p; }), st);
  var d = tripDay(), n = function(k){ return pick.filter(function(x){ return x.k === k; }).length; };
  var reasons = [
    (d.getMonth() + 1) + "/" + d.getDate() + " 휴무 " + closed.length + "곳 제외",
    "동행 점수 반영 · " + state.who,
    "맛집 " + n("food") + " · 카페 " + n("cafe") + " · 관광지 " + n("sight"),
  ];
  var cur = pick.filter(function(x){ return CURATED[x.p.id]; }).length; if (cur) reasons.push("로컬 엄선 " + cur + "곳 포함");
  if (themes.indexOf("실내·우천") >= 0) reasons.push("비 와도 괜찮은 곳 우선");
  if (bus) reasons.push("역·터미널에서 가까운 곳 우선(뚜벅이)");
  if (kws.length) reasons.push("키워드: " + kws.join(", "));
  reasons.push("1인 예상 비용 " + won(spent)); if (budget) reasons.push("예산 상한 " + won(budget));
  return { ids:ids, reasons:reasons, closed:closed.length };
}
function smartCourseHtml(){
  var days = tripDays().length, pro = isPro(), left = scLeft();
  var chip = function(group, val, label, on){ return `<button type="button" class="chipbtn" data-sc="${group}:${esc(val)}" aria-pressed="${!!on}">${esc(label)}</button>`; };
  return `<form class="revbox revapp smartbox" id="smartForm" data-pos="E0" autocomplete="off">
    <h3>스마트 맞춤 코스 <span class="okpill">오프라인</span></h3>
    <p class="meta"><span>그날 휴무를 피해 하루 코스를 바로 짜 드려요. 인터넷이 없어도 돼요. 지금 코스는 바뀌어요.</span> <b>기준: ${esc(regionLabel())} · ${tripDay().getMonth() + 1}/${tripDay().getDate()}</b></p>
    <div class="scrow"><span class="meta">이동 수단</span>${chip("mode", "car", "🚗 자차", state.mode === "car")}${chip("mode", "bus", "🚌 뚜벅이", state.mode === "bus")}</div>
    <div class="scrow"><span class="meta">페이스</span>${chip("pace", "3", "여유 3곳", SC.pace !== 5)}${chip("pace", "5", "알찬 5곳", SC.pace === 5)}</div>
    <div class="scrow"><span class="meta">여행 테마</span>${SC_THEMES.map(function(t){ return chip("theme", t, t, SC.themes.indexOf(t) >= 0); }).join("")}</div>
    <div class="scrow"><span class="meta">1인 예산</span>${SC_BUDGETS.map(function(b){ return chip("budget", String(b), b ? won(b) : "제한 없음", +SC.budget === b); }).join("")}</div>
    <input id="scKw" class="search" value="${esc(SC.kw)}" placeholder="자유 키워드 (예: 순두부, 일출, 아이와)" aria-label="자유 키워드">
    ${days > 1 ? `<label class="meta scmulti"><input type="checkbox" id="scMulti" ${SC.multi ? "checked" : ""}> ${days}일 전체 일괄 스마트 코스 ${proBadge()}</label>` : ""}
    <div class="cbar" style="margin:0"><button class="btn" type="submit">스마트 코스 짜기</button>
      <span class="meta" id="scLeft">${pro ? "Pro · 무제한" : "오늘 무료 남은 횟수 " + left}</span></div>
    ${SC.msg ? `<p class="okline">${esc(SC.msg)}</p>` : ""}${SC.err ? `<p class="errline">${esc(SC.err)}</p>` : ""}
    ${SC.reasons.length ? `<ul class="screasons">${SC.reasons.map(function(r){ return `<li>${esc(r)}</li>`; }).join("")}</ul>` : ""}
  </form>`;
}
function scRefresh(){ var f = document.getElementById("smartForm"); if (f) f.outerHTML = smartCourseHtml(); }
function smartRun(){
  var days = tripDays().length, multi = SC.multi && days > 1;
  SC.msg = SC.err = ""; SC.reasons = [];
  var props = { mode:state.mode, pace:SC.pace, themes:SC.themes.slice(), multi:multi };
  if (!isPro() && (multi || scLeft() <= 0)){
    props.status = "gated"; trackEvent("smart_course_run", props);
    SC.err = multi ? "다일 일괄 스마트 코스는 Pro 기능이에요." : "오늘 무료 스마트 코스를 모두 썼어요. 내일 다시 쓰거나 Pro 로 무제한 이용하세요.";
    scRefresh(); openPaywall("smart_course", multi ? "smart_course_multi" : "smart_course_limit"); return false;
  }
  var t0 = Date.now(), seed = SC.runs++, opt = { themes:SC.themes, pace:SC.pace, budget:SC.budget, kw:SC.kw, seed:seed };
  if (multi){
    var keep = state.day, used = new Set(), all = [];
    save();
    for (var i = 0; i < days; i++){ state.day = i; var r = smartCourse(Object.assign({}, opt, { exclude:used }));
      r.ids.forEach(function(id){ used.add(id); }); state.courses[i] = r.ids; all.push((i + 1) + "일차 " + r.ids.length + "곳"); }
    state.day = keep; state.course = state.courses[keep] || [];
    SC.reasons = all;
  } else {
    var res = smartCourse(opt);
    if (!res.ids.length){ SC.err = "조건에 맞는 곳이 없어요. 예산·테마를 줄여 보세요."; props.status = "empty"; trackEvent("smart_course_run", props); scRefresh(); return false; }
    state.course = res.ids; SC.reasons = res.reasons;
  }
  if (!isPro()) scUse();
  SC.msg = "코스를 짰어요 · " + (Date.now() - t0) + "ms";
  props.status = "ok"; props.stopCount = state.course.length; trackEvent("smart_course_run", props);
  save(); render();
  return true;
}
document.addEventListener("click", function(e){
  var b = e.target.closest("[data-sc]"); if (!b) return;
  var p = b.dataset.sc.split(":"), g = p[0], v = p.slice(1).join(":");
  var kw = document.getElementById("scKw"); if (kw) SC.kw = kw.value;
  if (g === "mode"){ state.mode = v; save(); scSavePrefs(); renderCourse(); if (v === "bus") trackEvent("region_or_filter_use", { filter:"carfree_mode", value:"bus" }); return; }
  if (g === "pace") SC.pace = +v === 5 ? 5 : 3;
  if (g === "theme"){ var i = SC.themes.indexOf(v); if (i >= 0) SC.themes.splice(i, 1); else SC.themes.push(v); }
  if (g === "budget") SC.budget = +v || 0;
  scSavePrefs(); scRefresh();
});
document.addEventListener("input", function(e){ if (e.target.id === "scKw"){ SC.kw = e.target.value; scSavePrefs(); } });
document.addEventListener("change", function(e){
  if (e.target.id !== "scMulti") return;
  if (e.target.checked && !isPro()){ e.target.checked = false; SC.multi = false; openPaywall("smart_course", "smart_course_multi"); trackEvent("smart_course_run", { mode:state.mode, pace:SC.pace, themes:SC.themes.slice(), multi:true, status:"gated" }); return; }
  SC.multi = e.target.checked; scSavePrefs();
});
document.addEventListener("submit", function(e){
  if (e.target.id !== "smartForm") return; e.preventDefault();
  var kw = document.getElementById("scKw"); if (kw) SC.kw = kw.value.trim();
  smartRun();
});
