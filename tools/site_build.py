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
# 검색 엔진과 방문자가 장소별 페이지로 들어갈 수 있도록 첫 화면 맨 아래에 목록 링크를 둔다
s = s.replace("<title>강원 여행 수첩</title>", '<title>강원 여행 수첩 - 강릉·속초·양양 등 강원도 여행 장소 안내</title>\n<meta name="description" content="강원도 맛집·카페·바다·관광지 약 200곳의 운영 시간, 휴무, 여행 팁과 코스 짜기. 강릉·속초·양양·평창·춘천 등.">', 1)
s = s.replace("</body>", '<nav style="text-align:center;font-size:13px;padding:18px 12px 90px"><a href="place/">전체 장소 목록</a> · ' + " · ".join(f'<a href="region/{r}/">{n}</a>' for r, n in [("gangneung","강릉"),("sokcho","속초·고성"),("yangyang","양양"),("donghae","동해·삼척"),("pyeongchang","평창"),("jeongseon","정선·영월"),("chuncheon","춘천"),("wonju","원주"),("inje","인제"),("hongcheon","홍천"),("hwacheon","화천")]) + "</nav></body>", 1)
p.write_text(s, encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print(f"홈페이지 폴더 {out} 생성: 사진 주소 {n}곳 바꿈, 파일 {sum(1 for _ in out.rglob('*') if _.is_file())}개")
