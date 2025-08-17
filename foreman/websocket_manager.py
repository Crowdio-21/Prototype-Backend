"""
WebSocket manager for CrowdCompute Foreman
"""

import asyncio
import json
import uuid
import websockets
from typing import Dict, Set, Optional, Any
from websockets.server import WebSocketServerProtocol
from .database import AsyncSession, update_worker_status, update_task_status, update_job_status
from common.protocol import (
    Message, MessageType, create_assign_task_message, 
    create_job_results_message, create_task_result_message,
    create_task_error_message, create_ping_message
)
from common.serializer import hex_to_bytes


class WebSocketManager:
    """Manages WebSocket connections for workers and clients"""
    
    def __init__(self):
        self.workers: Dict[str, WebSocketServerProtocol] = {}
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.available_workers: Set[str] = set()
        self.job_websockets: Dict[str, WebSocketServerProtocol] = {}  # job_id -> client_websocket
        self.job_cache: Dict[str, bytes] = {}  # job_id -> func_pickle
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        try:
            client_type = None
            
            async for message in websocket:
                try:
                    msg = Message.from_json(message)
                    
                    if client_type is None:
                        # First message determines client type
                        if msg.type == MessageType.SUBMIT_JOB:
                            client_type = "client"
                            await self._handle_client_message(msg, websocket)
                        elif msg.type == MessageType.WORKER_READY:
                            client_type = "worker"
                            await self._handle_worker_message(msg, websocket)
                        else:
                            print(f"Unknown first message type: {msg.type}")
                            break
                    else:
                        # Handle subsequent messages based on client type
                        if client_type == "client":
                            await self._handle_client_message(msg, websocket)
                        else:
                            await self._handle_worker_message(msg, websocket)
                            
                except Exception as e:
                    print(f"Error handling message: {e}")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        finally:
            await self._cleanup_connection(websocket)
    
    async def _handle_client_message(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle messages from client SDK"""
        if message.type == MessageType.SUBMIT_JOB:
            await self._handle_job_submission(message, websocket)
        elif message.type == MessageType.DISCONNECT:
            await websocket.close()
    
    async def _handle_worker_message(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle messages from workers"""
        if message.type == MessageType.WORKER_READY:
            await self._handle_worker_ready(message, websocket)
        elif message.type == MessageType.TASK_RESULT:
            await self._handle_task_result(message, websocket)
        elif message.type == MessageType.TASK_ERROR:
            await self._handle_task_error(message, websocket)
        elif message.type == MessageType.PONG:
            await self._handle_pong(message, websocket)
    
    async def _handle_job_submission(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle a new job submission from client"""
        try:
            job_id = message.job_id
            func_pickle = hex_to_bytes(message.data["func_pickle"])
            args_list = message.data["args_list"]
            total_tasks = message.data["total_tasks"]
            
            print(f"Received job {job_id} with {total_tasks} tasks")
            
            # Store client websocket for this job
            self.job_websockets[job_id] = websocket
            
            # Store func_pickle in cache
            self.job_cache[job_id] = func_pickle
            
            # Create job in database first
            await self._create_job_in_database(job_id, total_tasks)
            
            # Create tasks in database
            await self._create_tasks_for_job(job_id, args_list)
            
            # Update job status to running
            await self._update_job_status(job_id, "running")
            
            # Try to assign tasks to available workers
            await self._assign_tasks_to_workers(job_id, func_pickle, args_list)
            
            # Send job accepted message
            response = Message(
                MessageType.JOB_ACCEPTED,
                {"job_id": job_id},
                job_id
            )
            await websocket.send(response.to_json())
            
        except Exception as e:
            print(f"Error handling job submission: {e}")
            error_msg = Message(
                MessageType.JOB_ERROR,
                {"error": str(e)},
                message.job_id
            )
            await websocket.send(error_msg.to_json())
    
    async def _handle_worker_ready(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle worker ready message"""
        worker_id = message.data["worker_id"]
        
        print(f"Worker {worker_id} connected")
        
        # Store worker websocket
        self.workers[worker_id] = websocket
        self.available_workers.add(worker_id)
        
        # Create worker in database if it doesn't exist
        await self._create_worker_in_database(worker_id)
        
        # Update worker status in database
        await self._update_worker_status(worker_id, "online")
        
        # Assign any pending tasks
        await self._assign_tasks_to_worker(worker_id)
    
    async def _handle_task_result(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle task result from worker"""
        job_id = message.job_id
        task_id = message.data["task_id"]
        result = message.data["result"]
        worker_id = None
        
        # Find worker ID from websocket
        for wid, ws in self.workers.items():
            if ws == websocket:
                worker_id = wid
                break
        
        if not worker_id:
            print(f"Could not find worker for task result")
            return
        
        print(f"Task {task_id} completed for job {job_id} with result: {result}")
        
        # Update task status in database
        await self._update_task_status(
            task_id, 
            "completed", 
            worker_id=worker_id, 
            result=str(result)
        )
        
        # Update worker statistics
        await self._update_worker_task_stats(worker_id, task_completed=True)
        
        # Increment job completed tasks count
        await self._increment_job_completed_tasks(job_id)
        
        # Mark worker as available
        self.available_workers.add(worker_id)
        await self._update_worker_status(worker_id, "online", current_task_id=None)
        
        # Check if job is complete and send results to client
        await self._check_job_completion(job_id)
        
        # Assign next task to this worker
        await self._assign_tasks_to_worker(worker_id)
    
    async def _handle_task_error(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle task error from worker"""
        job_id = message.job_id
        task_id = message.data["task_id"]
        error = message.data["error"]
        worker_id = None
        
        # Find worker ID from websocket
        for wid, ws in self.workers.items():
            if ws == websocket:
                worker_id = wid
                break
        
        print(f"Task {task_id} failed for job {job_id}: {error}")
        
        # Update task status in database
        await self._update_task_status(
            task_id, 
            "failed", 
            worker_id=worker_id, 
            error=error
        )
        
        # Update worker statistics
        if worker_id:
            await self._update_worker_task_stats(worker_id, task_completed=False)
        
        # Increment job completed tasks count (includes failed tasks)
        await self._increment_job_completed_tasks(job_id)
        
        # Mark worker as available
        if worker_id:
            self.available_workers.add(worker_id)
            await self._update_worker_status(worker_id, "online", current_task_id=None)
            
            # Assign next task to this worker
            await self._assign_tasks_to_worker(worker_id)
    
    async def _handle_pong(self, message: Message, websocket: WebSocketServerProtocol):
        """Handle pong from worker"""
        # Update worker's last seen time
        worker_id = None
        for wid, ws in self.workers.items():
            if ws == websocket:
                worker_id = wid
                break
        
        if worker_id:
            await self._update_worker_status(worker_id, "online")
    
    async def _assign_tasks_to_workers(self, job_id: str, func_pickle: bytes, args_list: list):
        """Assign available tasks to available workers"""
        from .database import get_pending_tasks, AsyncSessionLocal
        
        # Get pending tasks for this job
        async with AsyncSessionLocal() as session:
            pending_tasks = await get_pending_tasks(session, job_id)
        
        # Assign tasks to available workers
        for task in pending_tasks:
            if self.available_workers:
                worker_id = self.available_workers.pop()
                # Deserialize args from JSON
                import json
                task_args = json.loads(task.args) if task.args else []
                await self._assign_task_to_worker(job_id, task.id, func_pickle, task_args, worker_id)
    
    async def _assign_tasks_to_worker(self, worker_id: str):
        """Assign pending tasks to a newly available worker"""
        from .database import get_pending_tasks, AsyncSessionLocal
        
        # Find any pending tasks across all jobs
        async with AsyncSessionLocal() as session:
            pending_tasks = await get_pending_tasks(session)
        
        for task in pending_tasks:
            # Get func_pickle from cache
            if task.job_id in self.job_cache:
                func_pickle = self.job_cache[task.job_id]
                # Deserialize args from JSON
                import json
                task_args = json.loads(task.args) if task.args else []
                await self._assign_task_to_worker(task.job_id, task.id, func_pickle, task_args, worker_id)
                return  # Only assign one task at a time
    
    async def _assign_task_to_worker(self, job_id: str, task_id: str, func_pickle: bytes, task_args: Any, worker_id: str):
        """Assign a specific task to a worker"""
        try:
            # Create task assignment message
            message = create_assign_task_message(
                func_pickle,
                [task_args],  # Wrap in list for single task
                task_id,
                job_id
            )
            
            # Send to worker
            websocket = self.workers[worker_id]
            await websocket.send(message.to_json())
            
            # Update task status in database
            await self._update_task_status(task_id, "assigned", worker_id=worker_id)
            
            # Mark worker as busy
            self.available_workers.discard(worker_id)
            await self._update_worker_status(worker_id, "busy", current_task_id=task_id)
            
            print(f"Assigned task {task_id} to worker {worker_id}")
            
        except Exception as e:
            print(f"Error assigning task {task_id} to worker {worker_id}: {e}")
            # Put worker back in available pool
            self.available_workers.add(worker_id)
    
    async def _check_job_completion(self, job_id: str):
        """Check if a job is complete and send results to client"""
        from .database import get_job_tasks, get_job_by_id, AsyncSessionLocal
        
        # Get all tasks for this job
        async with AsyncSessionLocal() as session:
            tasks = await get_job_tasks(session, job_id)
        
        print(f"Checking job completion for {job_id}: {len(tasks)} total tasks")
        
        # Check if all tasks are completed
        completed_tasks = [t for t in tasks if t.status == "completed"]
        failed_tasks = [t for t in tasks if t.status == "failed"]
        
        print(f"Completed: {len(completed_tasks)}, Failed: {len(failed_tasks)}")
        
        if len(completed_tasks) + len(failed_tasks) == len(tasks) and len(tasks) > 0:
            # Job is complete
            job = await get_job_by_id(session, job_id)
            if job:
                # Collect results in the correct order
                results = []
                for i in range(len(tasks)):
                    # Find task by index
                    task = None
                    for t in tasks:
                        if t.id == f"{job_id}_task_{i}":
                            task = t
                            break
                    
                    if task and task.status == "completed":
                        results.append(task.result)
                    else:
                        results.append(None)  # Failed or missing task
                
                print(f"Collected results: {results}")
                
                # Send results to client
                if job_id in self.job_websockets:
                    client_websocket = self.job_websockets[job_id]
                    message = create_job_results_message(results, job_id)
                    await client_websocket.send(message.to_json())
                    
                    # Update job status with completed tasks count
                    await update_job_status(session, job_id, "completed", completed_tasks=len(completed_tasks))
                    
                    # Clean up job cache
                    if job_id in self.job_cache:
                        del self.job_cache[job_id]
                    
                    print(f"Job {job_id} completed successfully")
                else:
                    print(f"Warning: No client websocket found for job {job_id}")
            else:
                print(f"Warning: Job {job_id} not found in database")
        else:
            print(f"Job {job_id} not complete yet: {len(completed_tasks) + len(failed_tasks)}/{len(tasks)} tasks done")
    
    async def _get_job_by_id(self, job_id: str):
        """Get job by ID from database"""
        from .database import get_job_by_id, AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            return await get_job_by_id(session, job_id)
    
    async def _create_job_in_database(self, job_id: str, total_tasks: int):
        """Create job in database"""
        from .database import create_job, AsyncSessionLocal
        
        # Create a new session for this operation
        async with AsyncSessionLocal() as session:
            await create_job(session, job_id, total_tasks)
        print(f"Created job {job_id} in database")
    
    async def _create_worker_in_database(self, worker_id: str):
        """Create worker in database if it doesn't exist"""
        from .database import create_worker, get_workers, update_worker_status, AsyncSessionLocal
        
        # Create a new session for this operation
        async with AsyncSessionLocal() as session:
            # Check if worker already exists
            workers = await get_workers(session)
            existing_worker_ids = [w.id for w in workers]
            
            if worker_id not in existing_worker_ids:
                await create_worker(session, worker_id)
                print(f"Created worker {worker_id} in database")
            else:
                # Worker exists, ensure it's marked as online
                await update_worker_status(session, worker_id, "online")
                print(f"Worker {worker_id} already exists in database, marked as online")
    
    async def _create_tasks_for_job(self, job_id: str, args_list: list):
        """Create tasks in database for a job"""
        from .database import TaskModel, AsyncSessionLocal
        import json
        
        # Create a new session for this operation
        async with AsyncSessionLocal() as session:
            tasks = []
            for i, args in enumerate(args_list):
                task_id = f"{job_id}_task_{i}"
                task = TaskModel(
                    id=task_id,
                    job_id=job_id,
                    args=json.dumps(args),  # Serialize args to JSON string
                    status="pending"
                )
                tasks.append(task)
            
            # Add all tasks to database
            session.add_all(tasks)
            await session.commit()
        
        print(f"Created {len(tasks)} tasks for job {job_id}")
    
    async def _update_job_status(self, job_id: str, status: str, completed_tasks: int = None):
        """Update job status with new session"""
        from .database import update_job_status, AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            await update_job_status(session, job_id, status, completed_tasks)
    
    async def _update_task_status(self, task_id: str, status: str, worker_id: str = None, result: str = None, error: str = None):
        """Update task status with new session"""
        from .database import update_task_status, AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            await update_task_status(session, task_id, status, worker_id, result, error)
    
    async def _update_worker_status(self, worker_id: str, status: str, current_task_id: str = None):
        """Update worker status with new session"""
        from .database import update_worker_status, AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            await update_worker_status(session, worker_id, status, current_task_id)
    
    async def _update_worker_task_stats(self, worker_id: str, task_completed: bool = True):
        """Update worker task statistics with new session"""
        from .database import update_worker_task_stats, AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            await update_worker_task_stats(session, worker_id, task_completed)
    
    async def _increment_job_completed_tasks(self, job_id: str):
        """Increment job completed tasks count with new session"""
        from .database import increment_job_completed_tasks, AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            await increment_job_completed_tasks(session, job_id)
    
    async def _cleanup_connection(self, websocket: WebSocketServerProtocol):
        """Clean up when a connection is closed"""
        # Remove worker if it was a worker connection
        for worker_id, ws in list(self.workers.items()):
            if ws == websocket:
                print(f"Worker {worker_id} disconnected")
                del self.workers[worker_id]
                self.available_workers.discard(worker_id)
                await self._update_worker_status(worker_id, "offline")
                break
        
        # Remove client if it was a client connection
        for job_id, ws in list(self.job_websockets.items()):
            if ws == websocket:
                print(f"Client for job {job_id} disconnected")
                del self.job_websockets[job_id]
                break
    
    async def ping_workers(self):
        """Periodically ping workers to keep connections alive"""
        while True:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                
                ping_message = create_ping_message()
                for worker_id, websocket in self.workers.items():
                    try:
                        await websocket.send(ping_message.to_json())
                    except:
                        # Worker connection is dead, will be cleaned up
                        pass
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in ping task: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current WebSocket manager stats"""
        return {
            "connected_workers": len(self.workers),
            "available_workers": len(self.available_workers),
            "connected_clients": len(self.job_websockets),
            "active_jobs": len(self.job_websockets)
        }
