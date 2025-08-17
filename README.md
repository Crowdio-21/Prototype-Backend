# CrowdCompute

A distributed computing system that allows you to run Python functions across multiple devices using a simple, intuitive API.

## 🚀 Overview

CrowdCompute is a Python-based distributed computing framework that enables you to:
- **Distribute Python functions** across multiple devices
- **Scale computations** by adding more worker devices
- **Execute tasks** on Android phones, laptops, or any Python-capable device
- **Monitor progress** through real-time dashboards
- **Handle failures** gracefully with automatic retry mechanisms

## 🏗️ Architecture

```
┌─────────────┐    WebSocket    ┌─────────────┐    WebSocket    ┌─────────────┐
│   Client    │ ──────────────► │   Foreman   │ ──────────────► │   Worker    │
│   (SDK)     │                 │  (Server)   │                 │  (Device)   │
└─────────────┘                 └─────────────┘                 └─────────────┘
       │                              │                              │
       │                              │                              │
       ▼                              ▼                              ▼
┌─────────────┐                 ┌─────────────┐                 ┌─────────────┐
│ User Code   │                 │ SQLite DB   │                 │ Task Exec   │
└─────────────┘                 └─────────────┘                 └─────────────┘
```

### Components

- **Client SDK** - Simple API for submitting distributed jobs
- **Foreman Server** - Central task manager and job scheduler
- **Worker Nodes** - Devices that execute the actual computations
- **Database** - Persistent storage for jobs, tasks, and worker status

## 📦 Packages

### [`common/`](common/README.md)
Shared modules for communication protocol and serialization utilities.

### [`client/`](client/README.md)
Python SDK for submitting distributed computing jobs.

### [`foreman/`](foreman/README.md)
FastAPI-based central server for job management and task distribution.

### [`worker/`](worker/README.md)
FastAPI-based worker nodes for executing distributed tasks.

### [`tests/`](tests/README.md)
Utility scripts for testing and running the system.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Foreman

```bash
cd tests
python run_foreman_simple.py
```

The foreman will start on:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:9000

### 3. Start a Worker

In another terminal:

```bash
cd tests
python run_worker_simple.py
```

The worker will start on:
- **Worker Dashboard**: http://localhost:8001
- **Worker API**: http://localhost:8001/docs

### 4. Run Example Client

In a third terminal:

```bash
cd tests
python example_client.py localhost
```

## 💻 Usage Examples

### Basic Distributed Map

```python
import asyncio
from client import connect, map, disconnect

async def main():
    # Connect to foreman
    await connect("localhost", 9000)
    
    # Define function to distribute
    def square(x):
        return x ** 2
    
    # Map function over data
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    results = await map(square, numbers)
    print(f"Results: {results}")
    # Output: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
    
    await disconnect()

asyncio.run(main())
```

### Complex Data Processing

```python
import asyncio
from client import connect, map, disconnect

async def process_data():
    await connect("localhost", 9000)
    
    def analyze_dataset(data):
        import numpy as np
        return {
            'mean': np.mean(data),
            'std': np.std(data),
            'sum': np.sum(data)
        }
    
    # Process multiple datasets
    datasets = [
        [1, 2, 3, 4, 5],
        [10, 20, 30, 40, 50],
        [100, 200, 300, 400, 500]
    ]
    
    results = await map(analyze_dataset, datasets)
    print(f"Analysis results: {results}")
    
    await disconnect()

asyncio.run(process_data())
```

### Single Function Execution

```python
import asyncio
from client import connect, run, disconnect

async def single_task():
    await connect("localhost", 9000)
    
    def fibonacci(n):
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    result = await run(fibonacci, 30)
    print(f"Fibonacci(30) = {result}")
    
    await disconnect()

asyncio.run(single_task())
```

## 🔧 Configuration

### Foreman Configuration

The foreman can be configured through environment variables:

