import json
import asyncio
from typing import Dict, List, Optional, Any
from websockets import serve
from websockets.server import WebSocketServerProtocol
from websockets.typing import Data
from src.task_manager import Task, TaskManager, TaskStatus

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self, task_manager: TaskManager, host: str = "127.0.0.1", port: int = 9000):
        self.task_manager = task_manager
        self.host = host
        self.port = port
        self.server = None
    
    async def start_server(self, port: int = 9000):
        """启动WebSocket服务器"""
        self.server = await serve(self._websocket_handler, self.host, self.port)
        print(f"WebSocket服务器启动在 ws://{self.host}:{self.port}")
        return self.server
    
    async def stop_server(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket服务器已停止")
    
    async def _websocket_handler(self, websocket: WebSocketServerProtocol, path: str):
        """处理WebSocket连接"""
        try:
            task_id = path.split('/')[-1]
            task = self.task_manager._get_task(task_id)
            
            if not task:
                await websocket.close(code=1008, reason="Task not found")
                return
                
            task.add_connection(websocket)
            print(f"新WebSocket连接: 任务 {task_id}")
            
            try:
                # 发送初始状态
                await self._send_initial_state(websocket, task)
                
                # 保持连接活跃，处理客户端消息
                async for message in websocket:
                    await self._handle_client_message(websocket, task, message)
                    
            except Exception as e:
                print(f"WebSocket处理错误: {e}")
            finally:
                await self._cleanup_connection(task, websocket, task_id)
                
        except Exception as e:
            print(f"WebSocket处理全局错误: {e}")
    
    async def _send_initial_state(self, websocket: WebSocketServerProtocol, task: Task):
        """发送初始任务状态"""
        await websocket.send(json.dumps({
            "event": "initial_state",
            "status": task.status.value
        }))
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, task: Task, message: Data):
        """处理客户端消息"""
        try:
            # 将消息转换为字符串处理
            if isinstance(message, bytes):
                message_str = message.decode('utf-8')
            else:
                message_str = message
                
            data = json.loads(message_str)
            print(f"收到客户端消息: {data}")
            # 根据消息类型进行相应处理
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"消息处理错误: {e}")
    
    async def _cleanup_connection(self, task: Task, websocket: WebSocketServerProtocol, task_id: str):
        """清理连接资源"""
        if websocket in task.connections:
            task.connections.remove(websocket)
            print(f"清理连接: 任务 {task_id}")
    
    async def broadcast_to_task(self, task_id: str, message: Dict[str, Any]):
        """向特定任务的所有连接广播消息"""
        task = self.task_manager._get_task(task_id)
        if not task or not task.connections:
            return
        
        message_json = json.dumps(message)
        for ws in task.connections:
            try:
                await ws.send(message_json)
            except Exception as e:
                print(f"广播消息失败: {e}")
    
    async def notify_status_change(self, task: Task, old_status: str, new_status: str):
        """通知状态变更"""
        await self.broadcast_to_task(task.id, {
            "event": "status_update",
            "task_id": task.id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": str(asyncio.get_event_loop().time())
        })
    
    async def notify_error(self, task: Task, error_msg: str):
        """通知错误信息"""
        await self.broadcast_to_task(task.id, {
            "event": "task_error",
            "task_id": task.id,
            "error": error_msg,
            "timestamp": str(asyncio.get_event_loop().time())
        })

# 使用示例
async def main():
    # 创建任务管理器
    task_manager = TaskManager()
    
    # 创建WebSocket管理器
    ws_manager = WebSocketManager(task_manager)
    
    try:
        # 启动WebSocket服务器
        await ws_manager.start_server()
        
        # 启动任务处理器
        await task_manager.start()
        
        # 保持运行
        await asyncio.Future()
        
    except KeyboardInterrupt:
        print("服务器被用户中断")
    finally:
        await task_manager.shutdown()
        await ws_manager.stop_server()

if __name__ == "__main__":
    asyncio.run(main())