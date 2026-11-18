"""강릉 중식집 후보를 구글 장소 검색으로 넓게 모은다(일회성). 평점은 고를 때만 보고 저장하지 않는다."""
import json, os, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
QS = ["강릉 중국집", "강릉 짬뽕 맛집", "강릉 짜장면", "강릉 탕수육", "주문진 중국집", "강릉 중화요리", "강릉 딤섬 만두", "강릉 마라 양꼬치", "강릉역 중국집", "교동 중국집 강릉", "포남동 중국집", "강릉 옥계 연곡 중국집"]
seen = {}
for q in QS:
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
            "locationRestriction": {"rectangle": {"low": {"latitude": 37.55, "longitude": 128.70}, "high": {"latitude": 37.93, "longitude": 129.10}}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.businessStatus,places.primaryTypeDisplayName,places.types,places.rating,places.userRatingCount,places.regularOpeningHours.weekdayDescriptions"})
    try: ps = json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", [])
    except Exception as e: print("ERR", q, e); continue
    for p in ps:
        if p["id"] in seen: continue
        seen[p["id"]] = {"name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
            "lat": p["location"]["latitude"], "lng": p["location"]["longitude"], "st": p.get("businessStatus"),
            "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "types": p.get("types", []),
            "r": p.get("rating"), "n": p.get("userRatingCount"), "gid": p["id"],
            "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions")}
    time.sleep(0.3)
print("CN_JSON=" + json.dumps(list(seen.values()), ensure_ascii=False))
