@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MetasAvinor - reiniciar Streamlit
echo.
echo === Metas Avinor ===
echo Pasta: %CD%
echo.

echo Versao no disco (arquivo VERSION):
type VERSION
echo.

echo Matando Python/Streamlit desta pasta na porta 8501...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; ^
   Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'streamlit_app.py' -and $_.CommandLine -match 'MetasAvinor' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

timeout /t 2 /nobreak >nul

echo.
echo Subindo Streamlit (nova janela)...
start "MetasAvinor Streamlit" cmd /k "cd /d \"%CD%\" && python -c \"from app.main import APP_VERSION, APP_ROOT; print('Carregando', APP_ROOT, 'versao', APP_VERSION)\" && python -m streamlit run streamlit_app.py --server.port 8501"

echo.
echo Abra http://localhost:8501
echo No topo deve aparecer a versao do arquivo VERSION (ex.: 1.5.2).
echo.
pause
