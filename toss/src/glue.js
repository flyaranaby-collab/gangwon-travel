/* 토스판 연결 코드 — 수첩 본문 스크립트가 끝난 뒤 실행된다.
   1) 밝은 화면만  2) 토스 뒤로 가기 하나만(최초 화면에서 누르면 미니앱 종료)  3) 외부 링크는 토스 방식으로 열기
   4) 공유는 토스 공유 링크  5) 광고 배너(목록 맨 아래, 상세 화면 맨 아래 — 화면마다 1개)  6) 공유 링크로 들어오면 그 장소 열기 */
(function () {
  var A = window.AIT;
  document.documentElement.setAttribute("data-theme", "light");
  if (!A) return; // 일반 브라우저(검사용)에서는 토스 기능 없이 그대로 동작

  // ── 뒤로 가기: 수첩이 쌓은 방문 기록이 있으면 한 단계 뒤로, 없으면 미니앱 종료
  var depth = 0, push = history.pushState;
  history.pushState = function () { depth++; return push.apply(history, arguments); };
  window.addEventListener("popstate", function () { if (depth > 0) depth--; });
  function onBack() {
    var zb = document.getElementById("zoomBox");
    if (zb && !zb.hidden) { zb.hidden = true; return; }
    var rd = document.querySelector(".redeem:not([hidden]), #redeemBox:not([hidden])");
    if (rd && typeof window.closeRedeem === "function") { window.closeRedeem(); return; }
    if (depth > 0) { history.back(); return; }
    var sp = document.getElementById("subPage");
    if (sp && !sp.hidden && typeof window.closeSub === "function") { window.closeSub(); return; }
    A.closeView();
  }
  try { A.graniteEvent.addEventListener("backEvent", { onEvent: onBack, onError: function () {} }); } catch (_) {}

  // ── 외부 링크: 토스 화면 밖으로 이동하지 않고 기기 브라우저·앱에서 연다
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (/^(https?:|tel:|sms:|mailto:|kakaot:|kakaomap:|nmap:|tmap:|intent:)/i.test(href)) {
      e.preventDefault(); e.stopPropagation();
      A.Device.openURL(href).catch(function () {});
    }
  }, true);

  // ── 광고 배너(테스트 ID는 콘솔에서 받은 실제 ID로 바꿔야 수익이 나요)
  var AD_ID = window.TOSS_AD_BANNER || "ait-ad-test-banner-id";
  function attach(id) {
    var el = document.getElementById(id);
    if (!el || el.dataset.on) return;
    try { if (!A.TossAds.attachBanner.isSupported()) return; } catch (_) { return; }
    el.dataset.on = "1";
    try { A.TossAds.attachBanner(AD_ID, el, { theme: "light", callbacks: { onNoFill: function () { el.classList.add("empty"); } } }); } catch (_) { el.classList.add("empty"); }
  }
  try {
    if (A.TossAds.initialize.isSupported()) {
      A.TossAds.initialize({ callbacks: { onInitialized: function () { attach("tossAdMain"); attach("tossAdSub"); }, onInitializationFailed: function () {} } });
    }
  } catch (_) {}

  // ── 공유 링크로 들어오면(intoss://gangwon-note?place=ID) 그 장소 상세를 연다
  try {
    var q = new URLSearchParams(location.search), pid = q.get("place");
    if (pid && typeof window.openDetail === "function") setTimeout(function () { window.openDetail("p", pid); }, 300);
  } catch (_) {}
})();
