from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, Union
import uuid
import json
import logging  # 新增
from app.backend.utils.event_bus import EventBus, TaskEventType
from pydantic import (
    BaseModel, 
    ConfigDict, 
    Field, 
    field_validator, 
    root_validator,
    model_validator
)

logger = logging.getLogger(__name__)  # 新增

class TaskStatus(Enum):
    PENDING = 1
    QUEUED = 2
    RUNNING = 3
    COMPLETED = 4
    FAILED = 5
    CANCELLED = 6

    @classmethod
    def from_string(cls, status_str: str) -> 'TaskStatus':
        """严格状态字符串转换"""
        try:
            return cls[status_str.upper()]
        except KeyError:
            raise ValueError(f"无效状态字符串: {status_str}")

    def __str__(self):
        """标准化状态输出"""
        return self.name.lower()

class TaskPriority(Enum):
    CRITICAL = 0  # 最高优先级
    HIGH = 1
    NORMAL = 2
    LOW = 3  # 最低优先级

    @classmethod
    def from_int(cls, priority: int) -> 'TaskPriority':
        if priority not in [p.value for p in cls]:
            raise ValueError(f"无效优先级值: {priority}")
        return cls(priority)

class Task(BaseModel):
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex}")
    title: str = Field(..., max_length=100, description="任务标题")
    description: str = Field("", max_length=500, description="任务描述")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="任务进度百分比")
    queue_position: Optional[int] = Field(None, description="队列位置")
    queue_total: Optional[int] = Field(None, description="队列总数")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="任务优先级(CRITICAL=0最高,HIGH=1,NORMAL=2,LOW=3最低)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "task_3fa85f6457174562b3fc2c963f66afa6",
                "title": "数据处理任务",
                "status": "pending"
            }
        }
    )

    @field_validator('status', mode='before')
    def validate_status(cls, value: Any) -> TaskStatus:
        """增强状态验证器"""
        def convert_status(v: Any) -> TaskStatus:
            if isinstance(v, str):
                return TaskStatus.from_string(v)
            if isinstance(v, int):
                if v not in [s.value for s in TaskStatus]:
                    raise ValueError(f"无效状态值: {v}")
                return TaskStatus(v)
            if isinstance(v, TaskStatus):
                return v
            raise TypeError(f"不支持的状态类型: {type(v)}")

        return convert_status(value)
        
    def __setattr__(self, name, value):
        """重写属性设置方法，用于捕获状态变更"""
        if name == 'status' and hasattr(self, 'status'):
            old_status = self.status
            super().__setattr__(name, value)
            # 发布状态变更事件
            if old_status != value:
                EventBus.publish(TaskEventType.STATUS_CHANGED, {
                    'task': self,
                    'old_status': old_status,
                    'new_status': value,
                    'timestamp': datetime.now(timezone.utc)
                })
        else:
            super().__setattr__(name, value)

    @field_validator('created_at', 'updated_at', mode='before')
    def parse_datetime(cls, value: Any) -> datetime:
        """严格时区转换器（强制UTC）"""
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if not dt.tzinfo:
                    raise ValueError("时间字符串必须包含时区信息")
                return dt.astimezone(timezone.utc)
            elif isinstance(value, datetime):
                if not value.tzinfo:
                    raise ValueError("datetime对象必须包含时区信息")
                return value.astimezone(timezone.utc)
            raise TypeError("必须提供datetime对象或ISO格式字符串")
        except Exception as e:
            raise ValueError(f"无效时间格式: {value}") from e

    @model_validator(mode='before')
    def check_timestamps(cls, values):
        """时间戳逻辑验证（Pydantic V2兼容）"""
        if isinstance(values, dict):
            created = values.get('created_at')
            updated = values.get('updated_at')
            if created and updated and updated < created:
                raise ValueError("更新时间不能早于创建时间")
        return values

    @field_validator('priority', mode='before')
    def validate_priority(cls, value: Any) -> TaskPriority:
        """增强型优先级验证器"""
        try:
            if isinstance(value, str) and value.isdigit():
                return TaskPriority.from_int(int(value))
            if isinstance(value, int):
                return TaskPriority.from_int(value)
            if isinstance(value, TaskPriority):
                return value
        except ValueError as e:
            raise ValueError(f"无效优先级值: {value}") from e
            
        raise TypeError(
            f"优先级需为整数/枚举/数字字符串，收到: {type(value)}"
        )

    def model_dump(self, *args, **kwargs) -> dict:
        """安全序列化"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "progress": round(self.progress * 100, 2),
            "queue_position": self.queue_position,
            "queue_total": self.queue_total,
            "status": self.status.name.lower(),
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def model_dump_json(self, *args, **kwargs) -> str:
        """增强JSON序列化"""
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=2)

    def _atomic_update_timestamp(self) -> None:
        """原子时间戳更新"""
        self.updated_at = datetime.now(timezone.utc)
        
    def update_progress(self, progress: float) -> None:
        """更新任务进度并发布事件"""
        old_progress = self.progress
        self.progress = max(0.0, min(1.0, progress))
        self._atomic_update_timestamp()
        
        # 发布进度更新事件
        EventBus.publish(TaskEventType.PROGRESS_UPDATED, {
            'task': self,
            'old_progress': old_progress,
            'new_progress': self.progress,
            'timestamp': self.updated_at
        })

    def cancel(self) -> bool:
        """取消任务（禁止取消已完成任务）"""
        if self.status == TaskStatus.COMPLETED:
            logger.warning(f"任务 {self.id} 已完成，取消操作被拒绝")
            return False

        try:
            old_status = self.status
            self._validate_transition(self.status, TaskStatus.CANCELLED)
            self.status = TaskStatus.CANCELLED
            self._atomic_update_timestamp()
            
            # 发布任务取消事件
            EventBus.publish(TaskEventType.CANCELLED, {
                'task': self,
                'old_status': old_status,
                'timestamp': self.updated_at
            })
            
            return True
        except ValueError as e:
            logger.error(f"取消任务失败: {str(e)}")
            return False

    def retry_failed_task(self) -> bool:
        """重试失败任务"""
        if self.status != TaskStatus.FAILED:
            logger.error(f"任务 {self.id} 当前状态 {self.status.name} 不可重试")
            return False

        try:
            old_status = self.status
            self._validate_transition(self.status, TaskStatus.QUEUED)
            self.status = TaskStatus.QUEUED
            self._atomic_update_timestamp()
            
            # 发布任务重试事件
            EventBus.publish(TaskEventType.STATUS_CHANGED, {
                'task': self,
                'old_status': old_status,
                'new_status': self.status,
                'timestamp': self.updated_at,
                'is_retry': True
            })
            
            return True
        except ValueError as e:
            logger.error(f"任务重试失败: {str(e)}")
            return False

    def _validate_transition(self, current: TaskStatus, new: TaskStatus) -> None:
        """核心状态转移验证"""
        TRANSITION_MATRIX = {
            TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
            TaskStatus.FAILED: {TaskStatus.QUEUED},
            TaskStatus.COMPLETED: set(),
            TaskStatus.CANCELLED: set()
        }

        if new not in TRANSITION_MATRIX[current]:
            allowed = ', '.join(s.name for s in TRANSITION_MATRIX[current])
            raise ValueError(
                f"无效状态转移: {current.name} → {new.name}\n"
                f"允许操作: {allowed}"
            )


# 示例使用
if __name__ == "__main__":
    # 创建测试任务
    task = Task(title="测试任务", description="状态机验证测试")
    print("初始状态:", task.status)
    
    # 添加事件监听器
    def on_status_change(event_data):
        task = event_data['task']
        old = event_data['old_status'].name if event_data.get('old_status') else 'None'
        new = event_data['new_status'].name if event_data.get('new_status') else task.status.name
        print(f"状态变更: {old} -> {new}")
    
    def on_task_cancelled(event_data):
        task = event_data['task']
        print(f"任务已取消: {task.id} ({task.title})")
    
    # 订阅事件
    EventBus.subscribe(TaskEventType.STATUS_CHANGED, on_status_change)
    EventBus.subscribe(TaskEventType.CANCELLED, on_task_cancelled)
    
    # 尝试取消已完成任务
    task.status = TaskStatus.COMPLETED
    print("尝试取消已完成任务:", task.cancel())
    
    # 重试失败任务
    failed_task = Task(title="失败任务", status=TaskStatus.FAILED)
    print("重试失败任务:", failed_task.retry_failed_task())
    
    # 更新进度
    task.update_progress(0.5)
    print(f"任务进度: {task.progress*100}%")
    
    # 清理事件总线
    EventBus.clear()