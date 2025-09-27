# 数据存储层文档

## TaskRepository 任务存储类

### 主要功能
- 任务持久化存储
- 任务状态更新
- 任务查询

### 核心方法
- `save(task)`: 保存任务实体
  - 参数：Task对象
  - 返回：保存后的Task对象
- `find_by_id(task_id)`: 按ID查询任务
  - 参数：任务ID字符串
  - 返回：Task对象或None

## ResultRepository 结果存储类

### 主要功能
- 执行结果存储
- 性能指标记录
- 产物元数据管理

### 事务管理示例
```python
with transaction():
    task = task_repo.find_by_id("123")
    task.start()
    task_repo.save(task)