@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo  Altiplano Resiliente - 앱 시작
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [오류] 가상환경(.venv)을 찾을 수 없습니다.
  echo        setup.bat 을 먼저 실행하세요.
  pause
  exit /b 1
)

if not exist ".env" (
  echo [오류] .env 파일이 없습니다.
  echo        setup.bat 을 실행하거나 .env 파일을 직접 만드세요.
  pause
  exit /b 1
)

echo  서버 주소: http://127.0.0.1:5000
echo  종료하려면 이 창에서 Ctrl+C 를 누르세요.
echo.

call ".venv\Scripts\python.exe" -m flask --app app run --host 127.0.0.1 --port 5000
