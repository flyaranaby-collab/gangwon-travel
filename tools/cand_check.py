"""후보 가게가 강릉에 실제로 있고 영업 중인지 구글 장소 검색으로 확인한다(일회성). 평점은 받지 않는다."""
import json, os, re, sys, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
norm = lambda s: re.sub(r"[\s·\-()（）\[\]'\"`.,&]|강릉|본점|점$", "", s or "")
def search(q):
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "maxResultCount": 5,
            "locationBias": {"circle": {"center": {"latitude": 37.76, "longitude": 128.90}, "radius": 30000.0}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.businessStatus,places.primaryTypeDisplayName,places.regularOpeningHours.weekdayDescriptions"})
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(rq, timeout=25).read()).get("places", [])
        except Exception as e: err = e; time.sleep(2)
    print("ERR", q, err); return []
out = {}
for name in json.load(open(sys.argv[1], encoding="utf-8")):
    res = []
    for p in search(name + " 강릉"):
        n1, n2 = norm(name), norm(p.get("displayName", {}).get("text"))
        ok = bool(n1 and n2 and (n1 in n2 or n2 in n1))
        res.append({"ok": ok, "name": p.get("displayName", {}).get("text"), "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
                    "lat": p["location"]["latitude"], "lng": p["location"]["longitude"], "st": p.get("businessStatus"),
                    "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "gid": p.get("id"),
                    "hours": (p.get("regularOpeningHours") or {}).get("weekdayDescriptions")})
    out[name] = res
print("CAND_JSON=" + json.dumps(out, ensure_ascii=False))
