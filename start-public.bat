@echo off
REM Starts the Docker stack and opens a public HTTPS link via a Cloudflare quick tunnel.
REM The public link is printed below (https://....trycloudflare.com) and changes each run.
REM Keep this window open: closing it stops the public link (the local app keeps running).
cd /d "%~dp0"
echo Starting Docker containers...
docker compose up -d
if errorlevel 1 (
  echo Docker failed to start. Is Docker Desktop running?
  pause
  exit /b 1
)
if not exist tools\cloudflared.exe (
  echo tools\cloudflared.exe not found. Download it from
  echo https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
  pause
  exit /b 1
)
echo.
echo Local app : http://127.0.0.1:8080
echo Look for the line containing  https://....trycloudflare.com  - that is your public link.
echo.
tools\cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:8080
