@echo off
chcp 65001 >nul
title Parar MetasAvinor (porta 8501)
echo.
echo Encerrando TUDO que usa a porta 8501...
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501') do (
    echo Matando PID %%a
    taskkill /F /PID %%a 2>nul
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ('PID ' + $_.OwningProcess); Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo.
echo Processos python com streamlit nesta pasta:
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'streamlit' } | ForEach-Object { Write-Host $_.ProcessId $_.CommandLine; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

timeout /t 1 /nobreak >nul
echo.
netstat -ano | findstr :8501
if errorlevel 1 (
    echo Porta 8501 LIVRE. Pode rodar reiniciar_streamlit.bat
) else (
    echo AINDA ha algo na 8501. Abra o Gerenciador de Tarefas ^> Detalhes ^> finalize python.exe manualmente.
)
echo.
pause
