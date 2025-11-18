"""Cache manager for repeated operations."""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any


class CacheManager:
    """Manages caching for repeated operations to improve performance."""
    
    def __init__(self, cache_dir: str = "~/.lolo/cache", ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live for cache entries in seconds (default: 1 hour)
        """
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        
        # In-memory cache for frequently accessed items
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Use hash of key as filename to avoid filesystem issues
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found or expired
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["value"]
            else:
                # Expired, remove from memory cache
                del self._memory_cache[key]
        
        # Check disk cache
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                entry = json.load(f)
            
            # Check if expired
            if time.time() - entry["timestamp"] > self.ttl:
                # Expired, delete file
                cache_path.unlink()
                return None
            
            # Add to memory cache for faster access
            self._memory_cache[key] = entry
            
            return entry["value"]
        except Exception:
            # If there's any error reading cache, return None
            return None
    
    def set(self, key: str, value: Any):
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        entry = {
            "timestamp": time.time(),
            "value": value
        }
        
        # Store in memory cache
        self._memory_cache[key] = entry
        
        # Store on disk
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w') as f:
                json.dump(entry, f)
        except Exception:
            # Silently fail if we can't write to disk
            pass
    
    def clear(self):
        """Clear all cache entries."""
        # Clear memory cache
        self._memory_cache.clear()
        
        # Clear disk cache
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
        except Exception:
            pass
    
    def cleanup_expired(self):
        """Remove expired cache entries from disk."""
        try:
            current_time = time.time()
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry = json.load(f)
                    
                    if current_time - entry["timestamp"] > self.ttl:
                        cache_file.unlink()
                except Exception:
                    # If we can't read the file, delete it
                    cache_file.unlink()
        except Exception:
            pass


# Global cache instance for web fetches (1 hour TTL)
web_cache = CacheManager(cache_dir="~/.lolo/cache/web", ttl=3600)

# Global cache instance for system info (5 minutes TTL)
system_cache = CacheManager(cache_dir="~/.lolo/cache/system", ttl=300)
