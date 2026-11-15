"""강릉 현지인 맛집·포토존 조사용(일회성). 구글 장소 검색으로 평점·리뷰 수·영업 상태·영업시간·리뷰 5개(날짜 포함)를 받아 기록에만 출력한다(저장소에 저장하지 않음)."""
import json, os, sys, urllib.request, concurrent.futures as cf
KEY = os.environ["GOOGLE_PLACES_KEY"]
DONG = "교동 포남동 홍제동 내곡동 입암동 송정동 견소동 남문동 성남동 옥천동 임당동 초당동 노암동 유천동 운정동 저동 박월동 사천면 연곡면 주문진읍 옥계면 강동면 구정면 성산면 왕산면".split()
FOODQ = [f"강릉 {d} 맛집" for d in DONG] + [f"강릉 {x}" for x in "장칼국수 칼국수 백반 국밥 생선구이 물회 막국수 중국집 순대국 감자옹심이 횟집 곰치국 섭국 해장국 두부 닭갈비 돈까스 수제버거 냉면 한정식 생선조림 아구찜 보리밥 수육".split()]
SPOTQ = [f"강릉 {x}" for x in "해변 산책로 전망대 호수 습지 숲길 일출 노을 포토존 출렁다리 등대 정자 사찰 유적지 공원 계곡 항구 솔밭 둘레길 저수지 카페거리 벽화마을 바다 정원".split()]
MASK = ",".join("places." + f for f in ["id", "displayName", "formattedAddress", "rating", "userRatingCount", "businessStatus", "primaryTypeDisplayName", "types",
                                         "regularOpeningHours.weekdayDescriptions", "nationalPhoneNumber", "googleMapsUri", "priceRange", "reviews", "location"])
def search(q):
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "maxResultCount": 20}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
                                headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY, "X-Goog-FieldMask": MASK})
    try:
        with urllib.request.urlopen(rq, timeout=30) as r: return q, json.loads(r.read()).get("places", [])
    except Exception as e:
        print("ERR", q, e, file=sys.stderr); return q, []
seen = {}
with cf.ThreadPoolExecutor(6) as ex:
    for kind, qs in (("food", FOODQ), ("spot", SPOTQ)):
        for q, ps in ex.map(search, qs):
            for p in ps:
                if "강릉" not in p.get("formattedAddress", ""): continue
                n, r = p.get("userRatingCount", 0), p.get("rating", 0)
                if kind == "food" and not (r >= 4.3 and 100 <= n <= 500): continue
                if kind == "spot" and not (r >= 4.3 and 20 <= n <= 800): continue
                if p["id"] in seen: continue
                rv = [{"r": x.get("rating"), "t": x.get("publishTime", "")[:10], "x": ((x.get("originalText") or x.get("text") or {}).get("text", "")).replace("\n", " ")[:400],
                       "a": (x.get("authorAttribution") or {}).get("displayName", "")} for x in p.get("reviews", [])]
                seen[p["id"]] = 1
                pr = p.get("priceRange") or {}
                print("ROW " + json.dumps({"k": kind, "q": q, "n": p["displayName"]["text"], "ad": p.get("formattedAddress"), "rt": r, "c": n,
                       "st": p.get("businessStatus"), "ty": (p.get("primaryTypeDisplayName") or {}).get("text"), "h": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"),
                       "ph": p.get("nationalPhoneNumber"), "u": p.get("googleMapsUri"), "pr": [(pr.get("startPrice") or {}).get("units"), (pr.get("endPrice") or {}).get("units")],
                       "rv": rv}, ensure_ascii=False), flush=True)
print("TOTAL", len(seen))
