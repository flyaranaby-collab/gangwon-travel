"""한국관광공사 관광사진 정보(포토코리아, 공공누리 제1유형)로 사진 없는 장소의 사진을 찾아 web/kto.json 의 photos 에 더한다.
사용: python3 tools/gallery_sync.py --key 인증키 --kto web/kto.json --html web/index.html --ver web/kto_ver.txt
- 장소 이름이 사진 제목·키워드에 들어 있고 촬영지가 강원(가능하면 같은 시·군)일 때만 쓴다(엉뚱한 사진 방지).
- 키가 이 서비스에 아직 등록되지 않았으면 아무것도 바꾸지 않고 끝낸다(장소 업데이트는 그대로 성공).
"""
import argparse, json, re, subprocess, urllib.parse, concurrent.futures as cf, time, pathlib, sys
B = "https://apis.data.go.kr/B551011/PhotoGalleryService1"
class NotReady(Exception): pass
def call(key, op, **p):
    p.update(serviceKey=key, MobileOS="ETC", MobileApp="GangwonTrip", _type="json")
    u = B + "/" + op + "?" + urllib.parse.urlencode(p, safe="")
    for _ in range(4):
        r = subprocess.run(["curl","-sS","-m","40",u], capture_output=True, text=True)
        out = r.stdout.strip()
        if r.returncode == 0 and out.startswith("{"):
            j = json.loads(out)
            if "OpenAPI_ServiceResponse" in j: raise NotReady(json.dumps(j, ensure_ascii=False)[:160])
            body = j["response"]["body"]; it = body.get("items") or {}
            it = it.get("item") if isinstance(it, dict) else None
            return it if isinstance(it, list) else ([it] if it else [])
        time.sleep(1)
    return []
norm = lambda s: re.sub(r"[\s·()（）\[\]_,.\-]", "", s or "").lower()
clean = lambda n: re.sub(r"\(.*?\)|（.*?）", "", n).split(" · ")[0].strip()
def find(key, pl):
    q = clean(pl["name"]); nq = norm(q)
    if len(nq) < 2: return None
    try: rows = call(key, "gallerySearchList1", keyword=q, numOfRows=30, pageNo=1, arrange="A")
    except NotReady: raise
    except Exception: return None
    best = None
    for r in rows:
        text = norm((r.get("galTitle") or "") + " " + (r.get("galSearchKeyword") or ""))
        loc = r.get("galPhotographyLocation") or ""
        if nq not in text or not r.get("galWebImageUrl") or "강원" not in loc: continue
        hit = { "url": r["galWebImageUrl"].replace("http://","https://"), "by": r.get("galPhotographer","") or "한국관광공사",
                "credit": "사진: 한국관광공사 포토코리아" + (" · " + r["galPhotographer"] if r.get("galPhotographer") else "") + " · 공공누리 제1유형" }
        if pl.get("city") and pl["city"] in loc: return hit
        best = best or hit
    return best
def targets(kto, html):
    have = set(kto.get("photos", {}))
    s = pathlib.Path(html).read_text(encoding="utf-8")
    wiki = set(json.loads(s[s.index("/*PHOTOS*/")+10 : s.index("/*END_PHOTOS*/")]))
    a = s.index("const PLACES = ["); b = s.index("const REG = ")
    out = [{ "id":pid, "name":name, "city":"" } for pid, name in re.findall(r'\{\s*id:"([^"]+)",\s*name:"([^"]+)"', s[a:b]) if pid not in wiki and pid not in have]
    for x in kto["items"]:
        pid = "kto-" + x["contentid"]
        if x.get("firstimage") or pid in have: continue
        city = (x.get("addr1","").split(" ") + ["",""])[1]
        out.append({ "id":pid, "name":x["title"], "city":city })
    return out
def main():
    ap = argparse.ArgumentParser()
    for k in ("key","kto","html"): ap.add_argument("--"+k, required=True)
    ap.add_argument("--ver", default=None); a = ap.parse_args()
    kto = json.loads(pathlib.Path(a.kto).read_text(encoding="utf-8")); kto.setdefault("photos", {})
    tg = targets(kto, a.html)
    try: call(a.key, "galleryList1", numOfRows=1, pageNo=1)
    except NotReady as e: print("관광사진 서비스 키가 아직 등록되지 않아 건너뜀:", e); return
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(lambda pl: find(a.key, pl), tg))
    got = { pl["id"]: r for pl, r in zip(tg, res) if r }
    kto["photos"].update(got); kto["rev"] = int(time.time()*1000)
    pathlib.Path(a.kto).write_text(json.dumps(kto, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    if a.ver: pathlib.Path(a.ver).write_text(str(kto["rev"]), encoding="utf-8")
    print(f"관광사진으로 사진 {len(got)}곳 채움 / 대상 {len(tg)}곳")
main()
