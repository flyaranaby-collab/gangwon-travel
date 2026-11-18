"""고른 중식집 리뷰에서 자주 나오는 메뉴만 센다(리뷰 글은 저장하지 않음, 일회성)."""
import json, os, re, sys, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]
DISH = ["짬뽕","짜장면","간짜장","물짜장","탕수육","볶음밥","잡채밥","울면","굴짬뽕","해물짬뽕","고기짬뽕","차돌짬뽕","백짬뽕","볶음짬뽕","짬뽕밥","유린기","깐풍기","깐쇼새우","멘보샤","팔보채","유산슬","군만두","물만두","찐만두","마파두부","고추잡채","꽃빵","양장피","쟁반짜장","수타","중국냉면","해물누룽지탕","크림새우","칠리새우","동파육","짜장밥","삼선짬뽕","냉짬뽕"]
for gid in json.load(open(sys.argv[1])):
    rq = urllib.request.Request(f"https://places.googleapis.com/v1/places/{gid}?languageCode=ko", headers={"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": "displayName,reviews,editorialSummary,shortFormattedAddress,formattedAddress"})
    try: p = json.loads(urllib.request.urlopen(rq, timeout=25).read())
    except Exception as e: print("ERR", gid, e); continue
    txt = " ".join(((r.get("text") or {}).get("text") or "") for r in p.get("reviews", []))
    cnt = {d: len(re.findall(d, txt)) for d in DISH}; top = [d for d, n in sorted(cnt.items(), key=lambda x: -x[1]) if n][:5]
    print("M=" + json.dumps({"gid": gid, "name": p["displayName"]["text"], "addr": p.get("formattedAddress"), "short": p.get("shortFormattedAddress"), "top": top, "cnt": {d: cnt[d] for d in top}, "nrev": len(p.get("reviews", [])), "ed": (p.get("editorialSummary") or {}).get("text")}, ensure_ascii=False))
