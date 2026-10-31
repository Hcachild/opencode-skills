@echo off
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0opencode-desktop-retry-e2e.ps1" %*
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0opencode-desktop-retry-e2e.ps1" %*
)
