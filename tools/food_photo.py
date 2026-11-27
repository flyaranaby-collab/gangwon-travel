"""음식점·카페·빵집의 대표 사진을 '간판'이 아니라 '음식 사진'으로 바꾼다. 사진이 다른 가게 것으로 붙은 것도 바로잡는다.

사용: python3 tools/food_photo.py --key KEY --kto web/kto.json --gmap web/gmap.json --html web/index.html --ver web/kto_ver.txt
  [--only 강릉] [--max 4] [--limit 0] [--sheet out/]

하는 일
1) 가게마다 구글 장소를 이름 확인(same_name)과 강원 주소 확인을 거쳐 찾는다. 구글 인기 장소 목록(gmap.json)에 같은 이름이 있으면 검색 없이 그 장소 번호를 쓴다.
   - 이름이 맞는 곳을 못 찾으면, 예전에 이름 확인 없이 붙였던 구글 사진(작가 'Google')은 지운다(다른 가게 사진일 수 있어서).
2) 그 장소 사진을 앞에서부터 한 장씩(최대 --max 장) 받아 CLIP 그림 판별로 '음식·빵·커피' 사진인지 본다.
   음식 사진이 나오면 거기서 멈춘다(사진 요청을 아끼려고). 끝까지 없으면 첫 사진을 쓴다.
3) 결과를 kto.json 의 fphoto 에 {장소id: {url, by, food}} 로 저장 → 앱이 음식점 사진으로 가장 먼저 쓴다.
   구글 약관에 따라 찍은 사람(by)을 함께 저장해 사진 아래에 표시한다.
"""
import argparse, io, json, pathlib, re, sys, time, urllib.request, urllib.error, concurrent.futures as cf

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gplaces_sync import same_name, GW_ADDR, CITIES  # noqa: E402

API = "https://places.googleapis.com/v1"
REGION_CITY = {"gangneung": "강릉", "sokcho": "속초", "yangyang": "양양", "donghae": "동해", "pyeongchang": "평창", "jeongseon": "정선",
               "chuncheon": "춘천", "wonju": "원주", "inje": "인제", "hongcheon": "홍천", "hwacheon": "화천"}
SIGUNGU = {"1": "강릉", "2": "고성", "3": "동해", "4": "삼척", "5": "속초", "6": "양구", "7": "양양", "8": "영월", "9": "원주", "10": "인제",
           "11": "정선", "12": "철원", "13": "춘천", "14": "태백", "15": "평창", "16": "홍천", "17": "화천", "18": "횡성"}

FOOD = ["a photo of a plate of food", "a close-up photo of Korean food on a table", "a photo of a bowl of soup or noodles",
        "a photo of grilled meat or fish", "a photo of raw fish sashimi", "a photo of fried chicken", "a photo of bread and pastries",
        "a photo of a cake or dessert", "a photo of a cup of coffee or a drink", "a photo of tofu dishes", "a photo of dumplings"]
OTHER = ["a photo of a store front with a sign", "a photo of a shop signboard", "a photo of a restaurant interior with empty tables",
         "a photo of a menu board with text", "a photo of a building exterior", "a photo of a street", "a photo of people's faces",
         "a logo", "a photo of a parking lot", "a photo of the sea and a landscape", "a screenshot of text", "a photo of a cafe interior"]


def nz(x): return re.sub(r"[\s()·&\-_.,'\[\]]", "", str(x)).lower()


def post(url, body, mask, key):
    rq = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                headers={"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": mask})
    with urllib.request.urlopen(rq, timeout=20) as r: return json.loads(r.read())


def get(url, key, mask=None):
    h = {"X-Goog-Api-Key": key}
    if mask: h["X-Goog-FieldMask"] = mask
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r: return json.loads(r.read())


