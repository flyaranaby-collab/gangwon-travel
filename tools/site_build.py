"""홈페이지(GitHub Pages)용 폴더 _site 를 만든다.
- web/ 전체를 복사하고, index.html 의 앱 전용 사진 주소(appassets.androidplatform.net)를 홈페이지 안의 photos/ 로 바꾼다.
- 운영자·문의·AI 기능은 앱과 같이 숨겨진 상태(APK_BUILD)로 둔다. 방문자에게는 열람용 수첩이다.
사용: python3 tools/site_build.py _site
"""
import shutil, sys, pathlib
out = pathlib.Path(sys.argv[1]); src = pathlib.Path("web")
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
p = out / "index.html"
s = p.read_text(encoding="utf-8")
n = s.count("https://appassets.androidplatform.net/assets/photos/")
s = s.replace("https://appassets.androidplatform.net/assets/photos/", "photos/")
p.write_text(s, encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print(f"홈페이지 폴더 {out} 생성: 사진 주소 {n}곳 바꿈, 파일 {sum(1 for _ in out.rglob('*') if _.is_file())}개")
