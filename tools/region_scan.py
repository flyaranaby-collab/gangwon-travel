"""강원 시·군 맛집·카페 후보를 구글로 모아 고르고, 고른 곳만 메뉴·영업시간을 확인한다(일회성).
평점·후기 수는 고를 때만 쓰고 앱에 저장하지 않는다. 리뷰 글은 메뉴 낱말 수만 센다."""
import json, math, os, re, sys, time, urllib.request
KEY = os.environ["GOOGLE_PLACES_KEY"]; API = "https://places.googleapis.com/v1"
CFG = [("sokcho","속초",38.207,128.591,14,7),("sokcho","고성",38.38,128.47,7,4),("yangyang","양양",38.075,128.62,16,8),
       ("donghae","동해",37.525,129.114,12,6),("donghae","삼척",37.44,129.165,10,5),("pyeongchang","평창",37.45,128.45,18,8),
       ("jeongseon","정선",37.38,128.66,12,5),("jeongseon","영월",37.18,128.46,10,5),("chuncheon","춘천",37.881,127.73,20,10),
       ("wonju","원주",37.342,127.92,20,10),("inje","인제",38.07,128.17,14,6),("hongcheon","홍천",37.697,127.888,14,6),("hwacheon","화천",38.106,127.708,10,4)]
FQ = ["맛집","현지인 맛집","한식","막국수","국밥 해장국","닭갈비","고기 맛집","중국집","횟집","칼국수","순두부 두부","돈가스 일식","분식 김밥","곤드레 산채"]
CQ = ["카페","베이커리 카페","디저트 카페"]
CAFE_T = {"cafe","coffee_shop","bakery","dessert_shop","tea_house","ice_cream_shop","cake_shop","confectionery","dessert_restaurant","cafeteria"}
CHAIN = re.compile(r"스타벅스|이디야|투썸|메가MGC|메가커피|컴포즈|빽다방|할리스|파스쿠찌|엔제리너스|탐앤탐스|커피빈|폴바셋|더벤티|매머드|공차|맘스터치|롯데리아|맥도날드|버거킹|KFC|교촌|BBQ|bhc|굽네|파리바게뜨|뚜레쥬르|배스킨|설빙|본죽|김밥천국|한솥|이삭토스트|서브웨이|도미노|피자헛|신전떡볶이|엽기떡볶이|홍콩반점|역전우동|명랑핫도그|하삼동|요거프레소|던킨|크리스피|아웃백|빕스|애슐리|CU|GS25|세븐일레븐|이마트|홈플러스|롯데마트|휴게소", re.I)
DISH = ["막국수","메밀","닭갈비","곤드레","산채","황태","순두부","두부","청국장","옹심이","감자","장칼국수","칼국수","수제비","국밥","순대","해장국","감자탕","뼈다귀","냉면","갈비","한우","삼겹살","돼지","오리","백숙","삼계탕","닭볶음탕","찜닭","보쌈","족발","불고기","정식","백반","한정식","쌈밥","비빔밥","보리밥","생선구이","물회","회","대게","홍게","곰치","섭국","전복","해물","매운탕","짬뽕","짜장","탕수육","돈가스","돈까스","초밥","우동","라멘","파스타","피자","스테이크","버거","김밥","떡볶이","만두","치킨","전","묵","송어","어죽","쏘가리","더덕","약초","곤달비","콧등치기","올챙이국수","부대찌개","김치찌개","된장","커피","라떼","핸드드립","케이크","빵","소금빵","크루아상","스콘","쿠키","빙수","젤라또","타르트","티라미수","에그타르트","아인슈페너","휘낭시에","베이글","브런치","대추차","쌍화차","감자빵","옥수수"]
def call(url, body=None, mask=""):
    h = {"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": mask}
    if body is not None: h["Content-Type"] = "application/json"
    rq = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET", headers=h)
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(rq, timeout=30).read())
        except Exception as e: err = e; time.sleep(2)
    print("ERR", url[:70], err, file=sys.stderr); return {}
