@echo off
echo ============================================================
echo Text Extraction Pipeline
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

REM Run text extraction
python 04_extract_text.py

REM Keep window open
pause
