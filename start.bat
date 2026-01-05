@echo off
echo ===================================================
echo Instagram Bot Starting...
echo ===================================================
echo.
echo Checking requirements...
py -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Fallback to pip...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Requirement installation failed.
        pause
        exit /b
    )
)
echo.
echo Running bot...
python main.py
if %errorlevel% neq 0 (
    echo Bot exited with an error.
    pause
    exit /b
)
echo.
echo ===================================================
echo Bot finished or closed.
echo ===================================================
pause
