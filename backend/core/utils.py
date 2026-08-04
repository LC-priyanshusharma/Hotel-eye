import numpy as np

def clean_numpy(obj):
    """
    Recursively converts NumPy scalar types and arrays to standard Python types
    so they can be cleanly serialized by json.dumps or jsonable_encoder.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_numpy(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(clean_numpy(v) for v in obj)
    return obj
