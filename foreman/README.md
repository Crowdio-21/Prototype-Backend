# Foreman Module

The `foreman` module is the central orchestrator for the CrowdCompute distributed computing system. It manages job submissions, task distribution, worker coordination, and result aggregation.

## Overview

The Foreman module provides:
- **FastAPI REST API** on port 8000 for HTTP requests and dashboard access
- **WebSocket Server** on port 9000 for real-time bidirectional communication with workers and clients
- **Job Management** - Job creation, tracking, and lifecycle management
- **Task Scheduling** - Pluggable scheduling algorithms for intelligent task distribution
- **Worker Coordination** - Connection management, load balancing, and failure recovery
- **SQLite Database** - Persistent storage of jobs, tasks, workers, and statistics

## Directory Structure

```
foreman/
├── main.py                 # FastAPI application entry point
├── api/                    # REST API and HTTP routes
│   ├── routes.py          # API endpoints
│   ├── websockets.py      # WebSocket endpoint handler
│   └── temp_dashboard.html # Web dashboard
├── core/                   # Core business logic
│   ├── job_manager.py     # Job lifecycle management
│   ├── task_dispatcher.py # Task scheduling and assignment
│   ├── connection_manager.py # WebSocket connection tracking
│   ├── message_handlers.py # Message processing logic
│   ├── completion_handler.py # Job completion logic
│   ├── ws_manager.py      # Main WebSocket orchestrator
│   ├── scheduling/        # Pluggable scheduling algorithms
│   │   ├── scheduler_interface.py
│   │   ├── fifo_scheduler.py
│   │   ├── round_robin_scheduler.py
│   │   ├── least_loaded_scheduler.py
│   │   ├── performance_scheduler.py
│   │   ├── priority_scheduler.py
│   │   └── factory.py
│   └── utils/  # WebSocket utility functions
├── db/                     # Database layer
│   ├── base.py            # SQLAlchemy setup and initialization
│   ├── models.py          # Database models (Job, Task, Worker, etc.)
│   ├── crud.py            # Database operations
│   └── __pycache__/
└── schema/                 # Pydantic schemas
    └── schema.py          # Response models

```

## Core Components

### `main.py` - FastAPI Application
Entry point that initializes the FastAPI app and WebSocket server.

**Key Features:**
- FastAPI application with lifespan management
- Automatic database initialization on startup
- WebSocket server initialization on port 9000
- CORS middleware configuration
- API router integration

### `api/routes.py` - REST API Endpoints
REST endpoints for job monitoring and system statistics.

**Key Endpoints:**
- `GET /` - Web dashboard
- `GET /api/stats` - System statistics (JobStats)
- `GET /api/jobs` - List all jobs with pagination
- `GET /api/jobs/{job_id}` - Get specific job details
- `GET /api/workers` - List all workers
- `GET /api/jobs/{job_id}/tasks` - Get tasks for a job
- `GET /api/worker-failures` - Get worker failure history
- `GET /api/worker-failure-stats` - Get failure statistics

### `api/websockets.py` - WebSocket Endpoint
Provides WebSocket endpoint for real-time communication.

**Path:** `ws://localhost:9000`

### `core/ws_manager.py` - Main Orchestrator
Central orchestrator that coordinates all components.

**Responsibilities:**
- Handle WebSocket connections from workers and clients
- Route messages to appropriate handlers
- Coordinate job creation, task assignment, and result collection
- Manage worker availability and failure handling

### `core/job_manager.py` - Job Lifecycle Management
Manages job creation, task generation, and state tracking.

**Key Responsibilities:**
- Create jobs with associated tasks
- Track job metadata and cached function code
- Manage task state transitions
- Retrieve job results
- Track job completion status

### `core/task_dispatcher.py` - Task Scheduling
Dispatches tasks to workers using pluggable scheduling algorithms.

**Key Responsibilities:**
- Use scheduler to select best worker for a task
- Send task assignments to workers
- Update task and worker status
- Support multiple scheduling strategies

**Supported Schedulers:**
- `FIFOScheduler` - First-in-first-out task order
- `RoundRobinScheduler` - Distribute tasks in round-robin fashion
- `LeastLoadedScheduler` - Assign to least busy worker
- `PerformanceScheduler` - Consider worker performance metrics
- `PriorityScheduler` - Task priority-based distribution

### `core/connection_manager.py` - Connection Tracking
Manages WebSocket connections for workers and clients.

**Key Responsibilities:**
- Track active worker connections
- Track client connections to jobs
- Provide connection lookups by ID
- Manage connection availability state

### `core/message_handlers.py` - Message Processing
Processes incoming messages from workers and clients.

**Message Types Handled:**
- Job submission messages
- Worker ready/available messages
- Task result messages
- Worker failure notifications
- Heartbeat/ping messages

### `core/completion_handler.py` - Job Completion
Handles job completion logic and result delivery.

