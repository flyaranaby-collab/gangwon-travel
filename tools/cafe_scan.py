"""강릉 카페 후보를 구글 장소 검색으로 모은다(일회성). 평점·후기 수는 고를 때만 보고 앱에 저장하지 않는다."""
import json, os, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
AREAS = ["안목 커피거리", "강문해변", "경포", "초당동", "송정해변", "남항진", "사천해변", "연곡 영진해변", "주문진", "소돌", "정동진", "옥계", "금진", "교동", "강릉역", "중앙시장 명주동", "포남동", "홍제동", "노암동", "내곡동", "입암동", "병산동", "성산면", "왕산면", "구정면", "사천면 미노리", "강동면", "견소동", "운정동", "저동"]
KINDS = ["카페", "베이커리 카페", "디저트 카페", "오션뷰 카페"]
seen = {}
for a in AREAS:
    for k in KINDS:
        q = f"강릉 {a} {k}"
        body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
                "locationRestriction": {"rectangle": {"low": {"latitude": 37.55, "longitude": 128.70}, "high": {"latitude": 37.95, "longitude": 129.10}}}}
        rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                     "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.addressComponents,places.businessStatus,places.primaryType,places.primaryTypeDisplayName,places.rating,places.userRatingCount,places.regularOpeningHours.weekdayDescriptions"})
        try: ps = json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", [])
        except Exception as e: print("ERR", q, e); continue
        for p in ps:
            if p["id"] in seen: continue
            comp = p.get("addressComponents", [])
            loc2 = [c.get("longText") for c in comp if "locality" in c.get("types", []) or "administrative_area_level_2" in c.get("types", [])]
            dong = [c.get("longText") for c in comp if any(t.startswith("sublocality") for t in c.get("types", []))]
            seen[p["id"]] = {"gid": p["id"], "name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""), "city": loc2, "dong": dong,
                "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"),
                "pt": p.get("primaryType"), "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "r": p.get("rating"), "n": p.get("userRatingCount"),
                "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"), "q": a}
        time.sleep(0.2)
for v in seen.values(): print("P=" + json.dumps(v, ensure_ascii=False))
