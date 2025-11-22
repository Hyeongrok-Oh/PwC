@echo off
echo ============================================================
echo Setting up Virtual Environment for Hankyung Crawler
echo ============================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo.
echo [1/4] Creating virtual environment...
python -m venv venv

echo.
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/4] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [4/4] Installing dependencies...
pip install -r requirements.txt

echo.
echo ============================================================
echo [OK] Virtual environment setup complete!
echo ============================================================
echo.
echo To activate the virtual environment, run:
echo     venv\Scripts\activate
echo.
echo To run the crawler, run:
echo     python crawler.py
echo.
pause
