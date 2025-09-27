# 工具模块文档

## 日期时间工具类

### 主要功能
- 时区转换：处理不同时区的时间转换
- 时长格式化：将秒数转换为易读格式（如"2小时30分钟"）
- 时间戳解析：将时间戳转换为本地时间

### 使用示例
```python
from datetime import datetime
from .utils import format_duration

duration = format_duration(3665)  # 返回"1小时1分钟5秒"
```

## 安全工具类

### 主要功能
- 输入消毒：移除危险字符
- 校验和验证：验证文件完整性
- 安全文件操作：防止路径遍历攻击

### 方法说明
- `sanitize_input(text)`：净化用户输入
- `verify_checksum(file_path, expected)`：验证文件校验和
- `safe_file_open(path)`：安全打开文件

## 日志工具类

### 配置参数
- 日志级别：DEBUG/INFO/WARNING/ERROR
- 输出格式：包含时间戳、模块名和日志级别
- 文件轮转：按大小或日期自动分割日志文件

### 示例代码
```python
from .utils import get_logger

logger = get_logger(__name__)
logger.info("任务启动", extra={"task_id": task.id})