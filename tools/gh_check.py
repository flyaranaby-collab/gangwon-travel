"""게스트하우스 후보가 실제로 있고 영업 중인지 구글 장소 검색으로 확인한다(일회성).
평점은 고를 때만 보고 저장하지 않는다."""
import json, os, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
C = {"gn": (37.76, 128.90), "sc": (38.20, 128.59), "yy": (38.07, 128.62), "cc": (37.88, 127.73)}
CAND = [
 ("gn","강릉 아카펠라 게스트하우스"),("gn","강릉 게스트하우스 중앙점"),("gn","강릉 ing 게스트하우스"),("gn","정동진 썬 게스트하우스"),
 ("gn","강릉 K 게스트하우스"),("gn","강릉 예울림 게스트하우스"),("gn","정동진 블루마루 게스트하우스"),
 ("sc","속초 휘테 게스트하우스"),("sc","속초 더 블루도어 게스트하우스"),("sc","속초 제임스블루 게스트하우스"),("sc","속초 길손 게스트하우스"),("sc","속초 하루 게스트하우스"),
 ("yy","양양 하조엔 게스트하우스"),("yy","양양 Home9 게스트하우스"),("yy","양양 바다정원 게스트하우스"),
 ("cc","게스트하우스 휴 춘천역"),("cc","춘천 로하스 게스트하우스"),
]
def search(q, c):
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "maxResultCount": 3,
            "locationBias": {"circle": {"center": {"latitude": c[0], "longitude": c[1]}, "radius": 25000.0}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.displayName,places.location,places.formattedAddress,places.businessStatus,places.primaryTypeDisplayName,places.rating,places.userRatingCount"})
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(rq, timeout=25).read()).get("places", [])
        except Exception as e: err = e; time.sleep(2)
    print("ERR", q, err); return []
for r, q in CAND:
    for p in search(q, C[r]):
        print("GH|" + json.dumps({"q": q, "name": p.get("displayName", {}).get("text"), "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
              "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"),
              "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "r": p.get("rating"), "n": p.get("userRatingCount")}, ensure_ascii=False))
