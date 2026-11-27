"""일회성: 지정한 가게의 구글 사진을 모두 받아 사람 얼굴이 있는지와 음식 점수를 함께 매겨 보여 준다."""
import json, sys, pathlib, io, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from food_photo import get, photo_uri, Judge, fetch_img, API  # noqa
import torch
key = sys.argv[1]; ids = json.loads(sys.argv[2]); out = pathlib.Path("pick"); out.mkdir(exist_ok=True)
J = Judge()
PERSON = ["a photo of a person", "a photo of people's faces", "a selfie", "a photo of a child", "a photo of a hand holding food"]
NOPERSON = ["a photo of food only with no people", "a close-up of a dish on a table", "a photo of a store front", "a photo of a menu"]
def person(img):
    inp = J.p(text=PERSON + NOPERSON, images=img, return_tensors="pt", padding=True)
    with torch.no_grad(): pr = J.m(**inp).logits_per_image.softmax(-1)[0]
    return round(float(pr[:len(PERSON)].sum()), 2)
res = {}
for pid, gid in ids.items():
    d = get(f"{API}/places/{gid}?languageCode=ko", key, "id,displayName,photos")
    rows = []
    for i, ph in enumerate((d.get("photos") or [])[:10]):
        try:
            url = photo_uri(key, ph); img = fetch_img(url)
        except Exception as e:
            print(pid, i, "ERR", e); continue
        by = ", ".join(x.get("displayName", "") for x in ph.get("authorAttributions", []) if x.get("displayName")) or "Google 지도 사용자"
        r = {"i": i, "url": url, "by": by, "food": round(J.food(img), 2), "fr": round(J.fresh(img), 2), "person": person(img)}
        img.save(out / f"{pid}_{i}.jpg", quality=80)
        rows.append(r); print(pid, json.dumps({k: v for k, v in r.items() if k != "url"}, ensure_ascii=False))
    res[pid] = rows
(out / "pick.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
