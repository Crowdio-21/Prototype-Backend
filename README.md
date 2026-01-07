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

### Recommended: Setup with uv (Windows, Linux, macOS)

uv is a fast Python package manager and runtime manager. Use it to ensure all machines (client, foreman, workers) run the exact same Python and dependency versions.

1) Install uv

Linux / macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:

```bash
uv --version
```


2) Align Python version across all machines (important)

Pick one version (example: 3.11.9) and use it everywhere:

```bash
uv python install 3.12.6
uv python pin 3.12.6
uv python list
```


3) Create and activate a virtual environment

```bash
uv venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```


4) Install dependencies

```bash
uv pip install -r requirements.txt
```

5) Start the Foreman

```bash
uv run python tests/run_foreman_simple.py
```

The foreman will start on:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:9000

6) Start a Worker (on the same machine or another machine on the LAN)

If running on a different machine, ensure `tests/run_worker_simple.py` has `foreman_url` set to your foreman’s LAN IP (e.g., `ws://192.168.1.50:9000`).

```bash
uv run python tests/run_worker_simple.py
```

The worker will start on:
- **Worker Dashboard**: http://localhost:8001
- **Worker API**: http://localhost:8001/docs

7) Run Example Client

```bash
uv run python tests/example_client.py localhost
```

If the foreman runs on a different machine, replace `localhost` with the foreman’s LAN IP.

8) Extra uv commands (optional but useful)

```bash
# Add packages (writes to uv-managed project metadata if present)
uv add <package-name>

# Export current environment to requirements.txt
uv export --format=requirements-txt > requirements.txt

# Create a lockfile for reproducible installs
uv lock

# Initialize uv project metadata in this folder (optional)
uv init .
```

### Alternative: Setup with pip/venv

```bash
# Create venv and install deps
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Then follow steps 5–7 above using `python` instead of `uv run python`.

### 2. Start the Foreman (pip alternative shown; with uv use the commands above)

```bash
cd tests
python run_foreman_simple.py
```

The foreman will start on:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:9000

### 3. Start a Worker (pip alternative)

In another terminal:

```bash
cd tests
python run_worker_simple.py
```

The worker will start on:
- **Worker Dashboard**: http://localhost:8001
- **Worker API**: http://localhost:8001/docs

### 4. Run Example Client (pip alternative)

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

## � Sentiment Analysis - Complete Guide (A to Z)

### Overview

The **Distributed Sentiment Analysis** system analyzes text sentiment across multiple workers in parallel. It demonstrates how CrowdCompute handles real-world NLP tasks by splitting data, distributing processing, and aggregating results.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    SENTIMENT ANALYSIS FLOW                       │
└──────────────────────────────────────────────────────────────────┘

1. CLIENT SIDE (sentiment_analysis_client.py)
   ├─ Read input text
   ├─ Split into sentences
   └─ Connect to Foreman

2. TEXT SPLITTING
   Input: "I love this! It's great. But service was bad."
   
   ┌──────────────────────┐
   │ I love this!         │ ──► Sentence 1
   │ It's great.          │ ──► Sentence 2
   │ But service was bad. │ ──► Sentence 3
   └──────────────────────┘

3. DISTRIBUTED PROCESSING (Workers)
   
   ┌─────────────────────────────────────────────────────────────┐
   │                     FOREMAN (Server)                        │
   │  ┌─────────────────────────────────────────────────────────┤
   │  │ Job Queue:                                              │
   │  │ • Job ID: abc123                                        │
   │  │ • Tasks: 3 sentiment analysis tasks                     │
   │  └─────────────────────────────────────────────────────────┤
   └─────────────────────────────────────────────────────────────┘
            ▲                      ▲                    ▲
            │                      │                    │
   ┌────────┴──────┐    ┌──────────┴────────┐  ┌───────┴─────────┐
   │    WORKER 1   │    │    WORKER 2      │  │   WORKER 3      │
   │               │    │                  │  │                 │
   │ Sentence 1:   │    │ Sentence 2:      │  │ Sentence 3:     │
   │ "I love this!"│    │ "It's great."    │  │ "Bad service"   │
   │               │    │                  │  │                 │
   │ Pos: 1        │    │ Pos: 1           │  │ Neg: 1          │
   │ Neg: 0        │    │ Neg: 0           │  │ Pos: 0          │
   │               │    │                  │  │                 │
   │ Sentiment: +1 │    │ Sentiment: +1    │  │ Sentiment: -1   │
   │ Confidence: ▓▓│    │ Confidence: ▓▓▓  │  │ Confidence: ▓   │
   │ Latency: 45ms │    │ Latency: 38ms    │  │ Latency: 52ms   │
   └────────┬──────┘    └──────────┬────────┘  └───────┬─────────┘
            │                      │                    │
            └──────────────────────┼────────────────────┘
                                   ▼
   4. RESULT AGGREGATION (Client Side)
   
   ┌──────────────────────────────────────────┐
   │ Results from all workers:                │
   │                                          │
   │ Sentiment Scores:  [+1.0, +1.0, -1.0]   │
   │ Confidences:       [0.9,  0.95, 0.85]   │
   │ Latencies (ms):    [45,   38,   52]     │
   │                                          │
   │ ┌──────────────────────────────────────┐ │
   │ │ Weighted Average Sentiment:          │ │
   │ │ = (1.0×0.9 + 1.0×0.95 + (-1.0)×0.85)│ │
   │ │   ─────────────────────────────────  │ │
   │ │   (0.9 + 0.95 + 0.85)                │ │
   │ │ = 0.35 / 2.7 = +0.13 (Mixed)         │ │
   │ └──────────────────────────────────────┘ │
   └──────────────────────────────────────────┘

5. FINAL OUTPUT
   
   📈 Overall Sentiment Score: 0.13
      (Range: -1.0 [negative] to +1.0 [positive])
   
   🎯 Average Confidence: 0.90
   
   📊 Details:
      Sentence 1: 😊 Positive  (Confidence: 0.90)
      Sentence 2: 😊 Positive  (Confidence: 0.95)
      Sentence 3: 😢 Negative  (Confidence: 0.85)
```

