@echo off
echo ========================================
echo Step 8: Graph 생성 및 시각화
echo ========================================
echo.

call venv\Scripts\activate.bat
python 09_create_graph_visualization.py

echo.
echo 완료! 아무 키나 눌러 종료하세요.
pause
