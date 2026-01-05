# These functions are defined in utils.py, not in db module
# Import them from the current module
from .utils import (
    _record_worker_failure,
    _get_job_tasks,
    _get_pending_tasks,
    _get_job_by_id,
    _create_job_in_database,
    _create_worker_in_database,
    _create_tasks_for_job,
    _update_job_status,
    _update_task_status,
    _update_worker_status,
    _update_worker_task_stats,
    _increment_job_completed_tasks,
    _get_worker_stats,
)

__all__ = [
    "_record_worker_failure",
    "_get_job_tasks",
    "_get_pending_tasks",
    "_get_job_by_id",
    "_create_job_in_database",
    "_create_worker_in_database",
    "_create_tasks_for_job",
    "_update_job_status",
    "_update_task_status",
    "_update_worker_status",
    "_update_worker_task_stats",
    "_increment_job_completed_tasks",
    "_get_worker_stats",
]
