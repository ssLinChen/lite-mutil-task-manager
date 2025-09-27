# GitHub 同步工具使用指南

## 功能介绍

此脚本实现了项目代码一键同步到 GitHub 仓库的功能，具有以下特点：

- **智能检测**：自动判断是否已初始化 Git 仓库
- **自动初始化**：首次运行时自动创建 README 并设置远程仓库
- **增量同步**：检测文件变更并智能提交
- **错误处理**：提供详细的错误提示和解决方案
- **分支感知**：自动识别当前分支并推送到对应远程分支

## 使用前提

1. 已安装 Git 客户端
2. 已配置 SSH 密钥并添加到 GitHub 账户
3. 已在 GitHub 创建名为 `mutilTask` 的仓库

## 使用方法

### 首次使用

1. 双击运行 `sync_to_github.bat`
2. 脚本将自动：
   - 创建 README.md 文件
   - 初始化 Git 仓库
   - 设置远程仓库为 `git@github.com:ssLinChen/mutilTask.git`
   - 推送初始提交到 GitHub

### 日常同步

1. 完成代码修改后，双击运行 `sync_to_github.bat`
2. 脚本将自动：
   - 检测文件变更
   - 提交所有更改（提交信息包含时间戳）
   - 推送到远程仓库

## 常见问题

### SSH 连接失败

如遇到 SSH 连接问题，请执行以下命令测试连接：

```bash
ssh -T git@github.com
```

正常情况下应显示：`Hi ssLinChen! You've successfully authenticated...`

### 推送冲突

如遇到推送冲突，请先拉取最新代码：

```bash
git pull origin main
```

然后重新运行同步脚本。

### 仓库已存在

如果远程仓库已有内容，首次推送可能失败。解决方法：

```bash
git pull --rebase origin main
```

然后重新运行同步脚本。

## 技术支持

如有问题，请联系 tutu（腾讯首席技术专家）。

---

*文档创建于 2025-09-27*