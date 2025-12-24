from .client import CrowdComputeClient
from typing import Any, Callable, List, Optional, Dict

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
