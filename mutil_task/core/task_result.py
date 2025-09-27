from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import (
    BaseModel, 
    Field, 
    field_validator,
    model_validator
)
from collections import OrderedDict
import hashlib
import json
import re

class ArtifactStorageType(str, Enum):
    """产物存储类型"""
    LOCAL = "local"
    DATABASE = "db"
    S3 = "s3"
    IN_MEMORY = "memory"

class ArtifactRef(BaseModel):
    storage_type: ArtifactStorageType
    uri: str
    content_type: str = "application/octet-stream"
    size_bytes: Optional[int] = None
    checksum: str = Field(..., min_length=64, max_length=64)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_data(cls, data: bytes, storage_type: ArtifactStorageType, uri: str, content_type: Optional[str] = None) -> "ArtifactRef":
        """从二进制数据创建产物引用（自动计算校验和）"""
        if not data:
            raise ValueError("Data cannot be empty")
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes type")
        if not uri:
            raise ValueError("URI cannot be empty")
            
        return cls(
            storage_type=storage_type,
            uri=uri,
            size_bytes=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            content_type=content_type or "application/octet-stream"
        )

    @field_validator('uri')
    def sanitize_uri(cls, v):
        """消毒URI输入"""
        if not v:
            raise ValueError("URI cannot be empty")
        # 移除潜在危险字符，增强URI清理策略
        v = re.sub(r'[^a-zA-Z0-9\-_./:]', '', v)
        return v.strip()

class ErrorDetail(BaseModel):
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('error_type')
    def validate_error_type(cls, v):
        """验证错误类型是否合法"""
        valid_error_types = {'Validation', 'System', 'Timeout', 'Network', 'Unknown'}
        if v not in valid_error_types:
            raise ValueError(f"Invalid error type: {v}")
        return v

class TaskResult(BaseModel):
    task_id: str = Field(..., description="关联的任务ID")
    execution_id: str = Field(..., description="本次执行唯一ID")
    status: str = Field(..., description="最终状态")
    
    # 时间记录
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeline: OrderedDict[str, datetime] = Field(
        default_factory=OrderedDict,
        description="关键时间节点记录（保持顺序）"
    )
    
    # 性能指标
    metrics: Dict[str, Union[float, int]] = Field(
        default_factory=dict,
        description="性能指标（CPU/内存/耗时等）"
    )
    
    # 输出产物
    artifacts: Dict[str, ArtifactRef] = Field(
        default_factory=dict,
        description="输出产物引用"
    )
    
    # 错误处理
    error: Optional[ErrorDetail] = None
    
    # 上下文信息
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="执行上下文数据"
    )

    def _validate_non_empty_string(self, value: str, field_name: str):
        """验证非空字符串"""
        if not value or not isinstance(value, str):
            raise ValueError(f"{field_name} must be a non-empty string")
        return value

    def add_artifact(self, name: str, artifact: ArtifactRef) -> None:
        """添加输出产物"""
        self._validate_non_empty_string(name, "Artifact name")
        if name in self.artifacts:
            raise ValueError(f"Artifact '{name}' already exists")
        self.artifacts[name] = artifact

    def add_metric(self, name: str, value: Union[float, int]) -> None:
        """记录性能指标"""
        self._validate_non_empty_string(name, "Metric name")
        if not isinstance(value, (float, int)) or value < 0:
            raise ValueError("Metric value must be a non-negative numeric value")
        self.metrics[name] = value

    def record_timeline_event(self, event: str, time: Optional[datetime] = None) -> None:
        """记录时间节点"""
        self._validate_non_empty_string(event, "Event name")
        if event in self.timeline:
            raise ValueError(f"Event '{event}' already exists in timeline")
        self.timeline[event] = time or datetime.now(timezone.utc)

    def set_error(self, error_type: str, message: str, stack_trace: Optional[str] = None, **context) -> None:
        """设置结构化错误信息"""
        self.error = ErrorDetail(
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            context=context
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典形式"""
        return self.dict(by_alias=True, exclude_unset=True)

    def to_audit_log(self) -> Dict[str, Any]:
        """生成审计日志格式"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "duration": (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at
                else None
            ),
            "error": self.error.dict() if self.error else None,
            "artifacts_count": len(self.artifacts),
            "metrics": self.metrics
        }
