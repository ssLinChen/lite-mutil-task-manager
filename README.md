# lite-mutil-task-manager

🚀 轻量级多任务管理系统 - 基于Python的高效任务调度和执行框架

## 项目简介

`lite-mutil-task-manager` 是一个现代化的轻量级多任务管理系统，专注于提供高效、可靠的任务调度和执行能力。项目采用模块化设计和事件驱动架构，支持多种任务类型和基于优先级的智能调度策略。

## ✨ 核心特性

- **🎯 智能优先级调度** - 支持CRITICAL/HIGH/NORMAL/LOW四级优先级（数值越小优先级越高）
- **⚡ 多线程并发执行** - 基于ThreadPoolExecutor的可配置线程池
- **📊 实时状态监控** - 完整的任务生命周期跟踪和进度显示
- **📝 详细结果记录** - 全面的任务执行结果和产物管理
- **🛡️ 健壮的错误处理** - 自动重试机制和结构化错误记录
- **🔧 配置化任务** - 支持参数验证和约束检查的任务配置系统
- **📡 事件驱动架构** - 基于发布-订阅模式的状态变更通知
- **🔒 线程安全设计** - 关键操作使用锁机制保证线程安全
- **📍 队列位置服务** - 准确的队列位置显示和实时更新

## 🛠️ 技术栈

- **编程语言**: Python 3.8+
- **数据验证**: Pydantic v2
- **并发处理**: ThreadPoolExecutor
- **任务队列**: 基于heapq的优先级队列
- **事件系统**: 自定义事件总线
- **线程同步**: threading.Lock
- **结果管理**: 结构化结果存储和产物引用
- **位置服务**: QueuePositionService智能缓存机制

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本

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
from mutil_task.core.task import Task, TaskPriority
from mutil_task.queue.task_queue import TaskQueue
from mutil_task.core.task_result import TaskResult

# 创建任务队列（最大2个并发工作线程）
queue = TaskQueue(max_workers=2)

# 创建任务
task1 = Task(title="高优先级任务", priority=TaskPriority.HIGH)
task2 = Task(title="普通优先级任务", priority=TaskPriority.NORMAL)

# 添加任务到队列
queue.enqueue(task1)
queue.enqueue(task2)

# 获取准确的队列位置信息
position, total = queue.get_task_position(task1.id)
print(f"任务在队列中的位置: {position}/{total}")

# 获取任务结果
result = TaskResult(
    task_id=task1.id,
    execution_id="exec_001",
    status="completed"
)
result.add_metric("duration", 120.5)
print(f"任务完成，耗时: {result.metrics['duration']}秒")
```

## 📁 项目结构

```
lite-mutil-task-manager/
├── mutil_task/                    # 核心代码包
│   ├── core/                     # 核心数据模型
│   │   ├── task.py               # 任务模型（状态机实现）
│   │   ├── task_config.py        # 配置化任务参数管理
│   │   └── task_result.py        # 任务结果管理
│   ├── queue/                    # 队列管理
│   │   └── task_queue.py         # 优先级任务队列
│   └── utils/                    # 工具类
│       ├── event_bus.py          # 事件总线
│       ├── task_ui.py            # 任务可视化界面
│       └── queue_position_service.py  # 队列位置服务
├── tests/                        # 单元测试
│   ├── test_task_config.py       # 任务配置测试
│   ├── test_task_model.py        # 任务模型测试
│   ├── test_task_queue.py        # 任务队列测试
│   ├── test_task_result.py       # 任务结果测试
│   └── test_task_serialization_unittest.py  # 序列化测试
├── examples/                     # 使用示例
│   └── task_queue_mvp.py         # MVP演示程序
└── README.md                     # 项目文档
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

4级优先级系统（数值越小优先级越高）：
- **CRITICAL (0)** - 最高优先级
- **HIGH (1)** - 高优先级
- **NORMAL (2)** - 普通优先级（默认）
- **LOW (3)** - 低优先级

### 队列位置服务

系统提供准确的队列位置显示功能：

```python
from mutil_task.queue.task_queue import TaskQueue

# 创建队列
queue = TaskQueue(max_workers=2)

# 添加多个任务
tasks = []
for i in range(5):
    task = Task(title=f"任务{i+1}", priority=TaskPriority.NORMAL)
    queue.enqueue(task)
    tasks.append(task)

# 获取每个任务的准确位置
for task in tasks:
    position, total = queue.get_task_position(task.id)
    print(f"任务 {task.title}: 排队中({position}/{total})")
```

**技术特点**：
- **批量计算优化**：一次O(n)遍历服务所有显示需求
- **智能缓存机制**：200ms TTL平衡性能与准确性
- **线程安全设计**：Lock保护下的原子操作
- **实时更新**：队列变化时自动失效缓存

### 任务结果管理

```python
from mutil_task.core.task_result import TaskResult, ArtifactRef, ArtifactStorageType

# 创建任务结果
result = TaskResult(
    task_id="task_123",
    execution_id="exec_001",
    status="completed"
)

# 记录性能指标
result.add_metric("duration", 120.5)
result.add_metric("memory_usage", 256)

# 添加输出产物
artifact = ArtifactRef(
    storage_type=ArtifactStorageType.LOCAL,
    uri="/tmp/output.log",
    checksum="a"*64  # SHA-256
)
result.add_artifact("log", artifact)

# 记录错误信息
if failed:
    result.set_error(
        error_type="Validation",
        message="Invalid input data",
        stack_trace="Traceback..."
    )
```

### 配置化任务

支持参数验证的任务配置：

```python
from mutil_task.core.task_config import TaskConfig, ParamDefinition, ParamType

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

### 事件驱动架构

系统采用发布-订阅模式进行组件间通信：

```python
from mutil_task.utils.event_bus import EventBus, TaskEventType

# 订阅任务状态变更事件
def on_status_change(event_data):
    task = event_data['task']
    old_status = event_data['old_status']
    new_status = event_data['new_status']
    print(f"任务状态变更: {old_status.name} -> {new_status.name}")

EventBus.subscribe(TaskEventType.STATUS_CHANGED, on_status_change)
```

## 🧪 测试

运行测试套件确保功能正常：

```bash
python -m unittest discover tests
```

测试覆盖了以下方面：
- 任务模型和状态转换
- 任务配置和参数验证
- 任务队列和优先级调度
- 任务结果处理和产物管理
- 序列化和反序列化

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

*文档最后更新：2025-09-29*