**Key Responsibilities:**
- Check if all tasks are completed
- Aggregate results from tasks
- Send results back to client
- Clean up job resources

### `db/models.py` - Database Models
SQLAlchemy ORM models for data persistence.

**Models:**
- `Job` - Job information, status, creation time
- `Task` - Individual task within a job
- `Worker` - Worker information and status
- `WorkerFailure` - Worker failure history and statistics

### `db/crud.py` - Database Operations
CRUD operations for querying and updating database records.

**Key Operations:**
- Create and update jobs, tasks, workers
- Query jobs/tasks by status or ID
- Get system statistics
- Fetch worker failure information

### `db/base.py` - Database Setup
SQLAlchemy configuration and initialization.

**Features:**
- Async SQLAlchemy session management
- Database URL configuration
- Table creation (init_db)
- Connection pool setup

## Usage

### Starting the Foreman

The foreman runs two servers:
- **REST API** on `http://localhost:8000` (FastAPI)
- **WebSocket** on `ws://localhost:9000` (Raw WebSocket)

```bash
# Using the provided test script
uv run python tests/run_foreman_simple.py

# Or directly with uvicorn
uv run uvcornman.main:app --host 0.0.0.0 --port 8000
```

### REST API Usage

Get system statistics:
```python
import requests

response = requests.get("http://localhost:8000/api/stats")
stats = response.json()
print(f"Total jobs: {stats.get('total_jobs', 0)}")
print(f"Connected workers: {stats.get('connected_workers', 0)}")
```

List all jobs:
```python
response = requests.get("http://localhost:8000/api/jobs?skip=0&limit=100")
jobs = response.json()
for job in jobs:
    print(f"Job {job['id']}: {job['status']}")
```

Get specific job details:
```python
job_id = "job-123"
response = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
job = response.json()
print(f"Job {job_id} status: {job['status']}")
```

Get job tasks:
```python
response = requests.get(f"http://localhost:8000/api/jobs/{job_id}/tasks")
tasks = response.json()
for task in tasks:
    print(f"Task {task['id']}: {task['status']}")
```

### WebSocket Communication

Workers and clients connect directly to the WebSocket server on port 9000.

#### Client Job Submission
```python
import websockets
import json

async def submit_job():
    uri = "ws://localhost:9000"
    async with websockets.connect(uri) as websocket:
        # Submit a job
        message = {
            "type": "submit_job",
            "job_id": "job-123",
            "data": {
                "func_code": "serialized_function_hex",
                "args_list": [[1], [2], [3], [4], [5]],
                "total_tasks": 5
            }
        }
        await websocket.send(json.dumps(message))
        
        # Receive results
        response = await websocket.recv()
        result = json.loads(response)
        print(f"Job result: {result}")
```

#### Worker Connection
```python
import websockets
import json

async def worker_loop():
    uri = "ws://localhost:9000"
    async with websockets.connect(uri) as websocket:
        # Register as worker
        message = {
            "type": "register_worker",
            "worker_id": "worker-1"
        }
        await websocket.send(json.dumps(message))
        
        # Listen for task assignments
        while True:
            task = await websocket.recv()
            task_data = json.loads(task)
            # Execute task...
```

### Dashboard

Access the web dashboard at `http://localhost:8000/` to view:
- Real-time job statistics
- Active worker list
- Job progress tracking
- Task distribution visualization## Message Protocol

The WebSocket communication uses JSON-based messages with the following structure:

```json
{
  "type": "message_type",
  "job_id": "job-123",
  "worker_id": "worker-1",
  "data": {
    // Message-specific data
  }
}
```

### Supported Message Types

**From Client:**
- `submit_job` - Submit a new job for execution
- `get_job_status` - Query job status

**From Worker:**
- `register_worker` - Register as available worker
- `worker_ready` - Indicate readiness to accept tasks
- `task_result` - Return task execution result
- `worker_failure` - Report task execution failure

**From Foreman:**
- `assign_task` - Assign task to worker
- `job_result` - Return final job results
- `job_status` - Send job status update
- `error` - Error message

## Features

### Job Management
- **Job Submission** - Accept jobs from clients with function code and argument lists
- **Task Splitting** - Automatically split jobs into individual tasks
- **Status Tracking** - Monitor job and task progress (pending, assigned, completed, failed)
- **Result Collection** - Aggregate results from workers
- **Job Persistence** - Store jobs in database for recovery and monitoring

### Worker Management
- **Dynamic Registration** - Workers register on connection
- **Availability Tracking** - Track which workers are ready for tasks
- **Load Balancing** - Multiple scheduling algorithms for optimal distribution
- **Performance Monitoring** - Track worker execution times and success rates
- **Failure Recovery** - Automatic task reassignment on worker failure
- **Failure History** - Maintain detailed worker failure logs

