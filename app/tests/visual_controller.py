"""
任务可视化控制器
基于事件总线实现任务状态实时监控和可视化
"""
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from app.backend.utils.event_bus import EventBus, TaskEventType
from app.backend.utils.task_ui import render_full_panel
from app.backend.models.core.task import Task, TaskStatus

class TestVisualController:
    """测试可视化控制器，用于监控任务状态变更"""
    
    def __init__(self, test_name: str):
        """
        初始化控制器
        :param test_name: 测试名称，用于生成报告目录
        """
        self.test_name = test_name
        self.tasks: Dict[str, Task] = {}  # 任务ID到任务对象的映射
        self.snapshots = []  # 状态快照列表
        
        # 创建报告目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = f"test_reports/{timestamp}_{test_name}"
        os.makedirs(self.report_dir, exist_ok=True)
        
        # 订阅事件
        self._subscribe_events()
        
    def _subscribe_events(self):
        """订阅任务相关事件"""
        EventBus.subscribe(TaskEventType.STATUS_CHANGED, self._on_task_status_changed)
        EventBus.subscribe(TaskEventType.PROGRESS_UPDATED, self._on_task_progress)
        EventBus.subscribe(TaskEventType.CANCELLED, self._on_task_cancelled)
        EventBus.subscribe(TaskEventType.CREATED, self._on_task_created)
        
    def _on_task_status_changed(self, event_data: dict):
        """处理任务状态变更事件"""
        task = event_data['task']
        self.tasks[task.id] = task
        self._update_ui(f"状态变更: {event_data['old_status']} -> {event_data['new_status']}")
        
    def _on_task_progress(self, event_data: dict):
        """处理任务进度更新事件"""
        task = event_data['task']
        self.tasks[task.id] = task
        self._update_ui(f"进度更新: {event_data['old_progress']*100:.1f}% -> {event_data['new_progress']*100:.1f}%")
        
    def _on_task_cancelled(self, event_data: dict):
        """处理任务取消事件"""
        task = event_data['task']
        self.tasks[task.id] = task
        self._update_ui("任务已取消")
        
    def _on_task_created(self, event_data: dict):
        """处理任务创建事件"""
        task = event_data['task']
        self.tasks[task.id] = task
        self._update_ui("任务已创建")
    
    def track_task(self, task: Task):
        """
        手动跟踪任务
        :param task: 要跟踪的任务对象
        """
        self.tasks[task.id] = task
        self._update_ui(f"开始跟踪任务: {task.title}")
        
        # 发布任务创建事件（如果尚未发布）
        EventBus.publish(TaskEventType.CREATED, {
            'task': task,
            'timestamp': datetime.now()
        })
    
    def _update_ui(self, event_description: str = ""):
        """
        更新UI并保存快照
        :param event_description: 事件描述
        """
        # 获取当前所有任务
        tasks = list(self.tasks.values())
        
        # 使用Rich渲染面板
        from rich.console import Console
        console = Console()
        console.clear()
        
        # 显示事件描述
        if event_description:
            console.print(f"[bold cyan]事件:[/] {event_description}")
            
        # 渲染任务面板
        render_full_panel(tasks)
        
        # 保存快照
        self._save_snapshot(tasks, event_description)
    
    def _save_snapshot(self, tasks: List[Task], event_description: str):
        """
        保存状态快照
        :param tasks: 任务列表
        :param event_description: 事件描述
        """
        timestamp = datetime.now()
        
        # 创建快照
        snapshot = {
            'timestamp': timestamp,
            'event': event_description,
            'tasks': [task.model_dump() for task in tasks]
        }
        self.snapshots.append(snapshot)
        
        # 保存HTML快照
        from rich.console import Console
        console = Console(record=True)
        
        # 添加事件描述
        if event_description:
            console.print(f"[bold cyan]事件:[/] {event_description}")
            
        # 渲染任务面板
        render_full_panel(tasks)
        
        # 保存HTML
        html = console.export_html()
        snapshot_path = f"{self.report_dir}/snapshot_{timestamp.strftime('%H%M%S_%f')}.html"
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def generate_report(self):
        """生成测试报告"""
        # 创建索引页面
        index_path = f"{self.report_dir}/index.html"
        
        # 生成HTML报告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>测试报告: {self.test_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .snapshot-list {{ list-style-type: none; padding: 0; }}
                .snapshot-item {{ 
                    margin: 10px 0; 
                    padding: 10px; 
                    border: 1px solid #ddd; 
                    border-radius: 4px;
                }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
                .event {{ font-weight: bold; color: #0066cc; }}
            </style>
        </head>
        <body>
            <h1>测试报告: {self.test_name}</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>快照数量: {len(self.snapshots)}</p>
            
            <h2>任务状态时间线</h2>
            <ul class="snapshot-list">
        """
        
        # 添加快照列表
        for i, snapshot in enumerate(self.snapshots):
            timestamp = snapshot['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            event = snapshot['event']
            snapshot_file = f"snapshot_{snapshot['timestamp'].strftime('%H%M%S_%f')}.html"
            
            html_content += f"""
                <li class="snapshot-item">
                    <div class="timestamp">{timestamp}</div>
                    <div class="event">{event}</div>
                    <a href="{snapshot_file}" target="_blank">查看详情</a>
                </li>
            """
        
        html_content += """
            </ul>
        </body>
        </html>
        """
        
        # 写入索引文件
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return index_path
    
    def cleanup(self):
        """清理资源"""
        # 取消事件订阅
        EventBus.unsubscribe(TaskEventType.STATUS_CHANGED, self._on_task_status_changed)
        EventBus.unsubscribe(TaskEventType.PROGRESS_UPDATED, self._on_task_progress)
        EventBus.unsubscribe(TaskEventType.CANCELLED, self._on_task_cancelled)
        EventBus.unsubscribe(TaskEventType.CREATED, self._on_task_created)