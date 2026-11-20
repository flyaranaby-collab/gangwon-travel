"""웹 수첩(index.html)을 앱인토스(토스 미니앱)판으로 바꾼다. 기존 웹 수첩·안드로이드 앱 파일은 건드리지 않는다.
바꾸는 것(토스 검수 기준 맞추기)
- 완전한 HTML 문서로 감싸고, 밝은 화면만·손가락 확대 막기
- 운영자 기능(로그인·장소 수정·GitHub 저장)·문의·관광공사 키 입력칸 빼기
- 수첩 자체 뒤로 가기 버튼 숨기기(토스 뒤로 가기만 사용)
- 카카오 지도 스크립트 불러오지 않기(바깥 코드 실행 금지) → 약도로 표시
- 위치는 토스 위치 기능으로, 앱을 열자마자 위치 권한을 묻지 않기(이미 허용한 경우만 자동)
- 공유는 토스 공유 링크(intoss://)로
- 웹 수첩 저장소 사진(/_blob/...)은 GitHub에 올라간 사진으로
- 광고 자리 2곳(목록 맨 아래, 상세 화면 맨 아래)
사용: python3 tools/toss_copy.py <웹 수첩 index.html> <출력 index.html> <glue.js>
"""
import re, sys, time, pathlib
src, dst, glue = sys.argv[1], sys.argv[2], sys.argv[3]
s = pathlib.Path(src).read_text(encoding="utf-8")
RAW = "https://raw.githubusercontent.com/flyaranaby-collab/gangwon-travel/main/web/photos/"
APP_NAME = "gangwon-note"
AD_BANNER = "ait-ad-test-banner-id"   # ← 콘솔에서 받은 배너 광고 그룹 ID로 바꾸면 실제 광고가 나와요
n_fail = []
def sub(pat, rep, count=1, flags=0, need=True):
    global s
    s2, n = re.subn(pat, rep, s, count=count, flags=flags)
    if need and n == 0: n_fail.append(pat[:60])
    s = s2
def rep(old, new, need=True):
    global s
    if old not in s:
        if need: n_fail.append(old[:60])
        return
    s = s.replace(old, new, 1)

# 사진: 웹 수첩 저장소 → GitHub 사진
sub(r'/_blob/([0-9a-f]{32})', RAW + r'\1.jpg', count=0, need=False)
# 운영자용 입력칸(관광공사 키·문의 연락처)과 문의 양식 빼기 (앱판과 같음)
sub(r'<div class="sec-title"><h2>한국관광공사 TourAPI</h2>.*?(?=<div class="sec-title"><h2>문의·제보</h2>)', '', flags=re.S, need=False)
sub(r'<form class="revbox" id="inqForm".*?</form>`;', '`;', flags=re.S, need=False)
# 운영자 모드가 켜지지 않게
rep('if (isLocal && !window.APK_BUILD) state.isOps = true;', 'if (isLocal && !window.APK_BUILD && !window.TOSS_BUILD) state.isOps = true;')
# 장소 상세의 '정보 수정 문의' 줄 빼기, 리뷰 표시 기본값은 앱판과 같게
rep('(window.APK_BUILD ? "" : `<div class="ownerline">', '((window.APK_BUILD||window.TOSS_BUILD) ? "" : `<div class="ownerline">')
rep('showRev: window.APK_BUILD ? false', 'showRev: (window.APK_BUILD||window.TOSS_BUILD) ? false')
# 카카오 지도 스크립트를 불러오지 않음(약도 사용)
sub(r'const KMAP_KEY = window\.KAKAO_KEY \|\| "[^"]*";', 'const KMAP_KEY = "";')
# 택시: 카카오T가 없을 때 페이지를 바꾸는 코드 빼기(외부 이동은 토스 방식으로만)
sub(r''' onclick="setTimeout\(\(\)=>\{ if\(!document\.hidden\) location\.href='https://www\.kakaomobility\.com/'; \},1500\)"''', '', need=False)
# 위치: 토스 위치 기능 사용, 자동 조회는 이미 허용한 경우만
rep('function getPos(){\n  return new Promise(ok=>{', 'function getPos(){\n  if (window.TOSS_BUILD && window.AIT_GETPOS) return window.AIT_GETPOS();\n  return new Promise(ok=>{')
rep('async function refreshMyPos(){\n  if (MYPOS_BUSY', 'async function refreshMyPos(){\n  if (window.TOSS_BUILD && !(window.AIT_POS_OK && await window.AIT_POS_OK())) return;\n  if (MYPOS_BUSY')
# 공유: 토스 공유 링크
rep('    if (navigator.share && /Android|iPhone|iPad/i.test(navigator.userAgent) && !window.APK_BUILD){',
    '    if (window.TOSS_BUILD && window.AIT_SHARE){ await window.AIT_SHARE(b.dataset.sharelink); return; }\n    if (navigator.share && /Android|iPhone|iPad/i.test(navigator.userAgent) && !window.APK_BUILD){')
