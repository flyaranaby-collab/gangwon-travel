/* P0-4 로컬 상점 광고 슬롯 · 제휴 쿠폰북 · 입점 문의 복구
 * - 실제 쿠폰(OWNER.biz.coupons)이 없으면 '[예시/제휴 준비]' 샘플 쿠폰 6종을 보여 준다(설정: GW_CONFIG.BIZ.SAMPLE_COUPONS, 운영자 토글).
 * - 쿠폰북·할인 탭: 지역 필터 + '내 코스와 가까운 쿠폰' 우선 정렬 + 사용 완료 영수증 카드
 * - 추천 가게: 사진·한 줄 혜택·'광고' 배지를 분리한 네이티브 카드, Pro 사용자는 자동 숨김
 * - 입점 문의: 이 기기(local_inquiries)에 저장 + 운영자 연락처(contactBtns) 연결
 */
var LB_SAMPLES = [
  { id:"sample-gn-cafe", region:"gangneung", place:"gilgamja", shop:"안목 해변 카페 (제휴 준비)", title:"음료 10% 할인", cond:"결제 전 화면 제시 · 1인당 1회" },
  { id:"sample-gn-food", region:"gangneung", place:"jungang", shop:"중앙시장 먹거리 가게 (제휴 준비)", title:"닭강정 소컵 서비스", cond:"2만 원 이상 구매 시" },
  { id:"sample-sc-food", region:"sokcho", place:"sokcho-market", shop:"속초 관광수산시장 가게 (제휴 준비)", title:"회 포장 5% 할인", cond:"현금·지역화폐 결제 시" },
  { id:"sample-dh-cafe", region:"donghae", place:"mukho", shop:"묵호 골목 카페 (제휴 준비)", title:"디저트 1,000원 할인", cond:"음료 주문 시 · 1인당 1회" },
  { id:"sample-pc-act", region:"pyeongchang", place:"samyang", shop:"대관령 체험 농장 (제휴 준비)", title:"체험권 2,000원 할인", cond:"현장 매표 시 화면 제시" },
  { id:"sample-yw-food", region:"jeongseon", place:"mitan", shop:"영월 서부시장 가게 (제휴 준비)", title:"전병 1장 서비스", cond:"1만 원 이상 구매 시" }
];
function lbSamplesOn(){ var b = (typeof OWNER !== "undefined" && OWNER.biz) || {}; return typeof b.sampleCoupons === "boolean" ? b.sampleCoupons : !!(window.GW_CONFIG && window.GW_CONFIG.BIZ && window.GW_CONFIG.BIZ.SAMPLE_COUPONS); }
// main.js applyBiz() 에서 부른다: 실제 쿠폰이 하나도 없을 때만 샘플을 채운다
function lbApplySamples(list){
  if (list.length || !lbSamplesOn()) return;
  LB_SAMPLES.forEach(function(c){ list.push(Object.assign({ until:"", img:"", sample:true }, c)); });
}
var LB = (function(){ var d = { region:"here", near:true }; try { var s = JSON.parse(localStorage.getItem("gn_cpfilter") || "null"); if (s) d = Object.assign(d, s); } catch(_) {} return d; })();
function lbCouponRegion(c){ var p = c.place && byId(c.place); return c.region || (p ? p.region : ""); }
function lbCouponPt(c){ var p = c.place && byId(c.place); if (p && p.lat) return p; var r = REG[lbCouponRegion(c)]; return r ? { lat:r.lat, lng:r.lng } : null; }
function lbCourseCenter(){
  var stops = []; try { stops = tripCourseIds().map(byId).filter(function(p){ return p && p.lat; }); } catch(_) {}
  if (!stops.length) return null;
  return { lat:stops.reduce(function(a, p){ return a + p.lat; }, 0) / stops.length, lng:stops.reduce(function(a, p){ return a + p.lng; }, 0) / stops.length };
}
// 지역 필터와 '내 코스와 가까운 순' 정렬을 적용한 쿠폰 목록
function lbCoupons(list){
  var here = state.region, out = list.slice();
  if (LB.region === "here" && here !== "all") out = out.filter(function(c){ var r = lbCouponRegion(c); return !r || r === here; });
  else if (LB.region !== "here" && LB.region !== "all") out = out.filter(function(c){ return lbCouponRegion(c) === LB.region; });
  var cc = LB.near ? lbCourseCenter() : null;
  if (cc) out.sort(function(a, b){ var pa = lbCouponPt(a), pb = lbCouponPt(b); return (pa ? kmLine(cc, pa) : 1e9) - (pb ? kmLine(cc, pb) : 1e9); });
  return out;
}
function lbDist(c){ var cc = LB.near ? lbCourseCenter() : null, p = lbCouponPt(c); return cc && p ? kmLine(cc, p) : null; }
function lbFilterHtml(){
  var regs = []; PARTNER_COUPONS.forEach(function(c){ var r = lbCouponRegion(c); if (r && regs.indexOf(r) < 0) regs.push(r); });
  var chip = function(v, label){ return `<button type="button" class="chipbtn" data-cpf="${esc(v)}" aria-pressed="${LB.region === v}">${esc(label)}</button>`; };
  return `<div class="filters cpfilters" role="group" aria-label="쿠폰 지역">
    ${chip("here", state.region === "all" ? "강원 전체" : regionLabel() + " (지금 지역)")}${chip("all", "모든 지역")}
    ${regs.filter(function(r){ return r !== state.region && REG[r]; }).map(function(r){ return chip(r, REG[r].name); }).join("")}
    <span class="sep"></span><button type="button" class="chipbtn" data-cpnear="1" aria-pressed="${!!LB.near}">📍 내 코스와 가까운 순</button></div>`;
}
function lbCouponCard(c, surface){
  var got = state.claimed.indexOf(c.id) >= 0, d = lbDist(c), r = lbCouponRegion(c);
  return `<div class="sponsor cpcard">${cpImgHtml(c)}<span class="cphead">${c.sample ? `<span class="adpill samplepill">[예시/제휴 준비]</span>` : `<span class="adpill">제휴</span>`}${r && REG[r] ? `<span class="meta">${esc(REG[r].name)}</span>` : ""}${d != null ? `<span class="meta">내 코스에서 ${esc(d.toFixed(1))}km</span>` : ""}</span>
    <b>${esc(c.title)}</b><span>${esc(c.shop)}${c.cond ? " · " + esc(c.cond) : ""}</span>
    <button class="btn ${got ? "added" : ""}" style="justify-self:start" data-coupon="${esc(c.id)}" data-surface="${esc(surface)}" ${got ? "disabled" : ""}>${got ? "받음 ✓" : "쿠폰 받기"}</button></div>`;
}
// 할인 탭(B4)의 제휴 쿠폰 칸
function lbDealsCouponsHtml(){
  var list = lbCoupons(PARTNER_COUPONS), sample = PARTNER_COUPONS.some(function(c){ return c.sample; });
  return `<div class="revbox revapp" style="margin-top:22px" id="dealCoupons"><h2>${REV}제휴 쿠폰</h2>
    <p class="meta">제휴 가게가 이 앱 사용자에게만 주는 쿠폰이에요. 받으면 쿠폰북에 담기고 매장에서 한 번 쓸 수 있어요.</p>
    ${sample ? `<p class="notice">지금 보이는 쿠폰은 화면 확인용 예시예요. 실제 제휴 쿠폰이 등록되면 바로 바뀌어요.</p>` : ""}
    ${PARTNER_COUPONS.length ? lbFilterHtml() : `<p class="notice">강원 가게와 첫 쿠폰을 준비하고 있어요. 가게 사장님이시면 아래 문의 양식으로 연락 주세요.</p>`}
    <div class="sponsors">${list.map(function(c){ return lbCouponCard(c, "deals"); }).join("") || (PARTNER_COUPONS.length ? `<div class="empty">이 지역 쿠폰이 없어요. ‘모든 지역’을 눌러 보세요.</div>` : "")}</div>
    <p class="meta"><button class="linkbtn" data-tab="coupons">쿠폰북에서 받은 쿠폰 쓰기 ›</button></p>
  </div>`;
}
// 쿠폰 사용 완료 영수증 카드: 사용 시각·확인 번호를 남긴다
function lbReceiptCode(c){ var s = c.id + "|" + (state.used[c.id] || ""), h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return ("000000" + (h % 1e6)).slice(-6); }
function lbReceiptHtml(c){
  var t = new Date(state.used[c.id]), ts = isNaN(t) ? "" : isoLocal(t) + " " + String(t.getHours()).padStart(2, "0") + ":" + String(t.getMinutes()).padStart(2, "0");
  return `<div class="rcptcard" data-receipt="${esc(c.id)}"><span class="meta">사용 완료 영수증</span><b>${esc(c.title)}</b><span>${esc(c.shop)}</span>
    <dl class="kv"><dt>사용 시각</dt><dd>${esc(ts)}</dd><dt>확인 번호</dt><dd class="rcode">${esc(lbReceiptCode(c))}</dd></dl>
    ${c.sample ? `<small class="meta">예시 쿠폰이라 실제 혜택은 없어요.</small>` : `<small class="meta">이 화면을 가게에 보여 주면 사용 내역을 확인할 수 있어요.</small>`}</div>`;
}
function lbRenderCouponBook(){
  var el = document.getElementById("tab-coupons"); if (!el) return;
  var mine = PARTNER_COUPONS.filter(function(c){ return state.claimed.indexOf(c.id) >= 0; });
  var used = mine.filter(function(c){ return isUsed(c.id); }), open = mine.filter(function(c){ return !isUsed(c.id); });
  var more = lbCoupons(PARTNER_COUPONS.filter(function(c){ return state.claimed.indexOf(c.id) < 0; }));
  el.innerHTML = `<div class="sec-title"><h2>쿠폰북</h2><span class="en">Coupons</span></div>
    ${open.length ? `<div class="tickets">${open.map(function(c){ return `<div class="ticket">${cpImgHtml(c)}<div><b>${esc(c.title)}</b><span>${esc(c.shop)}</span><small>${c.sample ? "[예시/제휴 준비] " : ""}${esc(c.cond || "")}${c.until ? ` · ${esc(c.until)}까지` : ""}</small></div>${redeemSlot(c)}</div>`; }).join("")}</div>`
      : `<div class="empty cpempty"><b>받은 쿠폰이 아직 없어요</b><span>아래 ‘받을 수 있는 쿠폰’에서 원하는 혜택을 먼저 받아 보세요.</span></div>`}
    ${used.length ? `<h3 style="margin:18px 0 8px">사용 완료 영수증</h3><div class="rcptlist">${used.map(lbReceiptHtml).join("")}</div>` : ""}
    ${PARTNER_COUPONS.length ? `<h3 style="margin:18px 0 8px">받을 수 있는 쿠폰</h3>${lbFilterHtml()}<div class="sponsors">${more.map(function(c){ return lbCouponCard(c, "coupon_book"); }).join("") || `<div class="empty">조건에 맞는 쿠폰이 없어요.</div>`}</div>` : ""}
    <div class="wallet" style="margin-top:18px"><h2>내 쿠폰 메모</h2><span class="meta">다른 곳에서 받은 쿠폰이나 할인 코드를 적어 두세요. 이 휴대폰에만 저장돼요.</span>
      <form id="cpForm2"><input id="cpTitle2" placeholder="쿠폰 이름 (사진만 올려도 돼요)"><input id="cpNote2" placeholder="조건·유효기간·코드">
        <label class="btn ghost cpimgpick">📷 쿠폰 사진<input type="file" accept="image/*" id="cpImg2" hidden></label><button class="btn">추가</button></form>
      <p class="meta" id="cpImgName"></p>
      <ul class="cplist">${state.coupons.map(cpLi).join("") || `<li><span class="meta">저장된 쿠폰이 없어요.</span></li>`}</ul>
    </div>
    <p class="meta" style="margin-top:12px"><button class="linkbtn" data-tab="deals">강원 여행 할인 방법 보기 ›</button> · <button class="linkbtn" data-inquire="" data-inqtype="제휴 쿠폰">사장님 쿠폰 입점 문의 ›</button></p>`;
  loadRcImgs(el);
}
document.addEventListener("click", function(e){
  var f = e.target.closest("[data-cpf]"), n = e.target.closest("[data-cpnear]");
  if (!f && !n) return;
  if (f) LB.region = f.dataset.cpf; if (n) LB.near = !LB.near;
  try { localStorage.setItem("gn_cpfilter", JSON.stringify(LB)); } catch(_) {}
  trackEvent("region_or_filter_use", { filter:f ? "coupon_region" : "coupon_near", value:f ? LB.region : String(LB.near) });
  if (state.tab === "coupons") lbRenderCouponBook(); else renderDeals();
});
// 추천 가게(C4) — 네이티브 카드형 광고 슬롯. Pro 사용자에게는 숨긴다.
var LB_IMP = new Set();
function lbSponsorsHtml(){
  if (isPro()) return `<p class="meta proadfree">PRO · 추천 가게 광고를 숨겼어요.</p>`;
  var ads = SPONSORED.map(function(x){ return Object.assign({}, x, { p:byId(x.id) }); }).filter(function(x){ return x.p && inRegion(x.p); });
  ads.forEach(function(x){ var k = x.id + "|" + state.region; if (!LB_IMP.has(k)){ LB_IMP.add(k); trackEvent("sponsor_impression", { targetId:x.id, region:x.p.region, slot:"C4" }); } });
  var card = function(x){ var ph = null; try { ph = photoFor(x.p); } catch(_) {}
    return `<article class="adcard"><span class="adthumb">${ph ? `<img src="${esc(ph.url)}" alt="" loading="lazy" onerror="this.remove()">` : ""}<i aria-hidden="true">${catEmoji(x.p.cat)}</i></span>
      <span class="adbody"><span class="admeta"><span class="adpill adtag">광고</span><span class="meta">${esc(x.p.area || regionLabel())}</span></span><b>${esc(x.p.name)}</b><span class="adcopy">${esc(x.copy || x.p.sig || "")}</span>
        <button class="linkbtn" type="button" data-goto="${esc(x.p.id)}" data-rev="ad:${esc(x.p.id)}" data-sponsor="${esc(x.p.id)}">자세히 보기 ›</button></span></article>`; };
  return `<section class="adslot revapp" aria-label="추천 가게 광고">
    <div class="adhead"><h3>추천 가게</h3><span class="adpill">광고</span><button class="linkbtn" type="button" data-paywall="ad_free">광고 없이 보기 ${proBadge()}</button></div>
    <div class="adcards">${ads.map(card).join("")}
      <article class="adcard adempty"><span class="adbody"><span class="admeta"><span class="adpill adtag">광고 자리</span></span><b>${esc(regionLabel())} 가게를 여기에 소개하세요</b><span class="adcopy">지역·업종별 상단 노출과 앱 전용 쿠폰을 함께 운영할 수 있어요.</span>
        <button class="linkbtn" type="button" data-inquire="" data-inqtype="광고·추천 노출">입점·광고 문의 ›</button></span></article></div>
    <p class="meta">‘광고’ 표시가 붙은 곳은 비용을 받고 소개하는 가게예요. 추천 순위와 정보는 광고와 별개로 정리해요.</p></section>`;
}
document.addEventListener("click", function(e){
  var s = e.target.closest("[data-sponsor]"); if (!s) return;
  var p = byId(s.dataset.sponsor); trackEvent("sponsor_click", { targetId:s.dataset.sponsor, region:p ? p.region : "", slot:"C4" });
}, true);
// 입점·광고·쿠폰 문의 양식(할인 탭 하단). APK 에서도 이 기기에 저장되고 운영자 연락처로 바로 이어진다.
function lbInquiryHtml(){
  var i = state.inq || {};
  return `<section class="revbox revapp inqbox" id="inqForm" data-pos="I9" aria-label="사장님 입점·광고·쿠폰 문의">
    <h2>사장님 입점·광고·쿠폰 문의</h2>
    <p class="meta">가게 소개(광고), 앱 전용 쿠폰, 숙소·티켓 제휴를 문의할 수 있어요. 내용은 이 기기에 먼저 저장되고, 아래 연락처로 바로 보낼 수도 있어요.</p>
    <form id="inqFormEl" class="formgrid">
      <select id="inqType" aria-label="문의 종류">${INQ_TYPES.map(function(t){ return `<option ${t === i.type ? "selected" : ""}>${esc(t)}</option>`; }).join("")}</select>
      <input id="inqPlace" placeholder="가게·숙소·기관 이름" value="${esc(i.place || "")}" aria-label="가게 이름" required>
      <input id="inqContact" placeholder="연락처(선택) · 전화·카톡 ID" value="${esc(i.contact || "")}" aria-label="연락처">
      <textarea id="inqMsg" placeholder="문의 내용 (예: 안목 카페, 음료 10% 쿠폰 제휴 원해요)" aria-label="문의 내용" required>${esc(i.msg || "")}</textarea>
      <button class="btn" type="submit" ${i.busy ? "disabled" : ""}>문의 남기기</button>
    </form>
    ${i.ok ? `<p class="okline">${esc(i.ok)}</p>` : ""}${i.err ? `<p class="errline">${esc(i.err)}</p>` : ""}
    ${hasContact() ? `<p class="meta">운영자에게 바로 연락하기</p>${contactBtns("입점·광고 문의")}` : `<p class="meta">운영자 연락처가 등록되면 여기에서 카카오톡·전화·이메일로 바로 연결돼요.</p>`}
  </section>`;
}
function lbSaveInquiry(item){
  var all = []; try { all = store.get("local_inquiries", []); } catch(_) {}
  all.push(item); store.set("local_inquiries", all.slice(-50)); return all.length;
}
document.addEventListener("submit", function(e){
  if (e.target.id !== "inqFormEl") return; e.preventDefault();
  var v = function(id){ var el = document.getElementById(id); return el ? el.value.trim() : ""; };
  var item = { type:v("inqType"), place:v("inqPlace"), contact:v("inqContact"), msg:v("inqMsg"), region:state.region, at:new Date().toISOString() };
  if (!item.place || !item.msg){ state.inq = Object.assign({}, item, { err:"가게 이름과 문의 내용을 적어 주세요.", ok:"" }); renderDeals(); return; }
  lbSaveInquiry(item);
  trackEvent("biz_inquiry_submit", { inqType:item.type, region:item.region, hasContact:!!item.contact });
  try { if (RT.db && RT.uid) submitOrQueue("inquiries", item).catch(function(){}); } catch(_) {}
  state.inq = { type:item.type, place:"", contact:"", msg:"", ok:"문의를 이 기기에 저장했어요." + (hasContact() ? " 아래 연락처로 보내면 더 빨리 답을 받을 수 있어요." : " 운영자가 확인하면 연락드려요."), err:"" };
  renderDeals(); try { renderOps(); } catch(_) {}
  var f = document.getElementById("inqForm"); if (f) f.scrollIntoView({ block:"start" });
});
