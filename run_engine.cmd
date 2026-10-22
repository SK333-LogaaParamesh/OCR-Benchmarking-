@echo off
rem Re-run one OCR engine on all test images:  run_engine.cmd tesseract
rem Engines: tesseract easyocr doctr rapidocr paddleocr surya indra
rem Already-finished images are skipped, so it is safe to stop and restart.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if "%1"=="" (echo Usage: run_engine.cmd ^<engine^> [--per-group 3] & exit /b 1)
set ENV=env-torch
if "%1"=="paddleocr" set ENV=env-paddle
if "%1"=="rapidocr" set ENV=env-onnx
if "%1"=="surya" set ENV=env-surya
if "%1"=="indra" set ENV=env-indra
envs\%ENV%\Scripts\python.exe bench\run_engines.py %*
