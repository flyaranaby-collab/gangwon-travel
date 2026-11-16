#!/usr/bin/env python3
"""강원 공중화장실 · 공영주차장 목록 받기 (공공데이터포털 '전국 표준데이터')

필요한 활용신청 (KTO_KEY와 같은 일반 인증키로 신청):
  - 전국공중화장실표준데이터   (api.data.go.kr/openapi/tn_pubr_public_toilet_api)
  - 전국주차장정보표준데이터   (api.data.go.kr/openapi/tn_pubr_prkplce_info_api)

사용: python3 tools/facil_sync.py --key KEY --out web/facil.json
결과: { ts, wc:[[이름,주소,위도,경도,개방시간,장애인용(0/1),기저귀교환대(0/1)]],
        pk:[[이름,주소,위도,경도,구분(노상/노외/부설),요금(무료/유료/혼합),주차면수,평일운영,기본요금,전화]] }
"""
import argparse, json, subprocess, sys, time, urllib.parse
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
API = "https://api.data.go.kr/openapi/"

def page(key, name, n):
    u = API + name + "?" + urllib.parse.urlencode({"serviceKey": key, "pageNo": n, "numOfRows": 1000, "type": "json"}, safe="%")
    last = ""
    for t in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "90", u], capture_output=True, text=True)
        last = (r.stdout or r.stderr)[:300]
        try:
            j = json.loads(r.stdout)
            j = j.get("response", j)
            h = j["header"]
            if h.get("resultCode") not in ("00", "0", "NORMAL_CODE", "03"):
                raise RuntimeError(f"{name}: {h.get('resultMsg')} — 공공데이터포털에서 활용신청했는지 확인하세요")
            b = j.get("body") or {}
            it = b.get("items") or []
            if isinstance(it, dict): it = it.get("item") or []
            if isinstance(it, dict): it = [it]
            return it, int(b.get("totalCount") or 0)
        except RuntimeError: raise
        except Exception: time.sleep(3 * (t + 1))
    raise RuntimeError(f"{name}: 응답을 읽지 못함 — {last}")

def every(key, name):
    out, n, total = [], 1, None
    while True:
        items, tc = page(key, name, n)
        total = total or tc
        out += items
        if not items or len(out) >= total: break
        n += 1
    print(f"{name}: 전국 {len(out)}건", flush=True)
    return out

def g(d, *ks):
    for k in ks:
        v = d.get(k)
        if v not in (None, ""): return str(v).strip()
    return ""

def gw(d): return any(s in g(d, "rdnmadr", "lnmadr") for s in ("강원특별자치도", "강원도"))

def num(x):
    try: return round(float(x), 6)
    except Exception: return None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
    wc = []
    try: wcall = every(a.key, "tn_pubr_public_toilet_api")
    except RuntimeError as e:
        print("화장실 자료는 건너뜀:", e, flush=True); wcall = []
    for d in wcall:
        if not gw(d): continue
        la, lo = num(g(d, "latitude")), num(g(d, "longitude"))
        if not la or not lo: continue
        dis = 1 if any((g(d, k) or "0") not in ("0", "") for k in ("dspsnClosetBowlNumber", "mlDspsnClosetBowlNumber", "fmlDspsnClosetBowlNumber", "mlDspsnUrinalNumber")) else 0
        baby = 1 if g(d, "diaperExhgTabYn", "diaperExhgTabYnFmlToilet") == "Y" else 0
        wc.append([g(d, "toiletNm"), g(d, "rdnmadr", "lnmadr"), la, lo, g(d, "openTime", "opnTimeDetail", "opnTime"), dis, baby])
    pk = []
    for d in every(a.key, "tn_pubr_prkplce_info_api"):
        if not gw(d) or g(d, "prkplceSe") not in ("공영",): continue
        la, lo = num(g(d, "latitude")), num(g(d, "longitude"))
        if not la or not lo: continue
        op, cl = g(d, "weekdayOperOpenHhmm"), g(d, "weekdayOperColseHhmm", "weekdayOperCloseHhmm")
        bc = g(d, "basicCharge"); bt = g(d, "basicTime")
        pk.append([g(d, "prkplceNm"), g(d, "rdnmadr", "lnmadr"), la, lo, g(d, "prkplceType"), g(d, "parkingchrgeInfo"), g(d, "prkcmprt"),
                   f"{op}~{cl}" if op and cl else "", f"{bt}분 {bc}원" if bc and bc != "0" and bt else "", g(d, "phoneNumber")])
    if len(pk) < 50: raise SystemExit(f"강원 자료가 너무 적어요(주차장 {len(pk)}) — 저장하지 않음")
    json.dump({"ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "wc": wc, "pk": pk}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"강원 공중화장실 {len(wc)}곳 · 공영주차장 {len(pk)}곳 저장")

if __name__ == "__main__":
    main()
