@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title 강원 여행 수첩 업데이트

set "APK_URL=https://github.com/flyaranaby-collab/gangwon-travel/releases/latest/download/gangwon-travel.apk"
set "PT_URL=https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
set "APK=%~dp0gangwon-travel.apk"
set "ADB=%~dp0platform-tools\adb.exe"

echo.
echo  ============================================
echo     강원 여행 수첩 - 휴대폰 앱 업데이트
echo  ============================================
echo.
echo  [1/3] 최신 앱(APK)을 내려받는 중...
curl.exe -L --fail --silent --show-error -o "%APK%.new" "%APK_URL%"
if errorlevel 1 (
  powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%APK_URL%' -OutFile '%APK%.new' } catch { exit 1 }"
)
if not exist "%APK%.new" (
  echo.
  echo  ! 최신 앱을 내려받지 못했어요. 인터넷 연결을 확인하고 다시 실행해 주세요.
  echo    처음이라면 GitHub에서 첫 APK가 아직 만들어지는 중일 수 있어요. 5분 뒤 다시 실행하세요.
  goto :end
)
move /y "%APK%.new" "%APK%" >nul
echo        완료: gangwon-travel.apk

echo.
echo  [2/3] 휴대폰 연결 도구 준비...
if not exist "%ADB%" (
  echo        처음 한 번만 내려받아요. 1~2분 걸릴 수 있어요.
  curl.exe -L --fail --silent --show-error -o "%~dp0platform-tools.zip" "%PT_URL%"
  if errorlevel 1 powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%PT_URL%' -OutFile '%~dp0platform-tools.zip' } catch { exit 1 }"
  powershell -NoProfile -Command "Expand-Archive -Force -Path '%~dp0platform-tools.zip' -DestinationPath '%~dp0'" >nul 2>&1
  del /q "%~dp0platform-tools.zip" >nul 2>&1
)
if not exist "%ADB%" (
  echo  ! 휴대폰 연결 도구를 준비하지 못했어요. 아래 '휴대폰에서 직접 설치' 방법을 써 주세요.
  goto :manual
)
echo        준비됨

echo.
echo  [3/3] USB로 연결된 휴대폰에 설치하는 중...
"%ADB%" start-server >nul 2>&1
set "DEV="
"%ADB%" devices > "%TEMP%\gw_dev.txt" 2>nul
for /f "usebackq skip=1 tokens=1,2" %%a in ("%TEMP%\gw_dev.txt") do if "%%b"=="device" set "DEV=%%a"
if not defined DEV (
  echo  ! 연결된 휴대폰이 없어요.
  echo    - USB 선으로 휴대폰을 PC에 연결하고
  echo    - 휴대폰 화면에 'USB 디버깅을 허용하시겠습니까?'가 뜨면 [허용]을 눌러 주세요.
  echo    - 그래도 안 되면 사용법.txt 의 'USB 디버깅 켜기'를 참고하세요.
  goto :manual
)
"%ADB%" -s %DEV% install -r "%APK%" > "%TEMP%\gw_install.txt" 2>&1
findstr /c:"Success" "%TEMP%\gw_install.txt" >nul
if not errorlevel 1 (
  echo.
  echo  ** 업데이트 완료! 휴대폰에서 '강원 여행 수첩'을 열어 보세요. **
  goto :end
)
findstr /c:"INSTALL_FAILED_UPDATE_INCOMPATIBLE" "%TEMP%\gw_install.txt" >nul
if not errorlevel 1 (
  echo  ! 휴대폰에 있는 앱과 서명이 달라 덮어쓰기가 안 돼요.
  echo    휴대폰에서 '강원 여행 수첩'을 한 번 삭제한 뒤 이 파일을 다시 실행하세요.
  echo    ^(내 코스·스탬프 기록은 지워져요^)
  goto :end
)
type "%TEMP%\gw_install.txt"
echo  ! 설치하지 못했어요. 위 메시지를 Claude에게 보여 주세요.
goto :end

:manual
echo.
echo  ----- 휴대폰에서 직접 설치 -----
echo  휴대폰 인터넷 창에 아래 주소를 입력하면 최신 앱이 내려받아져요.
echo  %APK_URL%
echo  내려받은 파일을 열고 '출처를 알 수 없는 앱 설치'를 허용하면 설치돼요.

:end
echo.
echo  참고: 앱 안의 장소·문구는 앱을 켤 때 인터넷으로 자동 업데이트돼요.
echo        이 파일은 앱 자체를 새 버전으로 바꿀 때 쓰면 돼요.
echo.
pause
