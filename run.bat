@echo off
REM ============================================================================
REM Autonomous AI Incident Investigator (Production SRE Agent)
REM Windows Execution and Automation Script
REM
REM Orchestrated by: LangGraph StateGraph • FastAPI • LLM Reasoning
REM
REM This script automates:
REM 1. Python environment validation (Python 3.10+)
REM 2. Virtual environment (.venv) creation & system site-package linkage
REM 3. Automatic installation of production dependencies from requirements.txt
REM 4. Starting the FastAPI server, Streamlit dashboard, or automated CLI test suite
REM ============================================================================

setlocal enabledelayedexpansion
title Autonomous AI Incident Investigator - Production SRE Agent

echo ============================================================================
echo        INTELLITRACE — Autonomous SRE & Incident Intelligence Platform
echo        Author: Gajraj Jangid • LangGraph • FastAPI • LLM Reasoning
echo ============================================================================
echo.

REM ----------------------------------------------------------------------------
REM Step 1: Verify Python Installation
REM ----------------------------------------------------------------------------
echo [*] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.10+ from https://www.python.org/ and ensure
    echo 'Add Python to PATH' is checked during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [+] Found %PYTHON_VERSION%

REM ----------------------------------------------------------------------------
REM Step 2: Virtual Environment Setup
REM ----------------------------------------------------------------------------
set VENV_DIR=%~dp0.venv
set VENV_ACTIVATE=%VENV_DIR%\Scripts\activate.bat

if not exist "%VENV_ACTIVATE%" (
    echo [*] Virtual environment not found. Creating virtual environment in .venv...
    python -m venv --system-site-packages "%VENV_DIR%"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [+] Virtual environment created successfully.
)

echo [*] Activating virtual environment...
call "%VENV_ACTIVATE%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [+] Virtual environment active.

REM ----------------------------------------------------------------------------
REM Step 3: Install / Verify Dependencies
REM ----------------------------------------------------------------------------
echo [*] Verifying and installing dependencies from requirements.txt...
pip install -r "%~dp0requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Pip encountered an issue installing dependencies. Retrying with verbose output...
    pip install -r "%~dp0requirements.txt"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Dependency installation failed. Please check your internet connection or pip configuration.
        pause
        exit /b 1
    )
)
echo [+] Dependencies are up to date.
echo.

REM ----------------------------------------------------------------------------
REM Step 4: Handle Direct Command-Line Arguments (if provided)
REM ----------------------------------------------------------------------------
if not "%~1"=="" (
    echo [*] Executing command with argument: %*
    python "%~dp0main.py" %*
    goto :end
)

REM ----------------------------------------------------------------------------
REM Step 5: Interactive Menu
REM ----------------------------------------------------------------------------
:menu
cls
echo ============================================================================
echo        INTELLITRACE — Autonomous SRE & Incident Intelligence Platform
echo        Author: Gajraj Jangid • LangGraph • FastAPI • LLM Reasoning
echo ============================================================================
echo  [1] Run All Scenarios & Full LangGraph Evaluation (CLI Scorecard)
echo  [2] Start Full Stack (FastAPI Server + Streamlit Web Dashboard)
echo  [3] Start FastAPI Server Only (Port 8000: API + E-Commerce App)
echo  [4] Launch Streamlit Web Dashboard Only (Port 8501)
echo  [5] Run Comprehensive Pytest Suite (28 Unit & Integration Tests)
echo  [6] Run Synthetic Customer Traffic Generator (Load Test)
echo  [7] Run Scenario 1: Request Queue Bottleneck (High Latency)
echo  [8] Run Scenario 2: High Error Rate (Bad Config Deployment)
echo  [9] Run Scenario 3: Slow Response Time (Cache Saturation)
echo  [10] Run Scenario 4: Unrecoverable Outage (Human SRE Escalation)
echo  [11] Exit
echo ============================================================================
set /p choice="Enter your choice [1-11]: "

if "%choice%"=="1" goto :run_all
if "%choice%"=="2" goto :run_fullstack
if "%choice%"=="3" goto :run_api
if "%choice%"=="4" goto :run_dashboard
if "%choice%"=="5" goto :run_tests
if "%choice%"=="6" goto :run_traffic
if "%choice%"=="7" goto :run_scen_queue
if "%choice%"=="8" goto :run_scen_error
if "%choice%"=="9" goto :run_scen_latency
if "%choice%"=="10" goto :run_scen_unfixable
if "%choice%"=="11" goto :exit_script

echo [ERROR] Invalid choice. Please choose an option between 1 and 11.
timeout /t 2 >nul
goto :menu

:run_all
cls
echo [*] Executing all failure scenarios via LangGraph StateGraph...
python "%~dp0main.py" --all
echo.
pause
goto :menu

:run_fullstack
cls
echo [*] Starting FastAPI Server in background (http://127.0.0.1:8000)...
start "FastAPI Server (Port 8000)" cmd /k "call "%VENV_ACTIVATE%" && python "%~dp0main.py" --api"
timeout /t 2 >nul
echo [*] Launching Streamlit Dashboard (http://localhost:8501)...
python "%~dp0main.py" --dashboard
pause
goto :menu

:run_api
cls
echo [*] Starting FastAPI REST API & E-Commerce Service...
echo [*] OpenAPI Docs: http://127.0.0.1:8000/docs
python "%~dp0main.py" --api
pause
goto :menu

:run_dashboard
cls
echo [*] Launching Streamlit Interactive Web Dashboard...
echo [*] Open your web browser at: http://localhost:8501
python "%~dp0main.py" --dashboard
pause
goto :menu

:run_tests
cls
echo [*] Running full pytest test suite (28 tests)...
python "%~dp0main.py" --test
echo.
pause
goto :menu

:run_traffic
cls
echo [*] Running synthetic traffic generator load test...
python "%~dp0main.py" --traffic
echo.
pause
goto :menu

:run_scen_queue
cls
echo [*] Running Scenario 1: Request Queue Too Long via LangGraph...
python "%~dp0main.py" --scenario queue
echo.
pause
goto :menu

:run_scen_error
cls
echo [*] Running Scenario 2: High Error Rate (Bad Configuration) via LangGraph...
python "%~dp0main.py" --scenario error
echo.
pause
goto :menu

:run_scen_latency
cls
echo [*] Running Scenario 3: Slow Response (Cache Saturation) via LangGraph...
python "%~dp0main.py" --scenario latency
echo.
pause
goto :menu

:run_scen_unfixable
cls
echo [*] Running Scenario 4: Unrecoverable Outage (Human Escalation) via LangGraph...
python "%~dp0main.py" --scenario unfixable
echo.
pause
goto :menu

:end
echo.
echo [*] Execution completed.

:exit_script
echo [*] Exiting. Goodbye!
endlocal
exit /b 0
