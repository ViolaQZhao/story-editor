@echo off
rem Starts the Nootka simulation on this computer and opens it in the browser.
rem Needs Python 3 installed. Close this window to stop.
cd /d "%~dp0"
start "" http://localhost:8000/index.html
py -3 -m http.server 8000 2>nul || python -m http.server 8000
if errorlevel 1 (
  echo.
  echo Python was not found. Install it from python.org, then double-click this file again.
  pause
)
