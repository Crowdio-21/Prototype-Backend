"""
WebSocket connection management for workers and clients
"""

from typing import Dict, Set, Optional, List
from websockets.server import WebSocketServerProtocol


class ConnectionManager:
    """
    Manages WebSocket connections for workers and clients
    
    Responsibilities:
    - Track worker connections and availability
    - Track client connections for jobs
    - Provide lookup methods for connections
    - Maintain connection state
    """
    
    def __init__(self):
        # Worker connections: worker_id -> websocket
        self._workers: Dict[str, WebSocketServerProtocol] = {}
        
        # Client connections: job_id -> websocket
        self._clients: Dict[str, WebSocketServerProtocol] = {}
        
        # Job to client websocket mapping
        self._job_websockets: Dict[str, WebSocketServerProtocol] = {}
        
        # Available workers set (workers not currently processing tasks)
        self._available_workers: Set[str] = set()
    
    # ==================== Worker Management ====================
    
    def add_worker(self, worker_id: str, websocket: WebSocketServerProtocol) -> None:
        """
        Register a new worker connection
        
        Args:
            worker_id: Unique worker identifier
            websocket: WebSocket connection for the worker
        """
        self._workers[worker_id] = websocket
        self._available_workers.add(worker_id)
        print(f"ConnectionManager: Added worker {worker_id}")
    
    def remove_worker(self, worker_id: str) -> bool:
        """
        Remove a worker connection
        
        Args:
            worker_id: Worker identifier to remove
            
        Returns:
            True if worker was removed, False if not found
        """
        if worker_id in self._workers:
            del self._workers[worker_id]
            self._available_workers.discard(worker_id)
            print(f"ConnectionManager: Removed worker {worker_id}")
            return True
        return False
    
    def get_worker_websocket(self, worker_id: str) -> Optional[WebSocketServerProtocol]:
        """
        Get websocket connection for a specific worker
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            WebSocket connection or None if not found
        """
        return self._workers.get(worker_id)
    
    def mark_worker_available(self, worker_id: str) -> None:
        """
        Mark worker as available for new tasks
        
        Args:
            worker_id: Worker identifier
        """
        if worker_id in self._workers:
            self._available_workers.add(worker_id)
    
    def mark_worker_busy(self, worker_id: str) -> None:
        """
        Mark worker as busy (processing a task)
        
        Args:
            worker_id: Worker identifier
        """
        self._available_workers.discard(worker_id)
    
    def is_worker_available(self, worker_id: str) -> bool:
        """
        Check if worker is available
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            True if worker is available
        """
        return worker_id in self._available_workers
    
    def get_available_workers(self) -> Set[str]:
        """
        Get set of available worker IDs
        
        Returns:
            Set of available worker IDs (copy to prevent external modification)
        """
        return self._available_workers.copy()
    
    def get_all_worker_ids(self) -> Set[str]:
        """
        Get all connected worker IDs (available and busy)
        
        Returns:
            Set of all connected worker IDs
        """
        return set(self._workers.keys())
    
    def find_worker_by_websocket(self, websocket: WebSocketServerProtocol) -> Optional[str]:
        """
        Find worker ID by websocket connection
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Worker ID or None if not found
        """
        for worker_id, ws in self._workers.items():
            if ws == websocket:
                return worker_id
        return None
    
    def get_worker_count(self) -> int:
        """Get total number of connected workers"""
        return len(self._workers)
    
    def get_available_worker_count(self) -> int:
        """Get number of available workers"""
        return len(self._available_workers)
    
    def get_busy_worker_count(self) -> int:
        """Get number of busy workers"""
        return len(self._workers) - len(self._available_workers)
    
    # ==================== Client Management ====================
    
    def add_client(self, job_id: str, websocket: WebSocketServerProtocol) -> None:
        """
        Register a client connection for a job
        
        Args:
            job_id: Unique job identifier
            websocket: WebSocket connection for the client
        """
        self._clients[job_id] = websocket
        self._job_websockets[job_id] = websocket
        print(f"ConnectionManager: Added client for job {job_id}")
    
    def remove_client(self, job_id: str) -> bool:
        """
        Remove a client connection
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if client was removed, False if not found
        """
        removed = False
        if job_id in self._clients:
            del self._clients[job_id]
            removed = True
        if job_id in self._job_websockets:
            del self._job_websockets[job_id]
            removed = True
        
        if removed:
            print(f"ConnectionManager: Removed client for job {job_id}")
        return removed
    
    def get_client_websocket(self, job_id: str) -> Optional[WebSocketServerProtocol]:
        """
        Get websocket connection for a specific job's client
        
        Args:
            job_id: Job identifier
            
        Returns:
            WebSocket connection or None if not found
        """
        return self._job_websockets.get(job_id)
    
    def find_job_by_websocket(self, websocket: WebSocketServerProtocol) -> Optional[str]:
        """
        Find job ID by client websocket connection
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Job ID or None if not found
        """
        for job_id, ws in self._job_websockets.items():
            if ws == websocket:
                return job_id
        return None
    
    def has_client(self, job_id: str) -> bool:
        """
        Check if a client connection exists for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if client exists
        """
        return job_id in self._job_websockets
    
    def get_client_count(self) -> int:
        """Get total number of connected clients"""
        return len(self._clients)
    
    def get_active_job_count(self) -> int:
        """Get number of active jobs with connected clients"""
        return len(self._job_websockets)
    
    # ==================== General Operations ====================
    
    def get_all_websockets(self) -> List[WebSocketServerProtocol]:
        """
        Get all websocket connections (workers and clients)
        
        Returns:
            List of all websocket connections
        """
        return list(self._workers.values()) + list(self._clients.values())
    
    def clear_all(self) -> None:
        """Clear all connections (useful for testing or shutdown)"""
        self._workers.clear()
        self._clients.clear()
        self._job_websockets.clear()
        self._available_workers.clear()
        print("ConnectionManager: Cleared all connections")
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get connection statistics
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "connected_workers": len(self._workers),
            "available_workers": len(self._available_workers),
            "busy_workers": len(self._workers) - len(self._available_workers),
            "connected_clients": len(self._clients),
            "active_jobs": len(self._job_websockets)
        }
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        stats = self.get_stats()
        return (
            f"ConnectionManager("
            f"workers={stats['connected_workers']}, "
            f"available={stats['available_workers']}, "
            f"clients={stats['connected_clients']})"
        )