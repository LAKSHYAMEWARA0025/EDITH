@echo off
REM Local setup script for EDITH Drone Environment (Windows)

echo ==========================================
echo EDITH Drone Environment - Local Setup
echo ==========================================
echo.

REM Check Python version
echo [1/6] Checking Python version...
python --version
if errorlevel 1 (
    echo X Python not found
    pause
    exit /b 1
)
echo.

REM Create virtual environment
echo [2/6] Creating virtual environment...
if exist venv (
    echo ! venv already exists
) else (
    python -m venv venv
    echo + Virtual environment created
)
echo.

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo + Activated
echo.

REM Upgrade pip
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip
echo + Pip upgraded
echo.

REM Install pybullet from extracted files
echo [5/6] Installing PyBullet from extracted files...
echo Note: The wheel was extracted. Installing directly from PyPI instead...
python -m pip install pybullet==3.2.7
if errorlevel 1 (
    echo ! PyBullet installation failed
    echo   This is expected - it needs C++ compiler
    echo   Ask your friend for the actual .whl file (not extracted)
    echo.
    echo   Alternative: Continue anyway, other packages will install
    pause
)
echo.

REM Install other requirements
echo [6/6] Installing other dependencies...
pip install -r requirements.txt
echo + Dependencies installed
echo.

echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Install gym-pybullet-drones:
echo      git clone https://github.com/utiasDSL/gym-pybullet-drones.git
echo      cd gym-pybullet-drones
echo      git checkout main
echo      pip install -e .
echo      cd ..
echo.
echo   2. Test GUI mode:
echo      python test_gui.py
echo.
echo ==========================================
pause
