@echo off
rem Rebuild the PDF report (report\Indic-OCR-Benchmark.pdf) from the current results.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
envs\env-torch\Scripts\python.exe bench\build_dashboard_data.py || exit /b 1
envs\env-torch\Scripts\python.exe bench\build_report_pdf.py || exit /b 1
start "" "%~dp0report\Indic-OCR-Benchmark.pdf"
