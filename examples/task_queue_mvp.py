import sys
from pathlib import Path
from typing import Dict
sys.path.append(str(Path(__file__).parent.parent))  # 添加项目根目录到路径

from mutil_task.core.task import Task, TaskPriority, TaskStatus, TaskExecutor
from mutil_task.queue.task_queue import TaskQueue
from mutil_task.utils.event_bus import EventBus
import threading

class TimedTaskExecutor(TaskExecutor):
    """支持可中断的定时执行器"""
    def __init__(self, seconds: int):
        self.seconds = seconds
        self._stop_event = threading.Event()
        
    def execute_task(self, task: Task) -> str:
        import time
        start = time.time()
        for i in range(self.seconds):
            if self._stop_event.is_set():
                return f"任务被中断，已执行: {i}秒"
            time.sleep(1)
            task.update_progress((i+1)/self.seconds)
            if task.status == TaskStatus.CANCELLED:
                return "任务取消"
        return f"精确执行: {time.time()-start:.1f}秒"
        
    def cancel(self):
        """外部调用以中断任务"""
        self._stop_event.set()



from mutil_task.utils.task_ui import render_full_panel
import time

def run_mvp():
    """任务队列演示流程"""
    queue = TaskQueue(max_workers=1)

    
    # 创建任务
    tasks = [
        # 长时间执行任务 - 测试执行超时
        Task(
            title="长时间任务(10秒)", 
            priority=TaskPriority.HIGH,
            execution_timeout=3,  # 3秒执行超时
            description="执行超时测试（3秒超时/10秒执行）",
            executor=TimedTaskExecutor(10)  # 标准执行器实例
        ),


        
        # 专门测试执行超时的任务
        Task(
            title="执行超时测试任务",
            priority=TaskPriority.HIGH,
            execution_timeout=5,  # 5秒执行超时
            description="专门测试执行超时（5秒超时/8秒执行）",
            executor=TimedTaskExecutor(8)  # 标准执行器实例
        ),


        
        # 低优先级任务 - 测试等待超时
        Task(
            title="低优先级任务",
            priority=TaskPriority.LOW,
            queue_timeout=2,  # 2秒等待超时
            description="等待超时测试（2秒）",
            executor=TimedTaskExecutor(5)  # 标准执行器实例
        ),


        
        # 正常任务作为对照
        Task(
            title="正常任务",
            priority=TaskPriority.NORMAL,
            description="正常任务（无超时）"
        )
    ]




    # 入队逻辑
    print("开始任务入队...")
    print("=" * 50)
    
    for task in tasks:
        try:
            queue.enqueue(task)
            print(f"✅ 已入队: {task.title}")
            try:
                render_full_panel([task])
            except Exception as e:
                print(f"⚠️ 可视化渲染失败: {str(e)}")
                
        except ValueError as e:
            print(f"❌ 入队失败 {task.title}: {str(e)}")
        except Exception as e:
            print(f"❌ 未知错误 {task.title}: {str(e)}")

    
    # 增强版监控逻辑
    start_time = time.time()
    print("\n任务执行监控开始:")
    print("=" * 50)
    
    # 监控逻辑 - 每0.5秒更新一次面板
    while len(queue._active_tasks) > 0 or len(queue._heap) > 0:
        start_render = time.time()
        
        # 收集所有任务状态（包括排队、执行中和已完成的任务）
        current_tasks = []

        
        # 添加排队中的任务
        for _, _, task in queue._heap:
            current_tasks.append(task)
            
        # 添加执行中的任务（排除已失败/取消的任务）
        for task in queue._active_tasks.values():
            if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                current_tasks.append(task)

            
        # 添加已完成的任务
        for task in queue._completed_tasks.values():
            current_tasks.append(task)
        
        # 清屏效果（仅在控制台环境）
        if current_tasks:
 
            # 同时尝试使用Rich渲染
            try:
                render_full_panel(current_tasks, queue)
            except Exception as e:
                print(f"Rich渲染失败: {str(e)}")
                
            # 显示准确的队列位置信息
            queued_tasks = []
            for task in current_tasks:
                if task.status == TaskStatus.QUEUED:
                    position, total = queue.get_task_position(task.id)
                    if position is not None:
                        queued_tasks.append(f"{task.title}: 排队中({position}/{total})")
                    else:
                        queued_tasks.append(f"{task.title}: 不在队列中")
            
            if queued_tasks:
                print("队列状态:")
                for task_info in queued_tasks:
                    print(f"  {task_info}")
            
            # 准确统计执行中任务数量（排除失败/取消的任务）
            active_count = sum(1 for t in queue._active_tasks.values() 
                             if t.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED))
            # 确保总间隔为0.5秒
            render_time = time.time() - start_render
            if render_time < 0.5:
                time.sleep(0.5 - render_time)
            
            print(f"当前状态: {len(queue._heap)}等待 | {active_count}执行中 | "
                  f"已完成: {len(queue._completed_tasks)}")


    
    # 最终结果统计
    print("\n" + "=" * 50)
    print(f"所有任务完成! 总耗时: {time.time()-start_time:.2f}秒")
    print("执行顺序:")
    for task_id, task in queue._completed_tasks.items():
        print(f"- {task.title} (优先级: {task.priority.name})")

if __name__ == "__main__":
    run_mvp()