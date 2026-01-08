#!/usr/bin/env python3
"""
Launch multiple workers simultaneously
Usage: python tests/run_multiple_workers.py 8
"""

import sys
import os
import asyncio
import uuid
import argparse

# Add parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pc_worker import FastAPIWorker, WorkerConfig


async def run_worker(worker_id, port):
    """Run a single worker"""
    config = WorkerConfig(
        worker_id=worker_id,
        foreman_url="ws://localhost:9000",
        max_concurrent_tasks=1,
        auto_restart=True,
        heartbeat_interval=30,
    )
    
    worker = FastAPIWorker(config)
    
    print(f"🚀 Starting Worker: {worker_id} on port {port}")
    
    try:
        await worker.start()
    except Exception as e:
        print(f"❌ Worker {worker_id} error: {e}")


async def main():
    """Launch multiple workers simultaneously"""
    parser = argparse.ArgumentParser(description="Run multiple FastAPI Workers")
    parser.add_argument(
        "num_workers",
        type=int,
        nargs="?",
        default=8,
        help="Number of workers to launch (default: 8)",
    )
    parser.add_argument(
        "--start-port",
        type=int,
        default=8001,
        help="Starting port number (default: 8001)",
    )
    
    args = parser.parse_args()
    num_workers = args.num_workers
    start_port = args.start_port
    
    print("=" * 70)
    print(f"🚀 LAUNCHING {num_workers} WORKERS SIMULTANEOUSLY")
    print("=" * 70)
    
    # Create worker tasks
    tasks = []
    for i in range(num_workers):
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        port = start_port + i
        task = asyncio.create_task(run_worker(worker_id, port))
        tasks.append(task)
    
    print(f"\n✅ All {num_workers} workers initialized")
    print("Press Ctrl+C to stop all workers\n")
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n🛑 Stopping all workers...")


if __name__ == "__main__":
    asyncio.run(main())
