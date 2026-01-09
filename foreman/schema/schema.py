from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# Pydantic Models for API
class JobBase(BaseModel):
    total_tasks: int


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: str
    status: str
    completed_tasks: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    job_id: str
    worker_id: Optional[str] = None
    status: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkerResponse(BaseModel):
    id: str
    status: str
    last_seen: datetime
    current_task_id: Optional[str] = None
    total_tasks_completed: int
    total_tasks_failed: int
    
    class Config:
        from_attributes = True


class WorkerFailureResponse(BaseModel):
    id: int
    worker_id: str
    task_id: str
    job_id: Optional[str] = None
    error_message: str
    failed_at: datetime
    
    class Config:
        from_attributes = True


class WorkerFailureStats(BaseModel):
    worker_id: str
    total_failures: int
    total_tasks: int
    failure_rate: float


class WorkerFailureSummary(BaseModel):
    worker_id: str
    failures: List["WorkerFailureResponse"]
    stats: WorkerFailureStats


class JobStats(BaseModel):
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    online_workers: int
