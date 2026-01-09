from .scheduler_interface import *
from .fifo_scheduler import FIFOScheduler
from .round_robin_scheduler import RoundRobinScheduler
from .performance_scheduler import PerformanceBasedScheduler
from .least_loaded_scheduler import LeastLoadedScheduler
from .priority_scheduler import PriorityScheduler

# Scheduler factory
def create_scheduler(scheduler_type: str = "fifo") -> TaskScheduler:
    """
    Factory function to create scheduler instances
    
    Args:
        scheduler_type: Type of scheduler ("fifo", "round_robin", 
                       "performance", "least_loaded", "priority")
    
    Returns:
        TaskScheduler instance
    """
    schedulers = {
        "fifo": FIFOScheduler,
        "round_robin": RoundRobinScheduler,
        "performance": PerformanceBasedScheduler,
        "least_loaded": LeastLoadedScheduler,
        "priority": PriorityScheduler,
    }
    
    scheduler_class = schedulers.get(scheduler_type.lower())
    if not scheduler_class:
        raise ValueError(f"Unknown scheduler type: {scheduler_type}")
    
    return scheduler_class()