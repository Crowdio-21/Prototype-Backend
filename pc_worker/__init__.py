"""
FastAPI Worker for CrowdCompute
"""

from .core.worker import FastAPIWorker
from .config import WorkerConfig
from .schema.models import TaskResult

__version__ = "1.0.0"
__all__ = ["FastAPIWorker", "WorkerConfig", "TaskResult"]
