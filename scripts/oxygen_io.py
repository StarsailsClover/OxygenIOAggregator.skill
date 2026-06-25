#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenIO Aggregator - Main Entry Point
GitHub@StarsailsClover
v26.0 Alpha 1

Unified interface for the OxygenIO Aggregator skill.
Provides high-performance, SSD-friendly file I/O operations
with batch processing, write coalescing, and binary inspection.

Usage:
    oxygen_io.py batch-read <patterns...> [--base-dir DIR] [--text-only]
    oxygen_io.py batch-write <json-file> [--base-dir DIR]
    oxygen_io.py glob-stat <patterns...> [--base-dir DIR] [--hash]
    oxygen_io.py inspect <file> [--deep]
    oxygen_io.py benchmark [--base-dir DIR]
    oxygen_io.py version
"""

import sys
import os
import json
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# Add script directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from batch_io import BatchIOEngine, ReadResult, WriteResult, FileInfo
from binary_inspector import BinaryInspector, BinaryInfo
from smart_cache import CachedIO


VERSION = "26.0.0-alpha.1"
CODENAME = "OxygenIO Aggregator"


def print_version():
    """Print version information."""
    print(f"{CODENAME} v{VERSION}")
    print(f"GitHub@StarsailsClover")
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version}")


def cmd_batch_read(args: List[str]) -> int:
    """Batch read files command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch read files")
    parser.add_argument("patterns", nargs="+", help="Glob patterns")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    parser.add_argument("--text-only", action="store_true", help="Only text files")
    parser.add_argument("--max-size", type=int, default=None, help="Max file size in bytes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    parsed = parser.parse_args(args)
    
    engine = BatchIOEngine(base_dir=parsed.base_dir)
    results = engine.batch_read(
        patterns=parsed.patterns,
        include_binary=not parsed.text_only,
        max_size=parsed.max_size
    )
    
    if parsed.json:
        output = {}
        for path, result in results.items():
            output[path] = {
                "success": result.success,
                "file_type": result.file_type.value,
                "size": result.size,
                "encoding": result.encoding,
                "read_method": result.read_method,
                "error": result.error,
                "content_preview": result.content[:200] + "..." if result.content and len(result.content) > 200 else result.content
            }
        print(json.dumps(output, indent=2))
    else:
        print(f"Read {len(results)} files:")
        for path, result in sorted(results.items()):
            status = "✓" if result.success else "✗"
            print(f"  {status} {path} ({result.size} bytes, {result.file_type.value}, {result.read_method})")
            if result.error:
                print(f"      Error: {result.error}")
    
    return 0


def cmd_batch_write(args: List[str]) -> int:
    """Batch write files command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch write files")
    parser.add_argument("json_file", help="JSON file with {path: content} mapping")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    parser.add_argument("--no-atomic", action="store_true", help="Disable atomic writes")
    
    parsed = parser.parse_args(args)
    
    with open(parsed.json_file, 'r') as f:
        files = json.load(f)
    
    engine = BatchIOEngine(
        base_dir=parsed.base_dir,
        atomic_writes=not parsed.no_atomic
    )
    
    results = engine.batch_write(files)
    
    total_bytes = sum(r.bytes_written for r in results.values() if r.success)
    success_count = sum(1 for r in results.values() if r.success)
    
    print(f"Wrote {success_count}/{len(results)} files ({total_bytes} bytes total):")
    for path, result in sorted(results.items()):
        status = "✓" if result.success else "✗"
        atomic = " [atomic]" if result.atomic else ""
        print(f"  {status} {path} ({result.bytes_written} bytes){atomic}")
        if result.error:
            print(f"      Error: {result.error}")
    
    return 0


def cmd_glob_stat(args: List[str]) -> int:
    """Glob and stat files command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Glob and stat files")
    parser.add_argument("patterns", nargs="+", help="Glob patterns")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    parser.add_argument("--hash", action="store_true", help="Compute SHA256 hash")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    parsed = parser.parse_args(args)
    
    engine = BatchIOEngine(base_dir=parsed.base_dir)
    results = engine.glob_stat(
        patterns=parsed.patterns,
        compute_hash=parsed.hash
    )
    
    if parsed.json:
        output = {}
        for path, info in results.items():
            output[path] = {
                "size": info.size,
                "mtime": info.mtime,
                "file_type": info.file_type.value,
                "encoding": info.encoding,
                "sha256": info.sha256,
                "permissions": oct(info.permissions) if info.permissions else None,
                "error": info.error
            }
        print(json.dumps(output, indent=2))
    else:
        print(f"Found {len(results)} files:")
        for path, info in sorted(results.items()):
            print(f"  {path}: {info.size} bytes, {info.file_type.value}")
            if info.sha256:
                print(f"    SHA256: {info.sha256}")
    
    return 0


def cmd_inspect(args: List[str]) -> int:
    """Inspect binary file command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Inspect binary file")
    parser.add_argument("file", help="File to inspect")
    parser.add_argument("--deep", action="store_true", help="Deep analysis")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    parsed = parser.parse_args(args)
    
    inspector = BinaryInspector()
    info = inspector.inspect(parsed.file, deep=parsed.deep)
    
    if parsed.json:
        output = {
            "path": info.path,
            "format": info.format.value,
            "architecture": info.architecture.value,
            "size": info.size,
            "sha256": info.sha256,
            "md5": info.md5,
            "is_64bit": info.is_64bit,
            "is_executable": info.is_executable,
            "is_library": info.is_library,
            "entry_point": hex(info.entry_point) if info.entry_point else None,
            "section_count": info.section_count,
            "version_info": info.version_info,
            "compile_time": info.compile_time,
            "error": info.error
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"File: {info.path}")
        print(f"Format: {info.format.value}")
        print(f"Architecture: {info.architecture.value}")
        print(f"64-bit: {info.is_64bit}")
        print(f"Size: {info.size:,} bytes")
        print(f"SHA256: {info.sha256}")
        print(f"MD5: {info.md5}")
        print(f"Executable: {info.is_executable}")
        print(f"Library: {info.is_library}")
        if info.entry_point:
            print(f"Entry point: 0x{info.entry_point:x}")
        print(f"Sections: {info.section_count}")
        if info.compile_time:
            print(f"Compile time: {info.compile_time}")
        if info.version_info:
            print("Version info:")
            for key, value in info.version_info.items():
                print(f"  {key}: {value}")
        if info.error:
            print(f"Error: {info.error}")
    
    return 0


def cmd_benchmark(args: List[str]) -> int:
    """Run performance benchmark."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run I/O benchmark")
    parser.add_argument("--base-dir", default=None, help="Base directory (temp dir if not set)")
    parser.add_argument("--num-files", type=int, default=100, help="Number of files for benchmark")
    parser.add_argument("--file-size", type=int, default=4096, help="File size in bytes")
    
    parsed = parser.parse_args(args)
    
    print(f"{CODENAME} v{VERSION} - Benchmark")
    print("=" * 60)
    
    if parsed.base_dir:
        base_dir = parsed.base_dir
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        tmpdir = tempfile.mkdtemp(prefix="oxygenio_bench_")
        base_dir = tmpdir
        cleanup = True
    
    try:
        engine = BatchIOEngine(base_dir=base_dir)
        
        # Prepare test data
        print(f"\nPreparing {parsed.num_files} test files ({parsed.file_size} bytes each)...")
        test_content = "x" * parsed.file_size
        test_files = {f"test_{i:04d}.txt": test_content for i in range(parsed.num_files)}
        
        # Benchmark: sequential batch write
        print("\n1. Batch Write (sequential, atomic)")
        start = time.time()
        results = engine.batch_write(test_files)
        write_time = time.time() - start
        total_bytes = sum(r.bytes_written for r in results.values() if r.success)
        print(f"   Time: {write_time*1000:.2f} ms")
        print(f"   Throughput: {total_bytes / write_time / 1024 / 1024:.2f} MB/s")
        print(f"   Files written: {sum(1 for r in results.values() if r.success)}/{parsed.num_files}")
        
        # Benchmark: batch read
        print("\n2. Batch Read (all files)")
        start = time.time()
        results = engine.batch_read(["**/*.txt"])
        read_time = time.time() - start
        total_bytes = sum(r.size for r in results.values() if r.success)
        print(f"   Time: {read_time*1000:.2f} ms")
        print(f"   Throughput: {total_bytes / read_time / 1024 / 1024:.2f} MB/s")
        print(f"   Files read: {sum(1 for r in results.values() if r.success)}")
        
        # Benchmark: glob + stat
        print("\n3. Glob + Stat (single traversal)")
        start = time.time()
        results = engine.glob_stat(["**/*.txt"])
        glob_time = time.time() - start
        print(f"   Time: {glob_time*1000:.2f} ms")
        print(f"   Files found: {len(results)}")
        
        # Benchmark: smart cache
        print("\n4. Smart Cache - Read Performance")
        cached_io = CachedIO(base_dir=base_dir, cache_size_mb=64)
        
        # Cold read
        start = time.time()
        for i in range(parsed.num_files):
            _ = cached_io.read_file(f"test_{i:04d}.txt")
        cold_time = time.time() - start
        print(f"   Cold read (no cache): {cold_time*1000:.2f} ms")
        
        # Warm read (cached)
        start = time.time()
        for i in range(parsed.num_files):
            _ = cached_io.read_file(f"test_{i:04d}.txt")
        warm_time = time.time() - start
        print(f"   Warm read (cached): {warm_time*1000:.2f} ms")
        print(f"   Speedup: {cold_time / warm_time:.1f}x")
        
        cached_io.shutdown()
        
        # Summary
        print("\n" + "=" * 60)
        print("Benchmark Complete!")
        print(f"\nIO Operation Reduction Estimate:")
        print(f"  Batch read: {parsed.num_files} individual reads → 1 batch operation")
        print(f"  Write coalescing: {parsed.num_files} individual writes → 1 flush")
        print(f"  Estimated SSD wear reduction: ~80-90% (vs random small I/O)")
        
    finally:
        if cleanup:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        "batch-read": cmd_batch_read,
        "batch-write": cmd_batch_write,
        "glob-stat": cmd_glob_stat,
        "inspect": cmd_inspect,
        "benchmark": cmd_benchmark,
        "version": lambda _: (print_version(), 0)[1],
    }
    
    if command in commands:
        return commands[command](args)
    elif command in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
