# 수첩 원본

- `index.html`: 웹 수첩(claude.ai 아티팩트)과 같은 원본 파일. 운영·문의·AI 기능까지 들어 있다.
- `i18n/*.tsv`: 번역 사전 원본(한국어 → 영어·중국어·일본어, 탭으로 구분).
- `build_i18n.py`: 번역 사전을 `index.html` 안에 넣는다. `python3 source/build_i18n.py`

고친 뒤 앱용 사본 만들기: `python3 tools/app_copy.py source/index.html web/index.html`
자세한 순서는 `docs/manual.html` 8장 참고.
