# lite-mutil-task-manager
一款轻量级多任务管理系统
>>>>>>> 152f03afb5cead20ce9c07c5af159109759d0abd
=======
# lite-mutil-task-manager

🚀 轻量级多任务管理系统 - 基于Python的高效任务调度和执行框架

## 项目简介

`lite-mutil-task-manager` 是一个现代化的轻量级多任务管理系统，专注于提供高效、可靠的任务调度和执行能力。项目采用模块化设计，支持多种任务类型和基于优先级的智能调度策略。

## ✨ 核心特性

- **🎯 智能优先级调度** - 支持CRITICAL/HIGH/NORMAL/LOW四级优先级
- **⚡ 多线程并发执行** - 可配置的线程池管理
- **📊 实时状态监控** - 丰富的任务状态跟踪和进度显示
- **🛡️ 健壮的错误处理** - 自动重试和异常恢复机制
- **🎨 可视化界面** - 基于Rich库的实时任务监控面板
- **🔧 配置化任务** - 支持参数验证和约束检查的任务配置系统
- **📡 事件驱动架构** - 基于发布-订阅模式的状态变更通知

## 🛠️ 技术栈

- **编程语言**: Python 3.8+
- **数据验证**: Pydantic v2
- **并发处理**: ThreadPoolExecutor
- **可视化**: Rich库
- **任务队列**: 基于heapq的优先级队列
- **事件系统**: 自定义事件总线

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- Git

### 安装步骤

1. 克隆项目：
```bash
git clone https://github.com/ssLinChen/lite-mutil-task-manager.git
cd lite-mutil-task-manager
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行示例：
```bash
python examples/task_queue_mvp.py
```

### 基本使用

```python
from app.backend.models.core.task import Task, TaskPriority
from app.backend.models.queue.task_queue import TaskQueue

# 创建任务队列（最大2个并发工作线程）
queue = TaskQueue(max_workers=2)

# 创建任务
task1 = Task(title="高优先级任务", priority=TaskPriority.HIGH)
task2 = Task(title="普通任务", priority=TaskPriority.NORMAL)

# 添加任务到队列
queue.enqueue(task1)
queue.enqueue(task2)

# 任务会自动开始执行
```

## 📁 项目结构

```
lite-mutil-task-manager/
├── app/                           # 应用核心代码
│   ├── backend/
│   │   ├── models/
│   │   │   ├── core/             # 核心数据模型
│   │   │   │   ├── task.py       # 任务模型（状态机）
│   │   │   │   ├── task_config.py # 任务配置系统
│   │   │   │   └── ...
│   │   │   └── queue/            # 队列相关模型
│   │   │       └── task_queue.py # 优先级任务队列
│   │   └── utils/                # 工具类
│   │       ├── event_bus.py      # 事件总线
│   │       └── task_ui.py        # 任务可视化界面
│   └── tests/                    # 单元测试
├── examples/                     # 使用示例
│   └── task_queue_mvp.py        # MVP演示程序
├── github_sync.py               # GitHub同步脚本
├── git_config.json              # Git配置
└── README.md                    # 项目文档
```

## 🔧 核心功能详解

### 任务状态管理

系统支持6种任务状态：
- **PENDING** - 等待入队
- **QUEUED** - 已入队等待执行
- **RUNNING** - 执行中
- **COMPLETED** - 已完成
- **FAILED** - 执行失败
- **CANCELLED** - 已取消

### 优先级调度

4级优先级系统：
- **CRITICAL (0)** - 最高优先级
- **HIGH (1)** - 高优先级
- **NORMAL (2)** - 普通优先级（默认）
- **LOW (3)** - 低优先级

### 配置化任务

支持参数验证的任务配置：

```python
from app.backend.models.core.task_config import TaskConfig, ParamDefinition, ParamType

# 创建任务配置
config = TaskConfig(name="数据处理任务")
config.add_param(ParamDefinition(
    name="execution_time",
    type=ParamType.INTEGER,
    description="执行时间(秒)",
    default=10,
    constraints={"min": 1, "max": 300}
))
```

## 📊 示例演示

运行 `examples/task_queue_mvp.py` 查看完整功能演示：

```bash
python examples/task_queue_mvp.py
```

演示内容包括：
- 传统任务和配置化任务的对比
- 优先级调度效果展示
- 实时进度监控面板
- 参数验证错误处理

## 🔄 GitHub同步

项目提供智能同步脚本：

### 使用方法

1. 配置远程仓库信息（编辑 `git_config.json`）
2. 运行同步脚本：
```bash
python github_sync.py
```

### 同步功能

- ✅ 自动检测Git仓库状态
- ✅ 智能提交代码变更
- ✅ 处理推送冲突（支持强制推送）
- ✅ 详细的错误诊断和重试机制

## 🧪 测试

运行测试套件确保功能正常：

```bash
python -m pytest app/tests/
```

## 🤝 贡献指南

我们欢迎社区贡献！请参考以下步骤：

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 📞 技术支持

如有问题或建议，请通过以下方式联系：

- 🐛 提交Issue: [GitHub Issues](https://github.com/ssLinChen/lite-mutil-task-manager/issues)
- 💬 讨论区: [GitHub Discussions](https://github.com/ssLinChen/lite-mutil-task-manager/discussions)

---

*文档最后更新：2025-09-27*
=======
# lite-mutil-task-manager
一款轻量级多任务管理系统
>>>>>>> 152f03afb5cead20ce9c07c5af159109759d0abd
