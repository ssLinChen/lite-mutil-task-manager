from mutil_task.core.task import Task, TaskStatus, TaskPriority
from mutil_task.utils.queue_position_service import QueuePositionService
import heapq
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)

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

    def enqueue(self, task: Task) -> None:
        """
        添加任务到队列
        :param task: Task对象
        """
        with self._lock:
            # 验证任务状态
            if task.status != TaskStatus.PENDING:
                raise ValueError(f"只有PENDING状态的任务可以入队，当前状态: {task.status.name}")
            
            # 更新任务状态
            task.status = TaskStatus.QUEUED
            task.updated_at = datetime.now(timezone.utc)
            
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
        """执行队列中的任务 - 优化锁粒度版本"""
        # 第一阶段：获取任务（最小化锁范围）
        task_info = self._dequeue_task()
        if not task_info:
            return
            
        task_id, task = task_info
        
        # 任务出队，失效位置缓存（锁外操作）
        self.position_service.invalidate_cache()

        try:
            # 在锁外执行实际任务（避免阻塞队列）
            logger.debug(f"开始执行任务 {task_id}")
            result = task.execute()
            
            # 第二阶段：更新完成状态（最小化锁范围）
            self._handle_task_completion(task_id, task)
                
        except Exception as e:
            # 第三阶段：错误处理（最小化锁范围）
            self._handle_task_failure(task_id, task, e)
                    
        finally:
            # 第四阶段：清理资源（最小化锁范围）
            self._cleanup_task(task_id)
    
    def _dequeue_task(self) -> Optional[Tuple[str, Task]]:
        """从队列中取出任务（原子操作）"""
        with self._lock:
            # 检查队列是否为空
            if not self._heap:
                return None
                
            # 获取优先级最高的任务（数值最小）
            _, task_id, task = heapq.heappop(self._heap)
            
            # 从索引中移除
            self._task_index.pop(task_id, None)
            
            # 检查任务是否已被取消（新增原子检查）
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
    
    def _handle_task_completion(self, task_id: str, task: Task) -> None:
        """处理任务完成（原子操作）"""
        with self._lock:
            # 检查任务是否已被取消
            if task.status != TaskStatus.CANCELLED:
                task.atomic_set_status(TaskStatus.COMPLETED)
                task.progress = 1.0
                self._completed_tasks[task_id] = task
                logger.debug(f"任务 {task_id} 执行完成")
            else:
                logger.debug(f"任务 {task_id} 已被取消，跳过COMPLETED状态设置")
    
    def _handle_task_failure(self, task_id: str, task: Task, error: Exception) -> None:
        """处理任务失败（原子操作）"""
        with self._lock:
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
                    logger.warning(f"任务 {task_id} 执行失败，重试第 {task.retry_count} 次: {error}")
                else:
                    # 超过重试次数，记录最终失败
                    logger.error(f"任务 {task_id} 执行失败，已达到最大重试次数: {error}")
            else:
                logger.debug(f"任务 {task_id} 已被取消，跳过FAILED状态设置")
    
    def _cleanup_task(self, task_id: str) -> None:
        """清理任务资源（原子操作）"""
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