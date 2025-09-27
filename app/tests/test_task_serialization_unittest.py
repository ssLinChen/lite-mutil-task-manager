import unittest
from datetime import datetime, timezone
from app.backend.models.core.task import Task, TaskStatus

class TestTaskSerialization(unittest.TestCase):
    def setUp(self):
        self.sample_task = Task(
            title="测试任务",
            description="序列化测试",
            status=TaskStatus.QUEUED,
            progress=0.5,
            queue_position=1,
            queue_total=3
        )
        self.fixed_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def test_task_serialization(self):
        """测试任务序列化为字典"""
        data = self.sample_task.model_dump()
        self.assertEqual(data["title"], "测试任务")
        self.assertEqual(data["status"], "queued")
        self.assertEqual(data["progress"], 0.5)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_task_json_serialization(self):
        """测试任务序列化为JSON"""
        task = Task(title="JSON测试", status=TaskStatus.RUNNING)
        json_str = task.model_dump_json()
        
        # 更灵活的断言，处理JSON格式化差异
        self.assertIn('"title":"JSON测试"', json_str.replace(" ", ""))
        # 状态已正确序列化为字符串
        self.assertIn('"status":"running"', json_str.replace(" ", ""))

    def test_task_deserialization(self):
        """测试从字典反序列化任务"""
        data = self.sample_task.model_dump()
        new_task = Task.model_validate(data)
        
        self.assertEqual(new_task.title, self.sample_task.title)
        # 直接比较整数值
        expected = self.sample_task.status if isinstance(self.sample_task.status, int) else self.sample_task.status.value
        actual = new_task.status.value
        self.assertEqual(actual, expected)
        self.assertEqual(new_task.progress, self.sample_task.progress)
        self.assertIsInstance(new_task.created_at, datetime)
        self.assertIsInstance(new_task.updated_at, datetime)

    def test_invalid_deserialization(self):
        """测试无效数据反序列化"""
        with self.assertRaises(ValueError):
            Task.model_validate({"title": "", "status": "invalid"})

    def test_status_enum_serialization(self):
        """测试状态枚举序列化"""
        task = Task(title="枚举测试", status=TaskStatus.PENDING)
        data = task.model_dump()
        self.assertEqual(data["status"], "pending")
        
        new_task = Task.model_validate(data)
        self.assertEqual(new_task.status, TaskStatus.PENDING)

    def test_timestamp_serialization(self):
        """测试时间戳序列化"""
        task = Task(
            title="时间测试",
            created_at=self.fixed_time,
            updated_at=self.fixed_time
        )
        data = task.model_dump()
        self.assertEqual(data["created_at"], "2025-01-01T00:00:00+00:00")
        self.assertEqual(data["updated_at"], "2025-01-01T00:00:00+00:00")

if __name__ == "__main__":
    unittest.main()