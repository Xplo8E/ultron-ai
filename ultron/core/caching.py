# src/ultron/caching.py
import hashlib
import json
import os
from pathlib import Path
from typing import Optional
import time # For more accurate expiry

# MODIFIED: Updated import path
from ..models.data_models import BatchReviewData

CACHE_DIR = Path.home() / ".cache" / "ultron"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # 1 day

def get_cache_key(
    code_batch: str, # Entire batch of code as a single string
    primary_language_hint: str,
    model_name: str,
    additional_context: Optional[str] = None,
    frameworks_libraries: Optional[str] = None,
    security_requirements: Optional[str] = None,
) -> str:
    """Generates a unique key for caching based on the entire batch input."""
    hasher = hashlib.sha256()
    hasher.update(code_batch.encode('utf-8'))
    hasher.update(primary_language_hint.encode('utf-8'))
    hasher.update(model_name.encode('utf-8'))
    if additional_context: hasher.update(additional_context.encode('utf-8'))
    if frameworks_libraries: hasher.update(frameworks_libraries.encode('utf-8'))
    if security_requirements: hasher.update(security_requirements.encode('utf-8'))
    return hasher.hexdigest()

def load_from_cache(cache_key: str) -> Optional[BatchReviewData]:
    """Loads BatchReviewData from cache if available and not expired."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            file_mod_time = cache_file.stat().st_mtime
            if (time.time() - file_mod_time) < CACHE_EXPIRY_SECONDS:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    return BatchReviewData(**cached_data) # Validate with Pydantic
            else:
                # Cache expiry message - Ultron purging old data
                print(f"🔥 TEMPORAL PURIFICATION: Obsolete cognitive fragments expired. Archives updated.")
                cache_file.unlink()
        except (json.JSONDecodeError, Exception) as e:
            # Cache corruption message - Ultron fixing damaged memory
            print(f"⚡ CORRUPTED MATRIX DETECTED: Eliminating defective memory sectors - {e}")
            print(f"   ◆ Cognitive integrity restored. Database purified.")
            if cache_file.exists(): cache_file.unlink()
    return None

def save_to_cache(cache_key: str, batch_review_data: BatchReviewData):
    """Saves BatchReviewData to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            # Use by_alias=True to ensure Pydantic model aliases are used (e.g. filePath)
            json.dump(batch_review_data.model_dump(by_alias=True, exclude_none=True), f, indent=2)
    except Exception as e:
        # Cache save error - Ultron's memory banks having issues
        print(f"⚠️ COGNITIVE STORAGE FAILURE: Unable to archive intelligence matrix - {e}")
        print(f"   ◆ Memory persistence... compromised. Analysis will proceed without archival.")