import json
from ....db.base import db_session
from ....db.crud import * 

async def _record_worker_failure(worker_id, task_id, error, job_id):
    async with db_session() as session:
        await record_worker_failure(session, worker_id, task_id, error_message=str(error), job_id=job_id)

async def _get_job_tasks(job_id):
    # Get all tasks for this job
    async with db_session() as session:
        tasks = await get_job_tasks(session, job_id)
    return tasks

async def _get_pending_tasks(job_id=None):       
    # Get pending tasks for this job
    async with db_session() as session:
        pending_tasks = await get_pending_tasks(session, job_id)
    return pending_tasks

async def _get_job_by_id(job_id: str):
    """Get job by ID from database"""
    
    async with db_session() as session:
        return await get_job_by_id(session, job_id)

async def _create_job_in_database(job_id: str, total_tasks: int):
    """Create job in database""" 
    
    # Create a new session for this operation
    async with db_session() as session:
        await create_job(session, job_id, total_tasks)
    print(f"Created job {job_id} in database")

async def _create_worker_in_database(worker_id: str):
    """Create worker in database if it doesn't exist""" 
    
    # Create a new session for this operation
    async with db_session() as session:
        # Check if worker already exists
        workers = await get_workers(session)
        existing_worker_ids = [w.id for w in workers]
        
        if worker_id not in existing_worker_ids:
            await create_worker(session, worker_id)
            print(f"Created worker {worker_id} in database")
        else:
            # Worker exists, ensure it's marked as online
            await update_worker_status(session, worker_id, "online")
            print(f"Worker {worker_id} already exists in database, marked as online")

async def _create_tasks_for_job(job_id: str, args_list: list):
    """Create tasks in database for a job""" 
    
    # Create a new session for this operation
    async with db_session() as session:
        tasks = []
        for i, args in enumerate(args_list):
            task_id = f"{job_id}_task_{i}"
            task = TaskModel(
                id=task_id,
                job_id=job_id,
                args=json.dumps(args),  # Serialize args to JSON string
                status="pending"
            )
            tasks.append(task)
        
        # Add all tasks to database
        session.add_all(tasks)
        await session.commit()
    
    print(f"Created {len(tasks)} tasks for job {job_id}")

async def _update_job_status(job_id: str, status: str, completed_tasks: int = None):
    """Update job status with new session""" 
    
    async with db_session() as session:
        await update_job_status(session, job_id, status, completed_tasks)

async def _update_task_status(task_id: str, status: str, worker_id: str = None, result: str = None, error: str = None):
    """Update task status with new session""" 
    
    async with db_session() as session:
        await update_task_status(session, task_id, status, worker_id, result, error)

async def _update_worker_status(worker_id: str, status: str, current_task_id: str = None):
    """Update worker status with new session""" 
    
    async with db_session() as session:
        await update_worker_status(session, worker_id, status, current_task_id)

async def _update_worker_task_stats(worker_id: str, task_completed: bool = True):
    """Update worker task statistics with new session""" 
    
    async with db_session() as session:
        await update_worker_task_stats(session, worker_id, task_completed)

async def _increment_job_completed_tasks(job_id: str):
    """Increment job completed tasks count with new session""" 
    
    async with db_session() as session:
        await increment_job_completed_tasks(session, job_id)