#!/usr/bin/env python3
"""강원 공중화장실 · 공영주차장 목록 받기 (공공데이터포털 '전국 표준데이터')

필요한 활용신청 (KTO_KEY와 같은 일반 인증키로 신청):
  - 전국공중화장실표준데이터   (api.data.go.kr/openapi/→ 지금은 apis.data.go.kr/1741000/public_restroom_info_v2 '행정안전부_공중화장실정보 조회서비스')
  - 전국주차장정보표준데이터   (api.data.go.kr/openapi/tn_pubr_prkplce_info_api)

사용: python3 tools/facil_sync.py --key KEY --out web/facil.json
결과: { ts, wc:[[이름,주소,위도,경도,개방시간,장애인용(0/1),기저귀교환대(0/1),위치정확도(0 같은길·1 같은동리·2 같은읍면동),구분]],
        pk:[[이름,주소,위도,경도,구분(노상/노외/부설),요금(무료/유료/혼합),주차면수,평일운영,기본요금,전화]] }
"""
import argparse, json, re, subprocess, sys, time, urllib.parse
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

WC_API = "https://apis.data.go.kr/1741000/public_restroom_info_v2/info_v2"

def wc_all(key):
    """행정안전부_공중화장실정보 조회서비스(v2) — 강원 주소만, 100건씩. 좌표는 없음(2025-02부터 빠짐)"""
    out, n, total = [], 1, None
    while True:
        q = urllib.parse.urlencode({"serviceKey": key, "pageNo": n, "numOfRows": 100, "returnType": "json", "cond[LCTN_ROAD_NM_ADDR::LIKE]": "강원"})
        j = None
        for t in range(4):
            r = subprocess.run(["curl", "-sS", "-m", "60", WC_API + "?" + q], capture_output=True, text=True)
            try: j = json.loads(r.stdout); break
            except Exception: time.sleep(3 * (t + 1))
        if j is None: raise RuntimeError("화장실: 응답을 읽지 못함 — " + (r.stdout or r.stderr)[:200])
        j = j.get("response", j); h = j.get("header") or {}
        if str(h.get("resultCode")) not in ("0", "00"): raise RuntimeError(f"화장실: {h.get('resultMsg')} {str(j)[:200]}")
        b = j.get("body") or {}; it = (b.get("items") or {}); it = it.get("item", []) if isinstance(it, dict) else it
        if isinstance(it, dict): it = [it]
        total = total or int(b.get("totalCount") or 0); out += it
        if not it or len(out) >= total: break
        n += 1
    print(f"화장실(강원): {len(out)}건", flush=True)
    return out

RE_ROAD = re.compile(r"(\S+[시군])\s+(?:\S+[읍면]\s+)?(\S+(?:로|길))\s*(\d+)")
RE_LOT = re.compile(r"(\S+[시군])\s+(?:(\S+[읍면])\s+)?(\S+[동리가])\b")
def road_key(a):
    m = RE_ROAD.search(a or ""); return (m.group(1), m.group(2), int(m.group(3))) if m else None
def lot_key(a):
    m = RE_LOT.search(a or ""); return (m.group(1), m.group(2) or "", m.group(3)) if m else None
def emd_key(a):
    m = re.search(r"(\S+[시군])\s+(\S+[읍면동])", a or ""); return (m.group(1), m.group(2)) if m else None

class Locator:
    """주소가 같은(또는 같은 길의 가까운 번지) 관광지·주차장 좌표로 화장실 위치를 추정"""
    def __init__(self, refs):
        self.road, self.lot, self.emd = {}, {}, {}
        for addr, la, lo in refs:
            if not la or not lo: continue
            k = road_key(addr)
            if k: self.road.setdefault(k[:2], []).append((k[2], la, lo))
            for kk, store in ((lot_key(addr), self.lot), (emd_key(addr), self.emd)):
                if kk: store.setdefault(kk, []).append((la, lo))
    def find(self, road_addr, lot_addr):
        k = road_key(road_addr)
        if k and k[:2] in self.road:
            pts = sorted(self.road[k[:2]], key=lambda x: abs(x[0] - k[2]))
            if abs(pts[0][0] - k[2]) <= 40: return pts[0][1], pts[0][2], 0      # 같은 길 ±40번 (약 400m 안)
        for addr in (lot_addr, road_addr):
            kk = lot_key(addr)
            if kk and kk in self.lot: return (*cen(self.lot[kk]), 1)          # 같은 동·리 가운데
        if k and k[:2] in self.road and abs(pts[0][0] - k[2]) <= 150: return pts[0][1], pts[0][2], 1
        for addr in (lot_addr, road_addr):
            kk = emd_key(addr)
            if kk and kk in self.emd: return (*cen(self.emd[kk]), 2)          # 같은 읍·면·동 가운데
        return None

