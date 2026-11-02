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
s = re.sub(r'/_blob/([0-9a-f]{32})', r'file:///android_asset/photos/\1.jpg', s)
head = ('<script>window.APK_BUILD=true;'
        'document.addEventListener("error",function(e){var t=e.target;'
        'if(t&&t.tagName==="IMG"&&!t.dataset.fb&&t.src.indexOf("file:///android_asset/photos/")===0){'
        't.dataset.fb="1";t.src="' + RAW + '"+t.src.split("/").pop();}},true);</script>')
if "window.APK_BUILD=true" not in s:
    s = s.replace("<title>강원 여행 수첩</title>", "<title>강원 여행 수첩</title>\n" + head, 1)
pathlib.Path(dst).write_text(s, encoding="utf-8")
pathlib.Path(dst).with_name("version.txt").write_text(time.strftime("%Y%m%d%H%M"), encoding="utf-8")
missing = [m for m in set(re.findall(r'android_asset/photos/([0-9a-f]{32}\.jpg)', s)) if not (pathlib.Path(dst).parent / "photos" / m).exists()]
print("app copy written; photos missing in web/photos:", len(missing))
