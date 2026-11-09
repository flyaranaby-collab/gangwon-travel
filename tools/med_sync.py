#!/usr/bin/env python3
"""강원 야간·주말 의료 정보 받기 (국립중앙의료원 공공데이터)

필요한 공공데이터포털 활용신청 (KTO_KEY와 같은 일반 인증키로 신청):
  - 국립중앙의료원_전국 약국 정보 조회 서비스        (B552657/ErmctInsttInfoInqireService)
  - 국립중앙의료원_전국 병·의원 찾기 서비스          (B552657/HsptlAsembySearchService)
  - 국립중앙의료원_전국 응급의료기관 정보 조회 서비스 (B552657/ErmctInfoInqireService)

사용:
  python3 tools/med_sync.py --key KEY --out web/med.json          # 약국·병의원·응급실 전체 (하루 1번)
  python3 tools/med_sync.py --key KEY --er web/er.json            # 응급실 가용 병상만 (1시간마다)

결과 형식(짧게 줄인 배열):
  med.json: { ts, ph:[[이름,전화,주소,위도,경도,운영시간]], hs:[[이름,종류,전화,주소,위도,경도,운영시간]],
              baby:[...hs와 같음], er:[[hpid,이름,대표전화,응급실전화,주소,위도,경도]] }
  er.json:  { ts, beds:{hpid:[응급실가용병상, 갱신시각]} }
  운영시간 = "월|화|수|목|금|토|일|공휴일", 각 칸은 "0900-1800" 또는 "" (쉬는 날)
"""
import argparse, json, subprocess, sys, time, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

B = "https://apis.data.go.kr/B552657/"
SIDO = ["강원특별자치도", "강원도"]
KST = timezone(timedelta(hours=9))


def call(key, svc, op, **p):
    p["serviceKey"] = key
    u = B + svc + "/" + op + "?" + urllib.parse.urlencode(p, safe="%")
    last = ""
    for t in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "60", u], capture_output=True, text=True)
        last = (r.stdout or r.stderr)[:300]
        if r.returncode == 0 and r.stdout.lstrip().startswith("<"):
            root = ET.fromstring(r.stdout.encode("utf-8"))
            err = root.findtext(".//returnAuthMsg") or root.findtext(".//errMsg")
            code = root.findtext(".//resultCode")
            if err and not root.findall(".//item"):
                raise RuntimeError(f"{svc}/{op}: {err} — 공공데이터포털에서 이 서비스를 활용신청했는지 확인하세요")
            if code and code not in ("00", "0000") and not root.findall(".//item"):
                raise RuntimeError(f"{svc}/{op}: resultCode {code} {root.findtext('.//resultMsg')}")
            return root
        time.sleep(3 * (t + 1))
    raise RuntimeError(f"{svc}/{op}: 응답 없음 {last}")


def items(key, svc, op, extra):
    """시도 이름이 '강원특별자치도'/'강원도' 중 어느 쪽이든 받아 오고 페이지를 끝까지 넘긴다."""
    for sido in SIDO:
        out, page = [], 1
        while True:
            q = dict(extra); q.update(pageNo=page, numOfRows=500)
            if "Q0" in q or op.startswith("getEmrrm"):
                pass
            q = {k: (sido if v == "@SIDO" else v) for k, v in q.items()}
            root = call(key, svc, op, **q)
            got = [{c.tag: (c.text or "").strip() for c in it} for it in root.findall(".//item")]
            out += got
            total = int(root.findtext(".//totalCount") or 0)
            if not got or len(out) >= total or page > 40:
                break
            page += 1
        if out:
            return out
    return []


def hours(d):
    cells = []
    for i in range(1, 9):
        s, c = d.get(f"dutyTime{i}s", ""), d.get(f"dutyTime{i}c", "")
        cells.append(f"{s.zfill(4)}-{c.zfill(4)}" if s and c else "")
    return "|".join(cells)


def num(x):
    try:
        return round(float(x), 6)
    except Exception:
        return None


def is_night_or_weekend(h):
    """밤 8시 이후까지 하거나, 일요일·공휴일에 여는 곳만 남긴다(병·의원은 수가 많아서)."""
    cells = h.split("|")
    for i, c in enumerate(cells):
        if not c:
            continue
        s, e = c.split("-")
        if i >= 6 or int(e) >= 2000 or int(e) < int(s):   # 일요일·공휴일 진료, 밤 8시 이후, 자정 넘김 (토요일 오전 진료만은 제외)
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--out")
    ap.add_argument("--er")
    a = ap.parse_args()
    ts = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

    if a.out:
        ph = []
        try:
            ph_items = items(a.key, "ErmctInsttInfoInqireService", "getParmacyListInfoInqire", {"Q0": "@SIDO"})
        except Exception as e:
            print("약국 건너뜀:", e); ph_items = []
        for d in ph_items:
            la, lo = num(d.get("wgs84Lat")), num(d.get("wgs84Lon"))
            if la is None:
                continue
            ph.append([d.get("dutyName", ""), d.get("dutyTel1", ""), d.get("dutyAddr", ""), la, lo, hours(d)])
        print("약국", len(ph))

        hs = []
        try:
            hs_items = items(a.key, "HsptlAsembySearchService", "getHsptlMdcncListInfoInqire", {"Q0": "@SIDO"})
        except Exception as e:
            print("병의원 건너뜀:", e); hs_items = []
        for d in hs_items:
            la, lo = num(d.get("wgs84Lat")), num(d.get("wgs84Lon"))
            h = hours(d)
            if la is None or not is_night_or_weekend(h):
                continue
            hs.append([d.get("dutyName", ""), d.get("dutyDivNam", ""), d.get("dutyTel1", ""), d.get("dutyAddr", ""), la, lo, h])
        print("야간·주말 병의원", len(hs))

        baby = []
        try:
            for d in items(a.key, "HsptlAsembySearchService", "getBabyListInfoInqire", {"Q0": "@SIDO"}):
                la, lo = num(d.get("wgs84Lat")), num(d.get("wgs84Lon"))
                if la is None:
                    continue
                baby.append([d.get("dutyName", ""), "달빛어린이병원", d.get("dutyTel1", ""), d.get("dutyAddr", ""), la, lo, hours(d)])
        except Exception as e:
            print("달빛어린이병원 건너뜀:", e)
        print("달빛어린이병원", len(baby))

        er = []
        try:
            for d in items(a.key, "ErmctInfoInqireService", "getEgytListInfoInqire", {"Q0": "@SIDO"}):
                la, lo = num(d.get("wgs84Lat")), num(d.get("wgs84Lon"))
                if la is None:
                    continue
                er.append([d.get("hpid", ""), d.get("dutyName", ""), d.get("dutyTel1", ""), d.get("dutyTel3", ""), d.get("dutyAddr", ""), la, lo])
        except Exception as e:
            print("응급실 목록 건너뜀:", e)
        print("응급의료기관", len(er))

        if not ph and not hs:
            sys.exit("받은 자료가 없습니다. 인증키·활용신청을 확인하세요.")
        json.dump({"ts": ts, "ph": ph, "hs": hs, "baby": baby, "er": er}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    if a.er:
        beds = {}
        for d in items(a.key, "ErmctInfoInqireService", "getEmrrmRltmUsefulSckbdInfoInqire", {"STAGE1": "@SIDO"}):
            if d.get("hpid"):
                beds[d["hpid"]] = [d.get("hvec", ""), d.get("hvidate", "")]
        print("응급실 병상", len(beds))
        json.dump({"ts": ts, "beds": beds}, open(a.er, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
