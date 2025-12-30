"""
Task scheduling interface and implementations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from dataclasses import dataclass


@dataclass
class Task:
    """Task information for scheduling"""
    id: str
    job_id: str
    args: str
    priority: int = 0
    retry_count: int = 0


@dataclass
class Worker:
    """Worker information for scheduling"""
    id: str
    status: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task_id: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate worker success rate"""
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 1.0


class TaskScheduler(ABC):
    """Abstract base class for task scheduling algorithms"""
    
    @abstractmethod
    async def select_worker(
        self, 
        task: Task, 
        available_workers: Set[str],
        all_workers: dict
    ) -> Optional[str]:
        """
        Select the best worker for a given task
        
        Args:
            task: Task to be assigned
            available_workers: Set of available worker IDs
            all_workers: Dictionary of all workers (id -> Worker)
            
        Returns:
            Selected worker ID or None if no suitable worker
        """
        pass
    
    @abstractmethod
    async def select_task(
        self,
        pending_tasks: List[Task],
        worker_id: str
    ) -> Optional[Task]:
        """
        Select the best task for a given worker
        
        Args:
            pending_tasks: List of pending tasks
            worker_id: Worker ID requesting a task
            
        Returns:
            Selected task or None if no suitable task
        """
        pass



