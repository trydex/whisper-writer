@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d C:\Tools\whisper-writer
".venv\Scripts\python.exe" -u src\main.py > whisper-writer.log 2>&1
