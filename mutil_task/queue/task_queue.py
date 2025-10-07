from mutil_task.core.task import Task, TaskStatus, TaskPriority
from mutil_task.utils.queue_position_service import QueuePositionService
import heapq
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
import time
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TaskExecutionResult:
    """任务执行结果封装类"""
    task_id: str
    task: Task
    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None
    
    @classmethod
    def success(cls, task_id: str, task: Task, result: Any) -> 'TaskExecutionResult':
        """创建成功执行结果"""
        return cls(task_id=task_id, task=task, success=True, result=result)
    
    @classmethod
    def failure(cls, task_id: str, task: Task, error: Exception) -> 'TaskExecutionResult':
        """创建失败执行结果"""
        return cls(task_id=task_id, task=task, success=False, error=error)

class TaskQueue:
    def __init__(self, max_workers: int = 2):
        """初始化任务队列"""
        self._heap: list = []
        self._lock = threading.RLock()  # 使用递归锁支持嵌套锁定
        self._executor = ThreadPoolExecutor(max_workers, thread_name_prefix="TaskQueue")
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, Task] = {}
        self._task_index: Dict[str, Tuple[int, str, Task]] = {}  # 任务索引：task_id -> heap_entry
        self.position_service = QueuePositionService(self)
        
        # 启动超时监控线程
        self._timeout_scanner = threading.Thread(
            target=self._scan_timeouts,
            daemon=True
        )
        self._timeout_scanner.start()
        
    def _scan_timeouts(self):
        """定期扫描超时任务"""
        while True:
            time.sleep(1)  # 每秒扫描一次
            self._scan_queue_timeouts()
            
    def _scan_queue_timeouts(self):
        """扫描队列中的超时任务"""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            for _, task_id, task in self._heap:
                if task.queue_timeout and task.queue_started_at:
                    elapsed = (current_time - task.queue_started_at).total_seconds()
                    if elapsed > task.queue_timeout:
                        self._handle_queue_timeout(task_id, task)
    
    def _handle_queue_timeout(self, task_id: str, task: Task):
        """处理队列超时任务"""
        if task.atomic_set_status(TaskStatus.FAILED):
            task.timeout_reason = f"队列等待超时: {task.queue_timeout}秒"
            self._remove_from_heap(task_id)
            logger.warning(f"任务 {task_id} 因队列等待超时而失败")

    def enqueue(self, task: Task) -> None:
        """
        添加任务到队列
        :param task: Task对象
        """
        with self._lock:
            # 验证任务状态
            if task.status != TaskStatus.PENDING:
                raise ValueError(f"只有PENDING状态的任务可以入队，当前状态: {task.status.name}")
            
            # 更新任务状态并记录入队时间
            task.status = TaskStatus.QUEUED
            task.updated_at = datetime.now(timezone.utc)
            task.queue_started_at = datetime.now(timezone.utc)
            
            # 存入优先队列（数值越小优先级越高）
            heap_entry = (task.priority.value, task.id, task)
            heapq.heappush(self._heap, heap_entry)
            
            # 更新任务索引，支持O(1)查找
            self._task_index[task.id] = heap_entry
            
            # 提交任务执行
            self._executor.submit(self._run_task)
        
        # 队列结构变化，失效位置缓存
        self.position_service.invalidate_cache()
        logger.debug(f"任务 {task.id} 已入队，当前队列长度: {len(self._heap)}")

    def _run_task(self) -> None:
        """执行队列中的任务 - 重构版本：职责拆分，逻辑清晰"""
        # 1. 获取任务执行权（原子操作）
        task_info = self._acquire_task_for_execution()
        if not task_info:
            return
            
        task_id, task = task_info
        
        # 2. 安全执行任务（无锁操作，隔离异常）
        execution_result = self._execute_task_safely(task_id, task)
        
        # 3. 处理执行结果（原子操作）
        self._process_execution_result(task_id, task, execution_result)
        
        # 4. 清理执行资源
        self._cleanup_execution_resources(task_id)
    
    def _acquire_task_for_execution(self) -> Optional[Tuple[str, Task]]:
        """原子化获取任务执行权"""
        with self._lock:
            return self._dequeue_and_validate_task()
    
    def _dequeue_and_validate_task(self) -> Optional[Tuple[str, Task]]:
        """从队列中取出并验证任务（原子操作）"""
        # 检查队列是否为空
        if not self._heap:
            return None
            
        # 获取优先级最高的任务（数值最小）
        _, task_id, task = heapq.heappop(self._heap)
        
        # 从索引中移除
        self._task_index.pop(task_id, None)
        
        # 检查任务是否已被取消
        if task.status == TaskStatus.CANCELLED:
            logger.debug(f"任务 {task_id} 已被取消，跳过执行")
            return None
            
        # 检查优先级抢占
        if self._heap and self._heap[0][0] < task.priority.value:
            # 存在更高优先级任务，重新入队当前任务
            heap_entry = (task.priority.value, task.id, task)
            heapq.heappush(self._heap, heap_entry)
            self._task_index[task_id] = heap_entry
            return None
        
        # 原子化设置任务状态为RUNNING
        self._active_tasks[task_id] = task
        task.atomic_set_status(TaskStatus.RUNNING)
        
        return task_id, task
    
    def _execute_task_safely(self, task_id: str, task: Task) -> 'TaskExecutionResult':
        """安全执行任务，隔离异常"""
        try:
            logger.debug(f"开始执行任务 {task_id}")
            
            if task.execution_timeout:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(task.execute)
                    result = future.result(timeout=task.execution_timeout)
                    return TaskExecutionResult.success(task_id, task, result)
            else:
                result = task.execute()
                return TaskExecutionResult.success(task_id, task, result)
                
        except TimeoutError:
            return TaskExecutionResult.failure(
                task_id, 
                task, 
                TimeoutError(f"任务执行超时: {task.execution_timeout}秒")
            )
        except Exception as e:
            return TaskExecutionResult.failure(task_id, task, e)
    
    def _process_execution_result(self, task_id: str, task: Task, execution_result: 'TaskExecutionResult') -> None:
        """原子化处理执行结果"""
        with self._lock:
            if execution_result.success:
                self._handle_successful_execution(task_id, task, execution_result)
            else:
                self._handle_failed_execution(task_id, task, execution_result)
    
    def _handle_successful_execution(self, task_id: str, task: Task, execution_result: 'TaskExecutionResult') -> None:
        """处理成功执行的任务"""
        # 检查任务是否已被取消
        if task.status != TaskStatus.CANCELLED:
            task.atomic_set_status(TaskStatus.COMPLETED)
            task.progress = 1.0
            self._completed_tasks[task_id] = task
            logger.debug(f"任务 {task_id} 执行完成")
        else:
            logger.debug(f"任务 {task_id} 已被取消，跳过COMPLETED状态设置")
    
    def _handle_failed_execution(self, task_id: str, task: Task, execution_result: 'TaskExecutionResult') -> None:
        """处理执行失败的任务"""
        # 检查任务是否已被取消
        if task.status != TaskStatus.CANCELLED:
            task.atomic_set_status(TaskStatus.FAILED)
            
            # 简单的重试逻辑（最多重试3次）
            if not hasattr(task, 'retry_count'):
                task.retry_count = 0
                
            if task.retry_count < 3:
                task.retry_count += 1
                # 重新入队进行重试
                task.atomic_set_status(TaskStatus.QUEUED)
                heap_entry = (task.priority.value, task.id, task)
                heapq.heappush(self._heap, heap_entry)
                self._task_index[task_id] = heap_entry
                logger.warning(f"任务 {task_id} 执行失败，重试第 {task.retry_count} 次: {execution_result.error}")
            else:
                # 超过重试次数，记录最终失败
                logger.error(f"任务 {task_id} 执行失败，已达到最大重试次数: {execution_result.error}")
        else:
            logger.debug(f"任务 {task_id} 已被取消，跳过FAILED状态设置")
    
    def _cleanup_execution_resources(self, task_id: str) -> None:
        """清理执行资源"""
        # 失效位置缓存
        self.position_service.invalidate_cache()
        
        # 清理活动任务记录
        with self._lock:
            self._active_tasks.pop(task_id, None)
    


    def cancel_task(self, task_id: str) -> bool:
        """
        取消指定任务（优化版本，使用索引实现高效查找）
        :param task_id: 任务ID
        :return: 是否取消成功
        """
        cancelled = False
        with self._lock:
            # 优先检查任务索引（O(1)查找）
            if task_id in self._task_index:
                # 从队列中移除（需要重建堆）
                self._remove_from_heap(task_id)
                cancelled = True
                logger.debug(f"从队列中取消任务 {task_id}")
            
            # 取消执行中的任务
            elif task_id in self._active_tasks:
                task = self._active_tasks[task_id]
                cancelled = task.cancel()
                logger.debug(f"取消执行中的任务 {task_id}")
            
            # 检查已完成任务（无法取消）
            elif task_id in self._completed_tasks:
                logger.warning(f"任务 {task_id} 已完成，无法取消")
                return False
        
        # 如果任务被取消，失效缓存
        if cancelled:
            self.position_service.invalidate_cache()
                
        return cancelled
    
    def _remove_from_heap(self, task_id: str) -> bool:
        """从堆中移除指定任务"""
        if task_id not in self._task_index:
            return False
            
        # 获取任务对象
        _, _, task = self._task_index[task_id]
        
        # 标记任务为已取消
        task.cancel()
        
        # 从索引中移除
        del self._task_index[task_id]
        
        # 重建堆（移除已取消的任务）
        self._heap = [entry for entry in self._heap if entry[1] != task_id]
        heapq.heapify(self._heap)
        
        return True

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态
        :param task_id: 任务ID
        :return: 任务状态或None
        """
        with self._lock:
            # 检查活动任务
            if task_id in self._active_tasks:
                return self._active_tasks[task_id].status
                
            # 检查已完成任务
            if task_id in self._completed_tasks:
                return self._completed_tasks[task_id].status
                
            # 检查队列中的任务
            for _, tid, task in self._heap:
                if tid == task_id:
                    return task.status
                    
        return None

    def get_task_position(self, task_id: str) -> Tuple[Optional[int], int]:
        """
        获取任务在队列中的位置信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            tuple: (位置序号, 队列总长度)
            - 位置序号: 任务在队列中的位置（1-based），None表示不在队列中
            - 队列总长度: 当前队列中的任务总数
        """
        return self.position_service.get_position(task_id)

    def __enter__(self) -> 'TaskQueue':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._executor.shutdown(wait=True)
        # 关闭事件总线（如果使用了异步模式）
        from mutil_task.utils.event_bus import EventBus
        EventBus.shutdown(wait=True)