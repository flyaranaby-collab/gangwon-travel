"""고른 빵집이 영업 중인지·정확한 위치·영업시간 확인(일회성). 평점은 저장하지 않는다."""
import json, os, re, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
QS = ["인솔트 베이커리 강릉", "카페 초이 강릉 소금빵", "강릉빵다방 본점", "교동빵집 강릉", "돌체테리아 강릉"]
for q in QS:
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "maxResultCount": 2,
            "locationBias": {"circle": {"center": {"latitude": 37.76, "longitude": 128.89}, "radius": 15000.0}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.businessStatus,places.rating,places.userRatingCount,places.regularOpeningHours.weekdayDescriptions,places.reviews"})
    for p in json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", []):
        txt = " ".join(((r.get("text") or {}).get("text") or "") for r in p.get("reviews", []))
        w = {k: len(re.findall(k, txt)) for k in ["소금빵", "식빵", "먹물", "인절미", "바질", "치즈", "버터", "줄"] if re.search(k, txt)}
        print("C=" + json.dumps({"q": q, "gid": p["id"], "name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
              "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"), "r": p.get("rating"), "n": p.get("userRatingCount"),
              "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"), "w": w}, ensure_ascii=False))