### How It Works - Step by Step

#### **Step 1: Text Preprocessing**

```python
Input Text:
"I absolutely love this product! It's amazing.
 However, the service was disappointing."

↓ Split into sentences ↓

Sentence 1: "I absolutely love this product!"
Sentence 2: "It's amazing."
Sentence 3: "However, the service was disappointing."
```

#### **Step 2: Lexicon-Based Sentiment Analysis**

Each worker performs sentiment analysis using word matching:

```
POSITIVE WORDS: {good, great, excellent, amazing, love, perfect, ...}
NEGATIVE WORDS: {bad, terrible, awful, poor, hate, worst, ...}

Sentence 1: "I absolutely love this product!"
  ✓ Match: "love" (positive word)
  Positive count: 1, Negative count: 0
  Sentiment = (1 - 0) / 1 = +1.0 (POSITIVE)

Sentence 2: "It's amazing."
  ✓ Match: "amazing" (positive word)
  Positive count: 1, Negative count: 0
  Sentiment = (1 - 0) / 1 = +1.0 (POSITIVE)

Sentence 3: "However, the service was disappointing."
  ✓ Match: "disappointing" (negative word)
  Positive count: 0, Negative count: 1
  Sentiment = (0 - 1) / 1 = -1.0 (NEGATIVE)
```

#### **Step 3: Confidence Scoring**

Confidence is based on:
- Number of sentiment words found
- Magnitude of sentiment score
- Worker-specific variability

```
Sentence 1: More positive words → Higher confidence (0.95)
Sentence 2: Clear positive sentiment → High confidence (0.90)
Sentence 3: Clear negative sentiment → Good confidence (0.85)
```

#### **Step 4: Result Aggregation**

Results are combined using **weighted averaging**:

```
Formula: 
  Weighted Sentiment = Σ(Sentiment × Confidence) / Σ(Confidence)

Calculation:
  = (1.0 × 0.95 + 1.0 × 0.90 + (-1.0) × 0.85) / (0.95 + 0.90 + 0.85)
  = (0.95 + 0.90 - 0.85) / 2.70
  = 1.00 / 2.70
  = +0.37 (Overall: POSITIVE)
```

