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
    out, page = [], 1
    while True:
        b = call(key, "areaBasedList2", areaCode=32, sigunguCode=sg, contentTypeId=ct, numOfRows=300, pageNo=page, arrange="C")
        out += items(b)
        if len(out) >= b["totalCount"] or not items(b): return out
        page += 1

def detail(key, it):
    m = DETAIL.get(int(it["contenttypeid"]))
    if not m: return {}
    try: d = (items(call(key, "detailIntro2", contentId=it["contentid"], contentTypeId=it["contenttypeid"])) or [{}])[0]
    except Exception: return {}
    return {v: d.get(k, "") for k, v in m.items() if d.get(k)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("--html", default="index.html")
    a = ap.parse_args(); key = a.key
    jobs = [(sg, ct) for sg in SG for ct in CT]
    raw = []
    with cf.ThreadPoolExecutor(8) as ex:
        for r in ex.map(lambda j: list_all(key, *j), jobs): raw += r
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
    p = pathlib.Path(a.html); s = p.read_text(encoding="utf-8")
    # 직접 정리한 장소에 사진이 없으면 같은 이름의 관광공사 사진을 붙인다
    norm = lambda v: re.sub(r"[\s·()（）]", "", v or "")
    byname = {norm(x["title"]): x for x in snap if x["firstimage"]}
    start = s.index("const PLACES = ["); end = s.index("const REG = ")
    mine = re.findall(r'\{\s*id:"([^"]+)",\s*name:"([^"]+)"', s[start:end])
    photos_blob = s[s.index("/*PHOTOS*/")+10 : s.index("/*END_PHOTOS*/")]
    have = set(json.loads(photos_blob))
    kp = {}
    for pid, name in mine:
        if pid in have: continue
        hit = byname.get(norm(name))
        if hit: kp[pid] = {"url": hit["firstimage"]}
    s = re.sub(r"/\*KTO_DATA\*/.*?/\*END_KTO_DATA\*/", lambda m: "/*KTO_DATA*/" + json.dumps(snap, ensure_ascii=False, separators=(",",":")) + "/*END_KTO_DATA*/", s, count=1, flags=re.S)
    s = re.sub(r"/\*KTO_PHOTOS\*/.*?/\*END_KTO_PHOTOS\*/", lambda m: "/*KTO_PHOTOS*/" + json.dumps(kp, ensure_ascii=False, separators=(",",":")) + "/*END_KTO_PHOTOS*/", s, count=1, flags=re.S)
    p.write_text(s, encoding="utf-8")
    print(f"스냅샷 {len(snap)}건, 사진 {sum(1 for x in snap if x['firstimage'])}장, 기존 장소 사진 보강 {len(kp)}곳")
main()
