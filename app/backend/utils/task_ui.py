"""
任务状态面板渲染工具
功能：
1. 生成ASCII风格状态面板
2. 动态进度条显示
3. 操作按钮生成
"""
import math
from datetime import datetime
from typing import Optional
from ..models.core.task import Task, TaskStatus

# 进度条字符集
PROGRESS_BLOCKS = ['█', '▌', '░']

def get_progress_bar(progress: float, width: int = 10) -> str:
    """
    生成ASCII进度条(带百分比)
    :param progress: 自动裁剪到0-1范围
    :param width: 进度条总宽度(字符数)
    :return: 如"█████ 65%"
    """
    progress = max(0.0, min(1.0, progress))
    filled = int(progress * width)
    return f"{PROGRESS_BLOCKS[0] * filled} {progress*100:.0f}%"

def get_status_display(task: Task) -> str:
    """确保队列位置正确显示"""
    status = task.status
    if isinstance(status, int):
        try:
            status = TaskStatus(status)
        except ValueError:
            return f"未知状态({status})"
    
    # 特别处理排队状态
    if status == TaskStatus.QUEUED:
        pos = task.queue_position if hasattr(task, 'queue_position') else 0
        total = task.queue_total if hasattr(task, 'queue_total') else 0
        return f"🟡排队中({pos}/{total})"
    
    status_map = {
        TaskStatus.PENDING: "🟠待处理",
        TaskStatus.RUNNING: "🔴执行中",
        TaskStatus.COMPLETED: "🟢完成 ✓",
        TaskStatus.FAILED: "⚠️失败", 
        TaskStatus.CANCELLED: "⚫已取消"
    }
    return status_map.get(status, str(status))

def format_timestamp(dt: datetime) -> str:
    """统一时间格式化 (精确到秒)"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt.second > 0 else dt.strftime("%Y-%m-%d %H:%M")

def generate_task_row(task: Task) -> str:
    """
    生成单行任务信息（新版无操作区）
    格式：
    │ ID │ 描述      │ 进度    │ 状态          │ 时间信息               │
    """
    time_info = f"创建: {format_timestamp(task.created_at)}{'':<8}更新: {format_timestamp(task.updated_at)}"
    
    return (
        f"│ #{task.id[:6]} │ {task.title[:16]:<16} │ "
        f"{get_progress_bar(task.progress):<8} │ "
        f"{get_status_display(task):<14} │ "
        f"{time_info:<24} │"
    )

from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress
from rich.text import Text

def render_full_panel(tasks: list[Task]):
    """使用Rich渲染自动调整列宽的任务面板"""
    console = Console()
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        expand=True
    )
    
    # 动态列配置
    table.add_column("ID", width=8)
    table.add_column("任务", min_width=12, ratio=1)
    table.add_column("进度", width=10)
    table.add_column("状态", min_width=14)
    table.add_column("创建时间", width=12)
    table.add_column("更新时间", width=12)
    
    for task in tasks:
        progress = Progress(BarColumn(bar_width=None))
        progress.add_task("", completed=task.progress*100)
        
        row = [
            task.id[:6],
            Text(task.title[:16]),
            progress,
            Text(get_status_display(task), style=status_style(task.status)),
            format_timestamp(task.created_at),
            format_timestamp(task.updated_at)
        ]
        
        if task.description:
            table.add_row(*row)
            table.add_row("", Text(task.description[:32], style="dim"), "", "", "", "")
        else:
            table.add_row(*row)
    
    console.print(Panel.fit(table, title="任务队列监控"))

def status_style(status: int) -> str:
    """获取状态对应颜色样式"""
    styles = {
        TaskStatus.QUEUED: "yellow",
        TaskStatus.RUNNING: "red",
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "bold red",
        TaskStatus.PENDING: "orange1"
    }
    return styles.get(status, "")