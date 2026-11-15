"""이름으로 구글 장소의 좌표·주소만 받는다(일회성, 평점 없음)."""
import json, os, sys, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
for q in sys.argv[1:]:
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps({"textQuery": q, "languageCode": "ko", "regionCode": "KR", "maxResultCount": 1}).encode(), method="POST",
                                headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY, "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress"})
    try:
        p = json.loads(urllib.request.urlopen(rq, timeout=20).read()).get("places", [{}])[0]
        print("C " + json.dumps({"q": q, "n": p.get("displayName", {}).get("text"), "a": p.get("formattedAddress"), "lat": p.get("location", {}).get("latitude"), "lng": p.get("location", {}).get("longitude"), "id": p.get("id")}, ensure_ascii=False))
    except Exception as e: print("ERR", q, e)
