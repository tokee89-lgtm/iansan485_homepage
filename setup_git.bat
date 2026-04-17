@echo off
echo [GitHub Setup]
echo.

:: Init Git
git init

:: Link to GitHub
git remote set-url origin https://github.com/kappdansan/iansan485_homepage.git >nul 2>nul
if %errorlevel% neq 0 (
    git remote add origin https://github.com/kappdansan/iansan485_homepage.git
)

:: Fetch from GitHub
echo Linking to server...
git branch -M main >nul 2>nul
git fetch origin

echo.
echo SUCCESS! Now you can run 'deploy.bat'
pause
