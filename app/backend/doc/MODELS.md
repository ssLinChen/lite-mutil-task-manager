# 数据模型文档

## Task 任务模型

### 类功能
- 表示系统中的核心任务实体
- 管理任务状态机
- 处理任务生命周期事件

### 主要属性
- `task_id`: 任务唯一标识符 (字符串)
- `status`: 当前状态 (枚举值: pending/running/completed/failed)
- `created_at`: 创建时间 (datetime)

### 重要方法
- `start()`: 启动任务
- `cancel()`: 取消任务
- `get_progress()`: 获取任务进度

---

## TaskConfig 配置模型

### 类功能
- 存储任务执行参数
- 验证配置有效性
- 提供默认值

### 配置参数
- `timeout`: 超时时间(秒)
- `retries`: 最大重试次数
- `memory_limit`: 内存限制(MB)

### 示例
```python
config = TaskConfig(
    timeout=300,
    retries=3
)
```

---

## TaskResult 结果模型

### 类功能
- 记录任务执行结果
- 管理输出产物
- 跟踪性能指标

### 数据结构
- `artifacts`: 产物字典 {名称: 产物引用}
- `metrics`: 性能指标 {"duration": 120.5}
- `error`: 错误详情 (如果任务失败)