def targets(a):
    """앱에 나오는 음식점·카페 목록(직접 고른 곳 + 관광공사 음식점 + 구글 인기 맛집·카페)."""
    s = pathlib.Path(a.html).read_text(encoding="utf-8")
    seg = s[s.index("const PLACES = ["): s.index("const REG = ")]
    out = []
    for m in re.finditer(r'\{\s*id:"([^"]+)"([^{}]*?)name:"([^"]+)"[^{}]*?cat:"([^"]+)"', seg):
        pid, mid, name, cat = m.groups()
        if cat not in ("맛집", "카페"): continue
        rg = re.search(r'region:"(\w+)"', mid)
        t = {"id": pid, "name": name, "city": REGION_CITY.get(rg.group(1) if rg else "gangneung", "")}
        gm_ = re.search(r'gid:"([^"]+)"', mid)   # 앱에 적어 둔 구글 장소 번호가 있으면 그걸 그대로 쓴다(이름이 같은 다른 가게 사진 방지)
        if gm_: t["gid"] = gm_.group(1)
        ad_ = re.search(r'addr:"[^"]*?(강릉|속초|양양|고성|동해|삼척|평창|정선|영월|춘천|원주|인제|홍천|화천|태백|횡성|철원|양구)', mid)
        if ad_ and not rg: t["city"] = ad_.group(1)
        out.append(t)
    kto = json.loads(pathlib.Path(a.kto).read_text(encoding="utf-8"))
    for x in kto.get("items", []):
        if str(x.get("contenttypeid")) != "39": continue
        out.append({"id": "kto-" + x["contentid"], "name": x["title"], "city": SIGUNGU.get(str(x.get("sigungucode")), ""), "addr": x.get("addr1", "")})
    gm = json.loads(pathlib.Path(a.gmap).read_text(encoding="utf-8")).get("items", [])
    byname = {}
    for g in gm:
        if g.get("cat") not in ("맛집", "카페"): continue
        byname.setdefault(nz(g["name"]), g)
    seen = set()
    for t in out:   # 같은 이름의 구글 인기 장소가 있으면 검색 없이 그 장소 번호를 쓴다
        if t.get("gid"): seen.add(t["gid"]); continue
        g = byname.get(nz(t["name"]))
        if g and (not t["city"] or t["city"] == g.get("city", t["city"])): t["gid"] = g["id"]; seen.add(g["id"])
    for g in byname.values():
        if g["id"] in seen: continue
        out.append({"id": "g-" + g["id"], "name": g["name"], "city": g.get("city", ""), "gid": g["id"]})
    if a.only: out = [t for t in out if t["city"] in a.only.split(",")]
    return out, kto


def find(key, t):
    """이름이 맞는 구글 장소의 사진 목록. (place_id, 표시 이름, photos) 또는 None."""
    if t.get("gid"):
        try:
            d = get(f"{API}/places/{t['gid']}?languageCode=ko", key, "id,displayName,photos")
            return d["id"], (d.get("displayName") or {}).get("text", ""), d.get("photos") or []
        except Exception as e:
            print("  상세 오류", t["name"], e, file=sys.stderr)
            return None
    name = re.sub(r"\(.*?\)|（.*?）", "", t["name"]).split(" · ")[0].strip()
    if len(name) < 2: return None
    try:
        res = post(f"{API}/places:searchText", {"textQuery": f"{name} {t['city']} 강원", "languageCode": "ko", "regionCode": "KR", "maxResultCount": 3},
                   "places.id,places.displayName,places.formattedAddress,places.photos", key).get("places", [])
    except Exception as e:
        print("  검색 오류", t["name"], e, file=sys.stderr)
        return None
    for p in res:
        addr, disp = p.get("formattedAddress", ""), (p.get("displayName") or {}).get("text", "")
        if not GW_ADDR.search(addr) or not same_name(name, disp): continue
        if t["city"] and t["city"] in CITIES and t["city"] not in addr and not re.search(r"[A-Za-z]", addr): continue   # 다른 시·군의 같은 이름 가게
        return p["id"], disp, p.get("photos") or []
    return None


def photo_uri(key, ph):
    with urllib.request.urlopen(f"{API}/{ph['name']}/media?maxWidthPx=800&key={key}&skipHttpRedirect=true", timeout=20) as r:
        return json.loads(r.read()).get("photoUri")


class Judge:
    """CLIP(공개 그림 판별 모델)으로 음식 사진일 확률을 낸다. 비용 없음(작업 컴퓨터에서 돌림)."""
    def __init__(self):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        self.m = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
        self.p = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.tk = self.p(text=FOOD + OTHER, return_tensors="pt", padding=True)

    def food(self, img):
        # 모델 전체를 한 번에 돌려 그림-글 짝 점수(logits_per_image)를 받는다(버전마다 바뀌는 중간 함수는 쓰지 않음)
        with self.torch.no_grad():
            out = self.m(input_ids=self.tk["input_ids"], attention_mask=self.tk["attention_mask"],
                         pixel_values=self.p(images=img, return_tensors="pt")["pixel_values"])
            pr = out.logits_per_image.softmax(dim=-1)[0]
        return float(pr[:len(FOOD)].sum())


