@echo off
setlocal enabledelayedexpansion

:: Set console title
title Git Upload Tool
color 0A

echo.
echo ========================================
echo           Git Upload Tool
echo ========================================
echo.

:: Check if commit message parameter is provided
if "%~1"=="" (
    echo [ERROR] Please provide commit message!
    echo.
    echo Usage: upload.bat "your commit message"
    echo Example: upload.bat "Fixed login bug"
    echo.
    pause
    exit /b 1
)

:: Get commit message
set "commit_message=%~1"
echo [INFO] Commit message: %commit_message%
echo.

:: Check if we are in a Git repository
git status >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Current directory is not a Git repository!
    echo Please run this script in Git project root directory.
    echo.
    pause
    exit /b 1
)

:: Show current status
echo [INFO] Current Git status:
git status --short
echo.

:: Step 1: Add files
echo [STEP 1] Adding files...
git add .
if errorlevel 1 (
    echo [ERROR] Failed to add files!
    pause
    exit /b 1
)
echo [SUCCESS] Files added successfully!
echo.

:: Step 2: Commit changes
echo [STEP 2] Committing changes...
git commit -m "%commit_message%"
if errorlevel 1 (
    echo [ERROR] Commit failed! Maybe no changes to commit.
    pause
    exit /b 1
)
echo [SUCCESS] Commit successful!
echo.

:: Step 3: Push to remote repository
echo [STEP 3] Pushing to remote repository...
git push
if errorlevel 1 (
    echo [ERROR] Push failed! Please check network and remote repository.
    echo.
    echo Possible solutions:
    echo 1. Check network connection
    echo 2. Verify remote repository URL
    echo 3. Check Git credentials
    echo 4. Try manual: git push
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Upload completed successfully!
echo ========================================
echo.
echo Operation summary:
echo    - Added all changed files
echo    - Commit message: %commit_message%
echo    - Successfully pushed to remote repository
echo.

:: Show recent commit history
echo Recent commits:
git log --oneline -5
echo.

echo Press any key to exit...
pause >nul
