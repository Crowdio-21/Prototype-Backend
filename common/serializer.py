"""
Serialization utilities for CrowdCompute
"""

import cloudpickle
from typing import Any, Callable, List


def serialize_function(func: Callable) -> bytes:
    """Serialize a Python function using cloudpickle"""
    try:
        return cloudpickle.dumps(func)
    except Exception as e:
        raise ValueError(f"Failed to serialize function: {e}")


def deserialize_function(func_bytes: bytes) -> Callable:
    """Deserialize a Python function using cloudpickle"""
    try:
        return cloudpickle.loads(func_bytes)
    except Exception as e:
        raise ValueError(f"Failed to deserialize function: {e}")


def serialize_data(data: Any) -> bytes:
    """Serialize arbitrary data using cloudpickle"""
    try:
        return cloudpickle.dumps(data)
    except Exception as e:
        raise ValueError(f"Failed to serialize data: {e}")


def deserialize_data(data_bytes: bytes) -> Any:
    """Deserialize arbitrary data using cloudpickle"""
    try:
        return cloudpickle.loads(data_bytes)
    except Exception as e:
        raise ValueError(f"Failed to deserialize data: {e}")


def hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string back to bytes"""
    return bytes.fromhex(hex_str)


def bytes_to_hex(data_bytes: bytes) -> str:
    """Convert bytes to hex string"""
    return data_bytes.hex()