```bash
export FOREMAN_HOST=0.0.0.0
export FOREMAN_PORT=8000
export WEBSOCKET_PORT=9000
export DATABASE_URL=sqlite:///crowdcompute.db
```

### Worker Configuration

Workers can be configured with different settings:

```python
from worker_fastapi.worker import WorkerConfig

config = WorkerConfig(
    worker_id="worker-001",
    foreman_url="ws://192.168.1.100:9000",
    max_concurrent_tasks=2,
    auto_restart=True,
    heartbeat_interval=30
)
```

## 📊 Monitoring

### Foreman Dashboard

Visit http://localhost:8000 to see:
- Real-time system statistics
- Active jobs and their progress
- Connected workers and their status
- Task distribution visualization

### Worker Dashboard

Visit http://localhost:8001 to see:
- Worker status and health
- Task execution statistics
- Performance metrics
- Connection status

### API Endpoints

Both foreman and workers provide REST APIs:

```bash
# Foreman API
curl http://localhost:8000/api/stats
curl http://localhost:8000/api/jobs
curl http://localhost:8000/api/workers

# Worker API
curl http://localhost:8001/stats
curl http://localhost:8001/
```

## 🛠️ Development

### Project Structure

```
cc_MVP/
├── common/                    # Shared components
│   ├── protocol.py           # Communication protocol
│   ├── serializer.py         # Serialization utilities
│   └── README.md
├── client/                   # Client SDK
│   ├── client.py             # Main client implementation
│   ├── __init__.py           # SDK exports
│   └── README.md
├── foreman/          # Foreman server
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database models
│   ├── websocket_manager.py # WebSocket handling
│   └── README.md
├── worker/           # Worker implementation
│   ├── worker.py            # Worker logic
│   ├── dashboard.py         # Worker dashboard
│   └── README.md
├── tests/              # Testing utilities
│   ├── run_foreman_simple.py
│   ├── run_worker_simple.py
│   ├── example_client.py
│   └── README.md
├── requirements.txt          # Dependencies
└── README.md                # This file
```

### Running Tests

```bash
# Test imports
cd tests 

# Test the full system
python run_foreman_simple.py  # Terminal 1
python run_worker_simple.py   # Terminal 2
python example_client.py localhost  # Terminal 3
```

### Database Management

```bash
# View database contents
cd tests
python view_database.py

# Clear database
python quick_clear_db.py
```

## 🔒 Security Considerations

### Current Implementation
- **Local Network Only** - Designed for trusted local networks
- **No Authentication** - No user authentication implemented
- **Function Execution** - Executes arbitrary Python code

### Production Recommendations
- **Network Security** - Use VPN or secure network
- **Authentication** - Implement user authentication
- **Sandboxing** - Execute functions in restricted environments
- **Resource Limits** - Set CPU and memory limits
- **Monitoring** - Implement comprehensive logging

## 🚀 Deployment

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd cc_MVP

# Install dependencies
pip install -r requirements.txt

# Start the system
cd test_utils
python run_foreman_simple.py  # Terminal 1
python run_worker_simple.py   # Terminal 2
```

### Production Deployment

```bash
# Foreman (using gunicorn)
gunicorn foreman_fastapi.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Worker (using gunicorn)
gunicorn worker_fastapi.worker:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### Docker Deployment

```dockerfile
# Foreman Dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8000 9000
CMD ["python", "tests/run_foreman_simple.py"]
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation
- Use type hints
- Handle errors gracefully

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework for building APIs
- **WebSockets** - Real-time communication
- **SQLAlchemy** - Database ORM
- **Cloudpickle** - Function serialization
- **Uvicorn** - ASGI server

## 📞 Support

For questions, issues, or contributions:

1. **Check** the documentation in each package
2. **Search** existing issues
3. **Create** a new issue with detailed information
4. **Join** the community discussions

---

**CrowdCompute** - Distributed computing made simple! 🚀
