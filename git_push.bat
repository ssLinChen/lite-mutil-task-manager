@echo off
:: ==============================================
:: Git Automation Script v5.0 - Professional Edition
:: Created: 2025-09-27
:: Last Modified: 2025-09-27
:: ==============================================

:: Initialize
setlocal enabledelayedexpansion
chcp 65001 >nul
set "SCRIPT_VERSION=5.0"
set "CONFIG_FILE=gitConfig.json"
set "LOG_FILE=git_operations.log"
set "PROJECT_ROOT=%~dp0"

:: Main Execution Flow
call :main %*

:: ==============================================
:: Core Modules
:: ==============================================

:main
    call :log "===== Script Start ====="
    call :load_config || goto :error_handling
    call :verify_environment || goto :error_handling
    call :execute_git_operations || goto :error_handling
    goto :success

:load_config
    call :log "Loading configuration from %CONFIG_FILE%"
    
    if not exist "%CONFIG_FILE%" (
        call :log "Error: Config file not found"
        exit /b 1
    )

    :: Parse configuration
    for /f "tokens=2 delims=:," %%i in ('findstr "\"url\"" %CONFIG_FILE% ^| findstr "\"remote\""') do (
        set "REMOTE_URL=%%i"
        set "REMOTE_URL=!REMOTE_URL:"=!"
        set "REMOTE_URL=!REMOTE_URL: =!"
    )

    if "!REMOTE_URL!"=="" (
        call :log "Error: Missing remote URL in config"
        exit /b 1
    )
    exit /b 0

:verify_environment
    call :log "Verifying Git installation"
    git --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :log "Error: Git not installed"
        exit /b 1
    )
    exit /b 0

:execute_git_operations
    call :log "Checking repository status"
    git rev-parse --is-inside-work-tree >nul 2>&1
    if %errorlevel% equ 0 (
        call :regular_workflow
    ) else (
        call :initialize_repository
    )
    exit /b %errorlevel%

:initialize_repository
    call :log "Initializing new repository"
    
    :: Initialize Git
    git init || (
        call :log "Error: Failed to initialize repository"
        exit /b 1
    )

    :: Configure remote
    git remote add origin "!REMOTE_URL!" || (
        call :log "Error: Failed to add remote"
        exit /b 1
    )

    :: Initial commit
    git add . || (
        call :log "Error: Failed to stage files"
        exit /b 1
    )
    
    git commit -m "Initial commit" || (
        call :log "Error: Initial commit failed"
        exit /b 1
    )

    :: First push
    git push -u origin main || (
        call :log "Error: First push failed"
        exit /b 1
    )
    exit /b 0

:regular_workflow
    call :log "Starting regular workflow"
    
    :: Get current branch
    for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%a"
    call :log "Current branch: !CURRENT_BRANCH!"

    :: Pull latest changes
    git pull origin !CURRENT_BRANCH! || (
        call :log "Warning: Pull failed, attempting to continue"
    )

    :: Stage and commit
    git add . || (
        call :log "Error: Failed to stage changes"
        exit /b 1
    )
    
    git commit -m "Auto commit: %date% %time%" || (
        call :log "Warning: No changes to commit"
        exit /b 0
    )

    :: Push changes
    git push origin !CURRENT_BRANCH! || (
        call :log "Error: Push failed"
        exit /b 1
    )
    exit /b 0

:error_handling
    call :log "Script execution failed with error code %errorlevel%"
    echo.
    echo [ERROR] Operation failed
    echo [ADVICE] Check log file for details: %LOG_FILE%
    goto :end

:success
    call :log "Script completed successfully"
    echo.
    echo [SUCCESS] All operations completed
    goto :end

:log
    echo [%date% %time%] %~1 >> "%LOG_FILE%"
    exit /b 0

:end
    call :log "===== Script End ====="
    pause
    exit /b 0