"""
Message handling logic separated by client type
"""

from websockets.server import WebSocketServerProtocol

from .ws_manager_utils import (
    _create_worker_in_database, _record_worker_failure,
    _update_worker_status, _update_worker_task_stats
)
from common.protocol import Message, MessageType, create_job_accepted_message
from common.serializer import get_runtime_info


class ClientMessageHandler:
    """
    Handles messages from client SDK
    
    Responsibilities:
    - Handle job submissions
    - Handle client disconnections
    - Send job acknowledgments
    """
    
    def __init__(self, connection_manager, job_manager, task_dispatcher):
        """
        Initialize client message handler
        
        Args:
            connection_manager: ConnectionManager instance
            job_manager: JobManager instance
            task_dispatcher: TaskDispatcher instance
        """
        self.connection_manager = connection_manager
        self.job_manager = job_manager
        self.task_dispatcher = task_dispatcher
    
    async def handle_message(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Route client messages to appropriate handlers
        
        Args:
            message: Parsed message
            websocket: WebSocket connection
        """
        if message.type == MessageType.SUBMIT_JOB:
            await self._handle_job_submission(message, websocket)
        elif message.type == MessageType.DISCONNECT:
            await websocket.close()
        else:
            print(f"ClientMessageHandler: Unknown message type: {message.type}")
    
    async def _handle_job_submission(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Handle a new job submission from client
        
        Args:
            message: Job submission message
            websocket: Client websocket connection
        """
        try:
            job_id = message.job_id
            func_code = message.data["func_code"]
            args_list = message.data["args_list"]
            total_tasks = message.data["total_tasks"]
            
            print(f"ClientMessageHandler: Received job {job_id} with {total_tasks} tasks | foreman_runtime={get_runtime_info()}")
            
            # Register client websocket
            self.connection_manager.add_client(job_id, websocket)
            
            # Create job and tasks
            await self.job_manager.create_job(job_id, func_code, args_list, total_tasks)
            
            # Try to assign tasks to available workers
            assigned = await self.task_dispatcher.assign_tasks_for_job(job_id, func_code, args_list)
            
            print(f"ClientMessageHandler: Assigned {assigned} tasks immediately for job {job_id}")
            
            # Send job accepted message
            response = create_job_accepted_message(job_id)
            await websocket.send(response.to_json())
            
            print(f"ClientMessageHandler: Job {job_id} accepted and acknowledged")
            
        except KeyError as e:
            print(f"ClientMessageHandler: Missing required field in job submission: {e}")
            error_msg = Message(
                MessageType.JOB_ERROR,
                {"error": f"Missing required field: {e}"},
                message.job_id
            )
            await websocket.send(error_msg.to_json())
            
        except Exception as e:
            print(f"ClientMessageHandler: Error handling job submission: {e}")
            import traceback
            traceback.print_exc()
            
            error_msg = Message(
                MessageType.JOB_ERROR,
                {"error": str(e)},
                message.job_id
            )
            await websocket.send(error_msg.to_json())


class WorkerMessageHandler:
    """
    Handles messages from workers
    
    Responsibilities:
    - Handle worker registration
    - Handle task results
    - Handle task errors
    - Handle pong responses
    """
    
    def __init__(
        self, 
        connection_manager, 
        job_manager, 
        task_dispatcher,
        completion_handler
    ):
        """
        Initialize worker message handler
        
        Args:
            connection_manager: ConnectionManager instance
            job_manager: JobManager instance
            task_dispatcher: TaskDispatcher instance
            completion_handler: JobCompletionHandler instance
        """
        self.connection_manager = connection_manager
        self.job_manager = job_manager
        self.task_dispatcher = task_dispatcher
        self.completion_handler = completion_handler
    
    async def handle_message(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Route worker messages to appropriate handlers
        
        Args:
            message: Parsed message
            websocket: WebSocket connection
        """
        if message.type == MessageType.WORKER_READY:
            await self._handle_worker_ready(message, websocket)
        elif message.type == MessageType.TASK_RESULT:
            await self._handle_task_result(message, websocket)
        elif message.type == MessageType.TASK_ERROR:
            await self._handle_task_error(message, websocket)
        elif message.type == MessageType.PONG:
            await self._handle_pong(message, websocket)
        else:
            print(f"WorkerMessageHandler: Unknown message type: {message.type}")
    
    async def _handle_pong(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Handle pong from worker (heartbeat response)
        
        Args:
            message: Pong message
            websocket: Worker websocket connection
        """
        worker_id = self.connection_manager.find_worker_by_websocket(websocket)
        
        if worker_id:
            # Update worker's last seen time in database
            await _update_worker_status(worker_id, "online")
    
    async def _handle_worker_ready(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Handle worker ready message (worker registration)
        
        Args:
            message: Worker ready message
            websocket: Worker websocket connection
        """
        try:
            worker_id = message.data["worker_id"]
            
            print(f"WorkerMessageHandler: Worker {worker_id} connected")
            
            # Register worker
            self.connection_manager.add_worker(worker_id, websocket)
            
            # Create worker in database if it doesn't exist
            await _create_worker_in_database(worker_id)
            
            # Update worker status in database
            await _update_worker_status(worker_id, "online")
            
            # Assign any pending tasks to this worker
            assigned = await self.task_dispatcher.assign_task_to_available_worker(worker_id)
            
            if assigned:
                print(f"WorkerMessageHandler: Assigned task to newly connected worker {worker_id}")
            else:
                print(f"WorkerMessageHandler: No tasks available for worker {worker_id}")
                
        except KeyError as e:
            print(f"WorkerMessageHandler: Missing required field in worker ready: {e}")
        except Exception as e:
            print(f"WorkerMessageHandler: Error handling worker ready: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_task_result(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Handle task result from worker (successful completion)
        
        Args:
            message: Task result message
            websocket: Worker websocket connection
        """
        try:
            job_id = message.job_id
            task_id = message.data["task_id"]
            result = message.data["result"]
            
            # Find worker ID
            worker_id = self.connection_manager.find_worker_by_websocket(websocket)
            
            if not worker_id:
                print(f"WorkerMessageHandler: Could not find worker for task result")
                return
            
            print(f"WorkerMessageHandler: Task {task_id} completed by worker {worker_id} for job {job_id}")
            
            # Mark task as completed in job manager
            job_complete = await self.job_manager.mark_task_completed(
                task_id, job_id, worker_id, result
            )
            
            # Update worker statistics
            await _update_worker_task_stats(worker_id, task_completed=True)
            
            # Mark worker as available again
            self.connection_manager.mark_worker_available(worker_id)
            await _update_worker_status(worker_id, "online", current_task_id=None)
            
            # Check if job is complete and handle completion
            if job_complete:
                print(f"WorkerMessageHandler: Job {job_id} completed, triggering completion handler")
                await self.completion_handler.handle_job_completion(job_id)
            
            # Assign next task to this worker
            assigned = await self.task_dispatcher.assign_task_to_available_worker(worker_id)
            
            if assigned:
                print(f"WorkerMessageHandler: Assigned next task to worker {worker_id}")
            
        except KeyError as e:
            print(f"WorkerMessageHandler: Missing required field in task result: {e}")
        except Exception as e:
            print(f"WorkerMessageHandler: Error handling task result: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_task_error(self, message: Message, websocket: WebSocketServerProtocol):
        """
        Handle task error from worker (task failure)
        
        Args:
            message: Task error message
            websocket: Worker websocket connection
        """
        try:
            job_id = message.job_id
            task_id = message.data["task_id"]
            error = message.data["error"]
            
            # Find worker ID
            worker_id = self.connection_manager.find_worker_by_websocket(websocket)
            
            if not worker_id:
                print(f"WorkerMessageHandler: Could not find worker for task error")
                return
            
            print(f"WorkerMessageHandler: Task {task_id} failed on worker {worker_id} for job {job_id}: {error}")
            
            # Mark task as failed (resets to pending for retry)
            await self.job_manager.mark_task_failed(task_id, job_id, worker_id, error)
            
            # Update worker statistics
            await _update_worker_task_stats(worker_id, task_completed=False)
            
            # Record failure in history
            try:
                await _record_worker_failure(worker_id, task_id, error, job_id)
            except Exception as ex:
                print(f"WorkerMessageHandler: Error recording worker failure for {worker_id}/{task_id}: {ex}")
            
            # Mark worker as available again
            self.connection_manager.mark_worker_available(worker_id)
            await _update_worker_status(worker_id, "online", current_task_id=None)
            
            # Assign next task to this worker (the failed task will be retried by another worker)
            assigned = await self.task_dispatcher.assign_task_to_available_worker(worker_id)
            
            if assigned:
                print(f"WorkerMessageHandler: Assigned next task to worker {worker_id} after failure")
            
        except KeyError as e:
            print(f"WorkerMessageHandler: Missing required field in task error: {e}")
        except Exception as e:
            print(f"WorkerMessageHandler: Error handling task error: {e}")
            import traceback
            traceback.print_exc()