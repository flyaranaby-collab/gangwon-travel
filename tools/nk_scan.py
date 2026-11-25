"""강릉 동네 맛집 후보를(DONGS 환경값의 동만) 구글 장소 검색으로 모은다(일회성). 동 이름이 '내곡동'인 곳만. 평점은 고를 때만 보고 앱에 저장하지 않는다."""
import json, os, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
DONGS = os.environ.get("DONGS", "내곡동").split(",")
BOX = [float(v) for v in os.environ.get("BOX", "37.725,128.865,37.765,128.915").split(",")]
KINDS = ["맛집", "식당", "한식", "고기집", "국밥 해장국", "칼국수 막국수", "중식 중국집", "일식 초밥 돈가스", "횟집 해물", "찜닭 닭갈비", "분식", "술집", "백반 정식", "순두부", "양식 파스타"]
QS = [f"강릉 {d} {k}" for d in DONGS for k in KINDS]
seen = {}
for q in QS:
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
            "locationRestriction": {"rectangle": {"low": {"latitude": BOX[0], "longitude": BOX[1]}, "high": {"latitude": BOX[2], "longitude": BOX[3]}}}}
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
            "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"), "q": q, "gid": p["id"]}
    time.sleep(0.3)
for v in seen.values(): print("P=" + json.dumps(v, ensure_ascii=False))
