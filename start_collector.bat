@echo off
cd /d "%~dp0"
echo Starting Webcam Data Collector...
uv run python collect_data.py
pause
