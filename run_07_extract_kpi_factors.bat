@echo off
echo ========================================
echo Step 6: KPI-Factor 추출
echo ========================================
echo.

call venv\Scripts\activate.bat
python 07_extract_kpi_factors.py

echo.
echo 완료! 아무 키나 눌러 종료하세요.
pause