# 공유 버튼 이름(토스에서는 복사 대신 공유 창이 열려요)
rep('data-sharelink="${esc(p.id)}">🔗 이 장소 링크 복사</button>', 'data-sharelink="${esc(p.id)}">🔗 이 장소 공유하기</button>')
# 광고 자리
rep('  <section class="panel" id="tab-more" hidden></section>', '  <section class="panel" id="tab-more" hidden></section>\n  <div class="tossad" id="tossAdMain" aria-label="광고"></div>')
rep('  <div class="subbody inner" id="subBody"></div>', '  <div class="subbody inner" id="subBody"></div>\n  <div class="tossad" id="tossAdSub" aria-label="광고"></div>')
if n_fail:
    print("바꾸지 못한 곳:", n_fail); sys.exit(1)

VER = time.strftime("%Y%m%d%H%M%S")
pre = ('<script>window.TOSS_BUILD=true;window.NOTE_VER="' + VER + '";window.TOSS_AD_BANNER="' + AD_BANNER + '";'
       'document.documentElement.setAttribute("data-theme","light");</script>\n'
       '<script src="./ait-bridge.js"></script>\n'
       '<script>(function(){var A=window.AIT;if(!A)return;'
       # 위치: 사용자가 버튼을 눌렀을 때 토스 권한 창 → 현재 위치
       'window.AIT_GETPOS=function(){return A.Device.getLocation({accuracy:A.Accuracy.Balanced}).then(function(l){var c=l&&l.coords;return c?{lat:c.latitude,lng:c.longitude,acc:Math.round(c.accuracy||0)}:null;}).catch(function(){return null;});};'
       'window.AIT_POS_OK=function(){try{return A.Device.getLocation.getPermission().then(function(p){return p==="allowed";}).catch(function(){return false;});}catch(e){return Promise.resolve(false);}};'
       # 공유: intoss:// 링크를 만들어 토스 공유 창으로
       'window.AIT_SHARE=function(id){var p=(typeof byId==="function"&&byId(id))||{};return A.Share.createLink({path:"intoss://' + APP_NAME + '?place="+encodeURIComponent(id)}).then(function(link){return A.Share.sendMessage({message:"강원 여행 수첩 · "+(p.name||"")+"\\n"+link});}).catch(function(){});};'
       '})();</script>\n')
css = ('<style>\n'
       '/* 토스판: 수첩 자체 뒤로 가기 버튼 숨김(토스 뒤로 가기만), 광고 자리 */\n'
       '#subBack{display:none!important}\n'
       '.subbar{padding-left:16px}\n'
       '.tossad{width:100%;margin:24px 0 8px}\n'
       '.tossad.empty{display:none}\n'
       '#apkEntry,[data-apkops],[data-tab="ops"],#tab-ops{display:none!important}\n'
       '</style>\n')
head = ('<!doctype html><html lang="ko" data-theme="light"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">'
        '<meta name="color-scheme" content="light">'
        '<style>:root{color-scheme:light;box-sizing:border-box}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style>'
        '</head><body>\n')
g = pathlib.Path(glue).read_text(encoding="utf-8")
s = head + pre + css + s + '\n<script>\n' + g + '\n</script>\n</body></html>\n'
pathlib.Path(dst).write_text(s, encoding="utf-8")
print("토스판 화면 저장:", dst, "· 버전", VER, "· 광고 ID", AD_BANNER)
