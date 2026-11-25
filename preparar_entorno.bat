@echo off
rem Recrea el entorno virtual .venv con el Python de ESTE computador e instala las librerias del proyecto.
rem Ejecutalo una vez (o cada vez que cambies de computador): un .venv no se puede copiar entre equipos.
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python314\python.exe""
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Usando: %PY%
if exist .venv (
    echo Borrando el entorno anterior...
    rmdir /s /q .venv
)
echo Creando el entorno virtual...
%PY% -m venv .venv
if errorlevel 1 (
    echo No se pudo crear el entorno virtual.
    pause
    exit /b 1
)
echo Instalando librerias (puede tardar varios minutos)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Fallo la instalacion de las librerias. Revisa el mensaje de arriba.
    pause
    exit /b 1
)
echo Listo: el entorno .venv quedo preparado para este computador.
