@echo off
echo ========================================
echo Step 5: TV 관련 리포트 필터링
echo ========================================
echo.

call venv\Scripts\activate.bat
python 05_filter_tv_reports.py

echo.
echo 완료! 아무 키나 눌러 종료하세요.
pause
