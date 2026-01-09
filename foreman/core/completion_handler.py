from common.protocol import create_job_results_message


class JobCompletionHandler:
    """Handles job completion logic and result delivery"""
    
    def __init__(self, connection_manager, job_manager):
        self.connection_manager = connection_manager
        self.job_manager = job_manager
    
    async def handle_job_completion(self, job_id: str):
        """Handle completion of a job and send results to client"""
        # Get job info
        job = await self.job_manager.get_job_info(job_id)
        if not job:
            print(f"Warning: Job {job_id} not found in database")
            return
        
        # Get all tasks
        tasks = await self.job_manager.get_job_tasks_info(job_id)
        
        print(f"Job {job_id} completed with {len(tasks)} tasks")
        
        # Get ordered results
        results = await self.job_manager.get_job_results(job_id)
        
        if results is None:
            print(f"Warning: Could not retrieve results for job {job_id}")
            return
        
        print(f"Collected results: {results}")
        
        # Send results to client
        client_websocket = self.connection_manager.get_client_websocket(job_id)
        
        if not client_websocket:
            print(f"Warning: No client websocket found for job {job_id}")
            return
        
        # Create and send results message
        message = create_job_results_message(results, job_id)
        await client_websocket.send(message.to_json())
        
        # Finalize job (completed_tasks already tracked via increment_job_completed_tasks)
        await self.job_manager.finalize_job(job_id)
        
        print(f"Job {job_id} completed successfully")
        
        
        
