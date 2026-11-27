/* P0-5 '차 없이 가는 강원(뚜벅이)' 모드
 * - 역·터미널(STARTS/TRANSIT)·시티투어 타는 곳 반경 3km 안이면 뚜벅이 추천으로 자동 판별(🚌 배지)
 * - 일정 탭 대중교통 모드: 구간별 예상 택시 요금(참고용 추정)·배차 간격 주의·막차 확인 경고·바로가기
 */
var CF_CFG = (window.GW_CONFIG && window.GW_CONFIG.BIZ && window.GW_CONFIG.BIZ.CARFREE) || { radiusKm:3, longLegKm:5, lastBusWarnHour:18, taxi:{ base:4800, baseKm:1.6, perKm:760, nightRate:1.2 } };
var CF = { hubs:null, cache:new Map(), n:-1 };
function cfHubs(){
  if (CF.hubs) return CF.hubs;
  var h = [];
  try { STARTS.forEach(function(s){ if (/역|터미널|공항/.test(s.name)) h.push(s); }); } catch(_) {}
  try { TRANSIT.forEach(function(t){ if (t.lat) h.push(t); }); } catch(_) {}
  try { CITYTOUR.forEach(function(c){ if (c.lat) h.push(c); }); } catch(_) {}
  return CF.hubs = h;
}
function isCarFree(p){
  if (!p || !p.lat) return false;
  if (CF.n !== PLACES.length){ CF.cache.clear(); CF.n = PLACES.length; }
  if (CF.cache.has(p.id)) return CF.cache.get(p.id);
  var r = cfHubs().some(function(h){ return kmLine(h, p) <= CF_CFG.radiusKm; });
  CF.cache.set(p.id, r); return r;
}
function cfMark(p){ return isCarFree(p) ? `<span class="cfmark" title="뚜벅이 추천 · 역·터미널 3km 안" aria-label="뚜벅이 추천">🚌</span>` : ""; }
function taxiFare(d, minuteOfDay){
  var T = CF_CFG.taxi, f = T.base + Math.max(0, d - T.baseKm) * T.perKm;
  if (minuteOfDay != null){ var h = Math.floor(((minuteOfDay % 1440) + 1440) % 1440 / 60); if (h >= 22 || h < 4) f *= T.nightRate || 1; }   // 시각을 모르면 할증 없음
  return Math.round(f / 100) * 100;
}
// 일정 탭 대중교통 모드에서 구간마다 붙는 안내(leg: 이전 장소→이번 장소, arrive: 도착 분)
function cfLegHtml(from, to, d, arrive){
  if (state.mode !== "bus") return "";
  var warns = [];
  // 5km 초과 구간이거나 도착지가 역·터미널 생활권 밖이면 버스가 드물다
  if (d > CF_CFG.longLegKm || !isCarFree(to)) warns.push(`<span class="cfwarn">⚠ 배차 간격 주의 · 버스가 드문 구간</span>`);
  if (arrive >= CF_CFG.lastBusWarnHour * 60) warns.push(`<span class="cfwarn">🌙 막차 시간 확인</span>`);
  return `<span class="cfleg"><span>🚕 택시 약 ${esc(taxiFare(d, arrive).toLocaleString("ko-KR"))}원</span><small>참고용 추정</small>${warns.join("")}</span>`;
}
function cfCourseBoxHtml(stops, legs){
  if (state.mode !== "bus" || !stops.length) return "";
  var reg = stops[0].region, town = REG[reg] ? REG[reg].q : "강원";
  var tours = (typeof CITYTOUR !== "undefined" ? CITYTOUR : []).filter(function(c){ return c.region === reg; });
  var total = legs.reduce(function(a, d){ return a + taxiFare(d); }, 0), off = stops.filter(function(p){ return !isCarFree(p); }).length;
  return `<div class="cfbox" data-pos="E9"><b>🚌 뚜벅이 코스 도우미</b>
    <p class="meta">전 구간 택시로 이동하면 약 ${esc(total.toLocaleString("ko-KR"))}원 (참고용 추정 · 지역·시간대에 따라 달라요). ${off ? `역·터미널에서 먼 곳 ${off}곳은 버스가 드물 수 있어요.` : "모두 역·터미널 3km 안이에요."}</p>
    <div class="cbar" style="margin:0">
      ${tours.length ? `<button class="btn ghost" type="button" data-tab="transit">🚌 ${esc(town)} 시티투어·셔틀</button>` : ""}
      <a class="btn ghost" href="kakaot://taxi" data-rev="taxi:kakaot" onclick="setTimeout(()=>{ if(!document.hidden) location.href='https://www.kakaomobility.com/'; },1500)">카카오T 택시</a>
      <a class="btn ghost" href="${esc(naver(town + " 시내버스 노선 시간표"))}" target="_blank" rel="noopener">${esc(town)} 버스 시간표</a>
    </div></div>`;
}
// 가볼 곳 C6 필터 '🚌 뚜벅이 추천'
document.addEventListener("click", function(e){
  var b = e.target.closest("#carfreeBtn"); if (!b) return;
  state.carfree = !state.carfree;
  var n = 0; try { n = PLACES.filter(function(p){ return inRegion(p) && isCarFree(p); }).length; } catch(_) {}
  trackEvent("region_or_filter_use", { filter:"carfree", value:state.carfree ? "on" : "off", resultCount:n });
  renderPlaces();
});
