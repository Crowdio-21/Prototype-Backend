"""
Database models and connection for CrowdCompute Foreman
"""

import asyncio
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, create_engine, select, update, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from pydantic import BaseModel

# Database URL
DATABASE_URL = "sqlite+aiosqlite:///./crowdcompute.db"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()


# SQLAlchemy Models
class JobModel(Base):
    """Job table model"""
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    total_tasks = Column(Integer)
    completed_tasks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    #serialized code could be added here if needed
    #arguments for the job could be added here if needed
    
    # Relationships
    tasks = relationship("TaskModel", back_populates="job")


class TaskModel(Base):
    """Task table model"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    worker_id = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, assigned, completed, failed
    args = Column(Text, nullable=True)  # Serialized task arguments
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    job = relationship("JobModel", back_populates="tasks")


class WorkerModel(Base):
    """Worker table model"""
    __tablename__ = "workers"
    
    id = Column(String, primary_key=True)
    status = Column(String, default="online")  # online, offline, busy
    last_seen = Column(DateTime, default=datetime.now)
    current_task_id = Column(String, nullable=True)
    total_tasks_completed = Column(Integer, default=0)
    total_tasks_failed = Column(Integer, default=0)
    #device specs could be added here (CPU, RAM, etc.), battery draining, network speed, uptime
    #entering time and exit time could be added here
    
#todo: add a table for storing historical data of workers ( failed and reason for the failing(error), uptime, etc.)


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


# Database functions
async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_job(session: AsyncSession, job_id: str, total_tasks: int) -> JobModel:
    """Create a new job"""
    job = JobModel(id=job_id, total_tasks=total_tasks)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def create_task(session: AsyncSession, task_id: str, job_id: str) -> TaskModel:
    """Create a new task"""
    task = TaskModel(id=task_id, job_id=job_id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def create_worker(session: AsyncSession, worker_id: str) -> WorkerModel:
    """Create a new worker"""
    worker = WorkerModel(id=worker_id)
    session.add(worker)
    await session.commit()
    await session.refresh(worker)
    return worker


async def get_job(session: AsyncSession, job_id: str) -> Optional[JobModel]:
    """Get job by ID"""
    result = await session.execute(
        select(JobModel).where(JobModel.id == job_id)
    )
    return result.scalar_one_or_none()


async def get_jobs(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[JobModel]:
    """Get all jobs with pagination"""
    result = await session.execute(
        select(JobModel).order_by(JobModel.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_workers(session: AsyncSession) -> List[WorkerModel]:
    """Get all workers"""
    result = await session.execute(select(WorkerModel))
    return result.scalars().all()


async def update_job_status(session: AsyncSession, job_id: str, status: str, completed_tasks: int = None):
    """Update job status"""
    update_data = {"status": status}
    if completed_tasks is not None:
        update_data["completed_tasks"] = completed_tasks
    if status == "completed":
        update_data["completed_at"] = datetime.now()
    
    stmt = update(JobModel).where(JobModel.id == job_id).values(**update_data)
    await session.execute(stmt)
    await session.commit()


async def update_task_status(session: AsyncSession, task_id: str, status: str, worker_id: str = None, result: str = None, error: str = None):
    """Update task status"""
    update_data = {"status": status}
    if worker_id:
        update_data["worker_id"] = worker_id
    if result:
        update_data["result"] = result
    if error:
        update_data["error_message"] = error
    
    if status == "assigned":
        update_data["assigned_at"] = datetime.now()
    elif status in ["completed", "failed"]:
        update_data["completed_at"] = datetime.now()
    
    stmt = update(TaskModel).where(TaskModel.id == task_id).values(**update_data)
    await session.execute(stmt)
    await session.commit()


async def update_worker_status(session: AsyncSession, worker_id: str, status: str, current_task_id: str = None):
    """Update worker status"""
    update_data = {
        "status": status,
        "last_seen": datetime.now()
    }
    if current_task_id:
        update_data["current_task_id"] = current_task_id
    
    stmt = update(WorkerModel).where(WorkerModel.id == worker_id).values(**update_data)
    await session.execute(stmt)
    await session.commit()


async def update_worker_task_stats(session: AsyncSession, worker_id: str, task_completed: bool = True):
    """Update worker task completion statistics"""
    if task_completed:
        # Increment completed tasks
        stmt = update(WorkerModel).where(WorkerModel.id == worker_id).values(
            total_tasks_completed=WorkerModel.total_tasks_completed + 1
        )
    else:
        # Increment failed tasks
        stmt = update(WorkerModel).where(WorkerModel.id == worker_id).values(
            total_tasks_failed=WorkerModel.total_tasks_failed + 1
        )
    
    await session.execute(stmt)
    await session.commit()


async def increment_job_completed_tasks(session: AsyncSession, job_id: str):
    """Increment the completed_tasks count for a job"""
    stmt = update(JobModel).where(JobModel.id == job_id).values(
        completed_tasks=JobModel.completed_tasks + 1
    )
    await session.execute(stmt)
    await session.commit()





async def get_online_workers_count(session: AsyncSession) -> int:
    """Get count of online workers"""
    result = await session.execute(
        select(func.count(WorkerModel.id)).where(WorkerModel.status == "online")
    )
    return result.scalar() or 0


async def get_job_stats(session: AsyncSession) -> JobStats:
    """Get job statistics"""
    # Get all jobs and count by status
    jobs = await get_jobs(session, skip=0, limit=10000)  # Get all jobs
    
    total_jobs = len(jobs)
    pending_jobs = len([j for j in jobs if j.status == 'pending'])
    running_jobs = len([j for j in jobs if j.status == 'running'])
    completed_jobs = len([j for j in jobs if j.status == 'completed'])
    failed_jobs = len([j for j in jobs if j.status == 'failed'])
    
    # Get all tasks and count by status
    result = await session.execute(select(TaskModel))
    tasks = result.scalars().all()
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == 'completed'])
    failed_tasks = len([t for t in tasks if t.status == 'failed'])
    
    # Get online workers count
    online_workers = await get_online_workers_count(session)
    
    return JobStats(
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        running_jobs=running_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        online_workers=online_workers
    )


async def get_job_tasks(session: AsyncSession, job_id: str) -> List[TaskModel]:
    """Get all tasks for a job"""
    result = await session.execute(
        select(TaskModel).where(TaskModel.job_id == job_id)
    )
    return result.scalars().all()


async def get_pending_tasks(session: AsyncSession, job_id: str = None) -> List[TaskModel]:
    """Get pending tasks, optionally filtered by job_id"""
    query = select(TaskModel).where(TaskModel.status == "pending")
    if job_id:
        query = query.where(TaskModel.job_id == job_id)
    
    result = await session.execute(query)
    return result.scalars().all()


async def get_job_by_id(session: AsyncSession, job_id: str) -> Optional[JobModel]:
    """Get job by ID (alias for get_job)"""
    return await get_job(session, job_id)
