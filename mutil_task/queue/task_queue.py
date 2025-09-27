from mutil_task.core.task import Task, TaskStatus, TaskPriority
import heapq
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

class TaskQueue:
    def __init__(self, max_workers=2):
        """初始化任务队列"""
        self._heap = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers)
        self._active_tasks = {}
        self._completed_tasks = {}

    def enqueue(self, task: Task):
        """
        添加任务到队列
        :param task: Task对象
        """
        with self._lock:
            # 验证任务状态
            if task.status != TaskStatus.PENDING:
                raise ValueError(f"只有PENDING状态的任务可以入队，当前状态: {task.status.name}")
            
            # 更新任务状态和位置
            task.status = TaskStatus.QUEUED
            task.queue_position = len(self._heap) + 1
            task.queue_total = len(self._heap) + 1
            task.updated_at = datetime.now(timezone.utc)
            
            # 存入优先队列（数值越小优先级越高）
            # 使用task.priority.value而非负值，因为TaskPriority枚举已经定义了HIGH=1, MEDIUM=2, LOW=3
            heapq.heappush(self._heap, (task.priority.value, task.id, task))
            self._executor.submit(self._run_task)

    def _run_task(self):
        """执行队列中的任务"""
        with self._lock:
            if not self._heap:
                return
                
            # 获取优先级最高的任务（数值最小）
            _, task_id, task = heapq.heappop(self._heap)
            self._active_tasks[task_id] = task

            # 立即获取下一个高优先级任务（如果有）
            if self._heap:
                next_priority = self._heap[0][0]
                if next_priority < task.priority.value:
                    # 如果存在更高优先级任务，重新入队当前任务
                    heapq.heappush(self._heap, (task.priority.value, task.id, task))
                    self._active_tasks.pop(task_id, None)
                    return

        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.now(timezone.utc)
            
            # 执行任务
            result = task.execute()
            
            # 标记完成
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            self._completed_tasks[task_id] = task
        except Exception as e:
            task.status = TaskStatus.FAILED
            raise
        finally:
            with self._lock:
                self._active_tasks.pop(task_id, None)
                task.updated_at = datetime.now(timezone.utc)

    def cancel_task(self, task_id: str) -> bool:
        """
        取消指定任务
        :param task_id: 任务ID
        :return: 是否取消成功
        """
        with self._lock:
            # 从队列中移除
            for i, (_, tid, task) in enumerate(self._heap):
                if tid == task_id:
                    task = self._heap.pop(i)[2]
                    heapq.heapify(self._heap)
                    return task.cancel()
            
            # 取消执行中的任务
            if task_id in self._active_tasks:
                task = self._active_tasks[task_id]
                return task.cancel()
                
        return False

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._executor.shutdown(wait=True)