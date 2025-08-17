"""
FastAPI Foreman Server for CrowdCompute
"""

import asyncio
import websockets
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .database import (
    get_db, init_db, get_jobs, get_job, get_workers, get_job_stats,
    JobResponse, WorkerResponse, JobStats
)
from .websocket_manager import WebSocketManager

# Global WebSocket manager
ws_manager: WebSocketManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting CrowdCompute FastAPI Foreman...")
    await init_db()
    
    # Initialize WebSocket manager
    global ws_manager
    ws_manager = WebSocketManager()
    
    # Start WebSocket server in background task
    async def start_websocket_server():
        try:
            websocket_server = await websockets.serve(
                ws_manager.handle_connection,
                "0.0.0.0",
                9000
            )
            print("WebSocket server started on ws://localhost:9000")
            await websocket_server.wait_closed()
        except Exception as e:
            print(f"WebSocket server error: {e}")
    
    # Start WebSocket server as background task
    import asyncio
    websocket_task = asyncio.create_task(start_websocket_server())
    
    print("FastAPI Foreman started!")
    print("REST API: http://localhost:8000")
    print("WebSocket: ws://localhost:9000")
    
    yield
    
    # Shutdown
    print("Shutting down FastAPI Foreman...")
    websocket_task.cancel()
    try:
        await websocket_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="CrowdCompute Foreman",
    description="FastAPI-based foreman server for distributed computing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTML dashboard
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>CrowdCompute Foreman Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #333; }
        .stat-label { color: #666; margin-top: 5px; }
        .section { margin-bottom: 30px; }
        .section h2 { border-bottom: 2px solid #333; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .status-pending { color: #f39c12; }
        .status-running { color: #3498db; }
        .status-completed { color: #27ae60; }
        .status-failed { color: #e74c3c; }
        .status-online { color: #27ae60; }
        .status-offline { color: #e74c3c; }
        .status-busy { color: #f39c12; }
    </style>
</head>
<body>
    <div class="container">
        <h1>CrowdCompute Foreman Dashboard</h1>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-number" id="total-jobs">-</div>
                <div class="stat-label">Total Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="running-jobs">-</div>
                <div class="stat-label">Running Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="completed-jobs">-</div>
                <div class="stat-label">Completed Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="online-workers">-</div>
                <div class="stat-label">Online Workers</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Jobs</h2>
            <table id="jobs-table">
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Status</th>
                        <th>Tasks</th>
                        <th>Progress</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody id="jobs-body">
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Workers</h2>
            <table id="workers-table">
                <thead>
                    <tr>
                        <th>Worker ID</th>
                        <th>Status</th>
                        <th>Current Task</th>
                        <th>Tasks Completed</th>
                        <th>Last Seen</th>
                    </tr>
                </thead>
                <tbody id="workers-body">
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('total-jobs').textContent = stats.total_jobs;
                document.getElementById('running-jobs').textContent = stats.running_jobs;
                document.getElementById('completed-jobs').textContent = stats.completed_jobs;
                document.getElementById('online-workers').textContent = stats.online_workers || 0;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                const jobs = await response.json();
                
                const tbody = document.getElementById('jobs-body');
                tbody.innerHTML = '';
                
                jobs.forEach(job => {
                    const row = document.createElement('tr');
                    const progress = job.total_tasks > 0 ? Math.round((job.completed_tasks / job.total_tasks) * 100) : 0;
                    
                    row.innerHTML = `
                        <td>${job.id}</td>
                        <td><span class="status-${job.status}">${job.status}</span></td>
                        <td>${job.completed_tasks}/${job.total_tasks}</td>
                        <td>${progress}%</td>
                        <td>${new Date(job.created_at).toLocaleString()}</td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading jobs:', error);
            }
        }
        
        async function loadWorkers() {
            try {
                const response = await fetch('/api/workers');
                const workers = await response.json();
                
                const tbody = document.getElementById('workers-body');
                tbody.innerHTML = '';
                
                workers.forEach(worker => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${worker.id}</td>
                        <td><span class="status-${worker.status}">${worker.status}</span></td>
                        <td>${worker.current_task_id || '-'}</td>
                        <td>${worker.total_tasks_completed}</td>
                        <td>${new Date(worker.last_seen).toLocaleString()}</td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading workers:', error);
            }
        }
        
        // Load data on page load
        loadStats();
        loadJobs();
        loadWorkers();
        
        // Refresh data every 5 seconds
        setInterval(() => {
            loadStats();
            loadJobs();
            loadWorkers();
        }, 5000);
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard page"""
    return dashboard_html


# REST API endpoints
@app.get("/api/stats", response_model=JobStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get job statistics"""
    return await get_job_stats(db)


@app.get("/api/jobs", response_model=list[JobResponse])
async def list_jobs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """List all jobs"""
    jobs = await get_jobs(db, skip=skip, limit=limit)
    return [JobResponse.from_orm(job) for job in jobs]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job by ID"""
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_orm(job)


@app.get("/api/workers", response_model=list[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)):
    """List all workers"""
    workers = await get_workers(db)
    return [WorkerResponse.from_orm(worker) for worker in workers]


@app.get("/api/websocket-stats")
async def get_websocket_stats():
    """Get WebSocket manager statistics"""
    if ws_manager:
        return ws_manager.get_stats()
    return {"error": "WebSocket manager not available"}


# WebSocket endpoint for dashboard updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Send periodic updates
            if ws_manager:
                stats = ws_manager.get_stats()
                await websocket.send_text(f"data: {stats}")
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("Dashboard WebSocket disconnected")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
