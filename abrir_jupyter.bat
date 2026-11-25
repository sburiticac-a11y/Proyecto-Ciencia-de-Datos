@echo off
rem Abre los cuadernos del proyecto en Jupyter Lab usando el entorno .venv
cd /d "%~dp0"
rem Si el entorno .venv no funciona en este computador (por ejemplo, vino de otro equipo), se recrea solo
set "VENV_OK="
if exist ".venv\pyvenv.cfg" for /f "usebackq tokens=1,* delims== " %%a in (".venv\pyvenv.cfg") do if /i "%%a"=="home" if exist "%%b\python.exe" set "VENV_OK=1"
if not exist ".venv\Scripts\jupyter-lab.exe" set "VENV_OK="
if not defined VENV_OK call "%~dp0preparar_entorno.bat" || exit /b 1
".venv\Scripts\jupyter-lab.exe" --ServerApp.root_dir=notebooks
pause
