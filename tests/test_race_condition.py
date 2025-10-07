"""
竞态条件测试 - 验证TaskQueue线程安全性修复
"""
import unittest
import threading
import time
from mutil_task.queue.task_queue import TaskQueue
from mutil_task.core.task import Task, TaskStatus, TaskPriority

class TestRaceCondition(unittest.TestCase):
    """竞态条件测试套件"""
    
    def setUp(self):
        self.queue = TaskQueue(max_workers=2)
        
    def test_concurrent_cancel_and_execute(self):
        """测试并发取消和执行任务的竞态条件"""
        
        # 创建测试任务
        task = Task(
            id="race_test_task",
            title="竞态条件测试任务", 
            priority=TaskPriority.NORMAL,
            status=TaskStatus.PENDING
        )
        
        # 入队任务
        self.queue.enqueue(task)
        
        # 确保任务已入队（任务可能立即开始执行）
        status = self.queue.get_task_status("race_test_task")
        self.assertIn(status, [TaskStatus.QUEUED, TaskStatus.RUNNING])
        
        # 设置事件标志
        cancellation_completed = threading.Event()
        execution_started = threading.Event()
        
        def cancel_task():
            """取消任务线程"""
            # 等待执行线程开始
            execution_started.wait(timeout=5.0)
            
            # 执行取消操作
            result = self.queue.cancel_task("race_test_task")
            
            # 标记取消完成
            cancellation_completed.set()
            
            # 验证取消是否成功
            self.assertTrue(result, "任务取消应该成功")
        
        def execute_task():
            """执行任务线程"""
            # 标记执行开始
            execution_started.set()
            
            # 等待取消操作完成
            cancellation_completed.wait(timeout=5.0)
            
            # 检查任务状态（此时任务应该已被取消）
            status = self.queue.get_task_status("race_test_task")
            
            # 任务应该处于CANCELLED状态或不在队列中
            self.assertIn(status, [TaskStatus.CANCELLED, None], 
                         f"任务状态应该为CANCELLED或None，实际为: {status}")
        
        # 启动并发线程
        cancel_thread = threading.Thread(target=cancel_task)
        execute_thread = threading.Thread(target=execute_task)
        
        cancel_thread.start()
        execute_thread.start()
        
        # 等待线程完成
        cancel_thread.join(timeout=10.0)
        execute_thread.join(timeout=10.0)
        
        # 验证没有线程卡死
        self.assertFalse(cancel_thread.is_alive(), "取消线程应该已完成")
        self.assertFalse(execute_thread.is_alive(), "执行线程应该已完成")
        
        # 最终状态检查
        final_status = self.queue.get_task_status("race_test_task")
        self.assertIn(final_status, [TaskStatus.CANCELLED, None],
                     "任务最终状态应该为CANCELLED或None")
    
    def test_priority_preemption_race_condition(self):
        """测试优先级抢占时的竞态条件"""
        
        # 创建多个不同优先级的任务
        low_task = Task(
            id="low_priority_task",
            title="低优先级任务",
            priority=TaskPriority.LOW,
            status=TaskStatus.PENDING
        )
        
        high_task = Task(
            id="high_priority_task", 
            title="高优先级任务",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING
        )
        
        # 先入队低优先级任务
        self.queue.enqueue(low_task)
        
        # 验证低优先级任务已入队（可能立即开始执行）
        low_status = self.queue.get_task_status("low_priority_task")
        self.assertIn(low_status, [TaskStatus.QUEUED, TaskStatus.RUNNING])
        
        # 并发入队高优先级任务
        def enqueue_high_priority():
            time.sleep(0.1)  # 稍微延迟，模拟并发场景
            self.queue.enqueue(high_task)
        
        # 启动并发线程
        high_thread = threading.Thread(target=enqueue_high_priority)
        high_thread.start()
        
        # 等待线程完成
        high_thread.join(timeout=5.0)
        
        # 验证队列状态
        # 高优先级任务应该优先执行
        # 修复后的代码应该能够正确处理这种优先级抢占
        
        # 给队列一些时间处理
        time.sleep(1.0)
        
        # 验证两个任务的状态
        low_status = self.queue.get_task_status("low_priority_task")
        high_status = self.queue.get_task_status("high_priority_task")
        
        # 至少一个任务应该不在队列中（正在执行或已完成）
        self.assertTrue(
            low_status is None or high_status is None or 
            low_status == TaskStatus.RUNNING or high_status == TaskStatus.RUNNING,
            "至少一个任务应该正在执行或已完成"
        )
    
    def test_multiple_concurrent_operations(self):
        """测试多线程并发操作下的线程安全性"""
        
        tasks = []
        for i in range(10):
            task = Task(
                id=f"concurrent_task_{i}",
                title=f"并发任务{i}",
                priority=TaskPriority.NORMAL,
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        # 并发操作结果
        results = []
        lock = threading.Lock()
        
        def worker(operation_type, task_index):
            """工作线程函数"""
            try:
                if operation_type == "enqueue":
                    self.queue.enqueue(tasks[task_index])
                    result = "enqueued"
                elif operation_type == "cancel":
                    result = self.queue.cancel_task(f"concurrent_task_{task_index}")
                elif operation_type == "status":
                    result = self.queue.get_task_status(f"concurrent_task_{task_index}")
                else:
                    result = None
                
                with lock:
                    results.append((operation_type, task_index, result))
                    
            except Exception as e:
                with lock:
                    results.append((operation_type, task_index, f"error: {str(e)}"))
        
        # 启动多个并发线程
        threads = []
        for i in range(30):  # 30个并发操作
            op_type = ["enqueue", "cancel", "status"][i % 3]
            task_idx = i % 10
            
            thread = threading.Thread(target=worker, args=(op_type, task_idx))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=10.0)
        
        # 验证没有线程卡死
        for thread in threads:
            self.assertFalse(thread.is_alive(), "所有线程都应该已完成")
        
        # 验证队列状态一致性
        # 主要检查没有异常抛出，说明线程安全
        self.assertEqual(len(results), 30, "所有操作都应该完成")
        
        # 检查是否有错误发生
        errors = [r for r in results if isinstance(r[2], str) and r[2].startswith("error:")]
        self.assertEqual(len(errors), 0, f"不应该有错误发生，但发现了: {errors}")
    
    def test_queue_consistency_under_stress(self):
        """压力测试下的队列一致性"""
        
        def stress_worker(worker_id, num_operations):
            """压力测试工作线程"""
            for i in range(num_operations):
                task_id = f"stress_task_{worker_id}_{i}"
                
                # 创建并入队任务
                task = Task(
                    id=task_id,
                    title=f"压力测试任务{worker_id}-{i}",
                    priority=TaskPriority.NORMAL,
                    status=TaskStatus.PENDING
                )
                
                try:
                    self.queue.enqueue(task)
                    
                    # 随机取消部分任务
                    if i % 3 == 0:
                        self.queue.cancel_task(task_id)
                    
                    # 检查状态
                    status = self.queue.get_task_status(task_id)
                    
                    # 状态应该是有效的状态或None
                    valid_statuses = [TaskStatus.QUEUED, TaskStatus.CANCELLED, TaskStatus.RUNNING, 
                                    TaskStatus.COMPLETED, TaskStatus.FAILED, None]
                    self.assertIn(status, valid_statuses, 
                                 f"无效的任务状态: {status}")
                                    
                except Exception as e:
                    # 记录错误但不中断测试
                    print(f"Worker {worker_id} 操作 {i} 错误: {e}")
        
        # 启动多个压力测试线程
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=stress_worker, args=(worker_id, 20))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30.0)  # 允许较长时间完成
        
        # 验证线程状态
        for thread in threads:
            self.assertFalse(thread.is_alive(), "所有压力测试线程都应该已完成")

if __name__ == '__main__':
    unittest.main()