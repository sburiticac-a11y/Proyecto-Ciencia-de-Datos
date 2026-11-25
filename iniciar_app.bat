@echo off
rem Inicia el backend (API) y el frontend (pagina web), cada uno en su propia ventana, y abre el navegador
cd /d "%~dp0"
rem Si el entorno .venv no funciona en este computador (por ejemplo, vino de otro equipo), se recrea solo
set "VENV_OK="
if exist ".venv\pyvenv.cfg" for /f "usebackq tokens=1,* delims== " %%a in (".venv\pyvenv.cfg") do if /i "%%a"=="home" if exist "%%b\python.exe" set "VENV_OK=1"
if not exist ".venv\Scripts\streamlit.exe" set "VENV_OK="
if not defined VENV_OK call "%~dp0preparar_entorno.bat" || exit /b 1
start "Backend - API (FastAPI)" cmd /k ".venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --port 8000"
echo Esperando a que el backend cargue los modelos...
timeout /t 6 /nobreak >nul
start "Frontend - pagina web (Streamlit)" cmd /k ".venv\Scripts\python.exe -m streamlit run frontend\app.py --server.headless true --browser.gatherUsageStats false"
timeout /t 5 /nobreak >nul
start "" http://localhost:8501
