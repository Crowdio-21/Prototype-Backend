"""Staged Results Manager for PC Worker

This package handles incremental checkpointing of task computation state
to enable recovery when workers fail mid-execution.

Architecture:
- checkpoint_handler.py: Worker-side checkpoint coordination
- delta_computer.py: Framework-aware state diff computation (PyTorch, NumPy, generic)
"""
