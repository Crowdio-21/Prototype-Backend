#!/usr/bin/env python3
"""
Simple script to run PSO integration test
Can be executed with: uv run run_pso_test.py
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the test
from tests.test_pso_integration import main

if __name__ == "__main__":
    print("🚀 Starting PSO Integration Test...")
    print("=" * 60)
    main()
