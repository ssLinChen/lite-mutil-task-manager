"""
队列位置服务 - 提供准确的队列位置显示功能
"""
import time
import threading
from typing import Tuple, Optional

class QueuePositionService:
    """
    队列位置服务 - 提供实时准确的队列位置信息
    采用批量计算 + 智能缓存策略，平衡性能与准确性
    """
    
    def __init__(self, queue, cache_ttl: float = 0.2):
        """
        初始化位置服务
        
        Args:
            queue: 任务队列对象
            cache_ttl: 缓存有效期（秒），默认200ms
        """
        self.queue = queue
        self.cache_ttl = cache_ttl
        self._cache = None
        self._cache_time = 0
        self._cache_lock = threading.Lock()
    
    def get_position(self, task_id: str) -> Tuple[Optional[int], int]:
        """
        获取任务在队列中的位置信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Tuple[位置序号, 队列总长度]
            - 位置序号: 任务在队列中的位置（1-based），None表示不在队列中
            - 队列总长度: 当前队列中的任务总数
        """
        current_time = time.time()
        
        # 检查缓存是否有效
        with self._cache_lock:
            if (self._cache is not None and 
                current_time - self._cache_time < self.cache_ttl):
                return self._cache.get(task_id, (None, 0))
        
        # 缓存失效，重新计算所有位置
        return self._recalculate_positions(task_id)
    
    def _recalculate_positions(self, task_id: str) -> Tuple[Optional[int], int]:
        """
        重新计算队列中所有任务的位置信息
        
        Args:
            task_id: 需要获取位置的任务ID
            
        Returns:
            Tuple[位置序号, 队列总长度]
        """
        with self.queue._lock:
            total = len(self.queue._heap)
            positions = {}
            
            # 一次遍历计算所有任务位置（性能优化）
            for position, (_, tid, _) in enumerate(self.queue._heap, 1):
                positions[tid] = (position, total)
            
            # 更新缓存
            with self._cache_lock:
                self._cache = positions
                self._cache_time = time.time()
            
            return positions.get(task_id, (None, 0))
    
    def invalidate_cache(self):
        """
        使缓存失效 - 在队列结构变化时调用
        """
        with self._cache_lock:
            self._cache = None
    
    def get_queue_stats(self) -> dict:
        """
        获取队列统计信息
        
        Returns:
            包含队列统计信息的字典
        """
        with self.queue._lock:
            return {
                'total_tasks': len(self.queue._heap),
                'active_tasks': len(self.queue._active_tasks),
                'completed_tasks': len(self.queue._completed_tasks),
                'cache_valid': self._cache is not None and 
                              time.time() - self._cache_time < self.cache_ttl
            }