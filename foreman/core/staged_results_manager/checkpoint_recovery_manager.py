"""
Checkpoint-aware task assignment and recovery

Integrates with task_dispatcher to enable resuming failed tasks from
the last checkpoint instead of restarting from scratch.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from foreman.db.models import TaskModel
from common.protocol import create_resume_task_message
from common.serializer import bytes_to_hex


class CheckpointRecoveryManager:
    """Manages task recovery from checkpoints"""
    
    def __init__(self, checkpoint_manager):
        """
        Initialize recovery manager
        
        Args:
            checkpoint_manager: CheckpointManager instance for checkpoint retrieval
        """
        self.checkpoint_manager = checkpoint_manager
    
    async def should_resume_from_checkpoint(
        self,
        session: AsyncSession,
        task_id: str
    ) -> bool:
        """
        Check if task should be resumed from checkpoint
        
        A task is resumed if:
        1. It has checkpoint data available
        2. It has not already completed
        3. The checkpoint is recent enough (not stale)
        
        Args:
            session: Database session
            task_id: Task identifier
            
        Returns:
            True if task should be resumed from checkpoint
        """
        try:
            task = await session.get(TaskModel, task_id)
            if not task:
                return False
            
            # Check if checkpoint exists
            if not task.base_checkpoint_data:
                return False
            
            # Check if task is still pending/assigned (not completed)
            if task.status in ["completed", "failed"]:
                return False
            
            # Check checkpoint age (should be recent, within last hour)
            if task.last_checkpoint_at:
                from datetime import datetime, timedelta
                age = datetime.now() - task.last_checkpoint_at
                if age > timedelta(hours=1):
                    print(f"CheckpointRecoveryManager: Checkpoint for {task_id} is stale "
                          f"({age.total_seconds()} seconds old)")
                    return False
            
            return True
        
        except Exception as e:
            print(f"CheckpointRecoveryManager: Error checking checkpoint: {e}")
            return False
    
    async def create_resume_message(
        self,
        session: AsyncSession,
        task_id: str,
        job_id: str,
        func_code: str
    ) -> Optional[dict]:
        """
        Create a RESUME_TASK message for a failed task with checkpoint
        
        Reconstructs state from base + deltas and prepares resumption message.
        
        Args:
            session: Database session
            task_id: Task identifier
            job_id: Job identifier
            func_code: Updated function code
            
        Returns:
            Dictionary with message data or None if cannot resume
        """
        try:
            # Reconstruct full state from base + deltas
            reconstructed_state = await self.checkpoint_manager.reconstruct_state(
                session, task_id
            )
            
            if not reconstructed_state:
                print(f"CheckpointRecoveryManager: Could not reconstruct state for {task_id}")
                return None
            
            # Get task info
            task = await session.get(TaskModel, task_id)
            if not task:
                return None
            
            # For now, assume all args have been processed in checkpoint
            # In advanced implementation, track which args were completed
            remaining_args = []
            
            # Prepare message data
            message_data = {
                "task_id": task_id,
                "job_id": job_id,
                "func_code": func_code,
                "reconstructed_state_hex": bytes_to_hex(reconstructed_state),
                "remaining_args": remaining_args,
                "checkpoint_count": task.checkpoint_count
            }
            
            print(f"CheckpointRecoveryManager: Created resume message for {task_id} "
                  f"(progress: {task.progress_percent}%, checkpoints: {task.checkpoint_count})")
            
            return message_data
        
        except Exception as e:
            print(f"CheckpointRecoveryManager: Error creating resume message: {e}")
            return None
    
    async def on_task_completion(
        self,
        session: AsyncSession,
        task_id: str
    ) -> bool:
        """
        Clean up checkpoints when task completes (Option A)
        
        Delete checkpoint data to free up space since task is done.
        
        Args:
            session: Database session
            task_id: Task identifier
            
        Returns:
            True if cleanup successful
        """
        return await self.checkpoint_manager.cleanup_checkpoint(session, task_id)
