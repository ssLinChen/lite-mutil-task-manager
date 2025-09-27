import unittest
import time
import threading
import os
from datetime import datetime, timedelta
from app.backend.models.core.task import Task, TaskStatus, TaskPriority
from app.backend.models.queue.task_queue import TaskQueue
from app.tests.visual_controller import TestVisualController
from app.backend.utils.event_bus import EventBus

class TestTask(Task):
    """测试用任务类"""
    def execute(self):
        if hasattr(self, '_execute_mock'):
            return self._execute_mock()
        return f"Task {self.id} executed"

class TestTaskQueue(unittest.TestCase):
    def setUp(self):
        self.queue = TaskQueue(max_workers=2)
        # 初始化可视化控制器
        self.visual = TestVisualController(self.id())

    def tearDown(self):
        # 清理可视化控制器
        self.visual.cleanup()
        # 清理事件总线
        EventBus.clear()

    def test_task_execution(self):
        """测试基本任务执行"""
        task = TestTask(title="测试任务")
        # 跟踪任务
        self.visual.track_task(task)
        
        # 提交任务
        self.queue.enqueue(task)
        
        # 等待任务完成
        start = time.time()
        while task.status != TaskStatus.COMPLETED and time.time() - start < 1:
            time.sleep(0.1)
            
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        
        # 生成报告
        report_path = self.visual.generate_report()
        print(f"可视化报告已生成: {report_path}")

    def test_priority_execution(self):
        """测试优先级执行顺序"""
        results = []
        
        # 创建不同优先级的任务
        low_task = TestTask(title="低优先级", priority=TaskPriority.LOW)
        high_task = TestTask(title="高优先级", priority=TaskPriority.HIGH)
        
        # 跟踪任务
        self.visual.track_task(low_task)
        self.visual.track_task(high_task)
        
        # 添加执行回调
        def make_callback(task):
            def callback():
                results.append(task.title)
            return callback
        
        low_task._execute_mock = make_callback(low_task)
        high_task._execute_mock = make_callback(high_task)
        
        # 提交任务（先低后高）
        self.queue.enqueue(low_task)
        self.queue.enqueue(high_task)
        
        # 等待执行
        time.sleep(0.5)
        self.assertEqual(results, [high_task.title, low_task.title])
        
        # 生成报告
        report_path = self.visual.generate_report()
        print(f"可视化报告已生成: {report_path}")

    def test_task_cancellation(self):
        """测试任务取消"""
        task = TestTask(title="可取消任务")
        
        # 跟踪任务
        self.visual.track_task(task)
        
        # 模拟长时间运行
        def long_running():
            time.sleep(10)
        task._execute_mock = long_running
        
        self.queue.enqueue(task)
        time.sleep(0.1)  # 确保任务开始
        
        # 取消任务
        self.assertTrue(self.queue.cancel_task(task.id))
        self.assertEqual(task.status, TaskStatus.CANCELLED)
        
        # 生成报告
        report_path = self.visual.generate_report()
        print(f"可视化报告已生成: {report_path}")

if __name__ == "__main__":
    # 创建报告目录
    os.makedirs("test_reports", exist_ok=True)
    unittest.main()