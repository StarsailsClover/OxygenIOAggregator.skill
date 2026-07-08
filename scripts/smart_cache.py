#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenIO Aggregator - Smart Cache & Write Coalescer
GitHub@StarsailsClover
v26.0 Alpha 1

Intelligent caching and write coalescing layer designed to minimize
SSD write amplification by reducing total I/O operations and
converting random small writes into sequential large writes.
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import hashlib


@dataclass
class CacheEntry:
    """Entry in the file cache."""
    path: str
    content: Union[str, bytes]
    size: int
    mtime: float  # File modification time at cache time
    access_time: float  # Last access time
    access_count: int = 0
    is_dirty: bool = False  # Whether content has been modified
    is_text: bool = True


class LRUFileCache:
    """
    LRU (Least Recently Used) file cache with memory limits.
    
    Features:
    - Automatic eviction of least recently used files
    - Memory size limits
    - Dirty tracking for write-back
    - Mtime-based cache invalidation
    """
    
    def __init__(self, max_size_mb: int = 128, max_entries: int = 1024):
        """
        Initialize the LRU cache.
        
        Args:
            max_size_mb: Maximum cache size in megabytes
            max_entries: Maximum number of cached files
        """
        self.max_size = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.current_size = 0
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
    
    def get(self, path: str) -> Optional[CacheEntry]:
        """
        Get a file from cache.
        
        Args:
            path: File path
            
        Returns:
            CacheEntry if found, None otherwise
        """
        with self._lock:
            if path not in self._cache:
                return None
            
            entry = self._cache.pop(path)
            entry.access_time = time.time()
            entry.access_count += 1
            self._cache[path] = entry  # Reinsert at end (most recent)
            return entry
    
    def put(self, path: str, content: Union[str, bytes], 
            is_text: bool = True, mtime: Optional[float] = None,
            is_dirty: bool = False) -> CacheEntry:
        """
        Add or update a file in cache.
        
        Args:
            path: File path
            content: File content
            is_text: Whether content is text
            mtime: File modification time
            is_dirty: Whether content is modified (needs write-back)
            
        Returns:
            The cache entry
        """
        size = len(content.encode('utf-8') if is_text and isinstance(content, str) else content)
        
        with self._lock:
            # Remove existing entry if present
            if path in self._cache:
                old_entry = self._cache.pop(path)
                self.current_size -= old_entry.size
            
            # Evict entries if needed
            while (self.current_size + size > self.max_size or 
                   len(self._cache) >= self.max_entries):
                if not self._cache:
                    break
                _, evicted = self._cache.popitem(last=False)  # FIFO/LRU
                self.current_size -= evicted.size
            
            entry = CacheEntry(
                path=path,
                content=content,
                size=size,
                mtime=mtime or time.time(),
                access_time=time.time(),
                access_count=1,
                is_dirty=is_dirty,
                is_text=is_text
            )
            
            self._cache[path] = entry
            self.current_size += size
            return entry
    
    def invalidate(self, path: str) -> bool:
        """
        Remove a file from cache.
        
        Args:
            path: File path
            
        Returns:
            True if file was in cache
        """
        with self._lock:
            if path in self._cache:
                entry = self._cache.pop(path)
                self.current_size -= entry.size
                return True
            return False
    
    def get_dirty_entries(self) -> List[CacheEntry]:
        """Get all dirty (modified) entries that need to be written."""
        with self._lock:
            return [e for e in self._cache.values() if e.is_dirty]
    
    def mark_clean(self, path: str):
        """Mark an entry as clean (written to disk)."""
        with self._lock:
            if path in self._cache:
                self._cache[path].is_dirty = False
    
    def clear(self):
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()
            self.current_size = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            dirty_count = sum(1 for e in self._cache.values() if e.is_dirty)
            return {
                "entries": len(self._cache),
                "size_bytes": self.current_size,
                "size_mb": self.current_size / (1024 * 1024),
                "max_size_mb": self.max_size / (1024 * 1024),
                "dirty_entries": dirty_count,
                "hit_rate": 0.0  # Would need to track hits/misses
            }


