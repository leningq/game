@echo off
setlocal
cd /d "%~dp0"
set "GAME_PYTHON=.venv\Scripts\python.exe"

if not exist "%GAME_PYTHON%" (
    echo Creating the Brickfall Python environment...
    py -3.13 -m venv .venv >nul 2>&1 || py -3.12 -m venv .venv >nul 2>&1 || py -3.11 -m venv .venv >nul 2>&1
    if not exist "%GAME_PYTHON%" (
        echo Install Python 3.12 from python.org, then run this file again.
        pause
        exit /b 1
    )
)

"%GAME_PYTHON%" -c "import pygame, fastapi, uvicorn, jinja2" >nul 2>&1
if errorlevel 1 (
    echo Installing Brickfall dependencies...
    "%GAME_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Installation failed. Check the messages above and your internet connection.
        pause
        exit /b 1
    )
)

"%GAME_PYTHON%" run.py
if errorlevel 1 (
    echo Brickfall could not start. Check the message above.
    pause
    exit /b 1
)
