"""
事件总线模块
提供全局事件发布-订阅机制，用于组件间解耦通信
"""
import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class EventBus:
    """
    线程安全的全局事件总线
    支持事件发布与订阅，用于组件间通信
    """
    # 事件订阅者映射表 {事件类型: [回调函数列表]}
    _subscribers: Dict[str, List[Callable]] = defaultdict(list)
    _lock = threading.RLock()  # 递归锁，支持嵌套锁定
    _executor: Optional[ThreadPoolExecutor] = None
    _max_workers = 4  # 异步回调执行的最大工作线程数
    
    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """获取线程池执行器（懒加载）"""
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(
                max_workers=cls._max_workers,
                thread_name_prefix="EventBus"
            )
        return cls._executor
    
    @classmethod
    def subscribe(cls, event_type: str, callback: Callable[[dict], None]) -> None:
        """
        订阅指定类型的事件（线程安全）
        :param event_type: 事件类型标识符
        :param callback: 事件处理回调函数，接收事件数据字典作为参数
        """
        with cls._lock:
            if callback not in cls._subscribers[event_type]:
                cls._subscribers[event_type].append(callback)
                logger.debug(f"订阅事件 {event_type}，当前订阅者数量: {len(cls._subscribers[event_type])}")
    
    @classmethod
    def unsubscribe(cls, event_type: str, callback: Callable[[dict], None]) -> bool:
        """
        取消订阅指定事件（线程安全）
        :param event_type: 事件类型标识符
        :param callback: 要移除的回调函数
        :return: 是否成功移除
        """
        with cls._lock:
            if event_type in cls._subscribers and callback in cls._subscribers[event_type]:
                cls._subscribers[event_type].remove(callback)
                logger.debug(f"取消订阅事件 {event_type}，剩余订阅者数量: {len(cls._subscribers[event_type])}")
                return True
            return False
    
    @classmethod
    def publish(cls, event_type: str, data: dict, async_mode: bool = True) -> int:
        """
        发布事件到总线（线程安全）
        :param event_type: 事件类型标识符
        :param data: 事件数据字典
        :param async_mode: 是否异步执行回调（默认True）
        :return: 接收事件的订阅者数量
        """
        # 在锁内复制订阅者列表，避免长时间持锁
        with cls._lock:
            subscribers = cls._subscribers.get(event_type, [])[:]  # 浅拷贝
        
        if not subscribers:
            return 0
        
        if async_mode:
            # 异步执行回调，避免阻塞发布者
            executor = cls._get_executor()
            futures = []
            for callback in subscribers:
                future = executor.submit(cls._safe_callback, callback, data, event_type)
                futures.append(future)
            
            # 可选：等待所有回调完成（用于调试）
            # for future in as_completed(futures, timeout=5.0):
            #     try:
            #         future.result()
            #     except Exception as e:
            #         logger.error(f"异步回调执行失败: {e}")
        else:
            # 同步执行回调
            for callback in subscribers:
                cls._safe_callback(callback, data, event_type)
        
        return len(subscribers)
    
    @classmethod
    def _safe_callback(cls, callback: Callable, data: dict, event_type: str) -> None:
        """
        安全执行回调函数，隔离异常
        :param callback: 回调函数
        :param data: 事件数据
        :param event_type: 事件类型（用于日志）
        """
        try:
            callback(data)
        except Exception as e:
            # 避免一个订阅者异常影响其他订阅者
            logger.error(f"事件 {event_type} 处理异常: {e}", exc_info=True)
    
    @classmethod
    def clear(cls, event_type: Optional[str] = None) -> None:
        """
        清除事件订阅（线程安全）
        :param event_type: 指定事件类型，为None时清除所有
        """
        with cls._lock:
            if event_type:
                cleared_count = len(cls._subscribers[event_type])
                cls._subscribers[event_type].clear()
                logger.debug(f"清除事件 {event_type} 的 {cleared_count} 个订阅者")
            else:
                total_cleared = sum(len(subs) for subs in cls._subscribers.values())
                cls._subscribers.clear()
                logger.debug(f"清除所有事件的 {total_cleared} 个订阅者")
    
    @classmethod
    def get_subscriber_count(cls, event_type: str) -> int:
        """
        获取指定事件类型的订阅者数量
        :param event_type: 事件类型标识符
        :return: 订阅者数量
        """
        with cls._lock:
            return len(cls._subscribers.get(event_type, []))
    
    @classmethod
    def shutdown(cls, wait: bool = True) -> None:
        """
        关闭事件总线，清理资源
        :param wait: 是否等待所有异步任务完成
        """
        with cls._lock:
            if cls._executor:
                cls._executor.shutdown(wait=wait)
                cls._executor = None
                logger.info("事件总线已关闭")

# 预定义事件类型常量
class TaskEventType:
    """任务相关事件类型常量"""
    CREATED = "task_created"               # 任务创建
    STATUS_CHANGED = "task_status_changed" # 状态变更
    PROGRESS_UPDATED = "task_progress"     # 进度更新
    COMPLETED = "task_completed"           # 任务完成
    FAILED = "task_failed"                 # 任务失败
    CANCELLED = "task_cancelled"           # 任务取消