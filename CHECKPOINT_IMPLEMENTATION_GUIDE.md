"""
INCREMENTAL CHECKPOINTING IMPLEMENTATION GUIDE

This document covers the complete implementation of incremental checkpointing
for CrowdCompute with the following specifications:

- Strategy: Option B (Hybrid DB/Filesystem: <1MB in DB, >=1MB on disk)
- Delta Computation: Option B (Framework-aware: PyTorch, TensorFlow, NumPy)
- Garbage Collection: Option A (Delete on task completion)

============================
ARCHITECTURE OVERVIEW
============================

The checkpointing system has three main components:

1. FOREMAN SIDE (server-side checkpoint management)
   Location: foreman/core/staged_results_manager/

   - checkpoint_manager.py: Store, retrieve, reconstruct, cleanup checkpoints
   - storage_handler.py: Hybrid storage (SQLite + filesystem)
   - checkpoint_recovery_manager.py: Enable task resumption from checkpoints
   - checkpoint_routes.py: REST API for monitoring

2. WORKER SIDE (client-side checkpoint creation)
   Location: pc_worker/staged_results_manager/

   - checkpoint_handler.py: Background checkpoint monitoring & transmission
   - delta_computer.py: Framework-aware delta computation

3. PROTOCOL (Communication)
   Location: common/protocol.py
   New message types:

   - TASK_CHECKPOINT (worker → foreman): Send checkpoint data
   - CHECKPOINT_ACK (foreman → worker): Acknowledge receipt
   - RESUME_TASK (foreman → worker): Resume from checkpoint

4. DATABASE (Persistence)
   Location: foreman/db/models.py
   New fields in TaskModel:
   - base_checkpoint_data: Reference to base checkpoint
   - delta_checkpoints: JSON array of delta metadata
   - checkpoint_count: Number of checkpoints taken
   - progress_percent: Task progress (0-100)
   - last_checkpoint_at: Timestamp of last checkpoint
   - checkpoint_storage_path: Filesystem path if stored externally

============================
INTEGRATION GUIDE
============================

## STEP 1: Enable Checkpointing in Job Submission

When submitting a job from developer_sdk, pass checkpoint_interval:

    from developer_sdk import connect, map

    await connect("localhost", 9000)

    # Enable checkpointing with 10-second intervals
    results = await map(
        my_function,
        data,
        checkpoint_interval=10.0  # seconds
    )

This flag propagates through SUBMIT_JOB message to foreman.

## STEP 2: Worker-Side Checkpoint Initiation

Modify pc_worker/worker.py to initialize checkpoint handler:

    from pc_worker.staged_results_manager.checkpoint_handler import CheckpointHandler

    class FastAPIWorker:
        def __init__(self, config):
            # ... existing code ...
            self.checkpoint_handler = CheckpointHandler(
                checkpoint_interval=config.checkpoint_interval or 10.0
            )

        async def _execute_task(self, func_code, task_args, job_id, task_id):
            # ... deserialize function ...

            # Define state getter (captures function state during execution)
            def get_task_state():
                return {
                    "progress_percent": self.execution_context.get("progress", 0),
                    "intermediate_results": self.execution_context.get("results", {}),
                    "iterations_completed": self.execution_context.get("iterations", 0)
                }

            # Define checkpoint sender
            async def send_checkpoint(checkpoint_msg):
                message = create_task_checkpoint_message(
                    task_id=task_id,
                    job_id=job_id,
                    **checkpoint_msg
                )
                await self.websocket.send(message.to_json())

            # Start background checkpoint monitoring
            await self.checkpoint_handler.start_checkpoint_monitoring(
                task_id, get_task_state, send_checkpoint
            )

            try:
                # Execute function with checkpoint callback
                result = func(task_args)
            finally:
                # Stop checkpoint monitoring
                await self.checkpoint_handler.stop_checkpoint_monitoring()

            return result

## STEP 3: Foreman Checkpoint Reception & Storage

Already implemented in foreman/core/message_handlers.py
The \_handle_task_checkpoint() method:

1. Receives TASK_CHECKPOINT message from worker
2. Decompresses checkpoint data (gzip)
3. Routes to CheckpointManager for storage
4. Stores in hybrid location (DB if <1MB, filesystem if >=1MB)
5. Sends CHECKPOINT_ACK back to worker

No additional integration needed here.

## STEP 4: Task Recovery on Worker Failure

When a task fails and needs retry, modify foreman/core/task_dispatcher.py:

    from foreman.core.staged_results_manager.checkpoint_recovery_manager \
        import CheckpointRecoveryManager

    class TaskDispatcher:
        def __init__(self, connection_manager, checkpoint_recovery_manager=None):
            # ... existing code ...
            self.checkpoint_recovery_manager = checkpoint_recovery_manager

        async def assign_task_to_available_worker(self, worker_id):
            # Get next pending task
            task = await self._get_next_pending_task()

            if not task:
                return False

            # Check if task should be resumed from checkpoint
            if self.checkpoint_recovery_manager:
                should_resume = await self.checkpoint_recovery_manager\
                    .should_resume_from_checkpoint(self.session, task.id)

                if should_resume:
                    # Task has checkpoint data - resume instead of restart
                    resume_msg_data = await self.checkpoint_recovery_manager\
                        .create_resume_message(
                            self.session,
                            task.id,
                            task.job_id,
                            task.func_code
                        )

                    if resume_msg_data:
                        # Send RESUME_TASK message instead of ASSIGN_TASK
                        message = create_resume_task_message(**resume_msg_data)
                        await self.connection_manager.send_to_worker(worker_id, message)

                        task.status = "assigned"
                        await self.session.commit()
                        return True

            # Fallback: normal task assignment (restart from beginning)
            # ... existing ASSIGN_TASK code ...

## STEP 5: Checkpoint Cleanup on Task Completion

When task completes, cleanup checkpoints to free space (Option A):

In foreman/core/completion_handler.py, modify handle_job_completion():

    async def handle_job_completion(self, job_id):
        # ... existing completion code ...

        # Clean up checkpoints for all completed tasks
        for task in job.tasks:
            if task.status == "completed":
                await self.checkpoint_recovery_manager.on_task_completion(
                    session, task.id
                )

============================
USAGE EXAMPLES
============================

## EXAMPLE 1: Simple Stateless Function (No Checkpointing Needed)

    def process(x):
        return x ** 2

    results = await map(process, [1, 2, 3, 4, 5])
    # No checkpoint_interval → no checkpointing

## EXAMPLE 2: Long-Running ML Training (Checkpointing Enabled)

    def train_model(data):
        model = initialize_model()
        state = {"epoch": 0, "loss": [], "weights": model.state_dict()}

        def progress_callback(epoch):
            state["epoch"] = epoch
            state["progress_percent"] = (epoch / NUM_EPOCHS) * 100

        for epoch in range(NUM_EPOCHS):
            loss = train_epoch(model, data, epoch)
            state["loss"].append(loss)
            state["weights"] = model.state_dict()
            progress_callback(epoch)

        return state

    # Enable checkpointing every 5 seconds
    results = await map(
        train_model,
        training_data,
        checkpoint_interval=5.0
    )

    # If worker fails mid-training, recovers from last checkpoint

## EXAMPLE 3: Monitoring Checkpoint Progress

    # Monitor progress via REST API
    curl http://localhost:8000/api/checkpoints/jobs/{job_id}

    Response:
    {
        "job_id": "job_123",
        "job_status": "running",
        "total_tasks": 10,
        "tasks_with_checkpoints": 8,
        "average_progress_percent": 65.5,
        "total_checkpoints_taken": 452,
        "tasks": [
            {
                "task_id": "task_1",
                "progress_percent": 75.0,
                "checkpoint_count": 45,
                "last_checkpoint_at": "2026-01-07T10:30:45",
                "base_checkpoint_size": 524288
            },
            ...
        ]
    }

============================
EDGE CASES HANDLED
============================

1. CHECKPOINT SERIALIZATION FAILURE

   - If state cannot be serialized (e.g., unpicklable objects)
   - CheckpointHandler logs error and skips that checkpoint
   - Task continues executing normally
   - Previous checkpoints remain valid for recovery

2. LARGE CHECKPOINTS (>1MB)

   - Stored on filesystem instead of database
   - Compressed with gzip (6-level compression)
   - Reference stored in database
   - Automatic cleanup on task completion

3. STALE CHECKPOINTS

   - If checkpoint is >1 hour old when task fails
   - Recovery manager refuses to use it
   - Task restarts from beginning instead
   - Prevents using outdated state

4. MISSING DELTA FILES

   - During reconstruction, if a delta file is missing
   - Reconstruction continues with remaining deltas
   - Logs warning but doesn't fail the recovery
   - Uses best-effort state recovery

5. FRAMEWORK DETECTION FAILURE

   - DeltaComputer tries PyTorch → TensorFlow → NumPy
   - Falls back to generic dict-based delta computation
   - Works for any picklable state, just less efficient

6. DELTA COMPACTION

   - After 50+ deltas, automatically merges into new base
   - Improves recovery performance (fewer merges needed)
   - Transparent to user - no API changes

7. WORKER DISCONNECT DURING CHECKPOINT SEND

   - Checkpoint message in flight when worker disconnects
   - Task will retry from last successfully acknowledged checkpoint
   - No data loss - only lost the in-flight checkpoint

8. TASK REASSIGNMENT TO DIFFERENT WORKER

   - Reconstructed state sent via RESUME_TASK message
   - Worker deserializes state and continues
   - Works even if worker is different machine/process

9. CONCURRENT CHECKPOINT CALLS

   - CheckpointHandler serializes checkpoint operations
   - Only one checkpoint being sent at a time
   - Prevents race conditions during state capture

10. OUT-OF-MEMORY CHECKPOINTS
    - Very large states (>available RAM)
    - Checkpoint operations may fail
    - Error logged, task continues without checkpoint
    - Not ideal but graceful degradation

============================
CONFIGURATION & TUNING
============================

CHECKPOINT_INTERVAL (default: 10 seconds)

- How often to locally capture state
- Lower = more frequent checkpoints, less recomputation on failure
- Higher = fewer checkpoints, lower overhead
- Recommendation: 5-30 seconds depending on task length

DB_SIZE_LIMIT (default: 1MB)

- Threshold for storing in database vs filesystem
- Smaller checkpoints (<1MB) go to database (faster access)
- Larger checkpoints go to filesystem (saves DB space)
- Tunable in storage_handler.py

CHECKPOINT_RETENTION (default: Delete on completion)

- Currently Option A (immediate cleanup)
- Could change to Option B/C for longer retention
- Modify checkpoint_manager.cleanup_checkpoint() retention logic

MAX_DELTAS_PER_BASE (default: 50)

- After N deltas, automatically compact into new base
- Reduces reconstruction time (fewer merges)
- Reduces filesystem clutter
- Tunable in checkpoint_manager.py

============================
MONITORING & DEBUGGING
============================

View checkpoint progress:
curl http://localhost:8000/api/checkpoints/jobs/{job_id}

View task checkpoint details:
curl http://localhost:8000/api/checkpoints/tasks/{task_id}

Get storage info:
curl http://localhost:8000/api/checkpoints/storage-info/{task_id}

Force cleanup (admin only):
curl -X POST http://localhost:8000/api/checkpoints/tasks/{task_id}/force-checkpoint

Logs:
CheckpointManager logs in foreman console
CheckpointHandler logs in worker console
Watch for "CheckpointManager:" and "CheckpointHandler:" prefixes

============================
PERFORMANCE NOTES
============================

Overhead per checkpoint:

- Serialization: ~0.1-1ms per MB (pickle)
- Compression: ~1-10ms per MB (gzip level 6)
- Transmission: Variable (network dependent)
- Storage: Async, non-blocking

Total impact:

- For 100ms checkpoint + 10s interval = 1% overhead
- For 10ms checkpoint + 30s interval = 0.03% overhead

Recommendations:

- Start with 10-30s checkpoint_interval
- Monitor actual overhead with APM tools
- Adjust interval based on task characteristics
- Very short tasks (<1s): disable checkpointing
- Very long tasks (>1h): use shorter intervals (5s)

============================
FUTURE ENHANCEMENTS
============================

1. Selective state checkpointing

   - Only checkpoint changed fields
   - Skip temporary/recomputable values

2. Async checkpoint uploads

   - Don't wait for CHECKPOINT_ACK
   - Pipeline multiple checkpoints

3. Checkpoint versioning

   - Keep multiple checkpoint versions
   - Allow rollback to earlier states

4. Cross-worker checkpoint sharing

   - Share checkpoints between workers
   - Enables load balancing mid-task

5. Compression tuning

   - Detect compression efficiency
   - Switch between gzip, zstd, brotli

6. Checkpoint lifecycle policies

   - Retention by age, size, or task status
   - Automatic archive/cleanup

7. Checkpoint validation
   - Integrity checks (hashing)
   - Corruption detection

============================
TROUBLESHOOTING
============================

Issue: Checkpoints not being stored

- Check worker checkpoint_interval is set
- Verify foreman has write permissions for checkpoint_dir
- Check logs for serialization errors

Issue: Large memory usage on foreman

- Checkpoints stored in database accumulating
- Ensure tasks are completing to trigger cleanup
- Manually cleanup old checkpoints via API

Issue: Slow task recovery

- Checkpoints very large (many deltas)
- Trigger manual compaction or wait for automatic (50 deltas)
- Increase checkpoint_interval to reduce frequency

Issue: Checkpoint ACK not received by worker

- Network latency/packet loss
- Worker retries checkpoint on next interval
- No data loss, just redundant transmission

============================

For more details on specific modules, see:

- foreman/core/staged_results_manager/checkpoint_manager.py
- foreman/core/staged_results_manager/storage_handler.py
- pc_worker/staged_results_manager/checkpoint_handler.py
- pc_worker/staged_results_manager/delta_computer.py
  """
