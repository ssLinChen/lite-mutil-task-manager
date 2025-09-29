import sys
from pathlib import Path
from typing import Dict
sys.path.append(str(Path(__file__).parent.parent))  # 添加项目根目录到路径

from mutil_task.core.task import Task, TaskPriority, TaskStatus
from mutil_task.core.task_config import TaskConfig, ParamDefinition, ParamType, ParameterValidationError
from mutil_task.queue.task_queue import TaskQueue
from mutil_task.utils.event_bus import EventBus
from mutil_task.utils.task_ui import render_full_panel
import time

 
 
class ConfigurableMVPTask(Task):
    """支持配置的MVP任务类"""
    
    # 定义Pydantic模型字段
    validated_params: dict = {}
    _config: TaskConfig = None
    _execution_time: int = 5
    _timeout: int = 10
    _retries: int = 3
    
    def __init__(self, title: str, priority: TaskPriority, config: TaskConfig, input_params: dict):
        """
        初始化配置化任务
        :param title: 任务标题
        :param priority: 任务优先级
        :param config: TaskConfig配置对象
        :param input_params: 输入参数字典
        """
        super().__init__(title=title, priority=priority)
        
        # 验证输入参数
        try:
            validated_params = config.validate_input(input_params)
            self._config = config
            
            # 使用验证后的参数设置任务属性
            execution_time = validated_params.get('execution_time', 5)
            self.description = f"配置化任务 | 执行时间: {execution_time}秒"
            self._execution_time = execution_time
            self._timeout = validated_params.get('timeout', 10)
            self._retries = validated_params.get('retries', 3)
            
            # 存储验证后的参数（不通过Pydantic验证）
            object.__setattr__(self, 'validated_params', validated_params)
            
        except ParameterValidationError as e:
            raise ValueError(f"参数验证失败: {e.message}")
        except Exception as e:
            raise ValueError(f"配置处理错误: {str(e)}")
        
    def execute(self):
        """使用验证后的参数执行任务"""
        print(f"开始执行: {self.title} (超时: {self._timeout}s, 重试: {self._retries}次)")
        steps = self._execution_time * 2  # 每0.5秒更新一次进度
        
        for i in range(steps):
            time.sleep(0.5)
            self.update_progress((i+1)/steps)  # 0-1范围
            
            # 模拟配置参数的使用
            if i % 4 == 0:  # 每2秒显示一次配置信息
                print(f"  使用配置: timeout={self._timeout}, retries={self._retries}")
                
        return f"{self.title} 完成 (使用配置参数)"

class MVPTask(Task):
    """MVP版本的任务类（保持向后兼容）"""
    def __init__(self, title: str, priority: TaskPriority, execution_time: int = 5):
        """
        初始化任务
        :param title: 任务标题
        :param priority: 任务优先级
        :param execution_time: 执行时间(秒)
        """
        super().__init__(title=title, priority=priority)
        # 使用描述字段存储执行时间信息
        self.description = f"执行时间: {execution_time}秒"
        # 将执行时间作为私有变量存储
        self._execution_time = execution_time
        
    def execute(self):
        print(f"开始执行: {self.title} (预计耗时: {self._execution_time}秒)")
        steps = self._execution_time * 2  # 每0.5秒更新一次进度
        for i in range(steps):
            time.sleep(0.5)
            self.update_progress((i+1)/steps)  # 0-1范围
        return f"{self.title} 完成"

def get_stage(progress: float) -> str:
    """根据进度获取阶段描述"""
    if progress < 0.25:
        return "🟡 初始化"
    elif progress < 0.7:
        return "🟠 执行中"
    else:
        return "🔵 收尾中"
 
def create_task_configs() -> Dict[str, TaskConfig]:
    """创建优雅的任务配置示例
    
    Returns:
        包含不同优先级任务配置的字典
    """
    # 配置模板定义 - 使用清晰的数据结构
    config_templates = {
        "urgent": {
            "name": "urgent_processing",
            "params": [
                ("execution_time", ParamType.INTEGER, "执行时间(秒)", 6, {"min": 1, "max": 60}),
                ("timeout", ParamType.INTEGER, "超时时间(秒)", 30, {"min": 5, "max": 300}),
                ("retries", ParamType.INTEGER, "重试次数", 3, {"min": 0, "max": 10})
            ]
        },
        "normal": {
            "name": "normal_processing", 
            "params": [
                ("execution_time", ParamType.INTEGER, "执行时间(秒)", 10, {"min": 1, "max": 120}),
                ("timeout", ParamType.INTEGER, "超时时间(秒)", 60, {"min": 2, "max": 600})
            ]
        }
    }
    
    configs = {}
    
    for config_type, template in config_templates.items():
        config = TaskConfig(name=template["name"])
        
        # 批量添加参数 - 减少重复代码
        for name, param_type, description, default, constraints in template["params"]:
            param_def = ParamDefinition(
                name=name,
                type=param_type,
                description=description,
                default=default,
                constraints=constraints
            )
            config.add_param(param_def)
        
        configs[config_type] = config
    
    return configs

