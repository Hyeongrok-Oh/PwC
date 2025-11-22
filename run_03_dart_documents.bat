@echo off
echo ============================================================
echo Downloading DART Original Documents
echo ============================================================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup_venv.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run document downloader
python 03_download_dart_documents.py

REM Keep window open
pause
