@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo  Altiplano Resiliente - Setup
echo ============================================
echo.
echo  이 스크립트는 다음을 자동으로 처리합니다:
echo    - Python 가상환경 생성 및 패키지 설치
echo    - ArcGIS Pro 설치 경로 및 버전 탐지
echo    - 최소 .env 파일 생성 (자격증명만)
echo.
echo  폴더 경로(OneDrive, GDB 등)는 웹 앱 실행 후
echo  사이드바 [Rutas Locales] 버튼에서 설정합니다.
echo.

rem ─── 1. Python 확인 ──────────────────────────────────────────────
echo [1/3] Python 확인...
where python >nul 2>&1
if errorlevel 1 (
  echo [오류] Python을 찾을 수 없습니다.
  echo        설치: https://www.python.org/downloads/
  pause & exit /b 1
)
for /f "tokens=*" %%V in ('python --version 2^>&1') do echo        %%V OK

rem ─── 2. 가상환경 + 패키지 ───────────────────────────────────────
echo.
echo [2/3] 가상환경 및 패키지 설치...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 ( echo [오류] venv 생성 실패 & pause & exit /b 1 )
)
call ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 ( echo [오류] 패키지 설치 실패 & pause & exit /b 1 )
echo        완료

rem ─── 3. ArcGIS Pro 탐지 + .env 생성/업데이트 ───────────────────
echo.
echo [3/3] ArcGIS Pro 탐지 및 .env 처리...
set "S_ARCPY_PYTHON="
set "S_ARCGIS_PRO_VERSION="

for %%D in (C D E F) do (
  if not defined S_ARCPY_PYTHON (
    if exist "%%D:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" (
      set "S_ARCPY_PYTHON=%%D:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    )
  )
)

if defined S_ARCPY_PYTHON (
  echo import arcpy; print(arcpy.GetInstallInfo().get("Version","?")) > _av_tmp.py
  for /f "tokens=*" %%V in ('"!S_ARCPY_PYTHON!" _av_tmp.py 2^>nul') do set "S_ARCGIS_PRO_VERSION=%%V"
  del _av_tmp.py 2>nul
  echo        ArcGIS Pro !S_ARCGIS_PRO_VERSION! 발견
) else (
  echo        [주의] ArcGIS Pro를 찾지 못했습니다. 설치 후 재실행하세요.
)

if exist ".env" (
  echo        기존 .env 발견 -- ArcGIS 정보만 업데이트합니다.
  call ".venv\Scripts\python.exe" -c "import os; from dotenv import set_key; p='.env'; [set_key(p,k,os.environ.get('S_'+k,''),quote_mode='auto') for k in ['ARCPY_PYTHON','ARCGIS_PRO_VERSION'] if os.environ.get('S_'+k)]; print('[OK] .env 업데이트 완료')"
  goto :summary
)

rem ─── 신규 .env 생성: 자격증명 입력 ────────────────────────────
echo.
echo 신규 설치 -- 공유 자격증명을 입력하세요.
echo (이 값은 팀 내 동일하게 사용됩니다)
echo.
set /p "S_SMARTSHEET_TOKEN=    Smartsheet API Token: "
set /p "S_SHEET_C1=    Sheet ID - C1: "
set /p "S_SHEET_C2=    Sheet ID - C2 (없으면 Enter): "
set /p "S_SHEET_C3=    Sheet ID - C3 (없으면 Enter): "
set /p "S_ARCGIS_CLIENT_ID=    ArcGIS Client ID: "
set /p "S_ARCGIS_CLIENT_SECRET=    ArcGIS Client Secret: "
set "S_ARCGIS_ORG_URL=https://iucn.maps.arcgis.com"
set "S_DEFAULT_COMPONENT=C1"

call ".venv\Scripts\python.exe" -c "import os; from pathlib import Path; from dotenv import set_key; env='.env'; Path(env).write_text(''); keys=['ARCGIS_ORG_URL','ARCGIS_CLIENT_ID','ARCGIS_CLIENT_SECRET','SMARTSHEET_TOKEN','SHEET_C1','SHEET_C2','SHEET_C3','DEFAULT_COMPONENT','ARCPY_PYTHON','ARCGIS_PRO_VERSION']; [set_key(env, k, os.environ.get('S_'+k,''), quote_mode='auto') for k in keys]; print('[OK] .env 생성 완료')"

:summary
echo.
echo ============================================
echo  설치 완료!
echo.
echo  다음 단계:
echo    1. run.bat 실행
echo    2. 브라우저에서 http://127.0.0.1:5000 열기
echo    3. 사이드바 상단 [Rutas Locales] 에서
echo       OneDrive / GDB 경로 입력 후 저장
echo ============================================
echo.
pause
exit /b 0