def cen(L):
    return round(sum(x[0] for x in L) / len(L), 6), round(sum(x[1] for x in L) / len(L), 6)

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
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("--out", required=True); ap.add_argument("--kto", default="web/kto.json"); a = ap.parse_args()
    pk = []
    pkall = [d for d in every(a.key, "tn_pubr_prkplce_info_api") if gw(d)]
    for d in pkall:
        if not gw(d) or g(d, "prkplceSe") not in ("공영",): continue
        la, lo = num(g(d, "latitude")), num(g(d, "longitude"))
        if not la or not lo: continue
        op, cl = g(d, "weekdayOperOpenHhmm"), g(d, "weekdayOperColseHhmm", "weekdayOperCloseHhmm")
        bc = g(d, "basicCharge"); bt = g(d, "basicTime")
        pk.append([g(d, "prkplceNm"), g(d, "rdnmadr", "lnmadr"), la, lo, g(d, "prkplceType"), g(d, "parkingchrgeInfo"), g(d, "prkcmprt"),
                   f"{op}~{cl}" if op and cl else "", f"{bt}분 {bc}원" if bc and bc != "0" and bt else "", g(d, "phoneNumber")])
    refs = [(g(d, "rdnmadr"), num(g(d, "latitude")), num(g(d, "longitude"))) for d in pkall] + \
           [(g(d, "lnmadr"), num(g(d, "latitude")), num(g(d, "longitude"))) for d in pkall]
    try:
        k = json.load(open(a.kto, encoding="utf-8"))
        refs += [(x.get("addr1", ""), num(x.get("mapy")), num(x.get("mapx"))) for x in k.get("items", [])]
    except Exception as e: print("관광지 좌표 못 읽음:", e)
    loc = Locator(refs); wc, miss = [], 0
    try: wcall = wc_all(a.key)
    except RuntimeError as e: print("화장실 자료는 건너뜀:", e, flush=True); wcall = []
    for d in wcall:
        ra, la_ = g(d, "LCTN_ROAD_NM_ADDR"), g(d, "LCTN_LOTNO_ADDR")
        f = loc.find(ra, la_)
        if not f: miss += 1; continue
        dis = 1 if any((g(d, k) or "0") != "0" for k in ("MALE_FRDBL_TOILT_CNT", "MALE_FRDBL_URNL_CNT", "FEMALE_FRDBL_TOILT_CNT")) else 0
        baby = 1 if g(d, "DIAP_EXCHCON_EN") == "Y" else 0
        op = g(d, "OPN_HR_DTL") or g(d, "OPN_HR")
        wc.append([g(d, "RSTRM_NM"), ra or la_, f[0], f[1], op, dis, baby, f[2], g(d, "SE_NM")])
    print(f"화장실 위치 추정: {len(wc)}곳 (같은 길 {sum(1 for x in wc if x[7]==0)} · 같은 동리 {sum(1 for x in wc if x[7]==1)} · 같은 읍면동 {sum(1 for x in wc if x[7]==2)}) · 추정 못함 {miss}", flush=True)
    if len(pk) < 50: raise SystemExit(f"강원 자료가 너무 적어요(주차장 {len(pk)}) — 저장하지 않음")
    json.dump({"ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "wc": wc, "pk": pk}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"강원 공중화장실 {len(wc)}곳 · 공영주차장 {len(pk)}곳 저장")

if __name__ == "__main__":
    main()
