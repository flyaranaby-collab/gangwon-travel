window.APK_BUILD=true;window.NOTE_VER="20261127130835";window.GW_CONFIG={KAKAO_KEY:"0a386489f5dc157a8a5e8773ba2133b6",REMOTE_ENABLED:true};window.KAKAO_KEY=window.GW_CONFIG.KAKAO_KEY;document.addEventListener("error",function(e){var t=e.target;if(t&&t.tagName==="IMG"&&!t.dataset.fb&&/\/assets\/photos\/|android_asset\/photos\//.test(t.src)){t.dataset.fb="1";t.src="https://raw.githubusercontent.com/flyaranaby-collab/gangwon-travel/main/web/photos/"+t.src.split("/").pop();}},true);

/* ───────── 2-2 수익화 설정 (사업 설정값은 모두 여기서 바꾼다) ─────────
 * - 실결제·서버 없이 동작하는 1차 클라이언트 버전이다.
 * - affId 가 비어 있거나 "YOUR_" 로 시작하면 placeholder 로 보고, 제휴 파라미터를 뺀 일반 검색 링크(affiliate_mode: "fallback")로 연결한다.
 * - 운영 탭 '수익 설정'에서 바꾼 파트너 값(OWNER.biz.partner)이 있으면 그 값이 여기 기본값보다 우선한다.
 */
window.GW_CONFIG.BIZ = {
  // P0-1 멀티 제휴 링크. tpl 의 {q}=검색어, {affId}=제휴 ID. {affId}가 든 쿼리 파라미터는 제휴 ID가 없으면 통째로 빠진다.
  AFFILIATE: {
    utm: { source: "gw_note", medium: "app" },   // utm_campaign={카테고리}, utm_content={장소 id} 는 자동
    partners: {
      stay: [
        { id: "tripcom", name: "트립닷컴", badge: "해외카드 OK", enabled: true, affId: "YOUR_TRIPCOM_ALLIANCE_ID",
          tpl: "https://kr.trip.com/hotels/list?keyword={q}&Allianceid={affId}" },
        { id: "agoda", name: "아고다", badge: "", enabled: true, affId: "YOUR_AGODA_CID",
          tpl: "https://www.agoda.com/ko-kr/search?textToSearch={q}&cid={affId}" },
        { id: "naver", name: "네이버 가격비교", badge: "비교", enabled: true, affId: "",
          tpl: "https://search.naver.com/search.naver?query={q}+%EC%98%88%EC%95%BD+%EA%B0%80%EA%B2%A9" }
      ],
      ticket: [
        { id: "myrealtrip", name: "마이리얼트립", badge: "", enabled: true, affId: "YOUR_MRT_PARTNER_ID",
          tpl: "https://www.myrealtrip.com/search?q={q}&mrt_partner={affId}" },
        { id: "klook", name: "클룩", badge: "외국인 추천", enabled: true, affId: "YOUR_KLOOK_AID",
          tpl: "https://www.klook.com/ko/search/result/?query={q}&aid={affId}" },
        { id: "naver", name: "네이버 예매", badge: "비교", enabled: true, affId: "",
          tpl: "https://search.naver.com/search.naver?query={q}+%EC%98%88%EB%A7%A4" }
      ],
      car: [
        { id: "tripcom-car", name: "트립닷컴 렌터카", badge: "", enabled: true, affId: "YOUR_TRIPCOM_ALLIANCE_ID",
          tpl: "https://kr.trip.com/carhire/?pickupLocation={q}&Allianceid={affId}" },
        { id: "naver-car", name: "렌터카 가격비교", badge: "비교", enabled: true, affId: "",
          tpl: "https://search.naver.com/search.naver?query={q}+%EB%A0%8C%ED%84%B0%EC%B9%B4" }
      ]
    }
  },
  // P0-2 강원 수첩 Pro (실결제 없음 · 테스트 토글로만 전환)
  PRO: {
    plans: {
      pass7: { name: "7일 패스", price: 2900, days: 7 },
      annual: { name: "연간 Pro", price: 19900, days: 365 }
    },
    smartCourseFreePerDay: 2,   // P0-3 무료 사용자의 스마트 코스 하루 횟수
    freeTrips: 1                // P1-1/P0-2 무료 사용자가 가질 수 있는 여행 수첩 수
  },
  // P0-4 샘플 쿠폰: 운영자가 실제 쿠폰을 등록하지 않았을 때만 '[예시/제휴 준비]' 배지로 보여 준다. false 면 숨김.
  SAMPLE_COUPONS: true,
  // P0-5 뚜벅이: 역·터미널 반경(km)과 택시 요금 근사치(강원 중형 기준 [추정] · 참고용)
  CARFREE: { radiusKm: 3, longLegKm: 5, lastBusWarnHour: 18, taxi: { base: 4800, baseKm: 1.6, perKm: 760, nightRate: 1.2 } },
  // P0-6 반값여행(지역사랑 휴가지원) 계산기. 정책 기준·한도는 시기별로 바뀐다 → 공식 공고 확인 필수.
  HALFPRICE: {
    rate: 0.5, capPerPerson: 100000, capPerTeam: 200000,
    regions: [
      { id: "pyeongchang", name: "평창", app: "pyeongchang", target: true },
      { id: "yeongwol", name: "영월", app: "jeongseon", target: true },
      { id: "hoengseong", name: "횡성", app: "wonju", target: true },
      { id: "other", name: "그 밖의 강원 지역", app: "", target: false }
    ]
  },
  // P0-7 이벤트 로거
  EVENTS: { key: "gn_events", max: 1000 }
};
