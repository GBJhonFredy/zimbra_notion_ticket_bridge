REM Desactiva echo para que la consola no imprima cada comando.
@echo off
REM Cambia al directorio donde vive este .bat, sin importar desde donde se ejecuta.
cd /d %~dp0
REM Ejecuta la app con el Python del entorno virtual local.
.\.venv\Scripts\python.exe main.py
REM Mantiene ventana abierta para poder leer errores/salida al finalizar.
pause
