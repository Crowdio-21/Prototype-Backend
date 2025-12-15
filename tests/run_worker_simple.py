#!/usr/bin/env python3
"""
Simple script to run the FastAPI Worker without event loop conflicts
"""

import sys
import os
import asyncio
import uuid
import threading
import time

# Add parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pc_worker.worker import FastAPIWorker, WorkerConfig


def run_worker_background(worker):
    """Run worker in background thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        print("Worker stopped")
    finally:
        loop.close()


def main():
    """Main function to run the FastAPI worker"""
    
    # Generate unique worker ID
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    
    # Create worker configuration
    config = WorkerConfig(
        worker_id=worker_id,
        foreman_url="ws://localhost:9000",
        max_concurrent_tasks=1,
        auto_restart=True,
        heartbeat_interval=30
    )
    
    # Create worker
    worker = FastAPIWorker(config)
    
    print(f"🚀 Starting FastAPI Worker Server: {worker_id}")
    print("=" * 60)
    print(f"👤 Worker ID:     {worker_id}")
    print(f"🔌 Foreman URL:   {config.foreman_url}")
    print(f"🌐 Web Interface: http://localhost:8001")
    print(f"📊 API Docs:      http://localhost:8001/docs")
    print("=" * 60)
    
    # Start worker in background thread
    worker_thread = threading.Thread(
        target=run_worker_background,
        args=(worker,),
        daemon=True
    )
    worker_thread.start()
    
    # Give worker time to start
    time.sleep(2)
    
    # Run FastAPI server in main thread
    import uvicorn
    try:
        uvicorn.run(
            worker.app,
            host="0.0.0.0",
            port=8002,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")


if __name__ == "__main__":
    main()
