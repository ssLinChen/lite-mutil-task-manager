import unittest
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.backend.models.core.task_result import (
    TaskResult,
    ArtifactRef,
    ArtifactStorageType,
    ErrorDetail
)

class TestTaskResult(unittest.TestCase):
    def setUp(self):
        self.task_id = "test_task_123"
        self.result = TaskResult(
            task_id=self.task_id,
            execution_id="exec_123",
            status="completed"
        )

    def test_initialization(self):
        self.assertEqual(self.result.task_id, self.task_id)
        self.assertEqual(self.result.artifacts, {})
        self.assertEqual(self.result.timeline, {})
        self.assertEqual(self.result.metrics, {})

    def test_add_artifact(self):
        artifact = ArtifactRef(
            storage_type=ArtifactStorageType.LOCAL,
            uri="/tmp/output.log",
            checksum="a"*64  # Mock checksum
        )
        self.result.artifacts["log"] = artifact
        
        self.assertEqual(len(self.result.artifacts), 1)
        self.assertEqual(self.result.artifacts["log"].uri, "/tmp/output.log")

    def test_record_timeline(self):
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        self.result.timeline["start"] = start_time
        self.result.timeline["end"] = end_time
        
        self.assertEqual(len(self.result.timeline), 2)
        self.assertLessEqual(
            (self.result.timeline["end"] - self.result.timeline["start"]).total_seconds(),
            300
        )

    def test_add_error(self):
        error = ErrorDetail(
            error_type="Validation",
            message="Test error",
            stack_trace="Traceback...",
            context={"code": "E001"}
        )
        self.result.error = error
        
        self.assertIsNotNone(self.result.error)
        self.assertEqual(self.result.error.error_type, "Validation")
        self.assertEqual(self.result.error.message, "Test error")

    def test_boundary_conditions(self):
        """测试边界条件和异常情况"""
        # 测试空数据
        with self.assertRaises(ValueError):
            ArtifactRef.from_data(b"", ArtifactStorageType.LOCAL, "/tmp/test")
        
        # 测试无效URI
        with self.assertRaises(ValueError):
            ArtifactRef(
                storage_type=ArtifactStorageType.LOCAL,
                uri="",
                checksum="a"*64
            )
        
        # 测试重复时间事件
        self.result.record_timeline_event("start")
        with self.assertRaises(ValueError):
            self.result.record_timeline_event("start")
        
        # 测试负值指标
        with self.assertRaises(ValueError):
            self.result.add_metric("invalid", -1)
        
        # 测试重复产物名称
        artifact = ArtifactRef(
            storage_type=ArtifactStorageType.LOCAL,
            uri="/tmp/test",
            checksum="a"*64
        )
        self.result.add_artifact("test", artifact)
        with self.assertRaises(ValueError):
            self.result.add_artifact("test", artifact)

    def test_performance(self):
        """性能基准测试"""
        import time
        
        # 时间线记录性能
        start = time.time()
        for i in range(1000):
            self.result.record_timeline_event(f"perf_{i}")
        timeline_time = time.time() - start
        self.assertLess(timeline_time, 0.1, 
                       f"Timeline recording too slow: {timeline_time:.3f}s")
        
        # 产物添加性能
        artifact = ArtifactRef(
            storage_type=ArtifactStorageType.LOCAL,
            uri="/tmp/perf",
            checksum="a"*64
        )
        start = time.time()
        for i in range(1000):
            self.result.add_artifact(f"art_{i}", artifact)
        artifact_time = time.time() - start
        self.assertLess(artifact_time, 0.2,
                       f"Artifact adding too slow: {artifact_time:.3f}s")

    def test_add_metrics(self):
        self.result.metrics["duration"] = 120.5
        self.result.metrics["items_processed"] = 100
        
        self.assertEqual(len(self.result.metrics), 2)
        self.assertEqual(self.result.metrics["duration"], 120.5)

if __name__ == '__main__':
    unittest.main()
