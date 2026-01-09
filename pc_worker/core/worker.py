"""
FastAPI Worker for CrowdCompute.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import websockets
from fastapi import WebSocketDisconnect

from common.protocol import Message, MessageType
from common.serializer import deserialize_function_for_PC, get_runtime_info
from ..config import WorkerConfig
from ..schema.models import TaskResult
from .app import create_app


class FastAPIWorker:
    """FastAPI-based worker for CrowdCompute."""

    websocket_update_interval: int = 5

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
            "started_at": datetime.now(),
        }

        # Build FastAPI application with routes and dashboard
        self.app = create_app(self)

    # ---------- Public serialization helpers ----------
    def _stats_for_json(self) -> Dict[str, Any]:
        return {
            "tasks_completed": self.stats["tasks_completed"],
            "tasks_failed": self.stats["tasks_failed"],
            "total_execution_time": self.stats["total_execution_time"],
            "started_at": self.stats["started_at"].isoformat(),
        }

    def serialize_status(self) -> Dict[str, Any]:
        return {
            "worker_id": self.config.worker_id,
            "status": "online" if self.is_connected else "offline",
            "current_task": self.current_task["task_id"] if self.current_task else None,
            "stats": self._stats_for_json(),
            "config": self.config.dict(),
        }

    def serialize_stats(self) -> Dict[str, Any]:
        return {
            "worker_id": self.config.worker_id,
            "is_connected": self.is_connected,
            "current_task": self.current_task,
            "stats": self._stats_for_json(),
            "uptime": (datetime.now() - self.stats["started_at"]).total_seconds(),
        }

    def serialize_ws_status(self) -> Dict[str, Any]:
        status = self.serialize_stats()
        status["timestamp"] = datetime.now().isoformat()
        return status

    # ---------- Logging helper ----------
    def log(self, message: str) -> None:
        print(message)

    # ---------- Connection management ----------
    async def connect(self) -> bool:
        """Connect to the foreman WebSocket server."""
        try:
            print(f"🔌 Connecting to foreman at {self.config.foreman_url}/worker/ws...")

            self.websocket = await websockets.connect(
                f"{self.config.foreman_url}/worker/ws"
            )
            self.is_connected = True

            print(f"✅ Connected to foreman as {self.config.worker_id}")

            # Send initial ready message
            ready_message = Message(
                msg_type=MessageType.WORKER_READY,
                data={"worker_id": self.config.worker_id},
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

    async def restart(self) -> None:
        """Restart the worker connection to the foreman."""
        await self.disconnect()
        await self.connect()

    # ---------- Message handling ----------
    async def handle_message(self, message: Message):
        """Handle incoming messages from foreman"""
        try:
            if message.type == MessageType.ASSIGN_TASK:
                await self._handle_task_assignment(message)
            elif message.type == MessageType.PING:
                # Respond to ping
                pong_message = Message(
                    msg_type=MessageType.PONG, data={"worker_id": self.config.worker_id}
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
            func_code = message.data["func_code"]
            task_args = message.data["task_args"]

            print(
                f"📋 Received task {task_id} for job {job_id} | worker_runtime={get_runtime_info()}"
            )

            # Set current task
            self.current_task = {"task_id": task_id, "job_id": job_id}

            # Execute the task
            result = await self._execute_task(func_code, task_args)

            # Send result back
            result_message = Message(
                msg_type=MessageType.TASK_RESULT,
                data={"result": result, "task_id": task_id},
                job_id=job_id,
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
                data={"error": str(e), "task_id": task_id},
                job_id=job_id,
            )
            await self.websocket.send(error_message.to_json())

            # Clear current task
            self.current_task = None

    # ---------- Task execution ----------
    async def _execute_task(self, func_code: str, task_args: List[Any]) -> Any:
        """Execute a task in a safe environment"""
        start_time = datetime.now()

        try:
            print(f"🔄 Executing task... | worker_runtime={get_runtime_info()}")

            # Deserialize the function
            func = deserialize_function_for_PC(func_code)

            # Execute the function with the provided arguments
            if isinstance(task_args, list) and len(task_args) == 1:
                # Single argument
                result = func(task_args[0])
            elif (
                isinstance(task_args, list)
                and len(task_args) == 2
                and isinstance(task_args[1], dict)
            ):
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

    # ---------- Background tasks ----------
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
                            "current_task": (
                                self.current_task["task_id"]
                                if self.current_task
                                else None
                            ),
                        },
                    )
                    await self.websocket.send(heartbeat_message.to_json())

                await asyncio.sleep(self.config.heartbeat_interval)

            except Exception as e:
                print(f"❌ Error sending heartbeat: {e}")
                break

    # ---------- Main worker lifecycle ----------
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
        print(f"🌐 Web Interface: http://{self.config.api_host}:{self.config.api_port}")
        print(
            f"📊 API Docs:      http://{self.config.api_host}:{self.config.api_port}/docs"
        )
        print("=" * 60)

        # Run FastAPI server with worker in background
        try:
            uvicorn.run(
                self.app,
                host=self.config.api_host,
                port=self.config.api_port,
                log_level="info",
                loop="asyncio",
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
        print(f"🌐 Web Interface: http://{self.config.api_host}:{self.config.api_port}")
        print(
            f"📊 API Docs:      http://{self.config.api_host}:{self.config.api_port}/docs"
        )
        print("=" * 60)

        # Start worker in background
        worker_task = asyncio.create_task(self.start())

        # Create server config
        config = uvicorn.Config(
            self.app,
            host=self.config.api_host,
            port=self.config.api_port,
            log_level="info",
        )

        # Create and run server
        server = uvicorn.Server(config)
        try:
            await server.serve()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        finally:
            worker_task.cancel()
