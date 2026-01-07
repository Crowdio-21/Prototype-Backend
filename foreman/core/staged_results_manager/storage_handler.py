"""
Hybrid checkpoint storage handler

Strategy: Store checkpoints in DB if <1MB, filesystem if >=1MB
This minimizes DB bloat while keeping small checkpoints fast to access.
"""

import os
import json
import gzip
from pathlib import Path
from typing import Optional


class StorageHandler:
    """Manages hybrid storage for checkpoints"""
    
    # Size threshold: 1 MB
    DB_SIZE_LIMIT = 1024 * 1024
    
    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        """
        Initialize storage handler
        
        Args:
            checkpoint_dir: Root directory for checkpoint storage
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    async def store_checkpoint(
        self,
        task_id: str,
        checkpoint_data: bytes,
        is_base: bool = False,
        checkpoint_id: int = 0
    ) -> str:
        """
        Store checkpoint with hybrid strategy
        
        Args:
            task_id: Task identifier
            checkpoint_data: Raw checkpoint bytes
            is_base: True for base checkpoint
            checkpoint_id: Checkpoint sequential number
            
        Returns:
            Storage reference (location identifier)
        """
        # Compress for storage efficiency
        compressed_data = gzip.compress(checkpoint_data, compresslevel=6)
        
        if len(compressed_data) < self.DB_SIZE_LIMIT:
            # Small checkpoint - return DB reference
            return f"db_{checkpoint_id}"
        else:
            # Large checkpoint - store in filesystem
            checkpoint_subdir = self.checkpoint_dir / task_id
            checkpoint_subdir.mkdir(parents=True, exist_ok=True)
            
            checkpoint_type = "base" if is_base else f"delta_{checkpoint_id}"
            checkpoint_file = checkpoint_subdir / f"{checkpoint_type}.gz"
            
            try:
                with open(checkpoint_file, 'wb') as f:
                    f.write(compressed_data)
                
                relative_path = f"{task_id}/{checkpoint_type}.gz"
                return f"fs_{relative_path}"
            except Exception as e:
                print(f"StorageHandler: Error writing checkpoint file: {e}")
                raise
    
    async def retrieve_checkpoint(
        self,
        task_id: str,
        is_base: bool = False,
        checkpoint_id: int = 0
    ) -> Optional[bytes]:
        """
        Retrieve checkpoint and decompress
        
        Args:
            task_id: Task identifier
            is_base: True for base checkpoint
            checkpoint_id: Checkpoint sequential number
            
        Returns:
            Decompressed checkpoint bytes or None if not found
        """
        checkpoint_subdir = self.checkpoint_dir / task_id
        checkpoint_type = "base" if is_base else f"delta_{checkpoint_id}"
        checkpoint_file = checkpoint_subdir / f"{checkpoint_type}.gz"
        
        try:
            if checkpoint_file.exists():
                with open(checkpoint_file, 'rb') as f:
                    compressed_data = f.read()
                
                # Decompress
                decompressed = gzip.decompress(compressed_data)
                return decompressed
            else:
                print(f"StorageHandler: Checkpoint file not found: {checkpoint_file}")
                return None
        except Exception as e:
            print(f"StorageHandler: Error reading checkpoint file: {e}")
            return None
    
    async def delete_checkpoints(self, task_id: str) -> bool:
        """
        Delete all checkpoints for a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if deleted successfully
        """
        checkpoint_subdir = self.checkpoint_dir / task_id
        
        try:
            if checkpoint_subdir.exists():
                import shutil
                shutil.rmtree(checkpoint_subdir)
                print(f"StorageHandler: Deleted checkpoint directory for {task_id}")
            return True
        except Exception as e:
            print(f"StorageHandler: Error deleting checkpoints for {task_id}: {e}")
            return False
    
    def get_checkpoint_info(self, task_id: str) -> dict:
        """
        Get information about stored checkpoints
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with checkpoint info
        """
        checkpoint_subdir = self.checkpoint_dir / task_id
        
        info = {
            "task_id": task_id,
            "exists": checkpoint_subdir.exists(),
            "base_checkpoint": None,
            "delta_count": 0,
            "total_size_bytes": 0
        }
        
        if checkpoint_subdir.exists():
            for checkpoint_file in checkpoint_subdir.glob("*.gz"):
                size = checkpoint_file.stat().st_size
                info["total_size_bytes"] += size
                
                if checkpoint_file.name == "base.gz":
                    info["base_checkpoint"] = size
                else:
                    info["delta_count"] += 1
        
        return info
