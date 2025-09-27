@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ========================================
:: Git Push Script v4.0 - Minimalist Version
:: ========================================

:: Init
set "PROJECT_ROOT=%~dp0"
set "CONFIG_FILE=gitConfig.json"

:: Main Flow
call :load_config || goto :error
call :check_git || goto :error
call :git_operation || goto :error

goto :end

:: ========================================
:: Core Functions
:: ========================================

:load_config
    if not exist "%CONFIG_FILE%" (
        echo [错误] 缺少配置文件: %CONFIG_FILE%
        exit /b 1
    )

    for /f "tokens=2 delims=:," %%i in ('findstr "\"url\"" %CONFIG_FILE% ^| findstr "\"remote\""') do (
        set "REMOTE_URL=%%i"
        set "REMOTE_URL=!REMOTE_URL:"=!"
        set "REMOTE_URL=!REMOTE_URL: =!"
    )

    if "!REMOTE_URL!"=="" (
        echo [错误] 配置中未找到远程仓库URL
        exit /b 1
    )
    exit /b 0

:check_git
    git --version >nul 2>&1 || (
        echo [错误] Git未安装或不在PATH中
        exit /b 1
    )
    exit /b 0

:git_operation
    git rev-parse --is-inside-work-tree >nul 2>&1
    if %errorlevel% equ 0 (
        call :push_changes
    ) else (
        call :init_repo
    )
    exit /b %errorlevel%

:init_repo
    echo [信息] 初始化新仓库...
    git init || exit /b 1
    git remote add origin "!REMOTE_URL!" || exit /b 1
    git add .
    git commit -m "初始提交" || exit /b 1
    git push -u origin main || exit /b 1
    exit /b 0

:push_changes
    echo [信息] 执行推送操作...
    git add .
    git commit -m "自动提交: %date% %time%" || exit /b 1
    git push || exit /b 1
    exit /b 0

:error
    echo.
    echo [错误] 操作失败 (错误码: %errorlevel%)
    echo [建议] 检查网络连接和仓库权限

:end
    pause
    exit /b 0