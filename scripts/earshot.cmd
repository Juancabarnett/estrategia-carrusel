@echo off
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%\tools\earshot"
set "PYTHONUTF8=1"
"%ROOT%\tools\earshot\venv\Scripts\python.exe" -m earshot.cli %*
