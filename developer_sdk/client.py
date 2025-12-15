"""
CrowdCompute Client SDK
"""

import asyncio 
import json
import uuid
import websockets
from typing import Any, Callable, List, Optional, Dict
from common.protocol import (
    Message, MessageType, create_submit_job_message, 
    create_ping_message, create_pong_message
)
from common.serializer import serialize_function


class CrowdComputeClient:
    """Main client for interacting with CrowdCompute foreman"""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.foreman_host: Optional[str] = None
        self.foreman_port: Optional[int] = None
        self.connected = False
        self.pending_jobs: Dict[str, asyncio.Future] = {}
        self._listen_task: Optional[asyncio.Task] = None
    
    async def connect(self, host: str, port: int = 9000):
        """Connect to foreman server"""
        try:
            self.foreman_host = host
            self.foreman_port = port
            uri = f"ws://{host}:{port}"
            
            print(f"Connecting to foreman at {uri}...")
            self.websocket = await websockets.connect(uri)
            self.connected = True
            
            # Start listening for responses
            self._listen_task = asyncio.create_task(self._listen_for_messages())
            
            print(f"Connected to foreman at {uri}")
            
        except Exception as e:
            print(f"Failed to connect to foreman: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from foreman server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.connected = False
        
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None
        
        print("Disconnected from foreman")
    
    async def _listen_for_messages(self):
        """Listen for messages from foreman"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection to foreman closed")
            self.connected = False
        except Exception as e:
            print(f"Error in message listener: {e}")
            self.connected = False
    
    async def _handle_message(self, message_str: str):
        """Handle incoming message from foreman"""
        try:
            message = Message.from_json(message_str)
            
            if message.type == MessageType.JOB_RESULTS:
                job_id = message.job_id
                if job_id in self.pending_jobs:
                    future = self.pending_jobs.pop(job_id)
                    future.set_result(message.data["results"])
            
            elif message.type == MessageType.JOB_ERROR:
                job_id = message.job_id
                if job_id in self.pending_jobs:
                    future = self.pending_jobs.pop(job_id)
                    future.set_exception(Exception(message.data["error"]))
            
            elif message.type == MessageType.PING:
                # Respond to ping
                pong = create_pong_message()
                await self.websocket.send(pong.to_json())
                
        except Exception as e:
            print(f"Error handling message: {e}")
    
    async def map(self, func: Callable, iterable: List[Any]) -> List[Any]:
        """Map function over iterable using distributed workers"""
        if not self.connected:
            raise RuntimeError("Not connected to foreman. Call connect() first.")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create future for this job
        future = asyncio.Future()
        self.pending_jobs[job_id] = future
        
        try:
            # # Serialize function
            func_code = serialize_function(func)
            
            # Create submission message
            message = create_submit_job_message(func_code, iterable, job_id)
            
            # Send to foreman
            await self.websocket.send(message.to_json())
            
            # Wait for results
            results = await future
            return results
            
        except Exception as e:
            # Clean up on error
            if job_id in self.pending_jobs:
                del self.pending_jobs[job_id]
            raise
    
    async def run(self, func: Callable, *args, **kwargs) -> Any:
        """Run a single function with arguments"""
        # For single function execution, we'll just wrap it in a list
        result = await self.map(func, [(args, kwargs)])
        return result[0]


# Global client instance
_client = CrowdComputeClient()


# Public API functions
async def connect(host: str, port: int = 9000):
    """Connect to foreman server"""
    await _client.connect(host, port)


async def disconnect():
    """Disconnect from foreman server"""
    await _client.disconnect()


async def map(func: Callable, iterable: List[Any]) -> List[Any]:
    """Map function over iterable using distributed workers"""
    return await _client.map(func, iterable)


async def run(func: Callable, *args, **kwargs) -> Any:
    """Run a single function with arguments"""
    return await _client.run(func, *args, **kwargs)


async def get(job_id: str) -> Any:
    """Get results for a specific job (for future use)"""
    # This would be implemented for async job submission
    pass
