@echo off
cd /d "%~dp0"
echo Starting Object Spotter...
uv run python main.py
pause
