"""
任务模型定义 (Python 3.13.7)

特性：
    - 使用Python 3.13.7语法
    - 强类型状态管理(使用TaskStatus枚举)
    - 自动生成UUID
    - 记录创建/更新时间
    - 支持Pydantic序列化(model_dump/model_validate)
    - 严格的状态转移验证
    - 输入验证
"""

from enum import Enum, auto
import datetime
import uuid
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, validator, model_validator

class TaskStatus(Enum):
    """
    任务状态枚举 (Python 3.13.7)
    
    状态选项:
        PENDING - 待处理
        QUEUED - 已排队
        RUNNING - 运行中
        COMPLETED - 已完成
        FAILED - 已失败
        CANCELLED - 已取消
    """
    PENDING = auto()
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

    @classmethod
    def from_string(cls, status_str: str) -> 'TaskStatus':
        """从字符串转换为枚举值 (Python 3.13.7)"""
        try:
            return cls[status_str.upper()]
        except KeyError:
            return cls.PENDING
            
    @classmethod  
    def to_string(cls, status: 'TaskStatus') -> str:  
        """将枚举值转换为小写字符串 (Python 3.13.7)"""
        return status.name.lower()

class Task(BaseModel):
    """
    任务模型 (Python 3.13.7)
    """
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        json_encoders={
            datetime.datetime: lambda dt: dt.isoformat()
        },
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "title": "示例任务",
                "description": "这是一个示例任务",
                "status": "pending",
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00"
            }
        }
    )
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        index=True,
        description="任务唯一ID，自动生成"
    )
    title: str = Field(..., max_length=100)
    description: str = Field("", max_length=500)
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        index=True,
        description="任务状态，用于快速查询"
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="创建时间",
        frozen=True
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="更新时间（修改时自动更新）"
    )

    def __setattr__(self, name: str, value: Any) -> None:
        """重写属性设置方法以自动更新时间戳和验证状态"""
        if name == 'status':
            current_status = getattr(self, 'status', None)
            
            # 转换输入值为枚举
            if isinstance(value, str):
                try:
                    value = TaskStatus[value.upper()]
                except KeyError:
                    raise ValueError(f"Invalid status: {value}")
            elif isinstance(value, int) and value in [e.value for e in TaskStatus]:
                value = TaskStatus(value)
            elif value not in TaskStatus:
                raise ValueError(f"Invalid status: {value}")

            # 验证状态转移
            if current_status is not None:
                self._validate_status_transition(current_status, value)
                
            # 记录状态变更历史
            if hasattr(self, 'status_history'):
                self.status_history.append({
                    'from_status': current_status.name if current_status else None,
                    'to_status': value.name,
                    'timestamp': datetime.datetime.now(datetime.timezone.utc)
                })
                
        if name in {'title', 'description', 'status'}:
            object.__setattr__(self, 'updated_at', datetime.datetime.now(datetime.timezone.utc))
        super().__setattr__(name, value)

    def _validate_status_transition(self, current: TaskStatus, new: TaskStatus) -> None:
        """验证状态转移是否合法"""
        # 确保current和new都是枚举对象
        if isinstance(current, int):
            current = TaskStatus(current)
        if isinstance(new, int):
            new = TaskStatus(new)

        # 终态不能改变（FAILED允许重试）
        if current == TaskStatus.COMPLETED:
            raise ValueError(f"Cannot change status from {current.name}")

        # 状态转移规则
        allowed_transitions = {
            TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
            TaskStatus.FAILED: {TaskStatus.QUEUED},  # 允许重试失败任务
            TaskStatus.CANCELLED: set()  # 取消后不能改变状态
        }

        if new not in allowed_transitions.get(current, set()):
            raise ValueError(f"Invalid status transition: {current.name} -> {new.name}")

    def cancel(self) -> None:
        """取消任务"""
        self.status = TaskStatus.CANCELLED

    def retry_failed_task(self) -> None:
        """重试失败的任务"""
        if self.status != TaskStatus.FAILED:
            raise ValueError("Only failed tasks can be retried")
        self.status = TaskStatus.QUEUED

    @validator('title')
    def validate_title(cls, v: str) -> str:
        """验证标题非空且长度合适 (Python 3.13.7)"""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if len(v) > 100:
            raise ValueError("Title too long (max 100 chars)")
        return v

    @validator('description') 
    def validate_description(cls, v: str) -> str:
        """验证描述长度 (Python 3.13.7)"""
        if len(v) > 500:
            raise ValueError("Description too long (max 500 chars)")
        return v

    # 使用Pydantic内置序列化方法替代：
    # - 序列化: .model_dump() 或 .model_dump_json()
    # - 反序列化: .model_validate()

    # 配置已合并到model_config中

 