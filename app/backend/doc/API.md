# API接口文档

## 任务接口

### 创建任务
- 路径：`POST /api/tasks`
- 参数：
  ```json
  {
    "config": {
      "timeout": 300,
      "priority": "high"
    }
  }
  ```
- 返回：创建的任务ID

### 查询任务状态
- 路径：`GET /api/tasks/{task_id}`
- 返回：
  ```json
  {
    "status": "running",
    "progress": 0.65
  }
  ```

## 结果接口

### 获取执行结果
- 路径：`GET /api/results/{task_id}`
- 返回包含：
  - 产出物列表
  - 性能指标
  - 错误信息（如果失败）

### 错误代码
- 400：无效请求
- 404：任务不存在
- 500：服务器错误