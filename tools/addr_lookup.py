"""직접 고른 장소의 공식 주소를 한국관광공사 TourAPI(키워드 검색)에서 찾는다.
- 이름이 같고(공백·기호 무시, 한쪽이 다른 쪽을 포함) 좌표가 1.5km 안인 관광공사 등록 장소만 인정한다.
- 못 찾으면 비워 둔다(추측해서 넣지 않음).
사용: python3 tools/addr_lookup.py --key KEY tools/addr_targets.json > found.json
"""
import argparse, json, math, re, subprocess, time, urllib.parse
B = "https://apis.data.go.kr/B551011/KorService2/searchKeyword2"

def call(key, kw):
    q = urllib.parse.urlencode({"serviceKey": key, "MobileOS": "ETC", "MobileApp": "GangwonTrip", "_type": "json",
                                "keyword": kw, "areaCode": 32, "numOfRows": 50, "pageNo": 1, "arrange": "A"}, safe="")
    for t in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "40", B + "?" + q], capture_output=True, text=True)
        try:
            b = json.loads(r.stdout)["response"]["body"]; it = (b.get("items") or {})
            it = it.get("item") if isinstance(it, dict) else None
            return it if isinstance(it, list) else ([it] if it else [])
        except Exception: time.sleep(2 * (t + 1))
    return []

norm = lambda s: re.sub(r"[\s·\-()（）\[\]'\"`.,&]|강릉|속초|춘천|강원", "", s or "")
def km(a, b, c, d):
    r = math.radians; x = r(d - b) * math.cos(r((a + c) / 2)); y = r(c - a); return 6371 * math.hypot(x, y)

def parts(name):
    ps = [p.strip() for p in re.split(r"[·/]|\(|\)", name) if p.strip()]
    return [name] + [p for p in ps if p != name and len(norm(p)) >= 2]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("targets"); a = ap.parse_args()
    out = {}
    for t in json.load(open(a.targets, encoding="utf-8")):
        best = None
        for kw in parts(t["name"]):
            for it in call(a.key, kw):
                try: d = km(t["lat"], t["lng"], float(it["mapy"]), float(it["mapx"]))
                except Exception: continue
                n1, n2 = norm(kw), norm(it.get("title"))
                if not n1 or not n2 or not (n1 in n2 or n2 in n1) or d > 1.5 or not it.get("addr1"): continue
                score = d + (0 if n1 == n2 else 0.5)
                if not best or score < best[0]: best = (score, it, d)
            if best and best[0] < 0.3: break
        if best:
            it = best[1]; addr = (it["addr1"] + " " + (it.get("addr2") or "")).strip()
            out[t["id"]] = {"addr": addr, "kto": it["title"], "cid": it["contentid"], "km": round(best[2], 2)}
        time.sleep(0.15)
    print("FOUND_JSON=" + json.dumps(out, ensure_ascii=False))
    print(f"찾음 {len(out)} / {len(json.load(open(a.targets, encoding='utf-8')))}")

if __name__ == "__main__": main()
