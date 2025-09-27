#!/usr/bin/env python3
"""
Refactored Task Manager Example - Combines WebSocket and Continuous Monitoring

Features:
1. Create task manager with WebSocket interface
2. Real-time task status monitoring
3. Persist task data to JSON file
"""
import sys
import os

# 调试路径设置
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# 验证模块路径
task_manager_path = os.path.join(base_dir, 'src', 'task_manager.py')
print(f"任务管理器模块路径: {task_manager_path}")
print(f"文件存在: {os.path.exists(task_manager_path)}")

import asyncio
import json
import os
import logging
from dataclasses import asdict
from typing import Dict, List, Optional

# 增强日志配置
try:
    from rich.logging import RichHandler
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    USE_COLOR = True
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    USE_COLOR = False

logger = logging.getLogger(__name__)

def log_status_change(task_id: str, old: str, new: str):
    """彩色化任务状态变更日志"""
    if USE_COLOR:
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.text import Text
        logger.info(Columns([
            Panel(
                Text(f"任务 {task_id[:8]}", style="bold"),
                title="ID"
            ),
            Panel(
                Text(f"{old} → ", style="yellow") + 
                Text(new, style="green" if new == "COMPLETED" else "red"),
                title="状态变更"
            )
        ], width=30))
    else:
        logger.info(f"任务状态变更: {task_id[:8]} {old}→{new}")

class TaskManagerConfig:
    """任务管理器配置"""
    def __init__(
        self,
        storage_file: str = "tasks.json",
        max_concurrent: int = 2,
        websocket_port: int = 9000
    ):
        self.storage_file = os.path.abspath(storage_file)
        self.max_concurrent = max_concurrent
        self.websocket_port = websocket_port

async def setup_task_manager(config: TaskManagerConfig):
    """初始化任务管理器"""
    from src.task_manager import TaskManager, TaskStatus
    from src.websocket_manager import WebSocketManager
    
    # 创建管理器实例
    manager = TaskManager(config.storage_file, config.max_concurrent)
    ws_manager = WebSocketManager(manager)
    
    # 注册回调
    def on_status_change(task_id: str, old: TaskStatus, new: TaskStatus):
        logger.info(f"任务状态变更: {task_id[:8]} {old.value}→{new.value}")
        
    def on_error(task_id: str, error: str):
        logger.error(f"任务错误: {task_id[:8]} - {error}")
    
    manager.register_status_change_callback(on_status_change)
    manager.register_task_error_callback(on_error)
    
    return manager, ws_manager

async def run_demo_workflow(manager, ws_manager, config: TaskManagerConfig):
    """运行示例工作流"""
    from src.task_manager import TaskStatus
    
    try:
        # 启动服务
        await ws_manager.start_server(config.websocket_port)
        await manager.start()
        logger.info(f"WebSocket服务启动在 ws://localhost:{config.websocket_port}")
        
        # 创建示例任务
        tasks = await create_sample_tasks(manager)
        logger.info(f"已创建 {len(tasks)} 个示例任务")
        
        # 监控任务状态
        await monitor_tasks(manager, tasks)
        
        # 清理和持久化
        await shutdown_services(manager, ws_manager)
        
    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        raise

async def create_sample_tasks(manager) -> List[str]:
    """创建示例任务集合"""
    from src.task_manager import TaskStatus
    
    async def simple_task():
        await asyncio.sleep(5)
        
    async def failing_task():
        await asyncio.sleep(3)
        raise ValueError("模拟任务失败")
    
    async def long_task():
        await asyncio.sleep(10)
    
    tasks = [
        manager.create_task("简单任务", simple_task, priority="high"),
        manager.create_task("失败任务", failing_task, priority="medium"),
        manager.create_task("长时间任务", long_task, priority="low")
    ]
    
    return [t.id for t in tasks]

async def monitor_tasks(manager, task_ids: List[str]):
    """监控任务状态直到全部完成"""
    from src.task_manager import TaskStatus
    
    while True:
        completed = sum(
            1 for tid in task_ids 
            if manager.get_task(tid).status in [
                TaskStatus.COMPLETED, 
                TaskStatus.FAILED,
                TaskStatus.CANCELLED
            ]
        )
        
        if completed == len(task_ids):
            break
            
        await asyncio.sleep(0.5)
        logger.info(f"任务进度: {completed}/{len(task_ids)}")

async def shutdown_services(manager, ws_manager):
    """优雅关闭服务"""
    logger.info("正在关闭服务...")
    await manager.shutdown()
    await ws_manager.stop_server()
    logger.info("服务已关闭")

def main():
    """主执行函数"""
    # 加载配置
    config = TaskManagerConfig(
        storage_file=os.path.join("examples", "merged_tasks.json"),
        max_concurrent=2,
        websocket_port=9000
    )
    
    # 打印配置
    logger.info("任务管理器配置:")
    logger.info(f"  存储文件: {config.storage_file}")
    logger.info(f"  最大并发: {config.max_concurrent}")
    logger.info(f"  WebSocket端口: {config.websocket_port}")
    
    # 运行工作流
    asyncio.run(run_workflow(config))

async def run_workflow(config: TaskManagerConfig):
    """运行完整工作流"""
    manager, ws_manager = await setup_task_manager(config)
    try:
        await run_demo_workflow(manager, ws_manager, config)
    finally:
        await shutdown_services(manager, ws_manager)

if __name__ == "__main__":
    main()