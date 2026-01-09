#!/usr/bin/env python3
"""
Simple script to run the FastAPI foreman
"""

import sys
import os
import uvicorn

# Add parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


if __name__ == "__main__":
    print("🚀 Starting CrowdCompute FastAPI Foreman...")
    print("=" * 60)
    print("📊 Dashboard:     http://localhost:8000")
    print("📚 API Docs:      http://localhost:8000/docs")
    print("🔌 WebSocket:     ws://localhost:9000")
    print("🗄️  Database:      ./crowdcompute.db")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Use string import to avoid event loop issues
        uvicorn.run(
            "foreman.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Try running: python simple_test.py first")
