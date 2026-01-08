"""
Data models used by the PC worker service.
"""

from typing import Optional
from pydantic import BaseModel


class TaskResult(BaseModel):
    """Represents the result of an executed task."""

    task_id: str
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
