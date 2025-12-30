"""
Task dispatching with pluggable scheduling algorithms
"""

import json
from typing import List, Optional, Any, Dict

from .scheduling import TaskScheduler, Task as SchedulerTask, Worker
from .ws_manager_utils import (
    _get_pending_tasks, _update_task_status, _update_worker_status
)
from common.protocol import create_assign_task_message
from common.serializer import get_runtime_info


class TaskDispatcher:
    """
    Dispatches tasks to workers using pluggable scheduling algorithms
    
    Responsibilities:
    - Use scheduler to select best worker for task
    - Use scheduler to select best task for worker
    - Send task assignments to workers
    - Update task and worker status
    """
    
    def __init__(self, scheduler: TaskScheduler, connection_manager, job_manager):
        """
        Initialize task dispatcher
        
        Args:
            scheduler: Scheduling algorithm to use
            connection_manager: ConnectionManager instance
            job_manager: JobManager instance
        """
        self.scheduler = scheduler
        self.connection_manager = connection_manager
        self.job_manager = job_manager
    
    # ==================== Task Assignment ====================
    
    async def assign_tasks_for_job(
        self, 
        job_id: str, 
        func_code: str, 
        args_list: List[Any]
    ) -> int:
        """
        Assign available tasks for a specific job to available workers
        
        Args:
            job_id: Job identifier
            func_code: Function code to execute
            args_list: List of task arguments
            
        Returns:
            Number of tasks assigned
        """
        print(f"TaskDispatcher: Assigning tasks for job {job_id}")
        
        # Get pending tasks for this job
        pending_tasks = await _get_pending_tasks(job_id)
        
        if not pending_tasks:
            print(f"TaskDispatcher: No pending tasks for job {job_id}")
            return 0
        
        tasks_assigned = 0
        
        for task in pending_tasks:
            available_workers = self.connection_manager.get_available_workers()
            
            if not available_workers:
                print(f"TaskDispatcher: No available workers, {len(pending_tasks) - tasks_assigned} tasks remain")
                break
            
            # Get worker objects for scheduler
            all_workers = await self._get_all_workers()
            
            # Create scheduler task
            scheduler_task = SchedulerTask(
                id=task.id,
                job_id=task.job_id,
                args=task.args,
                priority=getattr(task, 'priority', 0)
            )
            
            # Let scheduler select best worker
            worker_id = await self.scheduler.select_worker(
                scheduler_task,
                available_workers,
                all_workers
            )
            
            if worker_id:
                task_args = json.loads(task.args) if task.args else []
                success = await self._assign_task_to_worker(
                    job_id, task.id, func_code, task_args, worker_id
                )
                if success:
                    tasks_assigned += 1
        
        print(f"TaskDispatcher: Assigned {tasks_assigned} tasks for job {job_id}")
        return tasks_assigned
    
    async def assign_task_to_available_worker(self, worker_id: str) -> bool:
        """
        Assign a pending task to a specific worker
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            True if task was assigned, False otherwise
        """
        # Get all pending tasks across jobs
        pending_tasks = await _get_pending_tasks()
        
        if not pending_tasks:
            print(f"TaskDispatcher: No pending tasks available for worker {worker_id}")
            return False
        
        # Convert to scheduler tasks
        scheduler_tasks = [
            SchedulerTask(
                id=task.id,
                job_id=task.job_id,
                args=task.args,
                priority=getattr(task, 'priority', 0)
            )
            for task in pending_tasks
        ]
        
        # Let scheduler select best task for this worker
        selected_task = await self.scheduler.select_task(
            scheduler_tasks,
            worker_id
        )
        
        if not selected_task:
            print(f"TaskDispatcher: Scheduler returned no task for worker {worker_id}")
            return False
        
        # Get func_code from job manager
        func_code = self.job_manager.get_func_code(selected_task.job_id)
        
        if not func_code:
            print(f"TaskDispatcher: No func_code found for job {selected_task.job_id}")
            return False
        
        # Parse task args
        task_args = json.loads(selected_task.args) if selected_task.args else []
        
        success = await self._assign_task_to_worker(
            selected_task.job_id,
            selected_task.id,
            func_code,
            task_args,
            worker_id
        )
        
        return success
    
    async def _assign_task_to_worker(
        self,
        job_id: str,
        task_id: str,
        func_code: str,
        task_args: Any,
        worker_id: str
    ) -> bool:
        """
        Assign a specific task to a specific worker
        
        Args:
            job_id: Job identifier
            task_id: Task identifier
            func_code: Function code to execute
            task_args: Task arguments
            worker_id: Worker identifier
            
        Returns:
            True if assignment successful, False otherwise
        """
        try:
            # Create task assignment message
            message = create_assign_task_message(
                func_code,
                [task_args],  # Wrap in list for single task
                task_id,
                job_id
            )
            
            # Get worker websocket
            websocket = self.connection_manager.get_worker_websocket(worker_id)
            
            if not websocket:
                print(f"TaskDispatcher: No websocket found for worker {worker_id}")
                return False
            
            # Send to worker
            await websocket.send(message.to_json())
            
            # Update task status in database
            await _update_task_status(task_id, "assigned", worker_id=worker_id)
            
            # Mark worker as busy
            self.connection_manager.mark_worker_busy(worker_id)
            await _update_worker_status(worker_id, "busy", current_task_id=task_id)
            
            print(f"TaskDispatcher: Assigned task {task_id} to worker {worker_id} | foreman_runtime={get_runtime_info()}")
            
            return True
            
        except Exception as e:
            print(f"TaskDispatcher: Error assigning task {task_id} to worker {worker_id}: {e}")
            
            # Put worker back in available pool on error
            self.connection_manager.mark_worker_available(worker_id)
            
            # Try to update worker status back to online
            try:
                await _update_worker_status(worker_id, "online", current_task_id=None)
            except Exception as status_error:
                print(f"TaskDispatcher: Error updating worker status: {status_error}")
            
            return False
    
    # ==================== Worker Information ====================
    
    async def _get_all_workers(self) -> Dict[str, Worker]:
        """
        Get all worker objects for scheduler with their statistics
        
        Returns:
            Dictionary mapping worker_id to Worker objects
        """
        all_worker_ids = self.connection_manager.get_all_worker_ids()
        workers = {}
        
        # Import here to avoid circular dependency
        from .ws_manager_utils import _get_worker_stats
        
        for worker_id in all_worker_ids:
            try:
                # Get worker stats from database
                stats = await _get_worker_stats(worker_id)
                
                if stats:
                    workers[worker_id] = Worker(
                        id=worker_id,
                        status=stats.get('status', 'online'),
                        tasks_completed=stats.get('tasks_completed', 0),
                        tasks_failed=stats.get('tasks_failed', 0),
                        current_task_id=stats.get('current_task_id')
                    )
                else:
                    # Worker exists but no stats yet
                    workers[worker_id] = Worker(
                        id=worker_id,
                        status='online',
                        tasks_completed=0,
                        tasks_failed=0,
                        current_task_id=None
                    )
            except Exception as e:
                print(f"TaskDispatcher: Error getting stats for worker {worker_id}: {e}")
                # Create basic worker object
                workers[worker_id] = Worker(
                    id=worker_id,
                    status='online',
                    tasks_completed=0,
                    tasks_failed=0,
                    current_task_id=None
                )
        
        return workers
    
    # ==================== Statistics ====================
    
    def get_scheduler_name(self) -> str:
        """Get the name of the current scheduler"""
        return self.scheduler.__class__.__name__
    
    def change_scheduler(self, new_scheduler: TaskScheduler) -> None:
        """
        Change the scheduling algorithm
        
        Args:
            new_scheduler: New scheduler instance
        """
        old_name = self.get_scheduler_name()
        self.scheduler = new_scheduler
        new_name = self.get_scheduler_name()
        print(f"TaskDispatcher: Changed scheduler from {old_name} to {new_name}")
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"TaskDispatcher(scheduler={self.get_scheduler_name()})"