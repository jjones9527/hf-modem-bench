@echo off
cd /d "%USERPROFILE%\hfbench"
"C:\Program Files\Python312\Scripts\hfbench.exe" audio check --snr 20 40 --json levels.json > check.txt 2>&1
echo EXIT %ERRORLEVEL% >> check.txt
