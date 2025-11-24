@echo off
echo ========================================
echo Step 5.5: Consensus TV 관련 문단 추출
echo ========================================
echo.

call venv\Scripts\activate.bat
python 06_extract_tv_content.py

echo.
echo 완료! 아무 키나 눌러 종료하세요.
pause
