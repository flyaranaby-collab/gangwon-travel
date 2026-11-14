"""구글 지도(Places API New)에서 지역×검색어 조합으로 평점·리뷰 수가 높은 장소를 찾아 web/gmap.json 에 저장한다.
사용: python3 tools/gmap_discover.py --key GOOGLE_API_KEY --out web/gmap.json
- 검색은 약 200회(지역 14곳 × 검색어 14~15개). 한 번 검색에 최대 20곳.
- 고르는 기준: 영업 중, 주소가 그 시·군, 분류별 평점·리뷰 수 하한(아래 RULE).
- 약관: 구글 장소 정보는 place_id 외에는 오래 저장할 수 없다. 그래서 평점·리뷰 수 숫자는 저장하지 않고
  고를 때만 쓰며, 이 작업을 30일 안에 다시 돌려 좌표를 새로 받는다(gmap.yml 이 매달 실행).
  앱은 place_id 로 구글 지도를 열어 최신 평점·영업시간을 보여 준다.
"""
import argparse, json, re, sys, time, pathlib, urllib.request, concurrent.futures as cf

URL = "https://places.googleapis.com/v1/places:searchText"
MASK = ",".join("places." + f for f in ["id", "displayName", "formattedAddress", "location", "rating", "userRatingCount",
                                        "businessStatus", "primaryType", "primaryTypeDisplayName", "types"])
# 시·군 → (수첩 지역, 바다 여부)
CITY = {"강릉": ("gangneung", 1), "속초": ("sokcho", 1), "고성": ("sokcho", 1), "양양": ("yangyang", 1), "동해": ("donghae", 1),
        "삼척": ("donghae", 1), "평창": ("pyeongchang", 0), "정선": ("jeongseon", 0), "영월": ("jeongseon", 0),
        "춘천": ("chuncheon", 0), "원주": ("wonju", 0), "인제": ("inje", 0), "홍천": ("hongcheon", 0), "화천": ("hwacheon", 0)}
FOOD_SEA = ["맛집", "현지인 맛집", "횟집 물회", "막국수", "해산물 생선구이", "칼국수 국밥"]
FOOD_IN = ["맛집", "현지인 맛집", "막국수", "한우 고기", "닭갈비 송어", "칼국수 국밥"]
COMMON = [("카페", "카페"), ("카페", "베이커리 디저트 카페"), ("소품샵", "소품샵 기념품"),
          ("산", "등산 산"), ("계곡", "계곡 폭포"), ("호수·강", "호수 강 저수지"), ("숲·꽃", "수목원 숲 자연휴양림"), ("관광지", "가볼만한곳 관광명소")]
SEA = [("바다", "해변 해수욕장")]
# 분류별 (리뷰 수 하한, 평점 하한) 조건들 중 하나라도 맞으면 통과 / 지역당 최대 개수
RULE = {"맛집": ([(300, 4.0), (100, 4.4)], 40), "카페": ([(200, 4.1), (80, 4.5)], 15), "소품샵": ([(20, 4.2)], 8),
        "산": ([(30, 4.0)], 10), "계곡": ([(30, 4.0)], 10), "바다": ([(50, 4.0)], 12), "호수·강": ([(50, 4.0)], 8),
        "숲·꽃": ([(50, 4.0)], 8), "관광지": ([(300, 4.2)], 12)}
FOOD_T = {"restaurant", "food", "meal_takeaway", "korean_restaurant", "seafood_restaurant", "noodle_restaurant", "barbecue_restaurant"}
CAFE_T = {"cafe", "coffee_shop", "bakery", "dessert_shop", "tea_house"}
SHOP_T = {"gift_shop", "store", "home_goods_store", "clothing_store", "book_store", "market"}
BAD_SHOP = {"convenience_store", "supermarket", "grocery_store", "department_store", "shopping_mall", "gas_station", "pharmacy", "electronics_store"}
NOT_NATURE = FOOD_T | CAFE_T | {"lodging", "hotel", "motel", "store", "campground", "rv_park", "parking", "bar", "gas_station", "guest_house", "resort_hotel"}
NAT_KEY = {"산": r"(산|봉|령|재|고개)($|\s)|등산|전망대|탐방", "계곡": r"계곡|폭포|소$|골$", "바다": r"해변|해수욕장|해안|항$|등대|바다",
           "호수·강": r"호|강|저수지|댐|습지|유원지|천$", "숲·꽃": r"수목원|숲|휴양림|정원|식물원|공원|꽃"}



def safe(v):
    """구글 지도 이름·주소는 누구나 바꿀 수 있으니 태그·따옴표를 없앤다(앱 화면에서 스크립트 실행 차단)."""
    return re.sub(r"[<>`\"\x00-\x1f]", "", str(v or "")).strip()

