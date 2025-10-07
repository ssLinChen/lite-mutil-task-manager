from enum import Enum
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, Union, Protocol
from abc import abstractmethod
import uuid
import json
import logging
from mutil_task.utils.event_bus import EventBus, TaskEventType
from pydantic import (
    BaseModel, 
    ConfigDict, 
    Field, 
    field_validator, 
    root_validator,
    model_validator
)

logger = logging.getLogger(__name__)

# ======
# 枚举定义层 - 定义任务状态和优先级枚举
# ======

class TaskStatus(Enum):
    """任务状态枚举 - 定义任务的6种生命周期状态"""
    PENDING = 1    # 等待入队
    QUEUED = 2     # 已加入队列
    RUNNING = 3    # 正在执行
    COMPLETED = 4  # 成功完成
    FAILED = 5     # 执行失败
    CANCELLED = 6  # 已取消

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
    """任务优先级枚举 - 定义4级优先级，数值越小优先级越高"""
    CRITICAL = 0  # 最高优先级 - 紧急任务
    HIGH = 1      # 高优先级 - 重要任务
    NORMAL = 2    # 普通优先级 - 常规任务
    LOW = 3       # 低优先级 - 后台任务

    @classmethod
    def from_int(cls, priority: int) -> 'TaskPriority':
        """从整数值创建优先级枚举"""
        if priority not in [p.value for p in cls]:
            raise ValueError(f"无效优先级值: {priority}")
        return cls(priority)


class TaskExecutor(Protocol):
    """任务执行器协议 - 支持自定义任务执行逻辑"""
    
    @abstractmethod
    def execute_task(self, task: 'Task') -> Any:
        """执行任务并返回结果"""
        pass


# ======
# Task类 - 任务数据模型和业务逻辑
# ======

