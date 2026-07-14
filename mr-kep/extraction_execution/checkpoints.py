import os
import json
import hashlib

CHECKPOINT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoints")

def _get_run_dir(run_id: str) -> str:
    path = os.path.join(CHECKPOINT_DIR, run_id)
    os.makedirs(path, exist_ok=True)
    return path

def save_checkpoint(run_id: str, stage: str, data: dict) -> str:
    """Save a checkpoint and return its checksum."""
    run_dir = _get_run_dir(run_id)
    filepath = os.path.join(run_dir, f"{stage}.json")
    
    # Remove any existing checksum before computing the new one
    data.pop('_checksum', None)
    content = json.dumps(data, sort_keys=True, indent=2)
    checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    # Store checksum in data for easy retrieval later
    data['_checksum'] = checksum
    content_with_checksum = json.dumps(data, sort_keys=True, indent=2)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_with_checksum)
        
    return checksum

def load_checkpoint(run_id: str, stage: str) -> dict:
    """Load a checkpoint for a given run and stage. Returns None if it doesn't exist."""
    filepath = os.path.join(_get_run_dir(run_id), f"{stage}.json")
    if not os.path.exists(filepath):
        return None
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return data

def verify_checksum(data: dict) -> bool:
    """Verify that the data hasn't been tampered with."""
    if not data or '_checksum' not in data:
        return False
        
    # Remove checksum to compute original hash
    data_copy = dict(data)
    expected_checksum = data_copy.pop('_checksum')
    
    content = json.dumps(data_copy, sort_keys=True, indent=2)
    actual_checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    return expected_checksum == actual_checksum

def clear_run(run_id: str):
    """Clear all checkpoints for a run."""
    run_dir = _get_run_dir(run_id)
    for filename in os.listdir(run_dir):
        os.remove(os.path.join(run_dir, filename))
