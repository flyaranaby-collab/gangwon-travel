/* 다중 여행 수첩(P0-2 ① Pro 잠금 대상, P1-1 의 최소 버전)
 * gn_trips = { active:"t1", list:[{ id, name, snap, at }] } — 무료는 1개, Pro 는 무제한.
 */
var TRIP_KEYS = ["date", "dateEnd", "who", "region", "courses", "day", "start", "mode", "people", "startTime"];
function tripsRead(){
  var t = null;
  try { t = JSON.parse(localStorage.getItem("gn_trips") || "null"); } catch(_) {}
  if (!t || !Array.isArray(t.list) || !t.list.length) t = { active:"t1", list:[{ id:"t1", name:"내 여행 1", snap:null, at:Date.now() }] };
  if (!t.list.some(function(x){ return x.id === t.active; })) t.active = t.list[0].id;
  return t;
}
function tripsWrite(t){ try { localStorage.setItem("gn_trips", JSON.stringify(t)); } catch(_) {} }
function tripsList(){ return tripsRead().list; }
function tripSnap(){ save(); var s = {}; TRIP_KEYS.forEach(function(k){ s[k] = JSON.parse(JSON.stringify(state[k] == null ? null : state[k])); }); return s; }
function tripLoad(s){
  if (!s) return;
  TRIP_KEYS.forEach(function(k){ if (s[k] !== undefined && s[k] !== null) state[k] = JSON.parse(JSON.stringify(s[k])); });
  if (!state.courses || typeof state.courses !== "object") state.courses = { 0:[] };
  state.day = Math.min(Math.max(0, state.day | 0), tripDays().length - 1);
  state.course = state.courses[state.day] || [];
  try { TRIPDAYS_MEMO = null; } catch(_) {}
  save();
}
function tripCreate(){
  var t = tripsRead(), free = PRO_CFG.freeTrips || 1;
  if (t.list.length >= free && !requirePro("multi_trip", "trip_manager")) return false;
  var cur = t.list.find(function(x){ return x.id === t.active; }); cur.snap = tripSnap(); cur.at = Date.now();
  var id = "t" + Date.now().toString(36);
  t.list.push({ id:id, name:"내 여행 " + (t.list.length + 1), snap:null, at:Date.now() });
  t.active = id; tripsWrite(t);
  state.courses = { 0:[] }; state.day = 0; state.course = []; save();
  trackEvent("trip_switch_or_create", { action:"create", tripCount:t.list.length });
  render(); return true;
}
function tripSwitch(id){
  var t = tripsRead(); if (id === t.active) return;
  var target = t.list.find(function(x){ return x.id === id; }); if (!target) return;
  var cur = t.list.find(function(x){ return x.id === t.active; }); cur.snap = tripSnap(); cur.at = Date.now();
  t.active = id; tripsWrite(t); tripLoad(target.snap);
  trackEvent("trip_switch_or_create", { action:"switch", tripCount:t.list.length });
  render();
}
function tripDelete(id){
  var t = tripsRead(); if (id === t.active || t.list.length < 2) return;
  t.list = t.list.filter(function(x){ return x.id !== id; }); tripsWrite(t); render();
}
function tripsHtml(){
  var t = tripsRead();
  var label = function(x){ var s = x.id === t.active ? null : x.snap;
    if (!s) return regionLabel() + " · " + state.date;
    var r = s.region === "all" ? "강원" : ((REG[s.region] || {}).name || "강원"); return r + " · " + (s.date || ""); };
  return `<section class="tripbox" aria-label="내 여행 수첩" data-pos="M2"><div class="tbhead"><h3>내 여행 수첩</h3>
      <button class="btn ghost" type="button" data-trip="new">＋ 새 여행 수첩 ${t.list.length >= (PRO_CFG.freeTrips || 1) ? proBadge() : ""}</button></div>
    <ul class="triplist">${t.list.map(function(x){ var on = x.id === t.active;
      return `<li class="${on ? "on" : ""}"><span><b>${esc(x.name)}</b><small>${esc(label(x))}</small></span>
        ${on ? `<span class="pill ok">지금 여행</span>` : `<span class="tbctl"><button class="linkbtn" type="button" data-trip="switch:${esc(x.id)}">열기</button><button class="linkbtn" type="button" data-trip="del:${esc(x.id)}">삭제</button></span>`}</li>`; }).join("")}</ul></section>`;
}
document.addEventListener("click", function(e){
  var b = e.target.closest("[data-trip]"); if (!b) return;
  var parts = b.dataset.trip.split(":"), a = parts[0], id = parts.slice(1).join(":");
  if (a === "new") tripCreate();
  else if (a === "switch") tripSwitch(id);
  else if (a === "del"){ if (confirm("이 여행 수첩을 지울까요?")) tripDelete(id); }
});
