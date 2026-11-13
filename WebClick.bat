@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Checking Python...
set "PY="
set "PYARGS="
if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY if exist "%ProgramData%\Anaconda3\python.exe" set "PY=%ProgramData%\Anaconda3\python.exe"

if not defined PY (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 (set "PY=py" & set "PYARGS=-3.12")
)
if not defined PY (
    py -3.11 -c "import sys" >nul 2>nul
    if not errorlevel 1 (set "PY=py" & set "PYARGS=-3.11")
)
if not defined PY (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 (set "PY=python")
)

if not defined PY (
    echo Python 3.10+ is required. Install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

"%PY%" %PYARGS% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or newer is required.
    pause
    exit /b 1
)

echo [2/4] Checking core dependencies...
"%PY%" %PYARGS% -c "import streamlit, pandas, requests" >nul 2>nul
if errorlevel 1 (
    echo Installing core dependencies...
    "%PY%" %PYARGS% -m pip install -q streamlit pandas requests
    if errorlevel 1 goto :error
)

echo [3/4] Checking map dependencies...
"%PY%" %PYARGS% -c "import folium, streamlit_folium, streamlit_geolocation, geonamescache" >nul 2>nul
if errorlevel 1 (
    echo Installing map dependencies...
    "%PY%" %PYARGS% -m pip install -q folium streamlit-folium streamlit-geolocation geonamescache
    if errorlevel 1 goto :error
)

echo [4/4] Starting RainWise...
"%PY%" %PYARGS% -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo Streamlit failed to start.
    pause
)
goto :eof

:error
echo.
echo Setup failed. Check your internet connection and try again.
pause
exit /b 1

