@echo off
title Configurando Acceso Directo
echo Creando acceso directo en el Escritorio...

set "TARGET=%~dp0Iniciar_Sistema.bat"
set "SHORTCUT=%USERPROFILE%\Desktop\Minuto para Ganar.lnk"
set "ICON=%~dp0static\img\logo.ico"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%ICON%'; $s.Save()"

echo.
echo ===================================================
echo  ¡Listo! Se creo el acceso directo con logo.
echo ===================================================
echo.
pause