def fetch_img(url):
    from PIL import Image
    u = re.sub(r"=s\d+-w\d+.*$|=w\d+.*$", "", url) + "=w320"
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    for k in ("key", "kto", "gmap", "html"): ap.add_argument("--" + k, required=True)
    ap.add_argument("--ver"); ap.add_argument("--only", default=""); ap.add_argument("--max", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--sheet", default=""); ap.add_argument("--min", type=float, default=0.6)
    ap.add_argument("--all", action="store_true", help="이미 고른 곳도 다시")
    ap.add_argument("--low", action="store_true", help="음식 사진을 못 찾은 곳만 뒤쪽 사진(5~10번째)까지 더 본다")
    a = ap.parse_args()
    tg, kto = targets(a)
    done = kto.get("fphoto", {})
    start = 0
    if a.low:
        tg = [t for t in tg if t["id"] in done and (done[t["id"]].get("food") or 0) < a.min and not done[t["id"]].get("deep")]
        start, a.max = a.max, 10
    elif not a.all: tg = [t for t in tg if t["id"] not in done]   # 이미 고른 곳은 다시 하지 않는다(요청 아끼기)
    if a.limit: tg = tg[:a.limit]
    print(f"대상 음식점·카페 {len(tg)}곳 (검색 필요 {sum(1 for t in tg if not t.get('gid'))}곳)")

    J = Judge()   # 판별 도구를 먼저 준비한다(여기서 실패하면 구글 검색을 하지 않음)
    from PIL import Image
    J.food(Image.new("RGB", (64, 64), "white"))
    found = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for t, r in zip(tg, ex.map(lambda t: find(a.key, t), tg)): found[t["id"]] = r
    fph, report, calls = {}, [], 0
    for i, t in enumerate(tg, 1):
        r = found.get(t["id"])
        if not r:
            old = kto.get("photos", {}).get(t["id"])
            if old and old.get("by") == "Google":   # 이름 확인 없이 붙었던 구글 사진은 믿을 수 없어 지운다
                kto["photos"].pop(t["id"]); report.append({"id": t["id"], "name": t["name"], "st": "removed"})
            else: report.append({"id": t["id"], "name": t["name"], "st": "notfound"})
            continue
        pid, disp, phs = r
        best = dict(done[t["id"]], deep=1) if a.low else None
        for k, ph in list(enumerate(phs[:a.max]))[start:]:
            try: uri = photo_uri(a.key, ph); calls += 1
            except Exception: continue
            if not uri: continue
            try: sc = J.food(fetch_img(uri))
            except Exception: sc = 0.0
            by = ", ".join(x.get("displayName", "") for x in ph.get("authorAttributions", []) if x.get("displayName")) or "Google 지도 사용자"
            cand = {"url": uri, "by": re.sub(r"[<>\"]", "", by)[:60], "food": round(sc, 2), "k": k}
            if best is None or sc > (best.get("food") or 0): best = cand
            if sc >= a.min: break
        if best:
            fph[t["id"]] = best
            old = kto.get("photos", {}).get(t["id"])
            if old and old.get("by") == "Google": kto["photos"].pop(t["id"])   # 옛 구글 사진 대신 새 사진
        report.append({"id": t["id"], "name": t["name"], "g": disp, "st": "food" if best and best["food"] >= a.min else ("other" if best else "nophoto"),
                       "food": best and best["food"], "k": best and best["k"]})
        if i % 50 == 0: print(f"  진행 {i}/{len(tg)} · 사진 요청 {calls}회", flush=True)

    done.update(fph)
    kto["fphoto"] = done
    kto["rev"] = int(time.time() * 1000)
    pathlib.Path(a.kto).write_text(json.dumps(kto, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if a.ver: pathlib.Path(a.ver).write_text(str(kto["rev"]), encoding="utf-8")
    c = {}
    for x in report: c[x["st"]] = c.get(x["st"], 0) + 1
    print(f"끝: 음식 사진 {c.get('food', 0)} · 음식 사진 없어 첫 사진 {c.get('other', 0)} · 구글에 사진 없음 {c.get('nophoto', 0)} · "
          f"이름 맞는 곳 못 찾음 {c.get('notfound', 0)} · 잘못 붙은 사진 지움 {c.get('removed', 0)} · 사진 요청 {calls}회")
    rp = pathlib.Path("tools/food_photo_report.json")   # 이전 결과와 합친다(장소 id 기준)
    allr = {x["id"]: x for x in (json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else [])}
    allr.update({x["id"]: x for x in report})
    rp.write_text(json.dumps(list(allr.values()), ensure_ascii=False, indent=0), encoding="utf-8")
    if a.sheet: sheets(a.sheet, tg, fph, report)


def sheets(out, tg, fph, report):
    """눈으로 확인할 수 있게 고른 사진을 이름과 함께 한 장에 20곳씩 모은다."""
    from PIL import Image, ImageDraw, ImageFont
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    try: font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 16)
    except Exception: font = ImageFont.load_default()
    rows = [t for t in tg if t["id"] in fph]
    for n in range(0, len(rows), 20):
        sh = Image.new("RGB", (5 * 240, 4 * 220), "white"); d = ImageDraw.Draw(sh)
        for j, t in enumerate(rows[n:n + 20]):
            x, y = (j % 5) * 240, (j // 5) * 220
            try: sh.paste(fetch_img(fph[t["id"]]["url"]).resize((232, 174)), (x + 4, y + 4))
            except Exception: pass
            d.text((x + 6, y + 180), f"{t['name'][:12]} {fph[t['id']]['food']}", fill="black", font=font)
        sh.save(f"{out}/sheet{n // 20:03d}.jpg", quality=80)


if __name__ == "__main__":
    main()
