from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from foreman.schema.schema import JobStats, WorkerFailureStats
from .models import *

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


async def record_worker_failure(session: AsyncSession, worker_id: str, task_id: str, error_message: str, job_id: Optional[str] = None) -> None:
    """Insert a worker failure record"""
    failure = WorkerFailureModel(
        worker_id=worker_id,
        task_id=task_id,
        job_id=job_id or "",
        error_message=error_message,
        failed_at=datetime.now()
    )
    session.add(failure)
    await session.commit()


async def get_worker_failures(session: AsyncSession, worker_id: str, skip: int = 0, limit: int = 100) -> List[WorkerFailureModel]:
    """Fetch failure history for a worker"""
    result = await session.execute(
        select(WorkerFailureModel)
        .where(WorkerFailureModel.worker_id == worker_id)
        .order_by(WorkerFailureModel.failed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_worker_failure_stats(session: AsyncSession, worker_id: str) -> WorkerFailureStats:
    """Compute failure stats and rate for a worker"""
    total_failures_result = await session.execute(
        select(func.count(WorkerFailureModel.id)).where(WorkerFailureModel.worker_id == worker_id)
    )
    total_failures = total_failures_result.scalar() or 0
    
    # Total tasks for worker = completed + failed from Workers table
    worker_result = await session.execute(select(WorkerModel).where(WorkerModel.id == worker_id))
    worker: Optional[WorkerModel] = worker_result.scalar_one_or_none()
    if worker:
        total_tasks = (worker.total_tasks_completed or 0) + (worker.total_tasks_failed or 0)
    else:
        total_tasks = 0
    
    failure_rate = float(total_failures) / float(total_tasks) if total_tasks > 0 else 0.0
    
    return WorkerFailureStats(
        worker_id=worker_id,
        total_failures=total_failures,
        total_tasks=total_tasks,
        failure_rate=round(failure_rate, 4)
    )





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