def run_mvp():
    """MVP演示流程（集成配置功能）"""
    queue = TaskQueue(max_workers=2)  # 双线程并发
    
    # 创建任务配置
    task_configs = create_task_configs()
    
    # 创建传统任务（保持向后兼容）
    traditional_tasks = [
        MVPTask(title="传统紧急任务", priority=TaskPriority.HIGH, execution_time=15),
        MVPTask(title="传统常规任务", priority=TaskPriority.NORMAL, execution_time=18),
    ]
    
    # 创建配置化任务
    configurable_tasks = [
        ConfigurableMVPTask(
            title="配置化紧急任务",
            priority=TaskPriority.HIGH,
            config=task_configs["urgent"],
            input_params={"execution_time": 8, "timeout": 10, "retries": 5}
        ),
        ConfigurableMVPTask(
            title="配置化常规任务", 
            priority=TaskPriority.NORMAL,
            config=task_configs["normal"],
            input_params={"execution_time": 5, "timeout": 6}
        )
    ]
    
    # 合并所有任务
    tasks = traditional_tasks + configurable_tasks
    
    # 入队逻辑（带配置验证演示）
    print("开始任务入队...")
    print("=" * 50)
    
    for task in tasks:
        try:
            queue.enqueue(task)
            print(f"✅ 已入队: {task.title}")
            
            # 显示配置化任务的验证信息
            if hasattr(task, 'validated_params'):
                print(f"  配置参数: {list(task.validated_params.keys())}")
                
            try:
                render_full_panel([task])
            except Exception as e:
                print(f"⚠️ 可视化渲染失败: {str(e)}")
                
        except ValueError as e:
            print(f"❌ 入队失败 {task.title}: {str(e)}")
        except Exception as e:
            print(f"❌ 未知错误 {task.title}: {str(e)}")
    
    # 演示参数验证错误场景
    print("" + "=" * 50)
    print("演示参数验证错误场景:")
    print("-" * 30)
    
    try:
        # 故意传入无效参数
        invalid_task = ConfigurableMVPTask(
            title="无效参数任务",
            priority=TaskPriority.LOW,
            config=task_configs["urgent"],
            input_params={"execution_time": -5}  # 违反最小值约束
        )
        print("❌ 预期外的成功：参数验证应该失败")
    except ValueError as e:
        print(f"✅ 参数验证正确拦截: {str(e)}")
    except Exception as e:
        print(f"⚠️ 其他错误: {str(e)}")
        
    try:
        # 传入类型错误的参数
        invalid_task = ConfigurableMVPTask(
            title="类型错误任务",
            priority=TaskPriority.LOW,
            config=task_configs["urgent"],
            input_params={"execution_time": "invalid_string"}  # 类型错误
        )
        print("❌ 预期外的成功：类型验证应该失败")
    except ValueError as e:
        print(f"✅ 类型验证正确拦截: {str(e)}")
    except Exception as e:
        print(f"⚠️ 其他错误: {str(e)}")
    
    # 增强版监控逻辑
    start_time = time.time()
    print("\n任务执行监控开始:")
    print("=" * 50)
    
    # 监控逻辑 - 保留所有任务状态
    while len(queue._active_tasks) > 0 or len(queue._heap) > 0:
        time.sleep(0.5)
        
        # 收集所有任务状态（包括排队、执行中和已完成的任务）
        current_tasks = []
        
        # 添加排队中的任务
        for _, _, task in queue._heap:
            current_tasks.append(task)
            
        # 添加执行中的任务
        for task in queue._active_tasks.values():
            current_tasks.append(task)
            
        # 添加已完成的任务
        for task in queue._completed_tasks.values():
            current_tasks.append(task)
        
        # 清屏效果（仅在控制台环境）
        if current_tasks:
 
            # 同时尝试使用Rich渲染
            try:
                render_full_panel(current_tasks, queue)
            except Exception as e:
                print(f"Rich渲染失败: {str(e)}")
                
            # 显示准确的队列位置信息
            queued_tasks = []
            for task in current_tasks:
                if task.status == TaskStatus.QUEUED:
                    position, total = queue.get_task_position(task.id)
                    if position is not None:
                        queued_tasks.append(f"{task.title}: 排队中({position}/{total})")
                    else:
                        queued_tasks.append(f"{task.title}: 不在队列中")
            
            if queued_tasks:
                print("队列状态:")
                for task_info in queued_tasks:
                    print(f"  {task_info}")
            
            print(f"当前状态: {len(queue._heap)}等待 | {len(queue._active_tasks)}执行中 | "
                  f"已完成: {len(queue._completed_tasks)}")
    
    # 最终结果统计
    print("\n" + "=" * 50)
    print(f"所有任务完成! 总耗时: {time.time()-start_time:.2f}秒")
    print("执行顺序:")
    for task_id, task in queue._completed_tasks.items():
        print(f"- {task.title} (优先级: {task.priority.name})")

if __name__ == "__main__":
    run_mvp()