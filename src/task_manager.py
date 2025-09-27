import json
import os
import asyncio
from enum import Enum
from uuid import uuid4
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Callable, Any, Coroutine

class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        self.metadata = {}

    def update_metadata(self, key: str, value: Any):
        """更新任务元数据"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取任务元数据"""
        return self.metadata.get(key, default)

class TaskManager:
    def __init__(self, storage_file: str = "tasks.json", max_concurrent: int = 5):
        self.tasks: Dict[str, Task] = {}
        self.storage_file = storage_file
        self.max_concurrent = max_concurrent
        self.task_queue = asyncio.Queue()
        self.active_tasks = set()
        self._queue_processor = None
        self.load_tasks()
        
        # 回调函数注册
        self.status_change_callbacks: List[Callable[[str, TaskStatus, TaskStatus], None]] = []
        self.task_error_callbacks: List[Callable[[str, str], None]] = []

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()

    def register_status_change_callback(self, callback: Callable[[str, TaskStatus, TaskStatus], None]):
        """注册状态变更回调"""
        self.status_change_callbacks.append(callback)

    def register_task_error_callback(self, callback: Callable[[str, str], None]):
        """注册任务错误回调"""
        self.task_error_callbacks.append(callback)

    async def start(self):
        """启动任务处理器"""
        if not self._queue_processor or self._queue_processor.done():
            self._queue_processor = asyncio.create_task(self._process_queue())
    
    async def shutdown(self):
        """停止任务处理器"""
        if self._queue_processor and not self._queue_processor.done():
            self._queue_processor.cancel()
            try:
                await self._queue_processor
            except asyncio.CancelledError:
                pass
            self._queue_processor = None

    def create_task(self, description: str, coro_func: Optional[Callable[[], Coroutine[Any, Any, Any]]] = None, **metadata) -> Task:
        """创建任务并可选地绑定执行函数"""
        task = Task(str(uuid4()), description)
        
        # 设置元数据
        for key, value in metadata.items():
            task.update_metadata(key, value)
        
        self.tasks[task.id] = task
        
        if coro_func:
            self.enqueue_task(task.id, coro_func)
        
        self.save_tasks()
        return task

    async def _process_queue(self):
        """处理任务队列"""
        try:
            while True:
                if len(self.active_tasks) < self.max_concurrent:
                    task_id, coro_func = await self.task_queue.get()
                    task = asyncio.create_task(
                        self._execute_task(task_id, coro_func)
                    )
                    self.active_tasks.add(task)
                    task.add_done_callback(
                        lambda t: self.active_tasks.remove(t)
                    )
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # 取消时完成所有进行中的任务
            if self.active_tasks:
                await asyncio.wait(
                    list(self.active_tasks),
                    timeout=2.0,
                    return_when=asyncio.ALL_COMPLETED
                )
            raise
        except Exception as e:
            print(f"任务处理器异常: {e}")
            raise

    async def _execute_task(self, task_id: str, coro_func: Callable[[], Coroutine[Any, Any, Any]]):
        """执行任务并处理状态变更"""
        task = self.tasks.get(task_id)
        if not task:
            return

        try:
            self.update_status(task_id, TaskStatus.RUNNING)
            await coro_func()
            self.update_status(task_id, TaskStatus.COMPLETED)
        except Exception as e:
            self.update_status(task_id, TaskStatus.FAILED)
            await self._notify_error(task_id, str(e))

    def enqueue_task(self, task_id: str, coro_func: Callable[[], Coroutine[Any, Any, Any]]):
        """将任务加入队列"""
        if task_id in self.tasks:
            self.task_queue.put_nowait((task_id, coro_func))
            self.update_status(task_id, TaskStatus.QUEUED)

    def _get_task(self, task_id: str) -> Optional[Task]:
        """内部获取任务方法"""
        return self.tasks.get(task_id)

    async def _notify_error(self, task_id: str, error_msg: str):
        """通知错误信息"""
        for callback in self.task_error_callbacks:
            try:
                callback(task_id, error_msg)
            except Exception as e:
                print(f"错误回调执行失败: {e}")

    def update_status(self, task_id: str, new_status: TaskStatus):
        """更新任务状态"""
        task = self.tasks.get(task_id)
        if task:
            old_status = task.status
            task.status = new_status
            
            # 触发状态变更回调
            for callback in self.status_change_callbacks:
                try:
                    callback(task_id, old_status, new_status)
                except Exception as e:
                    print(f"状态变更回调执行失败: {e}")
            
            self.save_tasks()

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """列出任务，可选按状态过滤"""
        if status:
            return [task for task in self.tasks.values() if task.status == status]
        return list(self.tasks.values())

    def cancel_task(self, task_id: str):
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
            self.update_status(task_id, TaskStatus.CANCELLED)

    def save_tasks(self):
        """保存任务到文件"""
        try:
            abs_path = os.path.abspath(self.storage_file)
            print(f"尝试保存到: {abs_path}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            with open(abs_path, 'w', encoding='utf-8') as f:
                data = {
                    task_id: asdict(task) 
                    for task_id, task in self.tasks.items()
                }
                json.dump(data, f, default=str, ensure_ascii=False, indent=2)
            
            # 验证写入
            with open(abs_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                print(f"成功保存 {len(saved_data)} 个任务到 {abs_path}")
                
        except Exception as e:
            print(f"保存任务失败: {str(e)}")
            if os.path.exists(abs_path):
                print(f"文件存在但写入失败，权限: {oct(os.stat(abs_path).st_mode)[-3:]}")
            raise

    def load_tasks(self):
        """从文件加载任务"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for task_id, task_data in data.items():
                    # 处理状态格式
                    status_value = task_data['status'].split('.')[-1] if '.' in task_data['status'] else task_data['status']
                    task_data['status'] = TaskStatus[status_value]
                    
                    # 移除不再使用的字段
                    task_data.pop('connections', None)
                    task_data.pop('ws_url', None)
                    
                    self.tasks[task_id] = Task(**task_data)
        except FileNotFoundError:
            print(f"任务文件不存在，将创建新文件: {self.storage_file}")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
        except UnicodeDecodeError as e:
            print(f"编码错误: {e} - 请确保文件使用UTF-8编码")
        except Exception as e:
            print(f"加载任务失败: {e}")

    def clear_completed_tasks(self):
        """清理已完成的任务"""
        completed_tasks = [task_id for task_id, task in self.tasks.items() 
                          if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]]
        
        for task_id in completed_tasks:
            del self.tasks[task_id]
        
        self.save_tasks()
        return len(completed_tasks)