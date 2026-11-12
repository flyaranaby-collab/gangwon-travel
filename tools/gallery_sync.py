"""한국관광공사 관광사진 정보(포토코리아, 공공누리 제1유형)로 사진 없는 장소의 사진을 찾아 web/kto.json 의 photos 에 더한다.
사용: python3 tools/gallery_sync.py --key 인증키 --kto web/kto.json --html web/index.html --ver web/kto_ver.txt
- 장소 이름이 사진 제목·키워드에 들어 있고 촬영지가 강원(가능하면 같은 시·군)일 때만 쓴다(엉뚱한 사진 방지).
- 키가 이 서비스에 아직 등록되지 않았으면 아무것도 바꾸지 않고 끝낸다(장소 업데이트는 그대로 성공).
"""
import argparse, json, re, subprocess, urllib.parse, concurrent.futures as cf, time, pathlib, sys
B = "https://apis.data.go.kr/B551011/PhotoGalleryService1"
class NotReady(Exception): pass
class Quota(Exception): pass
STATE = { "calls":0, "stop":False }
MAX_CALLS = 900   # 개발 단계 하루 한도(약 1,000회) 안에서만 쓴다
def call(key, op, **p):
    p.update(serviceKey=key, MobileOS="ETC", MobileApp="GangwonTrip", _type="json")
    u = B + "/" + op + "?" + urllib.parse.urlencode(p, safe="")
    if STATE["stop"] or STATE["calls"] >= MAX_CALLS: STATE["stop"] = True; raise Quota("limit")
    STATE["calls"] += 1
    for _ in range(4):
        r = subprocess.run(["curl","-sS","-m","40",u], capture_output=True, text=True)
        out = r.stdout.strip()
        if r.returncode == 0 and out.startswith("{"):
            j = json.loads(out)
            if "OpenAPI_ServiceResponse" in j:
                msg = json.dumps(j, ensure_ascii=False)
                if "LIMITED_NUMBER" in msg: STATE["stop"] = True; raise Quota(msg[:160])
                raise NotReady(msg[:160])
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
    out = [{ "id":pid, "name":name, "city":"" } for pid, name in re.findall(r'\{\s*id:"([^"]+)"[^{}]*?name:"([^"]+)"', s[a:b]) if pid not in wiki and pid not in have]
    for x in kto["items"]:
        pid = "kto-" + x["contentid"]
        if x.get("firstimage") or pid in have: continue
        parts = x.get("addr1","").split(" ") + ["","",""]
        town = re.sub(r"(읍|면|동|리|가)$", "", parts[2]) if re.search(r"(읍|면|동)$", parts[2]) else ""
        out.append({ "id":pid, "name":x["title"], "city":parts[1], "town":town })
    return out
def main():
    ap = argparse.ArgumentParser()
    for k in ("key","kto","html"): ap.add_argument("--"+k, required=True)
    ap.add_argument("--ver", default=None); a = ap.parse_args()
    kto = json.loads(pathlib.Path(a.kto).read_text(encoding="utf-8")); kto.setdefault("photos", {})
    tried = set(kto.get("gtried", []))
    tg = [t for t in targets(kto, a.html) if t["id"] not in tried]
    try:
        rows = call(a.key, "gallerySearchList1", keyword="강원", numOfRows=1, pageNo=1)
        print(f"포토코리아 API 연결 확인: 응답 {len(rows)}건", file=sys.stderr)
    except (NotReady, Quota) as e:
        print(f"관광사진 서비스를 지금 쓸 수 없어 건너뜀: {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"관광사진 API 오류로 건너뜀: {type(e).__name__}: {e}", file=sys.stderr)
        return
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(lambda pl: find(a.key, pl), tg))
    got = { pl["id"]: r for pl, r in zip(tg, res) if r }
    # 2단계: 그래도 없으면 같은 읍·면·동의 풍경 사진을 '주변 풍경 사진'으로 표시해 쓴다(그 가게 사진이 아님을 밝힘)
    towns = sorted({ pl["town"] for pl in tg if pl["id"] not in got and len(pl.get("town","")) >= 2 })
    def town_photo(t):
        try: rows = call(a.key, "gallerySearchList1", keyword=t, numOfRows=30, pageNo=1, arrange="A")
        except Exception: return None
        for r in rows:
            loc = r.get("galPhotographyLocation") or ""
            if "강원" in loc and t in (loc + (r.get("galTitle") or "")) and r.get("galWebImageUrl"):
                return { "url": r["galWebImageUrl"].replace("http://","https://"), "by": r.get("galPhotographer","") or "한국관광공사", "kind":"area",
                         "credit": "사진: 한국관광공사 포토코리아(" + (r.get("galTitle") or t) + ")" + (" · " + r["galPhotographer"] if r.get("galPhotographer") else "") + " · 공공누리 제1유형" }
        return None
    with cf.ThreadPoolExecutor(6) as ex: tp = dict(zip(towns, ex.map(town_photo, towns)))
    area = { pl["id"]: tp[pl["town"]] for pl in tg if pl["id"] not in got and tp.get(pl.get("town","")) }
    print(f"장소 사진 {len(got)}곳, 주변 풍경 사진 {len(area)}곳", file=sys.stderr)
    got.update(area)
    done_ids = [pl["id"] for pl, r in zip(tg, res) if r is not None or not STATE["stop"]]
    kto["photos"].update(got); kto["gtried"] = sorted(tried | set(done_ids)); kto["rev"] = int(time.time()*1000)
    if STATE["stop"]: print("하루 호출 한도에 닿아 여기까지 저장했어요. 다음 업데이트 때 이어서 찾아요.")
    pathlib.Path(a.kto).write_text(json.dumps(kto, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    if a.ver: pathlib.Path(a.ver).write_text(str(kto["rev"]), encoding="utf-8")
    print(f"관광사진으로 사진 {len(got)}곳 채움 / 대상 {len(tg)}곳")
try: main()
except Exception as e: print("관광사진 단계 오류(장소 업데이트는 계속):", e)
