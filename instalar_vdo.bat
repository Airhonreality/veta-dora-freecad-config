@echo off
REM =====================================================================
REM instalar_vdo.bat
REM Script de instalación VDO para Windows
REM =====================================================================

echo ==========================================
echo   INSTALADOR VDO - Veta de Oro
echo ==========================================
echo.

REM Detectar FreeCAD
SET FREECAD_CMD=""

REM Buscar FreeCAD en ubicaciones comunes
IF EXIST "C:\Program Files\FreeCAD\bin\FreeCAD.exe" (
    SET FREECAD_CMD="C:\Program Files\FreeCAD\bin\FreeCAD.exe"
) ELSE IF EXIST "C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe" (
    SET FREECAD_CMD="C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe"
) ELSE IF EXIST "C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe" (
    SET FREECAD_CMD="C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe"
) ELSE IF EXIST "%USERPROFILE%\AppData\Local\FreeCAD\bin\FreeCAD.exe" (
    SET FREECAD_CMD="%USERPROFILE%\AppData\Local\FreeCAD\bin\FreeCAD.exe"
)

IF %FREECAD_CMD%=="" (
    echo ❌ FreeCAD no encontrado en el sistema
    echo.
    echo Opciones:
    echo   1. Instale FreeCAD y vuelva a ejecutar este script
    echo   2. Ejecute manualmente dentro de FreeCAD:
    echo      Macro - Ejecutar - seleccione vdo_install.py
    echo.
    pause
    exit /b 1
)

echo ✅ FreeCAD encontrado: %FREECAD_CMD%
echo.

REM Obtener directorio del script
SET SCRIPT_DIR=%~dp0
SET INSTALL_SCRIPT=%SCRIPT_DIR%vdo_install.py

IF NOT EXIST "%INSTALL_SCRIPT%" (
    echo ❌ No se encontró vdo_install.py en: %SCRIPT_DIR%
    pause
    exit /b 1
)

echo 📦 Ejecutando instalador...
echo    Script: %INSTALL_SCRIPT%
echo.

REM Ejecutar instalador en FreeCAD
%FREECAD_CMD% "%INSTALL_SCRIPT%"

echo.
echo ==========================================
echo   INSTALACIÓN COMPLETADA
echo ==========================================
pause
