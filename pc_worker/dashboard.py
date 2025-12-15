"""
Web Dashboard for FastAPI Worker
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def create_dashboard_html(worker_id: str) -> str:
    """Create HTML dashboard for worker"""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>CrowdCompute Worker - {worker_id}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-online {{
            background-color: #28a745;
        }}
        .status-offline {{
            background-color: #dc3545;
        }}
        .status-busy {{
            background-color: #ffc107;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            color: #333;
        }}
        .task-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }}
        .no-task {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #6c757d;
            text-align: center;
            color: #666;
        }}
        .controls {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }}
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }}
        .btn-primary {{
            background-color: #007bff;
            color: white;
        }}
        .btn-danger {{
            background-color: #dc3545;
            color: white;
        }}
        .btn:hover {{
            opacity: 0.8;
        }}
        .log {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 CrowdCompute Worker</h1>
            <p>Worker ID: <strong>{worker_id}</strong></p>
        </div>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <div class="stat-number" id="connection-status">
                    <span class="status-indicator status-offline"></span>
                    Offline
                </div>
                <div class="stat-label">Connection Status</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="tasks-completed">0</div>
                <div class="stat-label">Tasks Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="tasks-failed">0</div>
                <div class="stat-label">Tasks Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="uptime">0s</div>
                <div class="stat-label">Uptime</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Current Task</h2>
            <div id="current-task" class="no-task">
                No task currently assigned
            </div>
        </div>
        
        <div class="section">
            <h2>🎛️ Controls</h2>
            <div class="controls">
                <button class="btn btn-primary" onclick="restartWorker()">🔄 Restart Worker</button>
                <button class="btn btn-danger" onclick="disconnectWorker()">🔌 Disconnect</button>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Performance</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="avg-execution-time">0.00s</div>
                    <div class="stat-label">Avg Execution Time</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-execution-time">0.00s</div>
                    <div class="stat-label">Total Execution Time</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📝 Recent Activity</h2>
            <div class="log" id="activity-log">
                Worker starting up...
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {{
            try {{
                ws = new WebSocket('ws://localhost:8001/ws');
                
                ws.onopen = function() {{
                    console.log('WebSocket connected');
                    addLog('WebSocket connected for real-time updates');
                }};
                
                ws.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                }};
                
                ws.onclose = function() {{
                    console.log('WebSocket disconnected');
                    addLog('WebSocket disconnected');
                    // Reconnect after 5 seconds
                    setTimeout(connectWebSocket, 5000);
                }};
                
                ws.onerror = function(error) {{
                    console.error('WebSocket error:', error);
                    addLog('WebSocket error: ' + error);
                }};
                
            }} catch (error) {{
                console.error('Failed to connect WebSocket:', error);
                addLog('Failed to connect WebSocket: ' + error);
            }}
        }}
        
        function updateDashboard(data) {{
            // Update connection status
            const statusElement = document.getElementById('connection-status');
            const statusIndicator = statusElement.querySelector('.status-indicator');
            
            if (data.is_connected) {{
                statusElement.innerHTML = '<span class="status-indicator status-online"></span>Online';
            }} else {{
                statusElement.innerHTML = '<span class="status-indicator status-offline"></span>Offline';
            }}
            
            // Update stats
            document.getElementById('tasks-completed').textContent = data.stats.tasks_completed;
            document.getElementById('tasks-failed').textContent = data.stats.tasks_failed;
            
            // Update uptime
            const uptime = Math.floor(data.uptime || 0);
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            const seconds = uptime % 60;
            document.getElementById('uptime').textContent = 
                hours + 'h ' + minutes + 'm ' + seconds + 's';
            
            // Update current task
            const taskElement = document.getElementById('current-task');
            if (data.current_task) {{
                taskElement.className = 'task-info';
                taskElement.innerHTML = `
                    <strong>Task ID:</strong> ${{data.current_task.task_id}}<br>
                    <strong>Status:</strong> Executing...<br>
                    <strong>Received:</strong> ${{new Date().toLocaleTimeString()}}
                `;
            }} else {{
                taskElement.className = 'no-task';
                taskElement.textContent = 'No task currently assigned';
            }}
            
            // Update performance stats
            const totalTasks = data.stats.tasks_completed + data.stats.tasks_failed;
            if (totalTasks > 0) {{
                const avgTime = data.stats.total_execution_time / totalTasks;
                document.getElementById('avg-execution-time').textContent = 
                    avgTime.toFixed(2) + 's';
            }}
            document.getElementById('total-execution-time').textContent = 
                data.stats.total_execution_time.toFixed(2) + 's';
        }}
        
        function addLog(message) {{
            const logElement = document.getElementById('activity-log');
            const timestamp = new Date().toLocaleTimeString();
            logElement.innerHTML += `[${{timestamp}}] ${{message}}\\n`;
            logElement.scrollTop = logElement.scrollHeight;
        }}
        
        async function restartWorker() {{
            try {{
                const response = await fetch('/restart', {{ method: 'POST' }});
                const result = await response.json();
                addLog('Worker restart: ' + result.message);
            }} catch (error) {{
                addLog('Failed to restart worker: ' + error);
            }}
        }}
        
        async function disconnectWorker() {{
            try {{
                if (ws) {{
                    ws.close();
                }}
                addLog('Worker disconnected manually');
            }} catch (error) {{
                addLog('Failed to disconnect worker: ' + error);
            }}
        }}
        
        // Load initial data
        async function loadInitialData() {{
            try {{
                const response = await fetch('/stats');
                const data = await response.json();
                updateDashboard(data);
                addLog('Initial data loaded');
            }} catch (error) {{
                addLog('Failed to load initial data: ' + error);
            }}
        }}
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {{
            loadInitialData();
            connectWebSocket();
            
            // Refresh data every 10 seconds as backup
            setInterval(loadInitialData, 10000);
        }});
    </script>
</body>
</html>
"""


def add_dashboard_route(app: FastAPI, worker_id: str):
    """Add dashboard route to FastAPI app"""
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Worker dashboard page"""
        return create_dashboard_html(worker_id)
