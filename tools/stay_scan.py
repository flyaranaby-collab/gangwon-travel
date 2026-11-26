"""강릉 숙소 후보(일회성). 평점·후기 수는 고를 때만 보고 앱에 저장하지 않는다."""
import json, os, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
QS = ["강릉 호텔", "강릉 오션뷰 호텔", "강릉 리조트", "경포 호텔", "강문 호텔", "안목 호텔", "강릉역 호텔", "강릉 시내 호텔", "주문진 호텔", "주문진 펜션", "사천 펜션", "연곡 펜션",
      "정동진 호텔", "정동진 펜션", "옥계 리조트", "강릉 한옥스테이", "강릉 한옥 숙소", "강릉 게스트하우스", "강릉 감성 숙소", "강릉 풀빌라", "강릉 독채 펜션", "강릉 비즈니스호텔", "강릉 가족 리조트", "송정해변 숙소"]
seen = {}
for q in QS:
    body = {"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20, "includedType": "lodging",
            "locationRestriction": {"rectangle": {"low": {"latitude": 37.55, "longitude": 128.70}, "high": {"latitude": 37.95, "longitude": 129.10}}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.formattedAddress,places.addressComponents,places.businessStatus,places.primaryType,places.primaryTypeDisplayName,places.rating,places.userRatingCount"})
    try: ps = json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("places", [])
    except Exception as e: print("ERR", q, e); continue
    for p in ps:
        city = " ".join(c.get("longText", "") for c in p.get("addressComponents", []))
        if p["id"] in seen or "강릉" not in city: continue
        seen[p["id"]] = {"gid": p["id"], "name": p["displayName"]["text"], "addr": p.get("formattedAddress", "").replace("대한민국 ", ""),
            "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"),
            "pt": p.get("primaryType"), "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "r": p.get("rating"), "n": p.get("userRatingCount"), "q": q}
    time.sleep(0.2)
for v in seen.values(): print("S=" + json.dumps(v, ensure_ascii=False))
