@echo off
setlocal

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5174 ^| findstr LISTENING') do (
  taskkill /PID %%p /F >nul 2>nul
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
  taskkill /PID %%p /F >nul 2>nul
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
  taskkill /PID %%p /F >nul 2>nul
)

echo Stopped processes listening on ports 5173, 5174 and 8000.
endlocal
