@echo off
echo ========================================
echo Step 7: KPI-Factor 집계
echo ========================================
echo.

call venv\Scripts\activate.bat
python 08_aggregate_kpi_factors.py

echo.
echo 완료! 아무 키나 눌러 종료하세요.
pause
