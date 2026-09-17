@echo off
chcp 65001 >nul
cd /d "%~dp0"
"D:\Users\14566\anaconda3\envs\Yet_myenv\python.exe" game.py
if errorlevel 1 pause
