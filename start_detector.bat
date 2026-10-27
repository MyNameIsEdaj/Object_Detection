@echo off
cd /d "%~dp0"
echo Starting Live Object Detection...
uv run python main.py
pause
