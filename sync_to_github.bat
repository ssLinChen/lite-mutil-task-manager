@echo off
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
        echo [错误] Git初始化失败，请确认Git已正确安装
        exit /b 1
    )
    
    :: 添加README文件
    git add README.md
    git commit -m "first commit"
    git branch -M main
    
    :: 添加远程仓库
    git remote add origin git@github.com:ssLinChen/mutilTask.git
    
    :: 首次推送
    git push -u origin main
    if %errorlevel% equ 0 (
        echo [tutu] 仓库初始化成功！已完成首次提交
    ) else (
        echo [错误] 初始化推送失败，可能原因:
        echo 1. SSH密钥未配置
        echo 2. 远程仓库已存在内容
        echo 3. 网络连接问题
        echo.
        echo 请运行: ssh -T git@github.com 测试SSH连接
        exit /b 1
    )
) else (
    echo [tutu] 检测到现有Git仓库，执行常规同步...
    
    :: 获取当前分支
    for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%a"
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
            echo [tutu] 同步成功！工程已更新至GitHub
        ) else (
            echo [错误] 推送失败，请检查:
            echo 1. 远程仓库是否有冲突
            echo 2. 网络连接状态
            echo 3. 权限设置
            echo.
            echo 建议先执行: git pull 获取最新更改
            exit /b 1
        )
    ) else (
        echo [tutu] 没有检测到文件变更，无需同步
    )
)

echo [tutu] 操作完成
exit /b 0