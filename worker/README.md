# Worker FastAPI Package

The `worker` package implements the worker nodes that execute distributed computing tasks for the CrowdCompute system.

## Overview

This package provides FastAPI-based worker servers that connect to the foreman, receive task assignments, execute Python functions, and return results. Workers can run on any device with Python support.

## Modules

### `worker.py`
Main worker implementation with FastAPI server and task execution engine.

**Key Classes:**
- `WorkerConfig` - Worker configuration settings
- `FastAPIWorker` - Main worker class with FastAPI integration

**Key Features:**
- FastAPI server for monitoring and control
- WebSocket client for foreman communication
- Task execution engine with error handling
- Statistics tracking and monitoring
- Automatic reconnection and recovery

**Key Methods:**
- `connect()` - Connect to foreman
- `disconnect()` - Disconnect from foreman
- `handle_message()` - Process incoming messages
- `_handle_task_assignment()` - Handle task assignments
- `_execute_task()` - Execute assigned tasks
- `listen_for_tasks()` - Listen for task assignments
- `heartbeat()` - Send periodic heartbeats

### `dashboard.py`
HTML dashboard for worker monitoring and control.

**Features:**
- Real-time worker status display
- Task execution statistics
- Connection status monitoring
- Performance metrics
- WebSocket-based live updates

## Usage

### Starting a Worker

```python
# Using the provided script
python tests/run_worker_simple.py

# Or programmatically
from worker.worker import FastAPIWorker, WorkerConfig
import asyncio

async def start_worker():
    config = WorkerConfig(
        worker_id="worker-001",
        foreman_url="ws://localhost:9000",
        max_concurrent_tasks=1,
        auto_restart=True,
        heartbeat_interval=30
    )
    
    worker = FastAPIWorker(config)
    await worker.start()

asyncio.run(start_worker())
```

### Worker Configuration

```python
from worker.worker import WorkerConfig

config = WorkerConfig(
    worker_id="unique-worker-id",      # Unique identifier
    foreman_url="ws://192.168.1.100:9000",  # Foreman WebSocket URL
    max_concurrent_tasks=2,            # Max concurrent tasks
    auto_restart=True,                 # Auto-restart on failure
    heartbeat_interval=30              # Heartbeat frequency (seconds)
)
```

### API Usage

```python
import requests

# Get worker status
response = requests.get("http://localhost:8001/")
status = response.json()
print(f"Worker ID: {status['worker_id']}")
print(f"Status: {status['status']}")
print(f"Current task: {status['current_task']}")

# Get worker statistics
response = requests.get("http://localhost:8001/stats")
stats = response.json()
print(f"Tasks completed: {stats['stats']['tasks_completed']}")
print(f"Tasks failed: {stats['stats']['tasks_failed']}")
print(f"Total execution time: {stats['stats']['total_execution_time']}")

# Restart worker
response = requests.post("http://localhost:8001/restart")
print("Worker restarted")
```

## Features

### Task Execution
- **Function Deserialization** - Deserialize functions from cloudpickle
- **Safe Execution** - Execute functions in controlled environment
- **Argument Handling** - Support for various argument formats
- **Error Handling** - Capture and report execution errors
- **Result Serialization** - Serialize results for transmission

### Connection Management
- **WebSocket Client** - Connect to foreman via WebSocket
- **Automatic Reconnection** - Reconnect on connection loss
- **Heartbeat Monitoring** - Send periodic heartbeats
- **Connection Recovery** - Handle network interruptions

### Monitoring and Control
- **FastAPI Server** - HTTP API for monitoring
- **Real-time Dashboard** - Web-based monitoring interface
- **Statistics Tracking** - Track performance metrics
- **Status Reporting** - Report current status and health

### Error Handling
- **Task Failures** - Handle task execution errors
- **Network Issues** - Handle connection problems
- **Resource Limits** - Respect system resource limits
- **Graceful Degradation** - Continue operation despite errors

## Architecture

```
Foreman → WebSocket → Worker → Task Execution
                ↓
            FastAPI Server → Dashboard
```

1. **Connection** - Worker connects to foreman via WebSocket
2. **Registration** - Worker announces availability
3. **Task Assignment** - Foreman assigns tasks to worker
4. **Task Execution** - Worker executes assigned tasks
5. **Result Return** - Results sent back to foreman
6. **Monitoring** - Status available via HTTP API

## Task Execution Flow

```python
# 1. Receive task assignment
task_message = {
    "type": "assign_task",
    "data": {
        "func_pickle": "serialized_function_hex",
        "args_list": [1, 2, 3],
        "task_id": "task-123"
    },
    "job_id": "job-456"
}

# 2. Deserialize function
func = deserialize_function(func_pickle)

# 3. Execute function
result = func(*args_list)

# 4. Send result
result_message = {
    "type": "task_result",
    "data": {
        "task_id": "task-123",
        "result": result
    },
    "job_id": "job-456"
}
```

## Configuration Options

### Worker Settings
- **Worker ID** - Unique identifier for the worker
- **Foreman URL** - WebSocket URL of the foreman
- **Max Concurrent Tasks** - Maximum tasks to execute simultaneously
- **Auto Restart** - Automatically restart on failure
- **Heartbeat Interval** - Frequency of heartbeat messages

### Network Settings
- **WebSocket Port** - Port for foreman communication (9000)
- **HTTP Port** - Port for monitoring API (8001)
- **Connection Timeout** - Timeout for WebSocket connections
- **Retry Interval** - Interval between reconnection attempts

### Execution Settings
- **Task Timeout** - Maximum time for task execution
- **Memory Limit** - Memory usage limit for tasks
- **CPU Limit** - CPU usage limit for tasks
- **Sandbox Mode** - Execute tasks in restricted environment

## Monitoring

### Dashboard Features
- **Real-time Status** - Current worker status
- **Task Statistics** - Completed and failed tasks
- **Performance Metrics** - Execution time and throughput
- **Connection Status** - Foreman connection status
- **Resource Usage** - CPU and memory usage

### API Endpoints
- `GET /` - Worker status and configuration
- `GET /stats` - Detailed statistics
- `POST /restart` - Restart worker connection
- `WebSocket /ws` - Real-time status updates

## Best Practices

### Security
1. **Sandbox Execution** - Execute tasks in restricted environment
2. **Resource Limits** - Set appropriate resource limits
3. **Network Security** - Use secure WebSocket connections
4. **Access Control** - Restrict API access if needed

### Performance
1. **Concurrent Tasks** - Adjust based on system capabilities
2. **Memory Management** - Monitor memory usage
3. **Network Optimization** - Optimize for network conditions
4. **Error Recovery** - Implement robust error handling

### Monitoring
1. **Health Checks** - Regular health check monitoring
2. **Logging** - Comprehensive logging for debugging
3. **Metrics Collection** - Collect performance metrics
4. **Alerting** - Set up alerts for critical issues

## Deployment

### Local Development
```bash
# Start worker locally
python tests/run_worker_simple.py
```

### Production Deployment
```bash
# Using uvicorn
uvicorn worker.worker:app --host 0.0.0.0 --port 8001

# Using gunicorn
gunicorn worker.worker:app -w 1 -k uvicorn.workers.UvicornWorker
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "tests/run_worker_simple.py"]
```
