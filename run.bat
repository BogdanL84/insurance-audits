@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo   Insurance Audit App — Patriot Growth
echo ============================================
echo.

:: Locate Python — try Anaconda first, then system python
set PYTHON=
if exist "%USERPROFILE%\anaconda3\python.exe"   set PYTHON=%USERPROFILE%\anaconda3\python.exe
if exist "%USERPROFILE%\miniconda3\python.exe"  set PYTHON=%USERPROFILE%\miniconda3\python.exe
if "%PYTHON%"=="" (
    where python >nul 2>&1 && set PYTHON=python
)
if "%PYTHON%"=="" (
    echo ERROR: Python not found.
    echo Looked for: Anaconda, Miniconda, system Python.
    echo Install Python 3.10+ from python.org or Anaconda from anaconda.com
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
echo Installing / updating dependencies...
"%PYTHON%" -m pip install -r app\requirements.txt --quiet --upgrade
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies.
    echo Try running manually: "%PYTHON%" -m pip install -r app\requirements.txt
    pause
    exit /b 1
)

echo.
echo Launching at http://localhost:8501
echo Press Ctrl+C to stop.
echo.

cd app
"%PYTHON%" -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

endlocal
