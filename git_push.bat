@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo [tutu] Git项目推送脚本 v1.0
echo [tutu] Git Project Push Script v1.0
echo ========================================

:: 设置项目根目录
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%" || (
    echo [ERROR] 无法进入项目目录: %PROJECT_ROOT%
    echo [ERROR] Cannot enter project directory: %PROJECT_ROOT%
    exit /b 1
)

echo [INFO] 项目目录: %PROJECT_ROOT%
echo [INFO] Project directory: %PROJECT_ROOT%

:: 检查Git是否安装
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git未安装或未添加到PATH环境变量
    echo [ERROR] Git is not installed or not in PATH
    echo.
    echo [建议] 请从 https://git-scm.com/downloads 下载并安装Git
    echo [Suggestion] Download Git from https://git-scm.com/downloads
    exit /b 1
)

echo [OK] Git已正确安装
echo [OK] Git is properly installed

:: 检测Git仓库状态
git rev-parse --is-inside-work-tree >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 未检测到Git仓库，执行初始化流程...
    echo [INFO] No Git repository detected, starting initialization...
    call :initialize_repository
) else (
    echo [INFO] 检测到现有Git仓库，执行常规推送...
    echo [INFO] Existing Git repository detected, starting regular push...
    call :regular_push
)

exit /b 0

:initialize_repository
    echo.
    echo ===== 仓库初始化 =====
    echo ===== Repository Initialization =====
    
    :: 创建基础README文件
    if not exist README.md (
        echo # 项目名称 > README.md
        echo 项目描述 >> README.md
        echo. >> README.md
        echo 创建时间: %date% %time% >> README.md
        echo [OK] 创建README.md文件
        echo [OK] Created README.md file
    )
    
    :: 初始化Git仓库
    git init
    if %errorlevel% neq 0 (
        echo [ERROR] Git仓库初始化失败
        echo [ERROR] Git repository initialization failed
        exit /b 1
    )
    echo [OK] Git仓库初始化成功
    echo [OK] Git repository initialized successfully
    
    :: 配置用户信息（如果未配置）
    git config user.name >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] 配置默认用户信息...
        echo [INFO] Configuring default user info...
        git config user.name "Git User"
        git config user.email "user@example.com"
        echo [提示] 请使用以下命令配置您的用户信息：
        echo [Hint] Please configure your user info with:
        echo   git config user.name "您的姓名"
        echo   git config user.email "您的邮箱"
    )
    
    :: 添加文件并提交
    git add .
    git commit -m "初始提交 - 项目初始化 [%date% %time%]"
    if %errorlevel% neq 0 (
        echo [ERROR] 初始提交失败
        echo [ERROR] Initial commit failed
        exit /b 1
    )
    echo [OK] 初始提交完成
    echo [OK] Initial commit completed
    
    :: 获取远程仓库信息
    set /p "REMOTE_URL=请输入远程Git仓库URL（如 git@github.com:username/repo.git）: "
    if "!REMOTE_URL!"=="" (
        echo [INFO] 未提供远程仓库URL，跳过推送
        echo [INFO] No remote URL provided, skipping push
        goto :eof
    )
    
    :: 添加远程仓库
    git remote add origin "!REMOTE_URL!"
    if %errorlevel% neq 0 (
        echo [ERROR] 添加远程仓库失败
        echo [ERROR] Failed to add remote repository
        exit /b 1
    )
    
    :: 首次推送
    echo [INFO] 正在推送到远程仓库...
    echo [INFO] Pushing to remote repository...
    git push -u origin main
    if %errorlevel% neq 0 (
        echo [WARNING] 首次推送失败，尝试推送到master分支...
        echo [WARNING] First push failed, trying master branch...
        git branch -M master
        git push -u origin master
    )
    
    if %errorlevel% equ 0 (
        echo [SUCCESS] 仓库初始化并推送成功！
        echo [SUCCESS] Repository initialized and pushed successfully!
    ) else (
        echo [ERROR] 推送失败，可能原因：
        echo [ERROR] Push failed, possible reasons:
        echo   - 远程仓库URL错误
        echo   - SSH密钥未配置
        echo   - 网络连接问题
        echo   - 远程仓库权限不足
        echo.
        echo [建议] 请检查远程仓库URL和SSH密钥配置
        echo [Suggestion] Check remote URL and SSH key configuration
    )
    
    goto :eof

:regular_push
    echo.
    echo ===== 常规推送 =====
    echo ===== Regular Push =====
    
    :: 获取当前分支
    for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%a"
    echo [INFO] 当前分支: !CURRENT_BRANCH!
    echo [INFO] Current branch: !CURRENT_BRANCH!
    
    :: 检查远程仓库配置
    git remote get-url origin >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] 未配置远程仓库
        echo [ERROR] Remote repository not configured
        echo [建议] 请使用: git remote add origin <url> 配置远程仓库
        echo [Suggestion] Use: git remote add origin <url> to configure remote
        exit /b 1
    )
    
    :: 拉取最新更改（避免冲突）
    echo [INFO] 获取远程最新更改...
    echo [INFO] Fetching latest changes from remote...
    git fetch origin
    
    :: 检查是否有本地更改
    git diff --exit-code --quiet
    if %errorlevel% equ 0 (
        git diff --cached --exit-code --quiet
        if %errorlevel% equ 0 (
            echo [INFO] 没有检测到文件变更
            echo [INFO] No file changes detected
            goto :check_remote
        )
    )
    
    :: 有更改，执行提交
    echo [INFO] 检测到文件变更，执行提交...
    echo [INFO] File changes detected, committing...
    
    git add .
    set "COMMIT_MSG=自动提交 - %date% %time%"
    git commit -m "!COMMIT_MSG!"
    if %errorlevel% neq 0 (
        echo [ERROR] 提交失败
        echo [ERROR] Commit failed
        exit /b 1
    )
    echo [OK] 提交完成
    echo [OK] Commit completed

:check_remote
    :: 检查远程分支状态
    git ls-remote --heads origin !CURRENT_BRANCH! >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] 远程分支不存在，创建新分支...
        echo [INFO] Remote branch doesn't exist, creating new branch...
        git push -u origin !CURRENT_BRANCH!
    ) else (
        :: 推送更改
        echo [INFO] 推送到远程分支...
        echo [INFO] Pushing to remote branch...
        git push origin !CURRENT_BRANCH!
    )
    
    if %errorlevel% equ 0 (
        echo [SUCCESS] 推送成功！
        echo [SUCCESS] Push successful!
        
        :: 显示推送信息
        git log --oneline -3
    ) else (
        echo [ERROR] 推送失败
        echo [ERROR] Push failed
        
        :: 提供冲突解决建议
        echo.
        echo [冲突解决建议]
        echo [Conflict Resolution Suggestions]
        echo 1. 拉取远程更改: git pull origin !CURRENT_BRANCH!
        echo 2. 解决冲突后重新提交
        echo 3. 再次推送: git push origin !CURRENT_BRANCH!
    )
    
    goto :eof

:error_handling
    echo.
    echo ===== 错误处理 =====
    echo ===== Error Handling =====
    echo [ERROR] 脚本执行过程中出现错误
    echo [ERROR] Error occurred during script execution
    echo 错误代码: %errorlevel%
    echo Error code: %errorlevel%
    
    goto :eof

:: 脚本结束
echo.
echo ========================================
echo [tutu] 脚本执行完成
echo [tutu] Script execution completed
echo ========================================
pause