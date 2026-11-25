@echo off
setlocal
title LIFEPOINT - Blood Donation Camp Register & Management System

:: Locate working Python executable (prefer virtual environment)
set "PY_CMD=.\venv\Scripts\python.exe"
if not exist "%PY_CMD%" (
    set "PY_CMD=python"
)

:menu
cls
echo ==============================================================================
echo        LIFEPOINT : BLOOD DONATION CAMP REGISTER & MANAGEMENT PLATFORM
echo ==============================================================================
echo.
echo   [1] Launch LIFEPOINT Desktop Application (Native GUI App Window)
echo   [2] Launch Interactive Terminal Menu Application (CLI)
echo   [3] Run Automated Unit & Integration Tests (Pytest)
echo   [4] Re-Generate / Reset Demonstration Seed Dataset (40 Records)
echo   [0] Exit
echo.
echo ==============================================================================
set /p choice="Enter option [0-4] (Default is 1): "

if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    cls
    echo Launching LIFEPOINT Desktop Application Window...
    start "" "%PY_CMD%" main.py
    goto menu
)

if "%choice%"=="2" (
    cls
    "%PY_CMD%" main.py --cli
    pause
    goto menu
)

if "%choice%"=="3" (
    cls
    echo Running Automated Pytest Suite...
    "%PY_CMD%" -m pytest -v
    pause
    goto menu
)

if "%choice%"=="4" (
    cls
    echo Re-generating demonstration records in SQLite database...
    "%PY_CMD%" scripts\seed_data.py
    pause
    goto menu
)

if "%choice%"=="0" (
    exit /b 0
)

goto menu