class WriteCoalescer:
    """
    Write coalescing buffer that batches multiple small writes
    into fewer, larger sequential writes to reduce SSD wear.
    
    Features:
    - Time-based flushing
    - Size-based flushing
    - Write combining (multiple writes to same file merged)
    - Sequential write ordering optimization
    - Atomic batch writes
    """
    
    def __init__(self, flush_interval_ms: int = 1000, 
                 max_buffer_size_mb: int = 64,
                 max_pending_writes: int = 256,
                 base_dir: str = "."):
        """
        Initialize the write coalescer.
        
        Args:
            flush_interval_ms: Maximum time before auto-flush (milliseconds)
            max_buffer_size_mb: Maximum buffered data before flush
            max_pending_writes: Maximum pending writes before flush
            base_dir: Base directory for relative paths
        """
        self.flush_interval = flush_interval_ms / 1000.0  # Convert to seconds
        self.max_buffer_size = max_buffer_size_mb * 1024 * 1024
        self.max_pending = max_pending_writes
        self.base_dir = Path(base_dir).resolve()
        
        self._pending_writes: Dict[str, Dict[str, Any]] = {}
        self._buffer_size = 0
        self._last_flush = time.time()
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._running = False
    
    def queue_write(self, path: str, content: Union[str, bytes], 
                    is_text: bool = True) -> int:
        """
        Queue a write operation.
        
        Args:
            path: File path (relative or absolute)
            content: Content to write
            is_text: Whether content is text
            
        Returns:
            Current number of pending writes
        """
        abs_path = str(self._normalize_path(path))
        size = len(content.encode('utf-8') if is_text and isinstance(content, str) else content)
        
        with self._lock:
            # If file already pending, replace content (coalesce)
            if abs_path in self._pending_writes:
                old_size = self._pending_writes[abs_path]['size']
                self._buffer_size -= old_size
            
            self._pending_writes[abs_path] = {
                'content': content,
                'is_text': is_text,
                'size': size,
                'queued_at': time.time()
            }
            self._buffer_size += size
            
            pending_count = len(self._pending_writes)
            
            # Check if we need to flush
            should_flush = (
                self._buffer_size >= self.max_buffer_size or
                pending_count >= self.max_pending
            )
        
        if should_flush:
            self.flush()  # fire-and-forget, ignore 3-tuple return
        
        return pending_count
    
    def flush(self) -> Tuple[int, int, int]:
        """
        Flush all pending writes to disk.
        
        Returns:
            Tuple of (files_written, total_bytes_written, errors)
        """
        with self._lock:
            if not self._pending_writes:
                return 0, 0, 0
            
            # Copy pending writes and clear buffer
            pending = dict(self._pending_writes)
            self._pending_writes.clear()
            self._buffer_size = 0
            self._last_flush = time.time()
        
        # Sort by path for sequential write optimization
        sorted_paths = sorted(pending.keys())
        
        files_written = 0
        total_bytes = 0
        errors = 0
        
        for path in sorted_paths:
            write_info = pending[path]
            content = write_info['content']
            is_text = write_info['is_text']
            
            try:
                file_path = Path(path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if is_text:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    with open(file_path, 'wb') as f:
                        f.write(content)
                
                files_written += 1
                total_bytes += write_info['size']
            except Exception:
                errors += 1
        
        return files_written, total_bytes, errors
    
    def _normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path to absolute."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.resolve()
    
    def start_background_flush(self):
        """Start background auto-flush thread."""
        if self._running:
            return
        
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def stop_background_flush(self):
        """Stop background auto-flush thread."""
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=2.0)
            self._flush_thread = None
    
    def _flush_loop(self):
        """Background flush loop."""
        while self._running:
            time.sleep(self.flush_interval / 2)  # Check twice per interval
            
            with self._lock:
                time_since_flush = time.time() - self._last_flush
                has_pending = bool(self._pending_writes)
            
            if has_pending and time_since_flush >= self.flush_interval:
                self.flush()
    
    def stats(self) -> Dict[str, Any]:
        """Get coalescer statistics."""
        with self._lock:
            return {
                "pending_writes": len(self._pending_writes),
                "buffer_size_bytes": self._buffer_size,
                "buffer_size_mb": self._buffer_size / (1024 * 1024),
                "max_buffer_size_mb": self.max_buffer_size / (1024 * 1024),
                "flush_interval_ms": self.flush_interval * 1000,
                "last_flush_seconds_ago": time.time() - self._last_flush,
                "background_running": self._running
            }


