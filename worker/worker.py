"""
FastAPI Worker for CrowdCompute
"""

import asyncio
import json
import uuid
import websockets
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.serializer import deserialize_function, deserialize_data, serialize_data, hex_to_bytes, get_runtime_info
from common.protocol import Message, MessageType
from .dashboard import add_dashboard_route


class WorkerConfig(BaseModel):
    """Worker configuration"""
    worker_id: str
    foreman_url: str = "ws://localhost:9000"
    max_concurrent_tasks: int = 1
    auto_restart: bool = True
    heartbeat_interval: int = 30


class TaskResult(BaseModel):
    """Task execution result"""
    task_id: str
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class FastAPIWorker:
    """FastAPI-based worker for CrowdCompute"""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.current_task: Optional[Dict[str, Any]] = None
        self.task_queue = asyncio.Queue()
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "started_at": datetime.now()
        }
        
        # Create FastAPI app
        self.app = FastAPI(
            title=f"CrowdCompute Worker - {config.worker_id}",
            description="FastAPI-based worker for distributed computing",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        # Add dashboard
        add_dashboard_route(self.app, config.worker_id)
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            """Worker status page"""
            # Convert datetime objects to ISO strings for JSON serialization
            stats_for_json = {
                "tasks_completed": self.stats["tasks_completed"],
                "tasks_failed": self.stats["tasks_failed"],
                "total_execution_time": self.stats["total_execution_time"],
                "started_at": self.stats["started_at"].isoformat()
            }
            
            return {
                "worker_id": self.config.worker_id,
                "status": "online" if self.is_connected else "offline",
                "current_task": self.current_task["task_id"] if self.current_task else None,
                "stats": stats_for_json,
                "config": self.config.dict()
            }
        
        @self.app.get("/stats")
        async def get_stats():
            """Get worker statistics"""
            # Convert datetime objects to ISO strings for JSON serialization
            stats_for_json = {
                "tasks_completed": self.stats["tasks_completed"],
                "tasks_failed": self.stats["tasks_failed"],
                "total_execution_time": self.stats["total_execution_time"],
                "started_at": self.stats["started_at"].isoformat()
            }
            
            return {
                "worker_id": self.config.worker_id,
                "is_connected": self.is_connected,
                "current_task": self.current_task,
                "stats": stats_for_json,
                "uptime": (datetime.now() - self.stats["started_at"]).total_seconds()
            }
        
        @self.app.post("/restart")
        async def restart_worker():
            """Restart worker connection"""
            await self.disconnect()
            await self.connect()
            return {"message": "Worker restarted"}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            try:
                while True:
                    # Send periodic status updates
                    # Convert datetime objects to ISO strings for JSON serialization
                    stats_for_json = {
                        "tasks_completed": self.stats["tasks_completed"],
                        "tasks_failed": self.stats["tasks_failed"],
                        "total_execution_time": self.stats["total_execution_time"],
                        "started_at": self.stats["started_at"].isoformat()
                    }
                    
                    status = {
                        "worker_id": self.config.worker_id,
                        "is_connected": self.is_connected,
                        "current_task": self.current_task,
                        "stats": stats_for_json,
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_text(json.dumps(status))
                    await asyncio.sleep(5)
            except WebSocketDisconnect:
                print("Status WebSocket disconnected")
    
    async def connect(self):
        """Connect to the foreman"""
        try:
            print(f"🔌 Connecting to foreman at {self.config.foreman_url}...")
            self.websocket = await websockets.connect(self.config.foreman_url)
            self.is_connected = True
            print(f"✅ Connected to foreman as worker {self.config.worker_id}")
            
            # Send worker ready message
            ready_message = Message(
                msg_type=MessageType.WORKER_READY,
                data={"worker_id": self.config.worker_id}
            )
            await self.websocket.send(ready_message.to_json())
            
            return True
        except Exception as e:
            print(f"❌ Failed to connect to foreman: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the foreman"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.is_connected = False
        print("🔌 Disconnected from foreman")
    

    
    async def handle_message(self, message: Message):
        """Handle incoming messages from foreman"""
        try:
            if message.type == MessageType.ASSIGN_TASK:
                await self._handle_task_assignment(message)
            elif message.type == MessageType.PING:
                # Respond to ping
                pong_message = Message(
                    msg_type=MessageType.PONG,
                    data={"worker_id": self.config.worker_id}
                )
                await self.websocket.send(pong_message.to_json())
            else:
                print(f"Unknown message type: {message.type}")
                
        except Exception as e:
            print(f"❌ Error handling message: {e}")
    
    async def _handle_task_assignment(self, message: Message):
        """Handle a task assignment from foreman"""
        try:
            task_id = message.data["task_id"]
            job_id = message.job_id
            func_pickle = hex_to_bytes(message.data["func_pickle"])
            task_args = message.data["task_args"]
            
            print(f"📋 Received task {task_id} for job {job_id} | worker_runtime={get_runtime_info()}")
            
            # Set current task
            self.current_task = {
                "task_id": task_id,
                "job_id": job_id
            }
            
            # Execute the task
            result = await self._execute_task(func_pickle, task_args)
            
            # Send result back
            result_message = Message(
                msg_type=MessageType.TASK_RESULT,
                data={
                    "result": result,
                    "task_id": task_id
                },
                job_id=job_id
            )
            await self.websocket.send(result_message.to_json())
            
            print(f"✅ Completed task {task_id}")
            
            # Clear current task
            self.current_task = None
            
        except Exception as e:
            print(f"❌ Error executing task {task_id}: {e}")
            
            # Send error back
            error_message = Message(
                msg_type=MessageType.TASK_ERROR,
                data={
                    "error": str(e),
                    "task_id": task_id
                },
                job_id=job_id
            )
            await self.websocket.send(error_message.to_json())
            
            # Clear current task
            self.current_task = None
    
    async def _execute_task(self, func_pickle: bytes, task_args: List[Any]) -> Any:
        """Execute a task in a safe environment"""
        start_time = datetime.now()
        
        try:
            print(f"🔄 Executing task... | worker_runtime={get_runtime_info()}")
            
            # Deserialize the function
            func = deserialize_function(func_pickle)
            
            # Execute the function with the provided arguments
            if isinstance(task_args, list) and len(task_args) == 1:
                # Single argument
                result = func(task_args[0])
            elif isinstance(task_args, list) and len(task_args) == 2 and isinstance(task_args[1], dict):
                # Function with args and kwargs
                args, kwargs = task_args
                result = func(*args, **kwargs)
            else:
                # Multiple arguments
                result = func(*task_args)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Task completed in {execution_time:.2f}s")
            
            # Update stats
            self.stats["tasks_completed"] += 1
            self.stats["total_execution_time"] += execution_time
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Task execution failed: {e}"
            
            print(f"❌ Task failed: {error_msg}")
            
            # Update stats
            self.stats["tasks_failed"] += 1
            self.stats["total_execution_time"] += execution_time
            
            raise Exception(error_msg)
    
    async def listen_for_tasks(self):
        """Listen for tasks from foreman"""
        while self.is_connected:
            try:
                if not self.websocket:
                    break
                
                # Receive message
                message_data = await self.websocket.recv()
                message = Message.from_json(message_data)
                
                # Handle message
                await self.handle_message(message)
                
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Connection to foreman closed")
                self.is_connected = False
                break
            except Exception as e:
                print(f"❌ Error in task listener: {e}")
                await asyncio.sleep(1)
    
    async def heartbeat(self):
        """Send periodic heartbeat to foreman"""
        while self.is_connected:
            try:
                if self.websocket:
                    # Send heartbeat
                    heartbeat_message = Message(
                        msg_type=MessageType.WORKER_HEARTBEAT,
                        data={
                            "worker_id": self.config.worker_id,
                            "status": "online",
                            "current_task": self.current_task["task_id"] if self.current_task else None
                        }
                    )
                    await self.websocket.send(heartbeat_message.to_json())
                
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                print(f"❌ Error sending heartbeat: {e}")
                break
    
    async def start(self):
        """Start the worker"""
        print(f"🚀 Starting FastAPI Worker: {self.config.worker_id}")
        
        # Connect to foreman
        if not await self.connect():
            if self.config.auto_restart:
                print("🔄 Auto-restart enabled, retrying connection...")
                await asyncio.sleep(5)
                await self.start()
            return
        
        # Start background tasks
        task_listener = asyncio.create_task(self.listen_for_tasks())
        heartbeat_task = asyncio.create_task(self.heartbeat())
        
        try:
            # Keep worker running
            await asyncio.gather(task_listener, heartbeat_task)
        except KeyboardInterrupt:
            print("\n🛑 Worker stopped by user")
        except Exception as e:
            print(f"❌ Worker error: {e}")
        finally:
            await self.disconnect()
    
    def run(self):
        """Run the worker with FastAPI server"""
        import uvicorn
        
        print(f"🚀 Starting FastAPI Worker Server: {self.config.worker_id}")
        print("=" * 60)
        print(f"👤 Worker ID:     {self.config.worker_id}")
        print(f"🔌 Foreman URL:   {self.config.foreman_url}")
        print(f"🌐 Web Interface: http://localhost:8001")
        print(f"📊 API Docs:      http://localhost:8001/docs")
        print("=" * 60)
        
        # Run FastAPI server with worker in background
        try:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=8001,
                log_level="info",
                loop="asyncio"
            )
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
    
    async def run_with_worker(self):
        """Run the worker with FastAPI server (async version)"""
        import uvicorn
        
        print(f"🚀 Starting FastAPI Worker Server: {self.config.worker_id}")
        print("=" * 60)
        print(f"👤 Worker ID:     {self.config.worker_id}")
        print(f"🔌 Foreman URL:   {self.config.foreman_url}")
        print(f"🌐 Web Interface: http://localhost:8001")
        print(f"📊 API Docs:      http://localhost:8001/docs")
        print("=" * 60)
        
        # Start worker in background
        worker_task = asyncio.create_task(self.start())
        
        # Create server config
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
        
        # Create and run server
        server = uvicorn.Server(config)
        try:
            await server.serve()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        finally:
            worker_task.cancel()