EX = json.load(open("tools/exist.json", encoding="utf-8"))
nz = lambda t: re.sub(r"\(.*?\)|[\s·\-&_.,'\"]|본점|점$|카페|cafe|커피|coffee", "", (t or "").lower())
def km(a, b, c, d): r = math.radians; return 6371 * math.hypot(r(d - b) * math.cos(r((a + c) / 2)), r(c - a))
def exists(x):
    for n, la, ln in EX:
        d = km(la, ln, x["lat"], x["lng"])
        if d < 0.04: return n
        a, b = nz(n), nz(x["name"])
        if d < 2 and len(a) >= 2 and len(b) >= 2 and (a in b or b in a): return n
    return None
SMASK = "places.id,places.displayName,places.location,places.formattedAddress,places.addressComponents,places.businessStatus,places.primaryType,places.primaryTypeDisplayName,places.rating,places.userRatingCount"
allpick = []
for rid, city, la, ln, fn, cn in CFG:
    seen = {}
    for kind, qs in (("f", FQ), ("c", CQ)):
        for q in qs:
            r = call(f"{API}/places:searchText", {"textQuery": f"강원 {city} {q}", "languageCode": "ko", "regionCode": "KR", "pageSize": 20,
                     "locationBias": {"circle": {"center": {"latitude": la, "longitude": ln}, "radius": 30000.0}}}, SMASK)
            for p in r.get("places", []):
                addr = p.get("formattedAddress", "")
                if p["id"] in seen or "강원" not in addr or city not in addr: continue
                pt = p.get("primaryType") or ""
                is_c = pt in CAFE_T
                if not is_c and not ("restaurant" in pt or pt in ("meal_takeaway", "food", "food_court", "barbecue_restaurant")): continue
                seen[p["id"]] = {"rid": rid, "city": city, "gid": p["id"], "name": p["displayName"]["text"], "addr": addr.replace("대한민국 ", "").replace(" KR", ""),
                    "lat": round(p["location"]["latitude"], 5), "lng": round(p["location"]["longitude"], 5), "st": p.get("businessStatus"),
                    "pt": pt, "type": (p.get("primaryTypeDisplayName") or {}).get("text"), "r": p.get("rating") or 0, "n": p.get("userRatingCount") or 0, "cafe": is_c,
                    "dong": [c.get("longText") for c in p.get("addressComponents", []) if any(t.startswith("sublocality") for t in c.get("types", []))]}
            time.sleep(0.15)
    minn = 30 if city in ("속초","춘천","원주","강릉","양양","동해","평창") else 15
    C = [x for x in seen.values() if x["st"] == "OPERATIONAL" and x["r"] >= 4.2 and x["n"] >= minn and not CHAIN.search(x["name"]) and not exists(x)]
    C.sort(key=lambda x: -(x["r"] * math.log(x["n"] + 1)))
    pick = [x for x in C if not x["cafe"]][:fn] + [x for x in C if x["cafe"]][:cn]
    print(f"{city}: 후보 {len(seen)} → 기준 통과 {len(C)} → 고름 {len(pick)}", file=sys.stderr)
    allpick += pick
for x in allpick:
    d = call(f"{API}/places/{x['gid']}?languageCode=ko", mask="reviews,editorialSummary,regularOpeningHours.weekdayDescriptions,priceRange")
    txt = " ".join([x["name"], (d.get("editorialSummary") or {}).get("text") or ""] + [((r.get("text") or {}).get("text") or "") for r in d.get("reviews", [])])
    x["w"] = {w: txt.count(w) for w in DISH if w in txt}
    x["ed"] = (d.get("editorialSummary") or {}).get("text")
    x["hours"] = (d.get("regularOpeningHours") or {}).get("weekdayDescriptions")
    pr = d.get("priceRange") or {}
    x["price"] = [int((pr.get("startPrice") or {}).get("units") or 0), int((pr.get("endPrice") or {}).get("units") or 0)] if pr else None
    print("R=" + json.dumps(x, ensure_ascii=False))
