@echo off
REM One-click build script for LapDoctor.exe
REM Double-click this file (or run it from a terminal) inside the mp/ folder.

echo === Installing build dependencies ===
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Building LapDoctor.exe ===
pyinstaller --noconfirm LapDoctor.spec

echo.
if exist dist\LapDoctor\LapDoctor.exe (
    echo Build succeeded! Your app is at: dist\LapDoctor\LapDoctor.exe
) else (
    echo Build finished, but LapDoctor.exe was not found -- check the log above for errors.
)
pause
