/* P0-7 운영자 '수익·KPI 요약' 아코디언 + 이벤트 JSON/CSV 내보내기·초기화 (APK·웹 공통) */
function kpiCompute(list){
  list = list || GW_EVENTS.read();
  var by = function(n){ return list.filter(function(e){ return e.name === n; }); };
  var group = function(arr, key){ var m = {}; arr.forEach(function(e){ var k = (e.props || {})[key] || "-"; m[k] = (m[k] || 0) + 1; }); return m; };
  var aff = by("affiliate_click"), claim = by("coupon_claim"), redeem = by("coupon_redeem_complete"), pw = by("paywall_view");
  var conv = by("pro_toggle_change").filter(function(e){ var p = e.props || {}; return p.toTier && p.toTier !== "free" && p.trigger !== "qa_toggle"; });
  var smart = by("smart_course_run"), cf = by("region_or_filter_use").filter(function(e){ var p = e.props || {}; return (p.filter === "carfree" && p.value === "on") || p.filter === "carfree_mode"; });
  var pct = function(a, b){ return b ? Math.round(a / b * 100) + "%" : "—"; };
  return {
    total:list.length, sessions:new Set(list.map(function(e){ return e.sid; })).size,
    affiliate:aff.length, affByCat:group(aff, "category"), affByPartner:group(aff, "partner"), affByMode:group(aff, "mode"),
    claim:claim.length, redeem:redeem.length, couponRate:pct(redeem.length, claim.length),
    paywall:pw.length, proConv:conv.length, proRate:pct(conv.length, pw.length), pwByTrigger:group(pw, "trigger"),
    smartOk:smart.filter(function(e){ return (e.props || {}).status === "ok"; }).length, smartGated:smart.filter(function(e){ return (e.props || {}).status === "gated"; }).length,
    carfree:cf.length + by("course_template_load").filter(function(e){ return (e.props || {}).carfree; }).length,
    halfprice:by("halfprice_calc_run").length, inquiry:by("biz_inquiry_submit").length,
    sponsorImp:by("sponsor_impression").length, sponsorClick:by("sponsor_click").length,
    detail:by("place_detail_view").length, courseAdd:by("course_add").length, opens:by("app_open").length
  };
}
var KPI_UI = { msg:"", open:true };
function kpiBoxHtml(){
  var k = kpiCompute(), kv = function(m){ var e = Object.entries(m); return e.length ? e.sort(function(a, b){ return b[1] - a[1]; }).map(function(x){ return esc(x[0]) + " " + x[1]; }).join(" · ") : "—"; };
  var tile = function(label, val){ return `<div>${esc(label)}<b>${esc(String(val))}</b></div>`; };
  var inq = []; try { inq = store.get("local_inquiries", []).slice(-5).reverse(); } catch(_) {}
  return `<details class="revbox pm kpibox" id="kpiBox" data-pos="O2" ${KPI_UI.open ? "open" : ""}>
    <summary><h2>수익·KPI 요약</h2></summary>
    <p class="meta"><span>이 기기에 쌓인 이벤트</span> <b>${esc(String(k.total))}</b> · <span>세션</span> <b>${esc(String(k.sessions))}</b> <span>(최대 ${esc(String(GW_EVENTS.max))}건, 오래된 것부터 지워져요).</span> <span>이름·전화번호·정밀 위치는 기록하지 않아요.</span></p>
    <div class="kpis">
      ${tile("제휴 클릭", k.affiliate)}${tile("쿠폰 받기 → 사용", k.claim + " → " + k.redeem + " (" + k.couponRate + ")")}
      ${tile("Paywall → Pro 테스트 전환", k.paywall + " → " + k.proConv + " (" + k.proRate + ")")}
      ${tile("스마트 코스 성공 / 잠금", k.smartOk + " / " + k.smartGated)}${tile("뚜벅이 사용", k.carfree)}
      ${tile("반값 계산기", k.halfprice)}${tile("입점 문의", k.inquiry)}${tile("광고 노출 → 클릭", k.sponsorImp + " → " + k.sponsorClick)}
      ${tile("장소 상세 · 코스 담기", k.detail + " · " + k.courseAdd)}${tile("앱 진입", k.opens)}
    </div>
    <p class="meta">제휴 클릭 카테고리별: ${kv(k.affByCat)}</p>
    <p class="meta">파트너별: ${kv(k.affByPartner)} · 링크 모드: ${kv(k.affByMode)}</p>
    <p class="meta">Paywall 트리거별: ${kv(k.pwByTrigger)}</p>
    ${inq.length ? `<div class="wrap"><table><thead><tr><th>날짜</th><th>문의 종류</th><th>가게</th><th>내용</th></tr></thead><tbody>${inq.map(function(x){ return `<tr><td>${esc(String(x.at || "").slice(0, 10))}</td><td>${esc(x.type)}</td><td>${esc(x.place)}</td><td>${esc(String(x.msg || "").slice(0, 60))}</td></tr>`; }).join("")}</tbody></table></div>` : ""}
    <div class="cbar kpiacts" style="margin:0"><button class="btn ghost" type="button" data-kpi="json">JSON 내보내기</button><button class="btn ghost" type="button" data-kpi="csv">CSV 내보내기</button><button class="linkbtn" type="button" data-kpi="reset">이벤트 초기화</button></div>
    ${KPI_UI.msg ? `<p class="okline">${esc(KPI_UI.msg)}</p>` : ""}
  </details>`;
}
// APK 는 AndroidBridge 로, 브라우저는 다운로드로 저장한다(APK_BUILD 플래그가 켜져 있어도 브라우저면 내려받기)
async function kpiSave(name, mime, data){
  if (window.AndroidBridge && window.AndroidBridge.saveFile) return saveFile(name, mime, data);
  try { var a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([data], { type:mime })); a.download = name; document.body.appendChild(a); a.click(); a.remove(); return "저장했어요."; }
  catch(_) { return "저장하지 못했어요."; }
}
function kpiRefresh(){ var b = document.getElementById("kpiBox"); if (b) b.outerHTML = kpiBoxHtml(); }
document.addEventListener("toggle", function(e){ if (e.target && e.target.id === "kpiBox") KPI_UI.open = e.target.open; }, true);
document.addEventListener("click", async function(e){
  var b = e.target.closest("[data-kpi]"); if (!b) return;
  var a = b.dataset.kpi, day = isoLocal(new Date());
  if (a === "json") KPI_UI.msg = await kpiSave("gw_events_" + day + ".json", "application/json", JSON.stringify({ exportedAt:new Date().toISOString(), kpi:kpiCompute(), events:GW_EVENTS.read() }, null, 2));
  if (a === "csv") KPI_UI.msg = await kpiSave("gw_events_" + day + ".csv", "text/csv", GW_EVENTS.csv());
  if (a === "reset"){ if (!confirm("이 기기의 이벤트 기록을 모두 지울까요?")) return; GW_EVENTS.clear(); KPI_UI.msg = "이벤트 기록을 지웠어요."; }
  kpiRefresh();
});
