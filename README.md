# 강원 여행 수첩 (안드로이드 앱)

강릉·속초·양양부터 평창·정선·춘천까지, 가볼 곳·맛집·계절 행사·교통·할인 방법·내 코스를 담은 강원 여행 안내 앱입니다. 한국어·English·中文·日本語를 지원합니다.

## APK 받기
휴대폰에서 아래 링크를 누르면 바로 내려받아집니다. (로그인 필요 없음)

**https://github.com/flyaranaby-collab/gangwon-travel/releases/latest/download/gangwon-travel.apk**

받은 파일을 열고 '출처를 알 수 없는 앱 설치'를 허용하면 설치됩니다.

## 업데이트는 두 가지
1. **수첩 내용(장소·문구·번역)**: `web/index.html` 과 `web/version.txt` 가 바뀌면, 앱을 켤 때 인터넷으로 자동으로 받아 바꿉니다. 다시 설치할 필요가 없습니다.
2. **앱 자체**: 저장소에 올리면 GitHub가 새 APK를 만들어 '다운로드 페이지(Releases)'에 올립니다. PC에서 `pc/업데이트.bat` 을 실행하면 최신 APK를 받아 USB로 연결된 휴대폰에 바로 설치합니다.

## 폴더
- `web/index.html` 앱에 들어가는 수첩 (웹 수첩과 같고, 운영·문의·AI 기능만 숨김)
- `web/version.txt` 수첩 버전 번호 (클수록 최신)
- `app/` 안드로이드 앱 (WebView)
- `pc/업데이트.bat`, `pc/사용법.txt` PC용 업데이트 도구

## 같은 서명 키 (덮어쓰기 업데이트에 필요)
안드로이드는 **같은 앱 이름표(kr.gangwon.travelnote) + 같은 서명 키**로 만든 APK만 기존 앱 위에 설치해 줍니다. 서명 키는 저장소에 올리지 않고 GitHub Secrets에 넣어 둡니다.
- `GANGWON_KEYSTORE`: 서명 키 파일을 base64로 바꾼 값
- `GANGWON_KEY_PASS`: 서명 키 비밀번호

서명 키를 잃어버리면 다시는 덮어쓰기 업데이트를 할 수 없으니 따로 보관하세요.
