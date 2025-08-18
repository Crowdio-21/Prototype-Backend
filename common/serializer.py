"""
Serialization utilities for CrowdCompute
"""

import sys
import cloudpickle
from typing import Any, Callable, List


def _env_info() -> str:
    """Return a concise runtime environment string for diagnostics"""
    return f"python={sys.version.split()[0]} cloudpickle={getattr(cloudpickle, '__version__', 'unknown')}"


def get_runtime_info() -> str:
    """Public helper to expose runtime info to other modules"""
    return _env_info()


def serialize_function(func: Callable) -> bytes:
    """Serialize a Python function using cloudpickle"""
    try:
        return cloudpickle.dumps(func)
    except Exception as e:
        raise ValueError(f"Failed to serialize function ({_env_info()}): {e}")


def deserialize_function(func_bytes: bytes) -> Callable:
    """Deserialize a Python function using cloudpickle"""
    try:
        return cloudpickle.loads(func_bytes)
    except Exception as e:
        raise ValueError(f"Failed to deserialize function ({_env_info()}): {e}")


def serialize_data(data: Any) -> bytes:
    """Serialize arbitrary data using cloudpickle"""
    try:
        return cloudpickle.dumps(data)
    except Exception as e:
        raise ValueError(f"Failed to serialize data ({_env_info()}): {e}")


def deserialize_data(data_bytes: bytes) -> Any:
    """Deserialize arbitrary data using cloudpickle"""
    try:
        return cloudpickle.loads(data_bytes)
    except Exception as e:
        raise ValueError(f"Failed to deserialize data ({_env_info()}): {e}")


def hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string back to bytes"""
    return bytes.fromhex(hex_str)


def bytes_to_hex(data_bytes: bytes) -> str:
    """Convert bytes to hex string"""
    return data_bytes.hex()