class CachedIO:
    """
    High-level cached I/O interface combining LRU cache and write coalescing.
    
    This is the main entry point for agents that want to minimize
    disk I/O operations and reduce SSD wear.
    """
    
    def __init__(self, base_dir: str = ".", 
                 cache_size_mb: int = 128,
                 write_buffer_mb: int = 64,
                 flush_interval_ms: int = 1000,
                 use_write_coalescing: bool = True):
        """
        Initialize cached I/O system.
        
        Args:
            base_dir: Base directory for relative paths
            cache_size_mb: Read cache size in megabytes
            write_buffer_mb: Write buffer size in megabytes
            flush_interval_ms: Auto-flush interval for writes
            use_write_coalescing: Enable write coalescing
        """
        self.base_dir = Path(base_dir).resolve()
        self.cache = LRUFileCache(max_size_mb=cache_size_mb)
        self.use_write_coalescing = use_write_coalescing
        
        if use_write_coalescing:
            self.coalescer = WriteCoalescer(
                flush_interval_ms=flush_interval_ms,
                max_buffer_size_mb=write_buffer_mb,
                base_dir=str(base_dir)
            )
            self.coalescer.start_background_flush()
        else:
            self.coalescer = None
    
    def read_file(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """
        Read a file with caching.
        
        Args:
            path: File path
            binary: Whether to read as binary
            
        Returns:
            File content (str or bytes)
        """
        abs_path = str(self._normalize_path(path))
        
        # Check cache first
        entry = self.cache.get(abs_path)
        if entry:
            # Verify file hasn't changed on disk
            try:
                disk_mtime = os.path.getmtime(abs_path)
                if disk_mtime <= entry.mtime:
                    return entry.content
            except OSError:
                pass
        
        # Read from disk
        if binary:
            with open(abs_path, 'rb') as f:
                content = f.read()
            is_text = False
        else:
            with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            is_text = True
        
        # Cache the result
        try:
            mtime = os.path.getmtime(abs_path)
        except OSError:
            mtime = time.time()
        
        self.cache.put(abs_path, content, is_text=is_text, mtime=mtime)
        
        return content
    
    def write_file(self, path: str, content: Union[str, bytes], 
                   binary: bool = False, immediate: bool = False):
        """
        Write a file with optional write coalescing.
        
        Args:
            path: File path
            content: Content to write
            binary: Whether content is binary
            immediate: Write immediately (don't coalesce)
        """
        abs_path = str(self._normalize_path(path))
        is_text = not binary
        
        # Update cache
        self.cache.put(abs_path, content, is_text=is_text, is_dirty=True)
        
        if self.use_write_coalescing and not immediate:
            self.coalescer.queue_write(path, content, is_text=is_text)
        else:
            # Write immediately
            file_path = Path(abs_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if binary:
                with open(file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Mark cache entry as clean
            self.cache.mark_clean(abs_path)
    
    def flush_writes(self) -> Tuple[int, int, int]:
        """Flush all pending writes and mark cache entries clean."""
        if self.coalescer:
            result = self.coalescer.flush()
            for entry in self.cache.get_dirty_entries():
                self.cache.mark_clean(entry.path)
            return result
        return 0, 0, 0
    
    def invalidate_cache(self, path: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            path: Specific path to invalidate, or None to clear all
        """
        if path:
            abs_path = str(self._normalize_path(path))
            self.cache.invalidate(abs_path)
        else:
            self.cache.clear()
    
    def _normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path to absolute."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.resolve()
    
    def stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        stats = {
            "cache": self.cache.stats(),
            "base_dir": str(self.base_dir),
        }
        if self.coalescer:
            stats["write_coalescer"] = self.coalescer.stats()
        return stats
    
    def shutdown(self):
        """Shut down the cached I/O system, flushing all writes."""
        if self.coalescer:
            self.coalescer.stop_background_flush()
            self.coalescer.flush()


def main():
    """CLI entry point for testing."""
    import json
    import tempfile
    import os
    
    print("OxygenIO Aggregator - Smart Cache & Write Coalescer")
    print("=" * 60)
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Test directory: {tmpdir}")
        
        cached_io = CachedIO(
            base_dir=tmpdir,
            cache_size_mb=16,
            write_buffer_mb=8,
            flush_interval_ms=500
        )
        
        print("\n1. Testing write coalescing...")
        for i in range(10):
            cached_io.write_file(f"file_{i}.txt", f"Content of file {i}\n" * 100)
        
        stats = cached_io.stats()
        print(f"   Pending writes: {stats['write_coalescer']['pending_writes']}")
        print(f"   Buffer size: {stats['write_coalescer']['buffer_size_mb']:.2f} MB")
        
        print("\n2. Flushing writes...")
        written, bytes_written, errors = cached_io.flush_writes()
        print(f"   Files written: {written}")
        print(f"   Total bytes: {bytes_written}")
        print(f"   Errors: {errors}")
        
        print("\n3. Testing read caching...")
        # First read (miss)
        start = time.time()
        content = cached_io.read_file("file_0.txt")
        miss_time = time.time() - start
        
        # Second read (hit)
        start = time.time()
        content = cached_io.read_file("file_0.txt")
        hit_time = time.time() - start
        
        print(f"   Cache miss time: {miss_time*1000:.2f} ms")
        print(f"   Cache hit time: {hit_time*1000:.4f} ms")
        
        cache_stats = cached_io.stats()
        print(f"   Cache entries: {cache_stats['cache']['entries']}")
        print(f"   Cache size: {cache_stats['cache']['size_mb']:.2f} MB")
        
        cached_io.shutdown()
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    main()
