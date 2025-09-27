from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional, Callable, Union
from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    field_validator,
    model_serializer
)
import threading
import json


class ConfigError(Exception):
    """配置异常基类"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ParameterValidationError(ConfigError):
    """参数验证异常"""
    def __init__(self, param_name: str, message: str):
        super().__init__(f"[{param_name}] {message}")
        self.param_name = param_name
        self.error_detail = message


class ParamType(str, Enum):
    """参数类型定义"""
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    JSON = "json"


class ParamDefinition(BaseModel):
    """参数定义规范"""
    name: str
    type: ParamType
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    dynamic_feed: Optional[Callable[[], Any]] = None

    @field_validator('default')
    def validate_default(cls, v, info):
        """验证默认值的类型是否与参数类型匹配"""
        if v is not None:
            expected_type = info.data['type']
            if expected_type == ParamType.INTEGER and not isinstance(v, int):
                raise ValueError(f"Default value must be int for {ParamType.INTEGER}")
            elif expected_type == ParamType.FLOAT and not isinstance(v, (float, int)):
                raise ValueError(f"Default value must be float for {ParamType.FLOAT}")
        return v


class TaskConfig(BaseModel):
    """任务参数配置中心"""
    name: str
    description: str = ""
    param_definitions: Dict[str, ParamDefinition] = Field(default_factory=dict)
    lock: threading.Lock = Field(default_factory=threading.Lock, exclude=True)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "sample_config",
                "description": "Example configuration"
            }
        }
    )

    def add_param(self, param: ParamDefinition) -> None:
        """添加参数定义"""
        with self.lock:
            if param.name in self.param_definitions:
                raise ValueError(f"Parameter '{param.name}' already exists")
            self.param_definitions[param.name] = param

    def feed_param_config(self, param_name: str, feed_func: Callable[[], Any]) -> None:
        """动态参数注入"""
        with self.lock:
            if param_name not in self.param_definitions:
                raise KeyError(f"Parameter {param_name} not defined")
            self.param_definitions[param_name].dynamic_feed = feed_func

    def validate_input(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证输入参数并返回类型转换后的字典
        
        Raises:
            ParameterValidationError: 参数验证失败
            ValueError: 缺少必需参数
        """
        validated = {}
        with self.lock:
            for name, param in self.param_definitions.items():
                value = self._get_param_value(name, param, input_params)
                try:
                    validated[name] = self._validate_parameter_value(
                        name,
                        param.type,
                        value,
                        param.constraints
                    )
                except (ValueError, TypeError) as e:
                    raise ParameterValidationError(name, f"Validation failed: {str(e)}")
            
            return validated

    def _get_param_value(self, name: str, param: ParamDefinition, input_params: Dict[str, Any]) -> Any:
        """获取参数值，支持动态注入"""
        if name in input_params:
            return input_params[name]
        if param.required:
            if param.dynamic_feed:
                return param.dynamic_feed()
            if param.default is None:
                raise ValueError(f"Missing required parameter: {name}")
        return param.default

    def _validate_parameter_value(
        self,
        name: str,
        param_type: ParamType,
        value: Any,
        constraints: Dict[str, Any]
    ) -> Any:
        """统一参数值验证逻辑"""
        validator_map = {
            ParamType.INTEGER: self._validate_numeric,
            ParamType.FLOAT: self._validate_numeric,
            ParamType.JSON: self._validate_json,
            ParamType.STRING: lambda n, v, c: str(v),
            ParamType.BOOLEAN: lambda n, v, c: bool(v)
        }
        
        if param_type not in validator_map:
            raise ValueError(f"Unsupported parameter type: {param_type}")
            
        return validator_map[param_type](name, value, constraints)

    def _validate_numeric(
        self,
        name: str,
        value: Any,
        constraints: Dict[str, Any]
    ) -> Union[int, float]:
        """验证数值类型参数"""
        try:
            num = float(value)
            if num.is_integer():
                num = int(num)
            
            # 统一约束检查
            if 'min' in constraints and num < constraints['min']:
                raise ValueError(f"Value must be ≥ {constraints['min']}")
            if 'max' in constraints and num > constraints['max']:
                raise ValueError(f"Value must be ≤ {constraints['max']}")
                
            return num
        except ValueError as e:
            raise ValueError(f"Invalid numeric value: {str(e)}")

    def _validate_json(
        self,
        name: str,
        value: Any,
        constraints: Dict[str, Any]
    ) -> Any:
        """验证JSON类型参数"""
        try:
            return json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
