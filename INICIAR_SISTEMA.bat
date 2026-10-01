@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo No se pudieron instalar los componentes necesarios. Revise que Python este instalado y que haya Internet.
  pause
  exit /b 1
)
%PY% app.py
pause