### Scheduling Algorithms
The foreman supports pluggable scheduling algorithms:

| Algorithm | Description |
|-----------|-------------|
| **FIFO** | Tasks assigned in first-in-first-out order |
| **Round Robin** | Distributes tasks evenly in round-robin fashion |
| **Least Loaded** | Assigns to worker with fewest active tasks |
| **Performance** | Uses worker performance metrics for selection |
| **Priority** | Respects task priority levels |

### Database Persistence
- **Job Persistence** - Complete job information with metadata
- **Task Tracking** - Individual task status and results
- **Worker Registry** - Worker information and statistics
- **Failure History** - Detailed logs of worker failures
- **Statistics** - System-wide statistics generation

### Real-time Communication
- **WebSocket Server** - Efficient bidirectional communication on port 9000
- **Async Processing** - Non-blocking message handling
- **Connection Management** - Track and manage multiple concurrent connections
- **Error Handling** - Robust error handling and recovery
- **Message Queuing** - Buffer messages during high load

## Architecture Flow

```
┌─────────────┐           ┌──────────────┐           ┌──────────────┐
│   Client    │           │    Foreman   │           │    Worker    │
└─────────────┘           └──────────────┘           └──────────────┘
      │                         │                          │
      │──submit_job────────────→│                          │
      │                         │                          │
      │                         │──create tasks────────────→
      │                         │                          │
      │                         │←─worker_ready────────────│
      │                         │                          │
      │                         │──assign_task────────────→│
      │                         │                          │
      │                         │←─task_result────────────│
      │                         │                          │
      │←────job_result─────────│                          │
      │                         │                          │
```

**Workflow:**
1. Client submits job with function code and arguments
2. Foreman creates job record and splits into tasks
3. Workers connect and register as available
4. Foreman assigns tasks to available workers
5. Workers execute tasks and return results
6. Foreman collects results and checks for completion
7. When all tasks complete, Foreman sends results to client

## Configuration

### Foreman Startup
The foreman initializes automatically when `main.py` is executed:

```bash
uv run python foreman/main.py
# Or via uvicorn:
uv run uvcornman.main:app --host 0.0.0.0 --port 8000
```

**Initialization Steps:**
1. Initialize SQLite database (auto-creates tables)
2. Create WebSocketManager instance
3. Start WebSocket server on port 9000
4. Start FastAPI server on port 8000

### Database Configuration
- **Default:** SQLite at `foreman.db`
- **Connection:** Async SQLAlchemy with SQLite
- **Pooling:** Built-in connection pool management
- **Auto-init:** Tables created automatically on startup

### WebSocket Configuration
- **Port:** 9000 (configurable via environment)
- **Host:** 0.0.0.0 (listen on all interfaces)
- **Protocol:** Python websockets library
- **Message Format:** JSON

### FastAPI Configuration
- **Port:** 8000 (configurable via uvicorn args)
- **Host:** 0.0.0.0 (listen on all interfaces)
- **Documentation:** Available at `/docs` (Swagger UI)
- **CORS:** Enabled for cross-origin requests

## Monitoring

### Web Dashboard
Access at `http://localhost:8000/`
- Real-time system statistics
- Job progress tracking
- Worker availability status
- Task distribution visualization

### REST API Statistics
```bash
curl http://localhost:8000/api/stats
```

Returns JobStats object with:
- `total_jobs` - Total number of jobs
- `completed_jobs` - Completed job count
- `pending_jobs` - Jobs awaiting task completion
- `connected_workers` - Currently connected workers
- `active_tasks` - Tasks being processed
- `total_tasks_completed` - Lifetime task completion count

### Database Queries
```python
from foreman.db.crud import get_job_stats, get_worker_failure_stats

# Get job statistics
stats = await get_job_stats(db_session)

# Get worker failure statistics
failures = await get_worker_failure_stats(db_session)
```

## Error Handling

The foreman implements comprehensive error handling:

| Error Scenario | Recovery Strategy |
|----------------|-------------------|
| **Worker Disconnect** | Mark tasks as unassigned, reassign to other workers |
| **Task Execution Failure** | Record failure, reassign to different worker |
| **Worker Timeout** | After timeout, treat as disconnected |
| **Database Error** | Log error, retry operation with backoff |
| **Invalid Message** | Return error message to sender |
| **Connection Exhaustion** | Queue messages during overload |

## Development

### Running Tests
```bash
uv run python tests/run_foreman_simple.py     # Start foreman
uv run python tests/run_worker_simple.py      # Start test worker
uv run python tests/example_client.py         # Submit test job
```

### Database Management
```bash
# View database contents
uv run python tests/view_database.py

# Clear database
uv run python tests/quick_clear_db.py
```

### Debugging
- FastAPI documentation: `http://localhost:8000/docs`
- WebSocket logs: Check console output
- Database logs: Check database file in root directory
