# Foreman FastAPI Package

The `foreman_fastapi` package implements the central task manager and job scheduler for the CrowdCompute distributed computing system.

## Overview

This package provides a FastAPI-based foreman server that manages job submissions, task distribution, worker coordination, and result aggregation. It serves as the central hub for the distributed computing network.

## Modules

### `main.py`
FastAPI application entry point with REST API endpoints and WebSocket server.

**Key Features:**
- FastAPI application with automatic API documentation
- WebSocket server for real-time communication
- REST API endpoints for monitoring and control
- HTML dashboard for system visualization
- Automatic database initialization

**Endpoints:**
- `GET /` - System dashboard
- `GET /api/stats` - System statistics
- `GET /api/jobs` - List all jobs
- `GET /api/workers` - List all workers
- `GET /api/jobs/{job_id}` - Get specific job details
- `GET /api/jobs/{job_id}/tasks` - Get job tasks
- `WebSocket /ws` - Real-time communication

### `database.py`
SQLAlchemy ORM models and database operations for job, task, and worker management.

**Models:**
- `JobModel` - Job information and status
- `TaskModel` - Individual task details
- `WorkerModel` - Worker information and status

**Key Functions:**
- `init_db()` - Initialize database tables
- `create_job()` - Create new job
- `create_task()` - Create new task
- `create_worker()` - Create new worker
- `update_job_status()` - Update job status
- `update_task_status()` - Update task status
- `update_worker_status()` - Update worker status
- `get_job_stats()` - Get system statistics

### `websocket_manager.py`
WebSocket connection manager handling client and worker communications.

**Key Features:**
- Client connection management
- Worker connection management
- Job submission handling
- Task assignment and distribution
- Result collection and aggregation
- Error handling and recovery

**Key Methods:**
- `handle_connection()` - Handle new WebSocket connections
- `_handle_job_submission()` - Process job submissions
- `_handle_worker_ready()` - Process worker availability
- `_handle_task_result()` - Process task results
- `_assign_tasks_to_workers()` - Distribute tasks to workers
- `_check_job_completion()` - Check and finalize completed jobs

## Usage

### Starting the Foreman

```python
# Using the provided script
python test_utils/run_foreman_simple.py

# Or directly with uvicorn
uvicorn foreman_fastapi.main:app --host 0.0.0.0 --port 8000
```

### API Usage

```python
import requests

# Get system statistics
response = requests.get("http://localhost:8000/api/stats")
stats = response.json()
print(f"Active workers: {stats['connected_workers']}")

# Get all jobs
response = requests.get("http://localhost:8000/api/jobs")
jobs = response.json()
print(f"Total jobs: {len(jobs)}")

# Get specific job
job_id = "job-123"
response = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
job = response.json()
print(f"Job status: {job['status']}")
```

### WebSocket Communication

```python
import websockets
import json

async def connect_to_foreman():
    uri = "ws://localhost:9000"
    async with websockets.connect(uri) as websocket:
        # Submit a job
        message = {
            "type": "submit_job",
            "data": {
                "func_pickle": "serialized_function_hex",
                "args_list": [1, 2, 3, 4, 5],
                "total_tasks": 5
            },
            "job_id": "job-123"
        }
        await websocket.send(json.dumps(message))
        
        # Listen for results
        response = await websocket.recv()
        result = json.loads(response)
        print(f"Job result: {result}")
```

## Features

### Job Management
- **Job Submission** - Accept jobs from clients
- **Task Splitting** - Automatically split jobs into tasks
- **Status Tracking** - Monitor job and task progress
- **Result Collection** - Aggregate results from workers

### Worker Management
- **Worker Registration** - Register available workers
- **Load Balancing** - Distribute tasks across workers
- **Health Monitoring** - Monitor worker status and availability
- **Failure Recovery** - Handle worker failures gracefully

### Database Persistence
- **Job Persistence** - Store job information and status
- **Task Tracking** - Track individual task progress
- **Worker History** - Maintain worker information
- **Statistics** - Generate system statistics

### Real-time Communication
- **WebSocket Server** - Real-time bidirectional communication
- **Message Protocol** - Structured message format
- **Error Handling** - Robust error handling and recovery
- **Connection Management** - Manage multiple client and worker connections

## Architecture

```
Clients → WebSocket → Foreman → Database
                ↓
            Workers ← Task Assignment
```

1. **Client Connection** - Clients connect via WebSocket
2. **Job Submission** - Clients submit jobs with functions and data
3. **Task Creation** - Foreman splits jobs into individual tasks
4. **Worker Assignment** - Tasks assigned to available workers
5. **Result Collection** - Results collected and aggregated
6. **Job Completion** - Final results sent back to client

## Configuration

### Database
- **SQLite** - Default database (can be changed to PostgreSQL/MySQL)
- **Auto-initialization** - Tables created automatically on startup
- **Connection pooling** - Efficient database connection management

### WebSocket
- **Port 9000** - Default WebSocket port
- **CORS enabled** - Cross-origin requests supported
- **Connection limits** - Configurable connection limits

### FastAPI
- **Port 8000** - Default HTTP port
- **Auto-reload** - Development mode with auto-reload
- **API documentation** - Automatic OpenAPI documentation

## Monitoring

### Dashboard
- **Real-time stats** - Live system statistics
- **Job monitoring** - Track job progress
- **Worker status** - Monitor worker availability
- **Task distribution** - Visualize task distribution

### API Endpoints
- **System stats** - Overall system statistics
- **Job details** - Individual job information
- **Worker info** - Worker status and history
- **Task progress** - Task-level progress tracking

## Error Handling

The foreman handles various error scenarios:
- **Worker failures** - Automatic task reassignment
- **Network issues** - Connection recovery and retry
- **Database errors** - Transaction rollback and recovery
- **Invalid messages** - Graceful error reporting
- **Resource exhaustion** - Queue management and throttling
