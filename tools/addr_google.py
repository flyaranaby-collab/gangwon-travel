"""주소가 없는 직접 고른 장소를 구글 장소 검색(이름 + 좌표 1km 근처)으로 찾는다. 일회성.
- 이름이 겹치고(한쪽이 다른 쪽 포함, 길이 절반 이상) 좌표가 가까운(맛집·카페 0.5km, 그 밖 1.2km) 강원 주소만 인정.
- 못 찾으면 비워 둔다. 평점 등은 받지 않는다.
"""
import json, math, os, re, sys, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
norm = lambda s: re.sub(r"[\s·\-()（）\[\]'\"`.,&]|강릉|속초|춘천|강원|본점|점$", "", s or "")
def km(a, b, c, d):
    r = math.radians; return 6371 * math.hypot(r(d - b) * math.cos(r((a + c) / 2)), r(c - a))
def parts(name):
    ps = [p.strip() for p in re.split(r"[·/]|\(|\)", name) if p.strip()]
    return list(dict.fromkeys([ps[0] if ps else name] + [p for p in ps[1:] if len(norm(p)) >= 3]))
def search(q, la, lo):
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "maxResultCount": 5,
            "locationBias": {"circle": {"center": {"latitude": la, "longitude": lo}, "radius": 1500.0}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY, "X-Goog-FieldMask": "places.displayName,places.location,places.formattedAddress,places.shortFormattedAddress"})
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(rq, timeout=25).read()).get("places", [])
        except Exception as e: err = e; time.sleep(2)
    print("ERR", q, err); return []
out, calls = {}, 0
for t in json.load(open(sys.argv[1], encoding="utf-8")):
    lim = 0.5 if t.get("cat") in ("맛집", "카페") else 1.2; best = None
    for kw in parts(t["name"]):
        calls += 1
        for p in search(kw, t["lat"], t["lng"]):
            n1, n2 = norm(kw), norm(p.get("displayName", {}).get("text"))
            a = (p.get("formattedAddress") or "").replace("대한민국 ", "").strip()
            if not n1 or not n2 or not (n1 in n2 or n2 in n1) or min(len(n1), len(n2)) / max(len(n1), len(n2)) < 0.5: continue
            if "강원" not in a: continue
            d = km(t["lat"], t["lng"], p["location"]["latitude"], p["location"]["longitude"])
            if d > lim: continue
            if not best or d < best[0]: best = (d, p, a)
        if best: break
    if best: out[t["id"]] = {"addr": best[2], "g": best[1]["displayName"]["text"], "km": round(best[0], 2)}
print("FOUND_JSON=" + json.dumps(out, ensure_ascii=False))
print(f"찾음 {len(out)} / 검색 {calls}회")