def search(key, q):
    body = json.dumps({"textQuery": q, "languageCode": "ko", "regionCode": "KR", "pageSize": 20}).encode()
    hd = {"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": MASK}
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=hd, method="POST"), timeout=25) as r:
                return json.loads(r.read()).get("places", [])
        except urllib.error.HTTPError as e:
            if e.code in (400, 403): raise
            err = e
        except Exception as e:
            err = e
        time.sleep(2 * (i + 1))
    print(f"  검색 실패 {q}: {err}", file=sys.stderr); return []


def ok_type(cat, p):
    t = set(p.get("types", [])); name = p.get("displayName", {}).get("text", "")
    if cat == "맛집": return bool(t & FOOD_T) and not (t & {"lodging", "cafe", "coffee_shop"} and not t & {"restaurant"})
    if cat == "카페": return bool(t & CAFE_T)
    if cat == "소품샵": return bool(t & SHOP_T) and not (t & BAD_SHOP) and not (t & FOOD_T)
    if cat == "관광지": return not (t & NOT_NATURE) and bool(t & {"tourist_attraction", "museum", "park", "historical_landmark", "amusement_park", "observation_deck", "cultural_landmark", "art_gallery", "zoo", "aquarium"})
    return not (t & NOT_NATURE) and bool(re.search(NAT_KEY[cat], name))


def passes(cat, p):
    n, r = p.get("userRatingCount") or 0, p.get("rating") or 0
    return any(n >= a and r >= b for a, b in RULE[cat][0])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    jobs = []
    for city, (reg, sea) in CITY.items():
        for kw in (FOOD_SEA if sea else FOOD_IN): jobs.append((city, reg, "맛집", f"{city} {kw}"))
        for cat, kw in COMMON + (SEA if sea else []): jobs.append((city, reg, cat, f"{city} {kw}"))
    print(f"검색 {len(jobs)}회 시작", file=sys.stderr)
    try: search(a.key, "강릉 맛집")
    except urllib.error.HTTPError as e:
        print(f"구글 지도 API 오류 HTTP {e.code}: 키·사용 설정을 확인하세요", file=sys.stderr); sys.exit(1)
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: search(a.key, j[3]), jobs))
    best, seen_total = {}, 0
    for (city, reg, cat, q), places in zip(jobs, res):
        for p in places:
            seen_total += 1
            addr = p.get("formattedAddress", "")
            if p.get("businessStatus") not in (None, "OPERATIONAL"): continue
            if "강원" not in addr or not re.search(city + r"(시|군)", addr): continue
            if not ok_type(cat, p) or not passes(cat, p): continue
            loc = p.get("location") or {}
            if not loc.get("latitude"): continue
            pid = p["id"]; n, r = p.get("userRatingCount") or 0, p.get("rating") or 0
            row = best.get(pid)
            if row and row["_n"] >= n and row["cat"] != "관광지": continue
            parts = addr.replace("대한민국", "").split()
            area = next((x for x in parts if re.search(r"(읍|면|동|리)$", x)), city)
            tags = (["리뷰많은곳"] if n >= (1000 if cat in ("맛집", "카페", "관광지") else 300) else []) + (["평점높은곳"] if r >= 4.5 else [])
            best[pid] = {"id": pid, "name": safe(p["displayName"]["text"]), "cat": cat, "region": reg, "city": city, "area": re.sub(r"\d+가?$", "", area),
                         "addr": safe(re.sub(r"^대한민국\s*", "", addr)), "lat": round(loc["latitude"], 5), "lng": round(loc["longitude"], 5),
                         "type": (p.get("primaryTypeDisplayName") or {}).get("text", ""), "tags": tags, "_n": n, "_r": r}
    # 지역(시·군)·분류별 상한: 리뷰 수 많은 순
    out, cnt = [], {}
    for row in sorted(best.values(), key=lambda x: (-x["_n"], -x["_r"])):
        k = (row["city"], row["cat"]); cnt[k] = cnt.get(k, 0) + 1
        if cnt[k] > RULE[row["cat"]][1]: continue
        out.append({k2: v for k2, v in row.items() if not k2.startswith("_")})
    by = {}
    for x in out: by[x["cat"]] = by.get(x["cat"], 0) + 1
    if len(out) < 50:
        print(f"고른 곳이 {len(out)}곳뿐이라 저장하지 않습니다", file=sys.stderr); sys.exit(1)
    rev = int(time.time() * 1000)
    pathlib.Path(a.out).write_text(json.dumps({"rev": rev, "src": "Google Maps", "items": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"검색 결과 {seen_total}건 중 {len(out)}곳 저장: {by}")


if __name__ == "__main__":
    main()
