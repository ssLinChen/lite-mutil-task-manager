@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo [tutu] 正在执行GitHub同步脚本...
echo [tutu] 当前时间: %date% %time%

:: 设置工程根目录路径
set "REPO_PATH=%~dp0"
cd /d %REPO_PATH% || (
    echo [错误] 无法进入项目目录
    exit /b 1
)

:: 检测Git仓库状态
git rev-parse --is-inside-work-tree >nul 2>&1
if %errorlevel% neq 0 (
    echo [tutu] 未检测到Git仓库，执行初始化流程...
    
    :: 创建README文件
    echo # mutilTask > README.md
    echo 项目同步时间: %date% %time% >> README.md
    
    :: 初始化Git仓库
    git init
    if %errorlevel% neq 0 (
        echo [ERROR] Git initialization failed. Please ensure Git is properly installed.
        echo [ERROR] 建议运行: git --version 检查Git安装状态
        exit /b 1
    )
    
    :: 添加README文件
    git add README.md
    git commit -m "first commit"
    git branch -M main
    
    :: 添加远程仓库
    git remote add origin git@github.com:ssLinChen/lite-mutil-task-manager.git
    
    :: 首次推送
    git push -u origin main
    if %errorlevel% equ 0 (
        echo [tutu] Repository initialized successfully! First commit completed.
        echo [tutu] 仓库初始化成功！已完成首次提交
    ) else (
        echo [ERROR] Initial push failed. Possible reasons:
        echo 1. SSH key not configured
        echo 2. Remote repository already has content
        echo 3. Network connection issue
        echo.
        echo Please run: ssh -T git@github.com to test SSH connection
        echo 请运行: ssh -T git@github.com 测试SSH连接
        exit /b 1
    )
) else (
    echo [tutu] Existing Git repository detected. Starting regular sync...
    echo [tutu] 检测到现有Git仓库，执行常规同步...
    
    :: 获取当前分支
    for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%a"
    echo [tutu] Current branch: !CURRENT_BRANCH!
    echo [tutu] 当前分支: !CURRENT_BRANCH!
    
    :: 检查是否有未提交的更改
    git diff --exit-code --quiet
    if %errorlevel% neq 0 (
        :: 有更改，执行提交
        git add .
        set "COMMIT_MSG=Auto-commit by tutu on %date% %time%"
        git commit -m "%COMMIT_MSG%"
        
        :: 推送到远程仓库
        git push origin !CURRENT_BRANCH!
        if %errorlevel% equ 0 (
            echo [tutu] Sync successful! Project updated to GitHub.
            echo [tutu] 同步成功！工程已更新至GitHub
        ) else (
            echo [ERROR] Push failed. Please check:
            echo 1. Remote repository conflicts
            echo 2. Network connection
            echo 3. Permission settings
            echo.
            echo Recommended: git pull to get latest changes
            echo 建议先执行: git pull 获取最新更改
            exit /b 1
        )
    ) else (
        echo [tutu] No file changes detected. Sync not required.
        echo [tutu] 没有检测到文件变更，无需同步
    )
)

echo [tutu] 操作完成
exit /b 0