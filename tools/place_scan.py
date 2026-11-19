"""강릉에서 검색어별 장소 후보를 구글 장소 검색으로 넓게 모은다(일회성). 평점은 고를 때만 보고 앱에 저장하지 않는다.
사용: python3 tools/place_scan.py tools/scan_queries.json"""
import json, os, sys, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
QS = json.load(open(sys.argv[1], encoding="utf-8"))
seen = {}
for q in QS:
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
            "locationRestriction": {"rectangle": {"low": {"latitude": 37.55, "longitude": 128.70}, "high": {"latitude": 37.93, "longitude": 129.10}}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.businessStatus,places.primaryTypeDisplayName,places.types,places.rating,places.userRatingCount,places.regularOpeningHours.weekdayDescriptions,places.servesBeer,places.servesWine"})
    try: ps = json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", [])
    except Exception as e: print("ERR", q, e); continue
    for p in ps:
        if p["id"] in seen: seen[p["id"]]["q"].append(q); continue
        seen[p["id"]] = {"name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
            "lat": p["location"]["latitude"], "lng": p["location"]["longitude"], "st": p.get("businessStatus"),
            "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "types": [t for t in p.get("types", []) if t not in ("point_of_interest", "establishment", "food")][:5],
            "r": p.get("rating"), "n": p.get("userRatingCount"), "gid": p["id"], "beer": p.get("servesBeer"), "wine": p.get("servesWine"),
            "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"), "q": [q]}
    time.sleep(0.3)
for v in seen.values(): print("P=" + json.dumps(v, ensure_ascii=False))
