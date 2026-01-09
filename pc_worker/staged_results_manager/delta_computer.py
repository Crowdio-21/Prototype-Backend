"""
Framework-aware delta computation for checkpoints

Detects framework (PyTorch, TensorFlow, NumPy) and computes efficient
deltas tailored to that framework. Falls back to generic pickle-based
dict merging if framework not detected.
"""

import pickle
import gzip
from typing import Any, Dict, Tuple


class DeltaComputer:
    """Framework-aware delta computation"""
    
    @staticmethod
    def detect_framework(state: Dict[str, Any]) -> str:
        """
        Detect which framework is used in the state
        
        Args:
            state: Task state dictionary
            
        Returns:
            Framework name: 'pytorch', 'tensorflow', 'numpy', 'generic'
        """
        try:
            import torch
            for val in state.values():
                if isinstance(val, torch.Tensor):
                    return 'pytorch'
        except ImportError:
            pass
        
        try:
            import tensorflow as tf
            for val in state.values():
                if isinstance(val, (tf.Tensor, tf.Variable)):
                    return 'tensorflow'
        except ImportError:
            pass
        
        try:
            import numpy as np
            for val in state.values():
                if isinstance(val, np.ndarray):
                    return 'numpy'
        except ImportError:
            pass
        
        return 'generic'
    
    @staticmethod
    def compute_delta(last_state: bytes, current_state: bytes) -> bytes:
        """
        Compute delta between two checkpoint states (framework-aware)
        
        Args:
            last_state: Previous checkpoint (gzip-compressed bytes)
            current_state: Current checkpoint (gzip-compressed bytes)
            
        Returns:
            Delta checkpoint (compressed bytes)
        """
        try:
            # Decompress and deserialize
            last_dict = pickle.loads(gzip.decompress(last_state))
            current_dict = pickle.loads(gzip.decompress(current_state))
            
            if not isinstance(last_dict, dict) or not isinstance(current_dict, dict):
                # Not a dict, return as-is
                return gzip.compress(current_state, compresslevel=1)
            
            # Detect framework
            framework = DeltaComputer.detect_framework(current_dict)
            
            if framework == 'pytorch':
                delta = DeltaComputer._compute_pytorch_delta(last_dict, current_dict)
            elif framework == 'tensorflow':
                delta = DeltaComputer._compute_tensorflow_delta(last_dict, current_dict)
            elif framework == 'numpy':
                delta = DeltaComputer._compute_numpy_delta(last_dict, current_dict)
            else:
                delta = DeltaComputer._compute_generic_delta(last_dict, current_dict)
            
            # Serialize and compress
            delta_bytes = pickle.dumps(delta)
            return gzip.compress(delta_bytes, compresslevel=6)
        
        except Exception as e:
            print(f"DeltaComputer: Error computing delta: {e}, returning full state")
            return gzip.compress(current_state, compresslevel=1)
    
    @staticmethod
    def _compute_pytorch_delta(last_state: Dict, current_state: Dict) -> Dict:
        """
        PyTorch-specific delta computation
        
        Only includes changed tensors/weights for efficiency.
        """
        try:
            import torch
            
            delta = {}
            for key, current_val in current_state.items():
                if key not in last_state:
                    # New parameter
                    delta[key] = current_val
                elif isinstance(current_val, torch.Tensor):
                    last_val = last_state[key]
                    if isinstance(last_val, torch.Tensor):
                        # Only store if different
                        if not torch.equal(current_val, last_val):
                            delta[key] = current_val
                else:
                    # Non-tensor value, check if changed
                    if current_val != last_state.get(key):
                        delta[key] = current_val
            
            print(f"DeltaComputer: PyTorch delta computed ({len(delta)} changed tensors)")
            return delta
        
        except Exception as e:
            print(f"DeltaComputer: Error in PyTorch delta computation: {e}")
            return DeltaComputer._compute_generic_delta(last_state, current_state)
    
    @staticmethod
    def _compute_tensorflow_delta(last_state: Dict, current_state: Dict) -> Dict:
        """
        TensorFlow-specific delta computation
        
        Similar to PyTorch - only changed variables included.
        """
        try:
            import tensorflow as tf
            import numpy as np
            
            delta = {}
            for key, current_val in current_state.items():
                if key not in last_state:
                    delta[key] = current_val
                elif isinstance(current_val, (tf.Tensor, tf.Variable)):
                    last_val = last_state[key]
                    if isinstance(last_val, (tf.Tensor, tf.Variable)):
                        # Convert to numpy for comparison
                        current_np = current_val.numpy() if hasattr(current_val, 'numpy') else current_val
                        last_np = last_val.numpy() if hasattr(last_val, 'numpy') else last_val
                        
                        if not np.array_equal(current_np, last_np):
                            delta[key] = current_val
                else:
                    if current_val != last_state.get(key):
                        delta[key] = current_val
            
            print(f"DeltaComputer: TensorFlow delta computed ({len(delta)} changed variables)")
            return delta
        
        except Exception as e:
            print(f"DeltaComputer: Error in TensorFlow delta computation: {e}")
            return DeltaComputer._compute_generic_delta(last_state, current_state)
    
    @staticmethod
    def _compute_numpy_delta(last_state: Dict, current_state: Dict) -> Dict:
        """
        NumPy-specific delta computation
        
        Detects array changes and stores only modified arrays.
        """
        try:
            import numpy as np
            
            delta = {}
            for key, current_val in current_state.items():
                if key not in last_state:
                    delta[key] = current_val
                elif isinstance(current_val, np.ndarray):
                    last_val = last_state[key]
                    if isinstance(last_val, np.ndarray):
                        if not np.array_equal(current_val, last_val):
                            delta[key] = current_val
                else:
                    if current_val != last_state.get(key):
                        delta[key] = current_val
            
            print(f"DeltaComputer: NumPy delta computed ({len(delta)} changed arrays)")
            return delta
        
        except Exception as e:
            print(f"DeltaComputer: Error in NumPy delta computation: {e}")
            return DeltaComputer._compute_generic_delta(last_state, current_state)
    
    @staticmethod
    def _compute_generic_delta(last_state: Dict, current_state: Dict) -> Dict:
        """
        Generic delta computation (fallback)
        
        Simple key-based diff for any dict-based state.
        """
        delta = {}
        for key, current_val in current_state.items():
            if key not in last_state or last_state[key] != current_val:
                delta[key] = current_val
        
        print(f"DeltaComputer: Generic delta computed ({len(delta)} changed keys)")
        return delta
