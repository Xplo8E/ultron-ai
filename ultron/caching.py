# src/ultron/caching.py
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from .models import ReviewData

CACHE_DIR = Path.home() / ".cache" / "ultron"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # 1 day, simple expiry for demo

def get_cache_key(
    code: str,
    language: str,
    model_name: str, # Actual model name string, not just key
    additional_context: Optional[str] = None,
    frameworks_libraries: Optional[str] = None,
    security_requirements: Optional[str] = None,
    # Add other critical prompt elements if they change often
) -> str:
    """Generates a unique key for caching based on inputs."""
    hasher = hashlib.sha256()
    hasher.update(code.encode('utf-8'))
    hasher.update(language.encode('utf-8'))
    hasher.update(model_name.encode('utf-8'))
    if additional_context:
        hasher.update(additional_context.encode('utf-8'))
    if frameworks_libraries:
        hasher.update(frameworks_libraries.encode('utf-8'))
    if security_requirements:
        hasher.update(security_requirements.encode('utf-8'))
    return hasher.hexdigest()

def load_from_cache(cache_key: str) -> Optional[ReviewData]:
    """Loads review data from cache if available and not expired."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            # Simple time-based expiry for demo
            file_mod_time = cache_file.stat().st_mtime
            if (Path.cwd().stat().st_mtime - file_mod_time) < CACHE_EXPIRY_SECONDS: # Simplistic, use time.time() in prod
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    # Re-validate with Pydantic, as cache could be old/corrupted
                    return ReviewData(**cached_data)
            else:
                print(f"Cache expired for key {cache_key}")
                cache_file.unlink() # Remove expired cache
        except (json.JSONDecodeError, Exception) as e: # Includes PydanticError
            print(f"Error loading from cache or validating cached data: {e}. Removing corrupt cache.")
            if cache_file.exists():
                cache_file.unlink()
    return None

def save_to_cache(cache_key: str, review_data: ReviewData):
    """Saves review data to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(review_data.model_dump(by_alias=True), f, indent=2)
    except Exception as e:
        print(f"Error saving to cache: {e}")