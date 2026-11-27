"""앱의 맛집·카페가 구글 지도의 같은 가게와 이름·위치가 맞는지 점검(일회성). 평점·리뷰는 받지 않는다."""
import json, math, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from gplaces_sync import same_name  # noqa: E402
KEY = os.environ["GOOGLE_PLACES_KEY"]; API = "https://places.googleapis.com/v1"
RC = {"gangneung":"강릉","sokcho":"속초","yangyang":"양양","donghae":"동해","samcheok":"삼척","goseong":"고성","pyeongchang":"평창","jeongseon":"정선","yeongwol":"영월","taebaek":"태백","chuncheon":"춘천","wonju":"원주","hongcheon":"홍천","hoengseong":"횡성","inje":"인제","yanggu":"양구","hwacheon":"화천","cheorwon":"철원"}
CITIES = list(RC.values())
MASK = "id,displayName,location,formattedAddress,businessStatus"
def km(a, b, c, d): r = math.radians; return 6371 * math.hypot(r(d - b) * math.cos(r((a + c) / 2)), r(c - a))
def call(url, body=None, mask=MASK):
    h = {"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": mask}
    if body is not None: h["Content-Type"] = "application/json"
    rq = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET", headers=h)
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(rq, timeout=25).read())
        except urllib.error.HTTPError as e:
            if e.code == 404: return {"_404": True}
            err = e
        except Exception as e: err = e
        time.sleep(2)
    return {"_err": str(err)[:80]}
s = open("source/index.html", encoding="utf-8").read()
seg = s[s.index("const PLACES = ["): s.index("const REG = ")]
T = []
for m in re.finditer(r'\{\s*id:"([^"]+)"([^{}]*?)name:"([^"]+)"([^{}]*?)cat:"(맛집|카페)"([^{}]*?)lat:([\d.]+), lng:([\d.]+)', seg):
    body = m[0]
    gid = re.search(r'gid:"([^"]*)"', body); addr = re.search(r'addr:"([^"]*)"', body); rg = re.search(r'region:"([a-z]+)"', body)
    city = RC.get(rg[1]) if rg else next((c for c in CITIES if addr and c in addr[1]), "")
    T.append({"id": m[1], "name": m[3], "cat": m[5], "lat": float(m[7]), "lng": float(m[8]), "gid": gid[1] if gid else "", "addr": addr[1] if addr else "", "city": city})
print("대상", len(T), file=sys.stderr)
for t in T:
    out = dict(t)
    if t["gid"]:
        d = call(f"{API}/places/{t['gid']}?languageCode=ko", mask=MASK)
        out["via"] = "gid"
    else:
        name = re.sub(r"\(.*?\)", "", t["name"]).strip()
        r = call(f"{API}/places:searchText", {"textQuery": f"{name} {t['city']} 강원", "languageCode": "ko", "regionCode": "KR", "maxResultCount": 3,
                 "locationBias": {"circle": {"center": {"latitude": t["lat"], "longitude": t["lng"]}, "radius": 3000.0}}}, ",".join("places." + f for f in MASK.split(",")))
        ps = r.get("places", []); d = next((p for p in ps if same_name(name, p.get("displayName", {}).get("text", ""))), ps[0] if ps else {})
        out["via"] = "search"
    if d.get("location"):
        out["g"] = {"gid": d.get("id"), "name": d.get("displayName", {}).get("text"), "lat": round(d["location"]["latitude"], 5), "lng": round(d["location"]["longitude"], 5),
                    "addr": d.get("formattedAddress", "").replace("대한민국 ", ""), "st": d.get("businessStatus")}
        out["same"] = same_name(t["name"], out["g"]["name"]); out["km"] = round(km(t["lat"], t["lng"], out["g"]["lat"], out["g"]["lng"]), 3)
    else: out["g"] = None; out["err"] = d.get("_err") or ("404" if d.get("_404") else "none")
    print("V=" + json.dumps(out, ensure_ascii=False))
