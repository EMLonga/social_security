@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

if not exist "%BACKEND%\venv\Scripts\python.exe" (
  echo [ERROR] Backend venv not found: %BACKEND%\venv\Scripts\python.exe
  echo Please create backend venv and install requirements first.
  pause
  exit /b 1
)

if not exist "%FRONTEND%\package.json" (
  echo [ERROR] Frontend package.json not found: %FRONTEND%\package.json
  pause
  exit /b 1
)

echo Starting backend on http://127.0.0.1:8000 ...
start "SocialSecurity Backend" cmd /k "cd /d "%BACKEND%" && .\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

echo Starting frontend on http://127.0.0.1:5173 ...
start "SocialSecurity Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"

timeout /t 3 >nul
start "" http://127.0.0.1:5173/

echo.
echo Done. If page is still loading, wait 5-10 seconds and refresh browser.
endlocal
