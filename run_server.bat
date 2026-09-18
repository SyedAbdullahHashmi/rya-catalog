@echo off
cd /d "%~dp0"

echo === Stopping any stale server on port 5001 ===
python3.14.exe -c "import subprocess; subprocess.run(['taskkill','/F','/IM','python3.14.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)"
timeout /t 2 /nobreak >nul

echo === Starting Catalog Manager on http://127.0.0.1:5001 ===
python3.14.exe catalog_server.py 5001