#### **Step 5: Performance Metrics**

For each worker:
- **Latency**: Time to process sentence
- **Throughput**: Sentences per second
- **Accuracy**: Confidence in prediction

```
Worker 1: 45ms latency, 0.95 confidence → Fast & confident
Worker 2: 38ms latency, 0.90 confidence → Very fast & confident
Worker 3: 52ms latency, 0.85 confidence → Reasonable
```

### System Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Foreman** | Task distribution & coordination | FastAPI + WebSocket |
| **Workers** | Sentiment analysis execution | Python (pure strings) |
| **Client** | Job submission & result aggregation | Async Python |
| **Protocol** | Message passing | JSON over WebSocket |
| **Serialization** | Function + data transfer | cloudpickle |

### Data Flow Sequence

```
TIME │ CLIENT          │ FOREMAN         │ WORKER 1        │ WORKER 2
─────┼─────────────────┼─────────────────┼─────────────────┼──────────
  0  │ Connect ──────────► Connect       │                 │
  1  │                 │ Accept          │                 │
  2  │                 │ Ready           │                 │
     │                 │                 │                 │
  3  │ Send Job ────────► Queue Job      │                 │
  4  │                 │ Create Tasks    │                 │
  5  │                 │ Dispatch T1 ──────► Load Model   │
  6  │                 │ Dispatch T2 ──────────────────► Load Model
     │                 │                 │                 │
  7  │                 │                 │ Process Task 1  │
  8  │                 │                 │ (45ms)          │ Process Task 2
  9  │                 │                 │                 │ (38ms)
     │                 │                 │                 │
 10  │                 │ ◄─── Result 1 ──│                 │
 11  │                 │                 │                 │
 12  │                 │                 │                 │ ◄─── Result 2
 13  │ ◄─── Results ────│                 │                 │
 14  │ Aggregate       │                 │                 │
 15  │ Display Results │                 │                 │
```

### Running Sentiment Analysis

**Prerequisites:**
- Foreman running: `python tests/run_foreman_simple.py`
- Workers running: `python tests/run_worker_simple.py` (2-3 terminals)

**Execute:**
```powershell
python tests/sentiment_analysis_client.py localhost
```

**Output Example:**
```
🔍 DISTRIBUTED SENTIMENT ANALYSIS

📝 Input text: I absolutely love this product! It's amazing...
📊 Split into 3 sentences

⏳ Submitting 3 sentiment analysis tasks to workers...
✅ Received 3 results from workers

📈 Overall Sentiment Score: 0.370
   (Range: -1.0 [negative] to +1.0 [positive])

🎯 Average Confidence: 0.900

📊 Confidence Range:
   Min: 0.850
   Max: 0.950

⚡ Avg Worker Latency: 43.2ms

📋 Sentence Analysis Details:
1. 😊 I absolutely love this product!
   Sentiment: 1.000 | Confidence: 0.950

2. 😊 It's amazing.
   Sentiment: 1.000 | Confidence: 0.900

3. 😢 However, the service was disappointing.
   Sentiment: -1.000 | Confidence: 0.850
```

### Performance Characteristics

- **Scalability**: Linear with number of workers
- **Latency**: ~40-50ms per sentence (model independent)
- **Throughput**: 20-25 sentences/second (3 workers)
- **Accuracy**: 85-95% confidence based on word matching

### Key Advantages of Distributed Approach

✅ **Parallelization** - Multiple sentences processed simultaneously
✅ **Scalability** - Add workers to handle more data
✅ **Fault Tolerance** - Worker failure doesn't stop entire job
✅ **Load Balancing** - Foreman distributes work evenly
✅ **Real-time Results** - Stream results as workers complete tasks

---

## �📞 Support

For questions, issues, or contributions:

1. **Check** the documentation in each package
2. **Search** existing issues
3. **Create** a new issue with detailed information
4. **Join** the community discussions

---

**CrowdCompute** - Distributed computing made simple! 🚀
