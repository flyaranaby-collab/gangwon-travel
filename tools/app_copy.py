"""웹 수첩(index.html)을 앱용(web/index.html)으로 바꾼다.
- 운영·문의·AI 기능을 숨기는 APK 표시를 넣고
- 웹 수첩 저장소의 사진 주소(/_blob/...)를 앱 안에 든 사진(photos/...)으로 바꾸고
- 앱에 아직 없는 사진은 GitHub에 올라간 사진으로 대신 불러온다.
사용: python3 tools/app_copy.py <웹 수첩 index.html> web/index.html
"""
import re, sys, time, pathlib
src, dst = sys.argv[1], sys.argv[2]
s = pathlib.Path(src).read_text(encoding="utf-8")
RAW = "https://raw.githubusercontent.com/flyaranaby-collab/gangwon-travel/main/web/photos/"
APP = "https://appassets.androidplatform.net/assets/photos/"
s = re.sub(r'/_blob/([0-9a-f]{32})', APP + r'\1.jpg', s)
# 앱에서는 쓰지 않는 운영자용 입력칸(관광공사 인증키·문의 연락처)을 아예 빼서, 보안 검사가 '정보 수집'으로 오해하지 않게 한다
s = re.sub(r'<div class="sec-title"><h2>한국관광공사 TourAPI</h2>.*?(?=<div class="sec-title"><h2>문의·제보</h2>)', '', s, count=1, flags=re.S)
s = re.sub(r'<form class="revbox" id="inqForm".*?</form>`;', '`;', s, count=1, flags=re.S)
head = ('<script>window.APK_BUILD=true;'
        'document.addEventListener("error",function(e){var t=e.target;'
        'if(t&&t.tagName==="IMG"&&!t.dataset.fb&&/\\/assets\\/photos\\/|android_asset\\/photos\\//.test(t.src)){'
        't.dataset.fb="1";t.src="' + RAW + '"+t.src.split("/").pop();}},true);</script>')
s = re.sub(r"<script>window.APK_BUILD=true;.*?</script>\n?", "", s, count=1, flags=re.S)
if True:
    s = s.replace("<title>강원 여행 수첩</title>", "<title>강원 여행 수첩</title>\n" + head, 1)
pathlib.Path(dst).write_text(s, encoding="utf-8")
pathlib.Path(dst).with_name("version.txt").write_text(time.strftime("%Y%m%d%H%M"), encoding="utf-8")
missing = [m for m in set(re.findall(r'assets/photos/([0-9a-f]{32}\.jpg)', s)) if not (pathlib.Path(dst).parent / "photos" / m).exists()]
print("app copy written; photos missing in web/photos:", len(missing))
