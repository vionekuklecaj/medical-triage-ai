@echo off
REM ===================================================================
REM  AI Medical Intake & Triage System - launch all four services
REM  Run from the project root (same folder as main.py).
REM  Each service opens in its own terminal window, activates the venv
REM  (if one exists), and runs via "python -m" so it does not depend on
REM  uvicorn being on PATH.
REM ===================================================================

echo Starting all services...

start "Intake Agent (8001)"  cmd /k "(if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) & python -m uvicorn agents.intake_api:app --host 0.0.0.0 --port 8001 --reload"
start "Triage Agent (8002)"  cmd /k "(if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) & python -m uvicorn agents.triage_api:app --host 0.0.0.0 --port 8002 --reload"
start "Drug History (8003)"  cmd /k "(if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) & python -m uvicorn agents.drug_history_api:app --host 0.0.0.0 --port 8003 --reload"

REM Give the agent services a moment to bind their ports before the
REM orchestrator comes up.
timeout /t 3 /nobreak >nul

start "Lead Orchestrator (8000)"  cmd /k "(if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) & python main.py"

echo.
echo All four services launching in separate windows:
echo   Intake        -^> http://localhost:8001
echo   Triage        -^> http://localhost:8002
echo   Drug History  -^> http://localhost:8003
echo   Lead / Main   -^> http://localhost:8000  (Swagger UI at /docs)
echo.
echo Send patient data with a POST to http://localhost:8000/run