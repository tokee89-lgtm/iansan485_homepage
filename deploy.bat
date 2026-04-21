@echo off
echo [Ansan Branch Website Deployment]
echo.

:: Check Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed.
    echo Please install it from https://git-scm.com/
    pause
    exit /b
)

echo 1. Configuring Git...
git config --global user.email "ansan485@example.com"
git config --global user.name "Ansan Branch Admin"

echo 2. Adding and Committing changes...
git add .
git commit -m "Manual update from Local" >nul 2>nul

echo 3. Syncing with remote...
git pull --rebase origin main

echo 4. Pushing to GitHub...
git branch -M main
git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to push. Check your connection or login.
) else (
    echo.
    echo SUCCESS! 
    echo Deployment will be live in 1-2 minutes.
)

echo.
pause
