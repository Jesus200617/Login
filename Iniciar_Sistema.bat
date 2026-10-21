@echo off
title Sistema Minuto para Ganar
echo Iniciando sistema, por favor espere...

cd /d "%~dp0"

:: Liberar el puerto 5000 si estaba ocupado
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do taskkill /F /PID %%a >nul 2>&1

:: Ejecutar Flask
python app.py