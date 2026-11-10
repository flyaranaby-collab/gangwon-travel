"""강원 11개 권역의 날씨 예보를 받아 web/weather.json 에 저장한다.
사용: python3 tools/weather_sync.py --html web/index.html --out web/weather.json
- 자료: 노르웨이 기상청(MET Norway) Locationforecast 2.0, CC BY 4.0 (출처 표시하면 상업적 이용 가능).
- 약관에 따라 User-Agent 로 앱을 밝히고, 좌표는 소수 4자리까지만 보내고, 앱이 직접 부르지 않고 이 작업이 대신 받아 둔다.
- 권역 좌표는 web/index.html 의 REGIONS 에서 읽는다(권역이 늘어도 따로 고칠 필요 없음).
"""
import argparse, json, re, sys, time, pathlib, urllib.request, datetime as dt

UA = "GangwonTravelNote/1.0 (https://github.com/flyaranaby-collab/gangwon-travel)"
API = "https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={:.4f}&lon={:.4f}"
KST = dt.timezone(dt.timedelta(hours=9))


def regions(html):
    s = pathlib.Path(html).read_text(encoding="utf-8")
    a = s.index("const REGIONS = ["); b = s.index("];", a)
    return [(m[0], float(m[1]), float(m[2])) for m in re.findall(r'id:"([^"]+)"[^}]*?lat:([\d.]+),\s*lng:([\d.]+)', s[a:b])]


def fetch(lat, lng):
    for i in range(3):
        try:
            req = urllib.request.Request(API.format(lat, lng), headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:  # 잠깐의 오류는 다시 시도
            err = e; time.sleep(3 * (i + 1))
    raise err


def r1(x):
    return None if x is None else round(float(x), 1)


def reduce(j, now=None):
    """시간별 예보를 한국 날짜별 최저·최고 기온, 강수량, 최대 풍속, 대표 날씨로 줄인다."""
    ts = j["properties"]["timeseries"]
    now = now or dt.datetime.now(dt.timezone.utc)
    days, cur = {}, None
    for e in ts:
        t = dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00"))
        d = e["data"]; ins = d["instant"]["details"]
        n1, n6 = d.get("next_1_hours"), d.get("next_6_hours")
        if cur is None and t >= now - dt.timedelta(minutes=59):
            sym = (n1 or n6 or {}).get("summary", {}).get("symbol_code", "")
            cur = {"t": r1(ins.get("air_temperature")), "w": r1(ins.get("wind_speed")), "s": sym}
        lt = t.astimezone(KST); key = lt.date().isoformat()
        day = days.setdefault(key, {"temps": [], "r": 0.0, "w": 0.0, "noon": None, "first": None, "n": 0})
        day["n"] += 1
        temps = [ins.get("air_temperature")]
        if n1:
            day["r"] += float(n1.get("details", {}).get("precipitation_amount", 0) or 0)
        elif n6:  # 6시간 간격 구간: 6시간 값이 그 구간 전체를 대신한다
            det = n6.get("details", {})
            day["r"] += float(det.get("precipitation_amount", 0) or 0)
            temps += [det.get("air_temperature_max"), det.get("air_temperature_min")]
        day["temps"] += [x for x in temps if x is not None]
        day["w"] = max(day["w"], float(ins.get("wind_speed", 0) or 0))
        sym = (n6 or n1 or {}).get("summary", {}).get("symbol_code")
        if sym:
            if day["first"] is None: day["first"] = sym
            if lt.hour == 12 or (day["noon"] is None and 9 <= lt.hour <= 15): day["noon"] = sym
    out = []
    for key in sorted(days):
        day = days[key]
        if not day["temps"] or not (day["noon"] or day["first"]): continue
        out.append({"d": key, "lo": r1(min(day["temps"])), "hi": r1(max(day["temps"])), "r": r1(day["r"]),
                    "w": r1(day["w"]), "s": day["noon"] or day["first"], "n": day["n"]})
    # 마지막 날은 예보 시각이 몇 개 없어 최저·최고가 틀릴 수 있으니 뺀다
    while out and out[-1]["n"] < 3: out.pop()
    for x in out: x.pop("n")
    return {"now": cur, "days": out[:9]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    regs = regions(a.html)
    if not regs:
        print("권역 좌표를 찾지 못했어요", file=sys.stderr); sys.exit(1)
    res = {}
    for rid, lat, lng in regs:
        try:
            res[rid] = reduce(fetch(lat, lng))
            print(f"{rid}: {len(res[rid]['days'])}일", file=sys.stderr)
        except Exception as e:
            print(f"{rid}: 실패 {type(e).__name__}: {e}", file=sys.stderr)
        time.sleep(1.5)
    if len(res) < max(1, len(regs) // 2):
        print("절반 넘게 실패해서 기존 자료를 그대로 둡니다", file=sys.stderr); sys.exit(1)
    out = {"rev": int(time.time() * 1000), "src": "MET Norway", "license": "CC BY 4.0", "regions": res}
    pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"날씨 {len(res)}/{len(regs)}개 권역 저장")


if __name__ == "__main__":
    main()
