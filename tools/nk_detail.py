"""내곡동 고른 맛집(검색으로 장소 id 확인 후): 리뷰에 자주 나오는 메뉴(글은 저장 안 함)와, 주소가 동네까지만 나오는 곳의 정확한 주소를 확인한다(일회성)."""
import json, os, re, sys, urllib.parse, urllib.request
G = os.environ["GOOGLE_PLACES_KEY"]; K = os.environ.get("KTO_KEY", "")
DISH = ["순두부","짬뽕순두부","막국수","옹심이","장칼국수","칼국수","순대국","순대","해장국","감자탕","뼈해장국","선지","곰치국","섭국","물회","회","생선구이","고등어","가자미","도루묵","삼숙이","대게","홍게","조개","전복","문어","오징어","갈비","돼지갈비","소갈비","갈비탕","삼겹살","오겹살","목살","항정","껍데기","족발","보쌈","수육","한우","육회","불고기","닭갈비","닭볶음탕","백숙","곤드레","쌈밥","보리밥","정식","한정식","백반","비빔밥","전","감자전","메밀전","두부","청국장","된장","김치찌개","부대찌개","냉면","국수","골뱅이","노가리","먹태","치킨","맥주","생맥주","수제맥주","하이볼","칵테일","위스키","와인","막걸리","소주","사케","꼬치","야키토리","사시미","오뎅","어묵탕","계란말이","닭발","곱창","막창","전어","방어","숙회","파전","해물파전","떡볶이","라면","안주","쌀국수","분짜","짜장면","짬뽕","탕수육","참치","연어","닭내장","내장탕","한약","화로","김밥","능이","수제비","물막국수","비빔막국수","편육","만두","제육","돈가스","우동","갈비살","등심","차돌"]
def get(url, headers=None):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=25).read())
def find_id(x):
    body = {"textQuery": x["name"] + " 강릉", "languageCode": "ko", "regionCode": "KR", "maxResultCount": 1,
            "locationBias": {"circle": {"center": {"latitude": x["lat"], "longitude": x["lng"]}, "radius": 300.0}}}
    rq = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": G, "X-Goog-FieldMask": "places.id,places.displayName"})
    ps = json.loads(urllib.request.urlopen(rq, timeout=25).read()).get("places", [])
    return ps[0]["id"] if ps else None
for x in json.load(open(sys.argv[1], encoding="utf-8")):
    x["gid"] = find_id(x)
    out = {"name": x["name"], "gid": x["gid"]}
    try:
        p = get(f"https://places.googleapis.com/v1/places/{x['gid']}?languageCode=ko", {"X-Goog-Api-Key": G, "X-Goog-FieldMask": "reviews,formattedAddress,addressComponents,editorialSummary"})
        txt = " ".join(((r.get("text") or {}).get("text") or "") for r in p.get("reviews", []))
        cnt = {d: len(re.findall(d, txt)) for d in DISH}
        out["top"] = {d: n for d, n in sorted(cnt.items(), key=lambda kv: -kv[1]) if n}
        out["top"] = dict(list(out["top"].items())[:7])
        out["addr"] = p.get("formattedAddress"); out["ed"] = (p.get("editorialSummary") or {}).get("text")
        comp = p.get("addressComponents", [])
        out["comp"] = " ".join(c.get("longText", "") for c in comp if any(t in c.get("types", []) for t in ("route", "street_number", "premise", "sublocality_level_4", "sublocality_level_2")))
    except Exception as e: out["err"] = str(e)[:120]
    try:
        g = get("https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode({"latlng": f"{x['lat']},{x['lng']}", "language": "ko", "result_type": "street_address|premise", "key": G}))
        out["rev"] = [r["formatted_address"] for r in g.get("results", [])[:2]]; out["rev_st"] = g.get("status")
    except Exception as e: out["rev_err"] = str(e)[:120]
    if K:
        try:
            q = urllib.parse.urlencode({"serviceKey": K, "MobileOS": "ETC", "MobileApp": "GangwonTrip", "_type": "json", "keyword": x["name"], "numOfRows": 5, "pageNo": 1}, safe="")
            b = get("https://apis.data.go.kr/B551011/KorService2/searchKeyword2?" + q)["response"]["body"]
            it = (b.get("items") or {}); it = it.get("item", []) if isinstance(it, dict) else []
            out["kto"] = [(i.get("title"), i.get("addr1"), i.get("addr2")) for i in it if "강릉" in (i.get("addr1") or "")][:2]
        except Exception as e: out["kto_err"] = str(e)[:80]
    print("D=" + json.dumps(out, ensure_ascii=False))
