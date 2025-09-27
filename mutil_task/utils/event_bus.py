"""
事件总线模块
提供全局事件发布-订阅机制，用于组件间解耦通信
"""
from collections import defaultdict
from typing import Callable, Dict, List, Any

class EventBus:
    """
    全局事件总线
    支持事件发布与订阅，用于组件间通信
    """
    # 事件订阅者映射表 {事件类型: [回调函数列表]}
    _subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    @classmethod
    def subscribe(cls, event_type: str, callback: Callable[[dict], None]) -> None:
        """
        订阅指定类型的事件
        :param event_type: 事件类型标识符
        :param callback: 事件处理回调函数，接收事件数据字典作为参数
        """
        if callback not in cls._subscribers[event_type]:
            cls._subscribers[event_type].append(callback)
    
    @classmethod
    def unsubscribe(cls, event_type: str, callback: Callable[[dict], None]) -> bool:
        """
        取消订阅指定事件
        :param event_type: 事件类型标识符
        :param callback: 要移除的回调函数
        :return: 是否成功移除
        """
        if event_type in cls._subscribers and callback in cls._subscribers[event_type]:
            cls._subscribers[event_type].remove(callback)
            return True
        return False
    
    @classmethod
    def publish(cls, event_type: str, data: dict) -> int:
        """
        发布事件到总线
        :param event_type: 事件类型标识符
        :param data: 事件数据字典
        :return: 接收事件的订阅者数量
        """
        subscribers = cls._subscribers.get(event_type, [])
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                # 避免一个订阅者异常影响其他订阅者
                print(f"事件处理异常: {e}")
        return len(subscribers)
    
    @classmethod
    def clear(cls, event_type: str = None) -> None:
        """
        清除事件订阅
        :param event_type: 指定事件类型，为None时清除所有
        """
        if event_type:
            cls._subscribers[event_type].clear()
        else:
            cls._subscribers.clear()

# 预定义事件类型常量
class TaskEventType:
    """任务相关事件类型常量"""
    CREATED = "task_created"               # 任务创建
    STATUS_CHANGED = "task_status_changed" # 状态变更
    PROGRESS_UPDATED = "task_progress"     # 进度更新
    COMPLETED = "task_completed"           # 任务完成
    FAILED = "task_failed"                 # 任务失败
    CANCELLED = "task_cancelled"           # 任务取消