@echo off
echo Starting Skill Bay Academy Backend Server...
cd backend
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe run.py
) else (
    python run.py
)
pause
