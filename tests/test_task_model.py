import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import json
try:
    from hypothesis import given, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 使用新的导入路径
from mutil_task.core.task import Task, TaskStatus, TaskPriority

class TestTaskModel(unittest.TestCase):
    """主测试类"""
    
    def setUp(self):
        self.base_task = Task(title="Base Task")
    
    # 基础功能测试
    def test_initialization(self):
        self.assertEqual(self.base_task.title, "Base Task")
        self.assertEqual(self.base_task.status, TaskStatus.PENDING)
        
    # 状态转换测试
    def test_valid_status_transition(self):
        self.base_task.status = TaskStatus.QUEUED
        self.assertEqual(self.base_task.status, TaskStatus.QUEUED)
    
    # 优先级测试
    if HAS_HYPOTHESIS:
        @given(st.integers(min_value=0, max_value=3))
        def test_priority_validation(self, value):
            task = Task(title="Test", priority=value)
            self.assertIsInstance(task.priority, TaskPriority)
    else:
        def test_priority_validation(self):
            for value in [0, 1, 2, 3]:
                with self.subTest(priority=value):
                    task = Task(title="Test", priority=value)
                    self.assertIsInstance(task.priority, TaskPriority)
    
    # 业务逻辑测试
    @patch('mutil_task.core.task.logger')
    def test_cancel_operation(self, mock_logger):
        task = Task(title="Test", status=TaskStatus.QUEUED)
        self.assertTrue(task.cancel())
        mock_logger.warning.assert_not_called()

class TestConcurrency(unittest.TestCase):
    def test_atomic_timestamp_update(self):
        task = Task(title="Concurrency Test")
        original_time = task.updated_at
        task._update_timestamp()
        self.assertGreater(task.updated_at, original_time)

class TestSerialization(unittest.TestCase):
    def test_json_roundtrip(self):
        original = Task(title="Serial Test", priority=TaskPriority.HIGH)
        json_str = original.model_dump_json()
        restored = Task(**json.loads(json_str))
        self.assertEqual(original.title, restored.title)
        self.assertEqual(original.priority, restored.priority)

class TestTimezoneHandling(unittest.TestCase):
    def test_timezone_conversion(self):
        # 测试UTC+8到UTC转换
        task1 = Task(
            title="UTC+8 Test",
            created_at="2025-01-01T00:00:00+08:00"
        )
        self.assertEqual(task1.created_at.hour, 16)  # UTC时间应为前一日16:00
        self.assertEqual(task1.created_at.tzinfo, timezone.utc)
        
        # 测试UTC时间保持
        task2 = Task(
            title="UTC Test",
            created_at="2025-01-01T00:00:00Z"
        )
        self.assertEqual(task2.created_at.hour, 0)
        self.assertEqual(task2.created_at.tzinfo, timezone.utc)
        
        # 测试不带时区应报错
        with self.assertRaises(ValueError):
            Task(title="No TZ Test", created_at="2025-01-01T00:00:00")

if __name__ == '__main__':
    unittest.main(verbosity=2)