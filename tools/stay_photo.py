"""숙소 대표 사진을 구글 지도에서 한 장씩 받는다(일회성). 이름·위치가 맞는 곳만. 평점은 받지 않는다."""
import json, math, os, re, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]; API = "https://places.googleapis.com/v1"
norm = lambda s: re.sub(r"[\s·\-()（）\[\]'\"`.,&!~]|강릉|속초|양양|춘천|평창|정선|동해|삼척|고성|원주|홍천|인제|화천|영월|태백|철원|횡성|양구|강원|점$", "", (s or "").lower())
def km(a, b, c, d):
    r = math.radians; x = r(d - b) * math.cos(r((a + c) / 2)); y = r(c - a); return 6371 * math.hypot(x, y)
def call(url, body=None, mask=None):
    h = {"X-Goog-Api-Key": KEY}
    if body is not None: h.update({"Content-Type": "application/json", "X-Goog-FieldMask": mask})
    rq = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET", headers=h)
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(rq, timeout=25).read())
        except Exception as e: err = e; time.sleep(2)
    print("ERR", url[:60], err); return {}
for s in json.load(open("tools/stay_photo_list.json", encoding="utf-8")):
    if "주변" in s["name"]: continue
    far = 5.0 if s["id"].startswith("st-") else 1.5
    res = call(f"{API}/places:searchText", {"textQuery": s["name"], "languageCode": "ko", "regionCode": "KR", "maxResultCount": 3,
        "locationBias": {"circle": {"center": {"latitude": s["lat"], "longitude": s["lng"]}, "radius": 3000.0}}},
        "places.displayName,places.location,places.photos").get("places", [])
    hit = None
    for p in res:
        n1, n2 = norm(s["name"]), norm(p.get("displayName", {}).get("text"))
        if n1 and n2 and (n1 in n2 or n2 in n1) and km(s["lat"], s["lng"], p["location"]["latitude"], p["location"]["longitude"]) <= far and p.get("photos"):
            hit = p; break
    if not hit: print("MISS|" + s["id"] + "|" + s["name"]); continue
    ph = hit["photos"][0]
    uri = call(f"{API}/{ph['name']}/media?maxWidthPx=800&key={KEY}&skipHttpRedirect=true").get("photoUri")
    by = ((ph.get("authorAttributions") or [{}])[0]).get("displayName", "")
    if uri: print("STAYPH|" + json.dumps({"id": s["id"], "url": uri, "by": by, "g": hit["displayName"]["text"]}, ensure_ascii=False))
