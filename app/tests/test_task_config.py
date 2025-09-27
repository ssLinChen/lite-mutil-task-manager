import unittest
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.backend.models.core.task_config import (
    TaskConfig, 
    ParamDefinition, 
    ParamType,
    ParameterValidationError
)
import threading

class TestTaskConfig(unittest.TestCase):
    def setUp(self):
        self.config = TaskConfig(name="test_config")
        self.sample_param = ParamDefinition(
            name="batch_size",
            type=ParamType.INTEGER,
            description="Processing batch size",
            required=True,
            default=100,
            constraints={"min": 1, "max": 1000}
        )

    def test_add_and_validate_parameter(self):
        """测试参数添加与验证"""
        self.config.add_param(self.sample_param)
        
        # 验证正常输入
        validated = self.config.validate_input({"batch_size": 200})
        self.assertEqual(validated["batch_size"], 200)
        
        # 测试默认值
        validated = self.config.validate_input({})
        self.assertEqual(validated["batch_size"], 100)
        
        # 测试类型转换
        validated = self.config.validate_input({"batch_size": "50"})
        self.assertEqual(validated["batch_size"], 50)

    def test_dynamic_parameter_feed(self):
        """测试动态参数注入"""
        self.config.add_param(self.sample_param)
        
        # 添加动态参数源
        feed_count = 0
        def dynamic_feed():
            nonlocal feed_count
            feed_count += 1
            return feed_count * 100
            
        self.config.feed_param_config("batch_size", dynamic_feed)
        
        # 验证动态获取
        validated = self.config.validate_input({})
        self.assertEqual(validated["batch_size"], 100)
        
        validated = self.config.validate_input({})
        self.assertEqual(validated["batch_size"], 200)

    def test_thread_safety(self):
        """测试线程安全操作"""
        self.config.add_param(self.sample_param)
        
        results = []
        def worker():
            try:
                result = self.config.validate_input({"batch_size": 300})
                results.append(result["batch_size"])
            except Exception as e:
                results.append(str(e))
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # 验证所有线程都成功执行
        self.assertEqual(len(results), 10)
        self.assertTrue(all(r == 300 for r in results))

    def test_parameter_constraints(self):
        """测试参数约束验证"""
        self.config.add_param(ParamDefinition(
            name="temperature",
            type=ParamType.FLOAT,
            constraints={"min": 0.0, "max": 1.0}
        ))
        
        # 边界值测试
        self.assertAlmostEqual(
            self.config.validate_input({"temperature": 1.0})["temperature"],
            1.0
        )
        self.assertAlmostEqual(
            self.config.validate_input({"temperature": 0.0})["temperature"],
            0.0
        )
        
        # 超出范围测试
        with self.assertRaises(ParameterValidationError):
            self.config.validate_input({"temperature": 1.1})
        with self.assertRaises(ParameterValidationError):
            self.config.validate_input({"temperature": -0.1})
            
        # 类型转换测试
        self.assertAlmostEqual(
            self.config.validate_input({"temperature": "0.5"})["temperature"],
            0.5
        )

    def test_json_parameter(self):
        """测试JSON类型参数"""
        self.config.add_param(ParamDefinition(
            name="filters",
            type=ParamType.JSON,
            default='{"active": true}'
        ))
        
        validated = self.config.validate_input({"filters": '{"active": false}'})
        self.assertFalse(validated["filters"]["active"])
        
        # 测试默认值转换
        validated = self.config.validate_input({})
        self.assertTrue(validated["filters"]["active"])

if __name__ == '__main__':
    unittest.main()