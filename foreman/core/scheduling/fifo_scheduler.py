from .scheduler_interface import *

class FIFOScheduler(TaskScheduler):
    """First-In-First-Out scheduler - assigns tasks in order received"""
    
    async def select_worker(
        self, 
        task: Task, 
        available_workers: Set[str],
        all_workers: dict
    ) -> Optional[str]:
        """Select first available worker"""
        return next(iter(available_workers)) if available_workers else None
    
    async def select_task(
        self,
        pending_tasks: List[Task],
        worker_id: str
    ) -> Optional[Task]:
        """Select first pending task"""
        return pending_tasks[0] if pending_tasks else None

