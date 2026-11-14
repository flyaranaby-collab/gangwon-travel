"""한국관광공사 TourAPI(국문 관광정보 서비스_GW)에서 강원 정보를 받아 index.html 에 넣는다.
사용: python3 tools/tourapi_sync.py --key 인증키 [--html index.html]
- 인증키는 파일에 저장하지 않는다.
- 사진은 공공누리 제1·3유형(출처 표시, 상업 이용 가능)만 쓴다.
"""
import argparse, json, re, subprocess, sys, pathlib, concurrent.futures as cf, urllib.parse

B = "https://apis.data.go.kr/B551011/KorService2"
SG = [1,5,2,7,3,4,15,11,8,13,9,10,16,17]
CT = [12,14,28,38,39,32]
OK_LICENSE = {"Type1", "Type3"}
DETAIL = {  # 콘텐츠 유형별 상세 필드 → 수첩이 쓰는 이름
  12: {"restdate":"restdate","usetime":"usetime"},
  14: {"restdateculture":"restdate","usetimeculture":"usetime","usefee":"usefee"},
  28: {"restdateleports":"restdate","usetimeleports":"usetime","usefeeleports":"usefee"},
  38: {"restdateshopping":"restdate","opentime":"usetime"},
  39: {"restdatefood":"restdate","opentimefood":"usetime","firstmenu":"firstmenu"},
}

