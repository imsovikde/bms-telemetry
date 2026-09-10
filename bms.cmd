@echo off
if "%1"=="ui" (
    python "%~dp0bms_engine.py" ui
) else (
    python "%~dp0bms_engine.py" %*
)
