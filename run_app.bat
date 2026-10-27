@echo off
setlocal
cd /d "%~dp0"
echo.
echo ================================================
echo    DISTRIBUTION STUDIO - STARTING LOCAL APP
echo ================================================
echo.
py -c "import pandas, matplotlib" >nul 2>&1
if errorlevel 1 (
  echo Installing the required Python libraries...
  py -m pip install --upgrade pip
  if errorlevel 1 goto install_error
  py -m pip install -r requirements.txt
  if errorlevel 1 goto install_error
)
echo.
echo Your browser address is: http://127.0.0.1:8000
echo Keep this window open while using the app.
echo Press Ctrl+C here to stop the app.
echo.
py server.py
if errorlevel 1 (
  echo.
  echo The server stopped with an error. Read the message above.
  pause
)
exit /b 0
:install_error
echo.
echo Could not install Python packages automatically.
echo Please check your internet connection and run: py -m pip install -r requirements.txt
pause
exit /b 1
