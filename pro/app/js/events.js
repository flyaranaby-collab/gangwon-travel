/* P0-7 클라이언트 이벤트 로거
 * localStorage "gn_events" 에 최대 1,000건 링버퍼로 쌓는다(서버 없음).
 * 스키마: { v, ts, sid, name, tab, region, lang, pro, props } — 이름·전화·이메일·정밀 좌표 같은 개인정보는 넣지 않는다.
 * 이 파일은 main.js 보다 먼저 로드되며, main.js 의 전역(state 등)은 함수가 실제로 불릴 때만 참조한다.
 */
var GW_EVENTS = (function(){
  var cfg = (window.GW_CONFIG && window.GW_CONFIG.BIZ && window.GW_CONFIG.BIZ.EVENTS) || { key:"gn_events", max:1000 };
  var sid = "s_" + Math.random().toString(36).slice(2, 9);
  var PII = /^(name|phone|tel|email|mail|contact|lat|lng|lon|addr|address|msg|text|memo)$/i;
  function clean(props){
    var out = {};
    if (!props || typeof props !== "object") return out;
    Object.keys(props).slice(0, 16).forEach(function(k){
      if (PII.test(k)) return;
      var v = props[k];
      if (Array.isArray(v)) out[k] = v.slice(0, 10).map(function(x){ return String(x).slice(0, 40); });
      else if (typeof v === "number" || typeof v === "boolean" || v == null) out[k] = v;
      else out[k] = String(v).slice(0, 80);
    });
    return out;
  }
  function read(){ try { var a = JSON.parse(localStorage.getItem(cfg.key) || "[]"); return Array.isArray(a) ? a : []; } catch(_) { return []; } }
  function write(list){ try { localStorage.setItem(cfg.key, JSON.stringify(list)); return true; } catch(_) { return false; } }
  function ctx(){
    var c = { tab:"", region:"", lang:"ko", pro:"free" };
    try { c.tab = state.tab; c.region = state.region; } catch(_) {}
    try { c.lang = LANG; } catch(_) {}
    try { c.pro = proTier(); } catch(_) {}
    return c;
  }
  function track(name, props){
    try {
      var c = ctx(), list = read();
      list.push({ v:1, ts:new Date().toISOString(), sid:sid, name:String(name).slice(0, 40), tab:c.tab, region:c.region, lang:c.lang, pro:c.pro, props:clean(props) });
      if (list.length > cfg.max) list.splice(0, list.length - cfg.max);
      write(list);
    } catch(_) {}
  }
  function csv(){
    var rows = [["ts","sid","name","tab","region","lang","pro","props"]].concat(read().map(function(e){
      return [e.ts, e.sid, e.name, e.tab, e.region, e.lang, e.pro, JSON.stringify(e.props || {})]; }));
    return "\ufeff" + rows.map(function(r){ return r.map(function(v){ return '"' + String(v == null ? "" : v).replace(/"/g, '""') + '"'; }).join(","); }).join("\r\n");
  }
  return { sid:sid, key:cfg.key, max:cfg.max, read:read, write:write, track:track, csv:csv, clear:function(){ write([]); } };
})();
function trackEvent(name, props){ GW_EVENTS.track(name, props); }

// 앱 진입(세션당 1회): 새로고침(softReload)으로 중복 집계하지 않도록 sessionStorage 로 막는다
document.addEventListener("DOMContentLoaded", function(){
  var first = false;
  try { first = !sessionStorage.getItem("gn_open"); sessionStorage.setItem("gn_open", "1"); } catch(_) { first = true; }
  if (!first) return;
  var returning = false;
  try { returning = !!localStorage.getItem("gn_first_open"); if (!returning) localStorage.setItem("gn_first_open", new Date().toISOString()); } catch(_) {}
  var tripCount = 1, daysToTrip = null;
  try { tripCount = tripsList().length; } catch(_) {}
  try { daysToTrip = Math.round((new Date(state.date + "T00:00:00") - new Date(todayISO + "T00:00:00")) / 864e5); } catch(_) {}
  trackEvent("app_open", { isApk: !!window.AndroidBridge || !!window.APK_BUILD, returning: returning, tripCount: tripCount, daysToTrip: daysToTrip });
});

// 화면 곳곳의 공통 동작을 main.js 를 고치지 않고 계측한다(캡처 단계라 원래 동작보다 먼저 상태를 읽는다)
document.addEventListener("click", function(e){
  var t = e.target && e.target.closest ? e.target.closest("button, a") : null; if (!t) return;
  try {
    var d = t.dataset || {};
    if (d.toggle){ var adding = state.course.indexOf(d.toggle) < 0;
      if (adding) trackEvent("course_add", { targetId:d.toggle, mode:state.mode, stopCount:state.course.length + 1 }); }
    if (d.detail && /^p:/.test(d.detail)){ var id = d.detail.slice(2), p = byId(id), D = (typeof DEALMAP !== "undefined" && DEALMAP[id]) || {};
      trackEvent("place_detail_view", { targetId:id, cat:p ? p.cat : "", isPaid:!!D.paid, isSponsored:SPONSORED.some(function(x){ return x.id === id; }) }); }
    if (d.region) trackEvent("region_or_filter_use", { filter:"region", value:d.region });
    if (t.id === "optBtn" || t.id === "tripOptBtn") trackEvent("course_optimize", { dayCount: t.id === "tripOptBtn" ? tripDays().length : 1, mode:state.mode, stopCount:state.course.length });
    if (d.tpl != null && typeof TEMPLATES !== "undefined"){ var tp = TEMPLATES[+d.tpl];
      if (tp) trackEvent("course_template_load", { name:tp.name, carfree:!!tp.carfree }); }
  } catch(_) {}
}, true);
