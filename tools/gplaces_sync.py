"""Google Places API (New) 로 사진 없는 장소의 사진을 찾아 web/kto.json 의 photos 에 더한다.
사용: python3 tools/gplaces_sync.py --key GOOGLE_API_KEY --kto web/kto.json --html web/index.html --ver web/kto_ver.txt
- Google Places API (New) Text Search → Place Details → Photo URL
- 월 $200 무료 크레딧 안에서 수백 곳 처리 가능 (장소당 약 2~3원)
- 구글 사진은 직접 저장 불가 → URL만 저장해 실시간 로딩
"""
import argparse, json, re, urllib.parse, urllib.request, concurrent.futures as cf, time, pathlib, sys

PLACES_BASE = "https://places.googleapis.com/v1"

def search_place(api_key, name, city=""):
    """Google Places Text Search로 장소 검색, place_id 반환"""
    query = name + (" " + city if city else "") + " 강원"
    url = f"{PLACES_BASE}/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.photos"
    }
    body = json.dumps({
        "textQuery": query,
        "languageCode": "ko",
        "regionCode": "KR",
        "maxResultCount": 3
    }).encode()
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        places = data.get("places", [])
        for p in places:
            addr = p.get("formattedAddress", "")
            # 강원도 주소인지 확인
            if "강원" not in addr:
                continue
            photos = p.get("photos", [])
            if photos:
                return p["id"], photos[0]["name"]
    except Exception as e:
        print(f"  검색 오류 ({name}): {e}", file=sys.stderr)
    return None, None

def get_photo_url(api_key, photo_name, max_width=800):
    """Google Places Photo API로 실제 이미지 URL 획득"""
    url = (f"{PLACES_BASE}/{photo_name}/media"
           f"?maxWidthPx={max_width}&key={api_key}&skipHttpRedirect=true")
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("photoUri")
    except Exception as e:
        print(f"  사진 URL 오류: {e}", file=sys.stderr)
    return None

def find_google_photo(api_key, pl):
    """장소 하나에 대해 Google Places 사진 검색"""
    name = re.sub(r"\(.*?\)|（.*?）", "", pl["name"]).split(" · ")[0].strip()
    if len(name) < 2:
        return None
    place_id, photo_name = search_place(api_key, name, pl.get("city", ""))
    if not photo_name:
        return None
    photo_url = get_photo_url(api_key, photo_name)
    if not photo_url:
        return None
    return {
        "url": photo_url,
        "by": "Google",
        "credit": "사진: Google Maps",
        "src": "google"
    }

def targets(kto, html):
    """KTO photos에도 없고 위키에도 없는 장소 목록 반환"""
    have = set(kto.get("photos", {}))
    s = pathlib.Path(html).read_text(encoding="utf-8")
    wiki = set(json.loads(s[s.index("/*PHOTOS*/")+10 : s.index("/*END_PHOTOS*/")]))
    a = s.index("const PLACES = ["); b = s.index("const REG = ")
    out = []
    for pid, name in re.findall(r'\{\s*id:"([^"]+)"[^{}]*?name:"([^"]+)"', s[a:b]):
        if pid not in wiki and pid not in have:
            # city 추출 시도
            city_m = re.search(r'id:"' + re.escape(pid) + r'"[^}]*area:"([^"]+)"', s[a:b])
            city = city_m.group(1) if city_m else ""
            out.append({"id": pid, "name": name, "city": city})
    # KTO items 중 firstimage 없는 것
    for x in kto.get("items", []):
        pid = "kto-" + x["contentid"]
        if x.get("firstimage") or pid in have:
            continue
        parts = x.get("addr1", "").split(" ") + ["", ""]
        out.append({"id": pid, "name": x["title"], "city": parts[1] if len(parts) > 1 else ""})
    return out

def main():
    ap = argparse.ArgumentParser()
    for k in ("key", "kto", "html"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--ver", default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    kto = json.loads(pathlib.Path(a.kto).read_text(encoding="utf-8"))
    kto.setdefault("photos", {})
    gtried_g = set(kto.get("gtried_g", []))  # google 시도 목록 별도 관리

    tg = [t for t in targets(kto, a.html) if t["id"] not in gtried_g]
    print(f"Google Places 검색 대상: {len(tg)}곳", file=sys.stderr)

    if not tg:
        print("검색할 장소 없음")
        return

    # API 키 유효성 간단 확인
    try:
        test_url = f"{PLACES_BASE}/places:searchText"
        test_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": a.key,
            "X-Goog-FieldMask": "places.id"
        }
        test_body = json.dumps({"textQuery": "강릉", "maxResultCount": 1}).encode()
        req = urllib.request.Request(test_url, data=test_body, headers=test_headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        print(f"Google Places API 오류 (키 확인 필요): HTTP {e.code}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Google Places API 연결 실패: {e}", file=sys.stderr)
        return

    got = {}
    done_ids = []

    def process(pl):
        result = find_google_photo(a.key, pl)
        return pl["id"], result

    with cf.ThreadPoolExecutor(a.workers) as ex:
        futures = {ex.submit(process, pl): pl for pl in tg}
        for i, fut in enumerate(cf.as_completed(futures), 1):
            pid, result = fut.result()
            done_ids.append(pid)
            if result:
                got[pid] = result
            if i % 20 == 0:
                print(f"  진행 {i}/{len(tg)} (찾음 {len(got)}곳)", file=sys.stderr)
            time.sleep(0.05)  # API 과부하 방지

    print(f"Google Places 사진 {len(got)}곳 채움 / 대상 {len(tg)}곳", file=sys.stderr)
    kto["photos"].update(got)
    kto["gtried_g"] = sorted(gtried_g | set(done_ids))
    kto["rev"] = int(time.time() * 1000)
    pathlib.Path(a.kto).write_text(json.dumps(kto, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if a.ver:
        pathlib.Path(a.ver).write_text(str(kto["rev"]), encoding="utf-8")
    print(f"Google Places 사진 {len(got)}곳 채움 / 대상 {len(tg)}곳")

try:
    main()
except Exception as e:
    print(f"Google Places 단계 오류: {e}")