def call(key, op, **p):
    p.update(serviceKey=key, MobileOS="ETC", MobileApp="GangwonTrip", _type="json")
    u = B + "/" + op + "?" + urllib.parse.urlencode(p, safe="")
    err = ""
    for _ in range(5):
        r = subprocess.run(["curl","-sS","-m","45",u], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.startswith("{"):
            j = json.loads(r.stdout); h = j["response"]["header"]
            if h["resultCode"] != "0000": raise SystemExit("API 오류: " + h["resultMsg"])
            return j["response"]["body"]
        err = r.stderr or r.stdout[:200]
    raise RuntimeError(err)

def items(b):
    it = (b.get("items") or {})
    it = it.get("item") if isinstance(it, dict) else None
    return it if isinstance(it, list) else ([it] if it else [])

def list_all(key, sg, ct):
    """(목록, 끝까지 받았는지). 한도 초과 등으로 중간에 끊기면 False 로 알려 준다."""
    out, page, total = [], 1, 0
    while True:
        b = call(key, "areaBasedList2", areaCode=32, sigunguCode=sg, contentTypeId=ct, numOfRows=300, pageNo=page, arrange="C")
        out += items(b); total = int(b.get("totalCount") or 0)
        if len(out) >= total: return out, True
        if not items(b): return out, False
        page += 1

def detail(key, it):
    m = DETAIL.get(int(it["contenttypeid"]))
    if not m: return {}
    try: d = (items(call(key, "detailIntro2", contentId=it["contentid"], contentTypeId=it["contenttypeid"])) or [{}])[0]
    except Exception: return {}
    return {v: d.get(k, "") for k, v in m.items() if d.get(k)}

def extra_image(key, cid):
    """대표 사진이 없거나 쓸 수 없는 유형일 때, 관광공사 추가 이미지(detailImage2) 중 공공누리 제1·3유형 사진을 찾는다."""
    try: rows = items(call(key, "detailImage2", contentId=cid, imageYN="Y", numOfRows=20, pageNo=1))
    except Exception: return ""
    for r in rows:
        if r.get("cpyrhtDivCd") in OK_LICENSE and r.get("originimgurl"): return r["originimgurl"]
    return ""

def fill_images(key, snap):
    need = [x for x in snap if not x.get("firstimage")]
    with cf.ThreadPoolExecutor(8) as ex:
        got = list(ex.map(lambda x: extra_image(key, x["contentid"]), need))
    n = 0
    for x, u in zip(need, got):
        if u: x["firstimage"] = u; x["imgsrc"] = "detail"; n += 1
    print(f"추가 이미지로 사진 {n}곳 채움 (대상 {len(need)}곳)", file=sys.stderr)
    return n

def merge_old(old, snap, kp, complete):
    """새로 받은 자료를 기존 kto.json 에 합친다. 기존 사진 기록(구글·포토코리아)과 시도 기록은 그대로 둔다.
    - 목록이 중간에 끊겼거나(한도 초과 등) 기존보다 20% 넘게 줄면 기존 장소를 지우지 않고 새 자료를 덮어쓰기만 한다.
    - 새 자료에서 비어 있는 값(사진·시간 등)은 기존 값을 지키고, 새 값이 있으면 새 값으로 바꾼다."""
    old_items = {x["contentid"]: x for x in old.get("items", [])}
    shrink = old_items and len(snap) < 0.8 * len(old_items)
    safe = complete and not shrink
    merged = {}
    for x in snap:
        prev = old_items.get(x["contentid"], {})
        row = dict(prev); row.update({k: v for k, v in x.items() if v not in ("", None)})
        for k in x:  # 새 자료가 비어 있고 기존에도 없던 칸은 빈 값으로 둔다
            row.setdefault(k, x[k])
        merged[x["contentid"]] = row
    if not safe:
        for cid, x in old_items.items(): merged.setdefault(cid, x)
    photos = dict(old.get("photos", {}))
    for k, v in kp.items():
        if k not in photos or photos[k].get("src") == "google": photos[k] = v
    out = {k: v for k, v in old.items() if k not in ("items", "photos", "rev")}
    out["items"] = list(merged.values()); out["photos"] = photos
    note = (f"합친 결과: 장소 {len(out['items'])}곳(새로 받은 {len(snap)}곳, 기존 {len(old_items)}곳), 사진 {len(photos)}곳. "
            + ("목록을 끝까지 받아 기존 장소도 새 목록 기준으로 정리" if safe else "목록이 일부만 와서 기존 장소를 모두 보존"))
    return out, note

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("--html", default=None)
    ap.add_argument("--json", default=None, help="앱이 받아 쓰는 kto.json 경로"); ap.add_argument("--ver", default=None, help="kto_ver.txt 경로")
    a = ap.parse_args(); key = a.key
    jobs = [(sg, ct) for sg in SG for ct in CT]
    raw, complete = [], True
    with cf.ThreadPoolExecutor(8) as ex:
        for r, ok in ex.map(lambda j: list_all(key, *j), jobs): raw += r; complete = complete and ok
    seen, uniq = set(), []
    for it in raw:
        if it["contentid"] not in seen: seen.add(it["contentid"]); uniq.append(it)
    print("목록", len(uniq), "건", file=sys.stderr)
    with cf.ThreadPoolExecutor(8) as ex:
        det = list(ex.map(lambda it: detail(key, it), uniq))
    snap = []
    for it, d in zip(uniq, det):
        img = it.get("firstimage", "") if it.get("cpyrhtDivCd") in OK_LICENSE else ""
        row = {"contentid":it["contentid"], "contenttypeid":it["contenttypeid"], "title":it["title"], "addr1":it.get("addr1",""),
               "sigungucode":it["sigungucode"], "mapx":it["mapx"], "mapy":it["mapy"], "firstimage":img, "tel":it.get("tel","")}
        row.update(d); snap.append(row)
    fill_images(key, snap)
    p = pathlib.Path(a.html or a.json and "web/index.html" or "index.html"); s = p.read_text(encoding="utf-8")
    # 직접 정리한 장소에 사진이 없으면 같은 이름의 관광공사 사진을 붙인다
    norm = lambda v: re.sub(r"[\s·()（）]", "", v or "")
    byname = {norm(x["title"]): x for x in snap if x["firstimage"]}
    start = s.index("const PLACES = ["); end = s.index("const REG = ")
    mine = re.findall(r'\{\s*id:"([^"]+)"[^{}]*?name:"([^"]+)"', s[start:end])
    photos_blob = s[s.index("/*PHOTOS*/")+10 : s.index("/*END_PHOTOS*/")]
    have = set(json.loads(photos_blob))
    kp = {}
    for pid, name in mine:
        if pid in have: continue
        hit = byname.get(norm(name))
        if hit: kp[pid] = {"url": hit["firstimage"]}
    s = re.sub(r"/\*KTO_DATA\*/.*?/\*END_KTO_DATA\*/", lambda m: "/*KTO_DATA*/" + json.dumps(snap, ensure_ascii=False, separators=(",",":")).replace("</", "<\\/") + "/*END_KTO_DATA*/", s, count=1, flags=re.S)
    s = re.sub(r"/\*KTO_PHOTOS\*/.*?/\*END_KTO_PHOTOS\*/", lambda m: "/*KTO_PHOTOS*/" + json.dumps(kp, ensure_ascii=False, separators=(",",":")).replace("</", "<\\/") + "/*END_KTO_PHOTOS*/", s, count=1, flags=re.S)
    if a.html: p.write_text(s, encoding="utf-8")
    if a.json:
        import time
        rev = int(time.time() * 1000)
        try: old = json.loads(pathlib.Path(a.json).read_text(encoding="utf-8"))
        except Exception: old = {}
        out, note = merge_old(old, snap, kp, complete)
        out["rev"] = rev; print(note, file=sys.stderr); snap = out["items"]
        pathlib.Path(a.json).write_text(json.dumps(out, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
        if a.ver: pathlib.Path(a.ver).write_text(str(rev), encoding="utf-8")
    print(("JSON " if a.json else "") + f"스냅샷 {len(snap)}건, 사진 {sum(1 for x in snap if x['firstimage'])}장, 기존 장소 사진 보강 {len(kp)}곳")
if __name__ == "__main__":
    main()
