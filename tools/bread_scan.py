"""강릉 소금빵·식빵 유명한 곳 후보(일회성). 리뷰 글은 메뉴 단어 수만 세고 저장하지 않는다. 평점은 고를 때만 본다."""
import json, os, re, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
QS = ["강릉 소금빵", "강릉 소금빵 맛집", "강릉 소금빵 베이커리", "강릉 버터 소금빵", "강릉 식빵 맛집", "강릉 우유식빵", "강릉 식빵 전문점", "강릉 옥수수 식빵",
      "강릉 빵집", "강릉 베이커리", "강릉 빵 맛집", "주문진 빵집", "강릉 교동 빵집", "강릉 초당 빵집", "강릉 안목 베이커리", "강릉 포남동 빵집"]
W = ["소금빵", "식빵", "우유식빵", "버터", "크루아상", "바게트", "단팥", "옥수수", "감자빵", "베이글", "스콘", "케이크"]
def post(q):
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
            "locationRestriction": {"rectangle": {"low": {"latitude": 37.55, "longitude": 128.70}, "high": {"latitude": 37.95, "longitude": 129.10}}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.addressComponents,places.businessStatus,places.primaryType,places.rating,places.userRatingCount,places.regularOpeningHours.weekdayDescriptions"})
    return json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", [])
seen = {}
for q in QS:
    try: ps = post(q)
    except Exception as e: print("ERR", q, e); continue
    for p in ps:
        city = " ".join(c.get("longText", "") for c in p.get("addressComponents", []))
        if p["id"] in seen or "강릉" not in city: continue
        seen[p["id"]] = {"gid": p["id"], "name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
            "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"), "pt": p.get("primaryType"),
            "r": p.get("rating"), "n": p.get("userRatingCount"), "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions"), "hit": [q]}
    time.sleep(0.2)
for v in seen.values():
    if v["st"] != "OPERATIONAL" or (v["n"] or 0) < 30 or (v["r"] or 0) < 4.0: continue
    try:
        rq = urllib.request.Request(f"https://places.googleapis.com/v1/places/{v['gid']}?languageCode=ko", headers={"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": "reviews,editorialSummary"})
        d = json.loads(urllib.request.urlopen(rq, timeout=25).read())
        txt = " ".join(((r.get("text") or {}).get("text") or "") for r in d.get("reviews", []))
        v["w"] = {w: len(re.findall(w, txt)) for w in W if re.search(w, txt)}
        v["ed"] = (d.get("editorialSummary") or {}).get("text")
    except Exception as e: v["err"] = str(e)[:80]
    print("B=" + json.dumps(v, ensure_ascii=False))
