"""고른 음식 사진을 다시 받아(구글 요청 아님, 사진 주소만 읽음) 가장 잘 맞는 설명을 적는다. 사람이 결과를 훑어보기 위한 점검용."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from food_photo import Judge, fetch_img, FOOD, OTHER
k = json.loads(pathlib.Path("web/kto.json").read_text(encoding="utf-8"))
rep = {x["id"]: x["name"] for x in json.loads(pathlib.Path("tools/food_photo_report.json").read_text(encoding="utf-8"))}
J = Judge(); L = FOOD + OTHER
for pid, f in k.get("fphoto", {}).items():
    try:
        img = fetch_img(f["url"])
        with J.torch.no_grad():
            out = J.m(input_ids=J.tk["input_ids"], attention_mask=J.tk["attention_mask"], pixel_values=J.p(images=img, return_tensors="pt")["pixel_values"])
            pr = out.logits_per_image.softmax(dim=-1)[0]
        i = int(pr.argmax()); print(f"{rep.get(pid, pid)}\t{f.get('food')}\t{L[i].replace('a photo of ', '')}\t{float(pr[i]):.2f}")
    except Exception as e: print(f"{rep.get(pid, pid)}\t오류 {e}")
