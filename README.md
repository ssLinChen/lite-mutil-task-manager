# mutilTask

多任务管理系统 - 基于Python的高效任务调度和执行框架

## 项目简介

mutilTask是一个现代化的多任务管理系统，专注于提供高效、可靠的任务调度和执行能力。项目采用模块化设计，支持多种任务类型和调度策略。

## 功能特性

- **多任务并行执行**：支持同时运行多个独立任务
- **智能任务调度**：基于优先级的动态调度算法
- **实时状态监控**：提供任务执行状态的实时监控
- **错误恢复机制**：自动重试和错误处理机制
- **可扩展架构**：易于添加新的任务类型和调度策略

## 技术栈

- **后端框架**：Python 3.8+
- **数据库**：SQLite/PostgreSQL
- **任务队列**：Celery/RQ
- **Web界面**：Flask/FastAPI

## 快速开始

### 环境要求

- Python 3.8 或更高版本
- Git

### 安装步骤

1. 克隆项目：
```bash
git clone https://github.com/ssLinChen/mutilTask.git
cd mutilTask
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行示例：
```bash
python examples/demo.py
```

### 基本使用

```python
from app.services.task_manager import TaskManager

# 创建任务管理器
task_manager = TaskManager()

# 添加任务
task_manager.add_task("data_processing", priority=1)
task_manager.add_task("report_generation", priority=2)

# 启动任务执行
task_manager.start()
```

## 项目结构

```
mutilTask/
├── app/                    # 应用核心代码
│   ├── backend/           # 后端API和服务
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务层
│   └── utils/             # 工具函数
├── docs/                  # 文档
├── examples/              # 使用示例
├── scripts/               # 部署脚本
└── test_reports/          # 测试报告
```

## GitHub同步

项目提供一键同步脚本，方便代码管理：

### 使用方法

1. 首次使用：双击运行 `sync_to_github.bat`
2. 日常同步：修改代码后运行同步脚本

### 同步脚本功能

- 自动检测Git仓库状态
- 智能提交代码变更
- 推送到远程GitHub仓库
- 详细的错误提示和解决方案

## 贡献指南

我们欢迎社区贡献！请参考以下步骤：

1. Fork本项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 技术支持

如有问题或建议，请通过以下方式联系：

- 创建Issue：GitHub Issues
- 邮件联系：项目维护者

---

*文档最后更新：2025-09-27*
*维护者：tutu（腾讯首席技术专家）*