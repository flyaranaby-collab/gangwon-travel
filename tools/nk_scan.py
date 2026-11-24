"""강릉 내곡동 맛집 후보를 구글 장소 검색으로 모은다(일회성). 동 이름이 '내곡동'인 곳만. 평점은 고를 때만 보고 앱에 저장하지 않는다."""
import json, os, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
QS = ["강릉 내곡동 맛집", "내곡동 식당 강릉", "강릉 내곡동 한식", "강릉 내곡동 고기집", "강릉 내곡동 국밥 해장국", "강릉 내곡동 칼국수 막국수",
      "강릉 내곡동 중식 중국집", "강릉 내곡동 일식 초밥 돈가스", "강릉 내곡동 횟집 해물", "강릉 내곡동 찜닭 닭갈비", "강릉 내곡동 카페 베이커리",
      "강릉 내곡동 분식", "강릉 내곡동 술집", "강릉 내곡동 백반 정식", "강릉 내곡동 순두부", "강릉 내곡동 브런치 양식 파스타"]
seen = {}
for q in QS:
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
            "locationRestriction": {"rectangle": {"low": {"latitude": 37.725, "longitude": 128.865}, "high": {"latitude": 37.765, "longitude": 128.915}}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.addressComponents,places.businessStatus,places.primaryTypeDisplayName,places.types,places.rating,places.userRatingCount,places.regularOpeningHours.weekdayDescriptions,places.priceRange"})
    try: ps = json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", [])
    except Exception as e: print("ERR", q, e); continue
    for p in ps:
        dong = [c.get("longText") for c in p.get("addressComponents", []) if any(t.startswith("sublocality") for t in c.get("types", []))]
        if p["id"] in seen: continue
        seen[p["id"]] = {"name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""), "dong": dong,
            "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"),
            "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "r": p.get("rating"), "n": p.get("userRatingCount"),
            "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"), "q": q}
    time.sleep(0.3)
for v in seen.values(): print("P=" + json.dumps(v, ensure_ascii=False))
