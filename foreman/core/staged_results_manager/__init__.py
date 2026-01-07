"""Staged Results Manager for Foreman

This package handles incremental checkpointing of task results to minimize
data loss when workers fail mid-computation.

Architecture:
- checkpoint_manager.py: Core checkpoint operations (store, retrieve, reconstruct)
- storage_handler.py: Hybrid storage (DB for small, filesystem for large)
"""