class Task(BaseModel):
    """
    任务模型 - 基于Pydantic的任务数据模型和业务逻辑封装
    采用三层架构：数据属性层、业务操作层、内部支持层
    """
    
    # ====== 数据属性层 ======
    # 定义任务的所有数据字段和验证规则
    
    # 基础标识信息
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex}", 
                   description="任务唯一标识符")
    title: str = Field(..., max_length=100, description="任务标题")
    description: str = Field("", max_length=500, description="任务详细描述")
    
    # 状态和进度信息
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务当前状态")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="任务进度百分比(0.0-1.0)")
    
    # 队列信息
    queue_position: Optional[int] = Field(None, description="任务在队列中的位置")
    queue_total: Optional[int] = Field(None, description="队列中总任务数")
    
    # 优先级配置
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="任务优先级(CRITICAL=0最高,HIGH=1,NORMAL=2,LOW=3最低)"
    )
    
    # 时间戳信息
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="任务创建时间(UTC)"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="任务最后更新时间(UTC)"
    )
    queue_started_at: Optional[datetime] = Field(
        None,
        description="任务进入队列时间(UTC)"
    )
    
    # 超时配置
    queue_timeout: Optional[int] = Field(
        None, ge=1,
        description="队列等待超时时间(秒)"
    )
    execution_timeout: Optional[int] = Field(
        None, ge=1,
        description="任务执行超时时间(秒)"
    )
    timeout_reason: Optional[str] = Field(
        None,
        description="超时原因描述"
    )
    
    # 执行器配置（不参与序列化）
    executor: Optional[Any] = Field(default=None, exclude=True)
    
    # Pydantic模型配置
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "task_3fa85f6457174562b3fc2c963f66afa6",
                "title": "数据处理任务",
                "status": "pending"
            }
        }
    )
    
    def model_dump(self, **kwargs) -> dict:
        """自定义序列化方法"""
        data = super().model_dump(**kwargs)
        # 自定义序列化格式
        if 'status' in data:
            data['status'] = self.status.name.lower()
        if 'priority' in data:
            data['priority'] = self.priority.value
        if 'created_at' in data:
            data['created_at'] = self.created_at.isoformat()
        if 'updated_at' in data:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    # ====== 数据验证器 ======
    # Pydantic验证器，确保数据完整性和一致性
    
    @field_validator('status', mode='before')
    def validate_status(cls, value: Any) -> TaskStatus:
        """增强状态验证器 - 支持多种输入格式"""
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

    @field_validator('created_at', 'updated_at', mode='before')
    def parse_datetime(cls, value: Any) -> datetime:
        """严格时区转换器 - 强制使用UTC时区"""
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
        """时间戳逻辑验证 - 确保更新时间不早于创建时间"""
        if isinstance(values, dict):
            created = values.get('created_at')
            updated = values.get('updated_at')
            if created and updated and updated < created:
                raise ValueError("更新时间不能早于创建时间")
        return values

    @field_validator('priority', mode='before')
    def validate_priority(cls, value: Any) -> TaskPriority:
        """增强型优先级验证器 - 支持多种输入格式"""
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
    
    # ====== 业务操作层 ======
    # 公开的业务方法，供外部调用
    
    def cancel(self) -> bool:
        """
        取消任务
        
        Returns:
            bool: 取消操作是否成功
            
        Raises:
            ValueError: 状态转移验证失败时抛出
        """
        if self.status == TaskStatus.COMPLETED:
            logger.warning(f"任务 {self.id} 已完成，取消操作被拒绝")
            return False

        try:
            self._validate_transition(self.status, TaskStatus.CANCELLED)
            self._set_status(TaskStatus.CANCELLED)
            
            # 发布任务取消事件
            EventBus.publish(TaskEventType.CANCELLED, {
                'task': self,
                'old_status': self.status,
                'timestamp': self.updated_at
            })
            
            return True
        except ValueError as e:
            logger.error(f"取消任务失败: {str(e)}")
            return False

    def retry_failed_task(self) -> bool:
        """
        重试失败任务 - 将失败任务重新加入队列
        
        Returns:
            bool: 重试操作是否成功
        """
        if self.status != TaskStatus.FAILED:
            logger.error(f"任务 {self.id} 当前状态 {self.status.name} 不可重试")
            return False

        try:
            self._validate_transition(self.status, TaskStatus.QUEUED)
            self._set_status(TaskStatus.QUEUED)
            
            # 发布任务重试事件
            EventBus.publish(TaskEventType.STATUS_CHANGED, {
                'task': self,
                'old_status': TaskStatus.FAILED,
                'new_status': self.status,
                'timestamp': self.updated_at,
                'is_retry': True
            })
            
            return True
        except ValueError as e:
            logger.error(f"任务重试失败: {str(e)}")
            return False

    def execute(self) -> Any:
        """
        执行任务 - 支持自定义执行器
        
        Returns:
            Any: 任务执行结果
            
        Raises:
            ValueError: 任务不在RUNNING状态时抛出
        """
        if self.executor:
            return self.executor.execute_task(self)
        else:
            return self._default_execute()

    def update_progress(self, progress: float) -> None:
        """
        更新任务进度并发布进度更新事件
        
        Args:
            progress: 进度值(0.0-1.0)
        """
        old_progress = self.progress
        self.progress = max(0.0, min(1.0, progress))
        self._update_timestamp()
        
        # 发布进度更新事件
        EventBus.publish(TaskEventType.PROGRESS_UPDATED, {
            'task': self,
            'old_progress': old_progress,
            'new_progress': self.progress,
            'timestamp': self.updated_at
        })

    def set_executor(self, executor: TaskExecutor) -> None:
        """
        设置任务执行器
        
        Args:
            executor: 实现TaskExecutor协议的执行器对象
        """
        self.executor = executor
    
    def atomic_set_status(self, new_status: TaskStatus, validate: bool = True) -> bool:
        """
        原子化状态设置方法 - 线程安全的状态变更
        
        Args:
            new_status: 目标状态
            validate: 是否进行状态转移验证
            
        Returns:
            bool: 状态变更是否成功
        """
        try:
            if validate:
                self._validate_transition(self.status, new_status)
            self._set_status(new_status)
            return True
        except ValueError as e:
            logger.warning(f"原子状态变更失败: {str(e)}")
            return False
    
    # ====== 内部支持层 ======
    # 私有方法，支持业务操作层的实现
    
    def _set_status(self, new_status: TaskStatus) -> None:
        """
        原子化状态设置方法 - 状态变更、时间戳更新、事件发布一体化
        
        Args:
            new_status: 新状态
        """
        old_status = self.status
        if old_status != new_status:
            super().__setattr__('status', new_status)
            self._update_timestamp()
            self._publish_status_change(old_status, new_status)
    
    def _publish_status_change(self, old_status: TaskStatus, new_status: TaskStatus) -> None:
        """
        统一发布状态变更事件
        
        Args:
            old_status: 旧状态
            new_status: 新状态
        """
        EventBus.publish(TaskEventType.STATUS_CHANGED, {
            'task': self,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': self.updated_at
        })

    def _update_timestamp(self) -> None:
        """统一时间戳更新"""
        self.updated_at = datetime.now(timezone.utc)

    def _validate_transition(self, current: TaskStatus, new: TaskStatus) -> None:
        """
        核心状态转移验证 - 基于状态转移矩阵
        
        Args:
            current: 当前状态
            new: 目标状态
            
        Raises:
            ValueError: 状态转移不合法时抛出
        """
        TRANSITION_MATRIX = {
            TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
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

    def _default_execute(self) -> Any:
        """
        默认执行逻辑 - 带进度更新的实现
        
        Returns:
            dict: 执行结果
            
        Raises:
            ValueError: 任务不在RUNNING状态时抛出
        """
        # 基础验证
        if self.status != TaskStatus.RUNNING:
            raise ValueError(f"任务必须在RUNNING状态才能执行，当前状态: {self.status.name}")
        
        import time
        steps = 10  # 将2秒执行分成10步
        for i in range(steps):
            time.sleep(0.2)
            self.update_progress((i+1)/steps)
            if self.status == TaskStatus.CANCELLED:
                return {
                    "task_id": self.id,
                    "status": "cancelled",
                    "message": "任务已取消"
                }
                
        return {
            "task_id": self.id,
            "status": "completed",
            "message": f"任务 {self.title} 执行完成"
        }



# ======
# 示例使用和测试代码
# ======

if __name__ == "__main__":
    """
    任务模型使用示例 - 演示核心功能
    """
    
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
    task._set_status(TaskStatus.COMPLETED)
    print("尝试取消已完成任务:", task.cancel())
    
    # 重试失败任务
    failed_task = Task(title="失败任务")
    failed_task._set_status(TaskStatus.FAILED)
    print("重试失败任务:", failed_task.retry_failed_task())
    
    # 更新进度
    task.update_progress(0.5)
    print(f"任务进度: {task.progress*100}%")
    
    # 清理事件总线
    EventBus.clear()