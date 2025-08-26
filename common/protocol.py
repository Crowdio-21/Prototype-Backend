"""
Network protocol definitions for CrowdCompute
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MessageType(Enum):
    """Message types for WebSocket communication"""
    # Client -> Foreman
    SUBMIT_JOB = "submit_job"
    GET_RESULTS = "get_results"
    DISCONNECT = "disconnect"
    
    # Foreman -> Worker
    ASSIGN_TASK = "assign_task"
    PING = "ping"
    
    # Worker -> Foreman
    TASK_RESULT = "task_result"
    TASK_ERROR = "task_error"
    WORKER_READY = "worker_ready"
    WORKER_HEARTBEAT = "worker_heartbeat"
    PONG = "pong"
    
    # Foreman -> Client
    JOB_RESULTS = "job_results"
    JOB_ERROR = "job_error"
    JOB_ACCEPTED = "job_accepted"


class Message:
    """Base message class"""
    
    def __init__(self, msg_type: MessageType, data: Dict[str, Any], job_id: Optional[str] = None):
        self.type = msg_type
        self.data = data
        self.job_id = job_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "job_id": self.job_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            msg_type=MessageType(data["type"]),
            data=data["data"],
            job_id=data.get("job_id")
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        return cls.from_dict(json.loads(json_str))


# Message factory functions
def create_submit_job_message(func_code: str, args_list: List[Any], job_id: str) -> Message:
    """Create a job submission message"""
    return Message(
        msg_type=MessageType.SUBMIT_JOB,
        data={
            "func_code": func_code,
            "args_list": args_list,
            "total_tasks": len(args_list)
        },
        job_id=job_id
    )


def create_assign_task_message(func_code: str, task_args: List[Any], task_id: str, job_id: str) -> Message:
    """Create a task assignment message"""
    return Message(
        msg_type=MessageType.ASSIGN_TASK,
        data={
            "func_code": func_code,
            "task_args": task_args,
            "task_id": task_id
        },
        job_id=job_id
    )


def create_task_result_message(result: Any, task_id: str, job_id: str) -> Message:
    """Create a task result message"""
    return Message(
        msg_type=MessageType.TASK_RESULT,
        data={
            "result": result,
            "task_id": task_id
        },
        job_id=job_id
    )


def create_task_error_message(error: str, task_id: str, job_id: str) -> Message:
    """Create a task error message"""
    return Message(
        msg_type=MessageType.TASK_ERROR,
        data={
            "error": error,
            "task_id": task_id
        },
        job_id=job_id
    )


def create_job_results_message(results: List[Any], job_id: str) -> Message:
    """Create a job results message"""
    return Message(
        msg_type=MessageType.JOB_RESULTS,
        data={"results": results},
        job_id=job_id
    )


def create_worker_ready_message(worker_id: str) -> Message:
    """Create a worker ready message"""
    return Message(
        msg_type=MessageType.WORKER_READY,
        data={"worker_id": worker_id}
    )


def create_ping_message() -> Message:
    """Create a ping message"""
    return Message(
        msg_type=MessageType.PING,
        data={}
    )


def create_pong_message() -> Message:
    """Create a pong message"""
    return Message(
        msg_type=MessageType.PONG,
        data={}
    )
