"""국토교통부(TAGO) 열차정보로 강원 주요 역 ↔ 서울·청량리(그리고 강원 안 몇 구간)의 7일치 열차 시간표·요금을 받아 web/train.json 에 저장한다.
사용: python3 tools/train_sync.py --key DATA_GO_KR_KEY --out web/train.json
- API: https://apis.data.go.kr/1613000/TrainInfo (2026-03 바뀐 주소). 공공데이터포털에서 '국토교통부_(TAGO)_열차정보' 활용신청이 필요하다.
- 호출 수를 줄이려고 첫날 열차가 없는 구간은 나머지 날짜를 건너뛴다(하루 약 200~300회).
- 좌석 잔여 여부는 이 API에 없다. 앱은 시간표·요금을 보여 주고, 예매는 네이버·코레일 화면으로 넘긴다.
"""
import argparse, json, sys, time, datetime as dt, pathlib, urllib.parse, urllib.request

BASE = "https://apis.data.go.kr/1613000/TrainInfo/"
KST = dt.timezone(dt.timedelta(hours=9))
HUBS = ["서울", "청량리"]
GW = ["강릉", "정동진", "묵호", "동해", "진부(오대산)", "평창", "둔내", "횡성", "만종", "원주", "서원주", "춘천", "남춘천", "영월", "태백", "삼척"]
INNER = [("강릉", "정동진"), ("강릉", "동해"), ("강릉", "묵호"), ("원주", "강릉"), ("만종", "강릉")]
DAYS = 7


class ApiError(Exception):
    pass


def call(key, op, **params):
    q = {"serviceKey": key, "_type": "json", "numOfRows": 300, "pageNo": 1, **params}
    url = BASE + op + "?" + urllib.parse.urlencode(q, safe="%")
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=30) as r:
                raw = r.read().decode("utf-8", "replace")
            if raw.lstrip().startswith("<"):
                # 인증 오류 등은 XML 로 온다
                code = raw.split("<returnReasonCode>")[1].split("<")[0] if "<returnReasonCode>" in raw else "?"
                msg = raw.split("<returnAuthMsg>")[1].split("<")[0] if "<returnAuthMsg>" in raw else raw[:200]
                raise ApiError(f"{code} {msg}")
            j = json.loads(raw)
            h = j.get("response", {}).get("header", {})
            if h.get("resultCode") not in ("00", "0000", None):
                raise ApiError(f"{h.get('resultCode')} {h.get('resultMsg')}")
            items = (j["response"].get("body", {}) or {}).get("items") or {}
            it = items.get("item", []) if isinstance(items, dict) else []
            return it if isinstance(it, list) else [it]
        except ApiError:
            raise
        except Exception as e:
            last = e; time.sleep(2 * (i + 1))
    raise ApiError(f"연결 실패 {last}")


def hhmm(v):
    s = str(v)
    return s[8:12] if len(s) >= 12 else ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--key", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    key = urllib.parse.unquote(a.key)  # 인코딩된 키가 와도 한 번 풀어서 쓴다
    try:
        cities = call(key, "GetCtyCodeList")
    except ApiError as e:
        print(f"열차정보 API를 쓸 수 없어요: {e}\n공공데이터포털에서 '국토교통부_(TAGO)_열차정보' 활용신청을 했는지 확인하세요.", file=sys.stderr)
        sys.exit(1)
    want = [c for c in cities if any(k in str(c.get("cityname", "")) for k in ("서울", "강원"))]
    stations = {}
    for c in want:
        for s in call(key, "GetCtyAcctoTrainSttnList", cityCode=c["citycode"]):
            stations[str(s["nodename"]).strip()] = str(s["nodeid"])
    miss = [n for n in HUBS + GW if n not in stations]
    if miss: print("역 ID를 못 찾은 역:", miss, file=sys.stderr)
    pairs = []
    for g in GW:
        for h in HUBS:
            if g in stations and h in stations: pairs += [(h, g), (g, h)]
    for x, y in INNER:
        if x in stations and y in stations: pairs += [(x, y), (y, x)]
    today = dt.datetime.now(KST).date()
    days = [(today + dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(DAYS)]
    routes, calls, empty = {}, 0, 0
    for (x, y) in pairs:
        key_r = f"{x}>{y}"; per = {}
        for di, d in enumerate(days):
            try:
                rows = call(key, "GetStrtpntAlocFndTrainInfo", depPlaceId=stations[x], arrPlaceId=stations[y], depPlandTime=d)
            except ApiError as e:
                print(f"  {key_r} {d}: {e}", file=sys.stderr); rows = []
            calls += 1
            out = []
            for r in rows:
                dep, arr = hhmm(r.get("depplandtime")), hhmm(r.get("arrplandtime"))
                if not dep or not arr: continue
                out.append([dep, arr, str(r.get("traingradename", "")).strip(), str(r.get("trainno", "")).strip(), int(r.get("adultcharge") or 0)])
            out.sort()
            if out: per[d] = out
            if di == 0 and not out:
                empty += 1; break   # 첫날 열차가 없으면 직행이 없는 구간으로 보고 건너뛴다
            time.sleep(0.15)
        if per: routes[key_r] = per
    if len(routes) < 4:
        print(f"받은 구간이 {len(routes)}개뿐이라 저장하지 않습니다", file=sys.stderr); sys.exit(1)
    st = sorted({n for k in routes for n in k.split(">")}, key=lambda n: (n not in HUBS, (HUBS + GW).index(n) if n in HUBS + GW else 99))
    pathlib.Path(a.out).write_text(json.dumps({"rev": int(time.time() * 1000), "src": "국토교통부(TAGO) 열차정보", "days": days, "stations": st, "routes": routes},
                                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = sum(len(v) for r in routes.values() for v in r.values())
    print(f"열차 {n}편 저장: 구간 {len(routes)}개, 호출 {calls}회, 직행 없는 구간 {empty}개")


if __name__ == "__main__":
    main()
