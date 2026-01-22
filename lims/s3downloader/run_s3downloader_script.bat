@echo off
REM run_s3_downloader.bat
REM This script runs the S3 Downloader Python application.

REM Optional: Navigate to the script's directory.
REM This makes sure relative paths (like for last_download_info.json) work correctly.
cd /d "%~dp0"

REM --- Option 1: Simple execution (assumes 'python' is in your PATH) ---
REM python s3_downloader.py

REM --- Option 2: Full path to python.exe (more robust) ---
REM Replace "C:\path\to\your\python.exe" with the actual path to your Python interpreter.
REM You can find this by typing 'where python' in Command Prompt.
"C:\Users\vijay\AppData\Local\Programs\Python\Python38\python.exe" "s3_downloader.py"


REM --- Keep the console open after execution (useful for debugging) ---
REM If you want the console window to stay open after the script finishes (e.g., to see logs if it crashes), uncomment the line below.
REM For continuous polling scripts, you typically want it to run silently in the background.
REM pause

REM End of script
exit /b 0