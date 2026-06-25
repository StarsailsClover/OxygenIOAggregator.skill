---
name: oxygen-io-aggregator
description: High-performance SSD-friendly file I/O aggregator skill. Use when you need to batch-read multiple files (especially .ts, .toml, .json, .yaml, and other code/config files), batch-write multiple files, inspect binary files (.dll, .so, .dylib, .exe), or reduce disk I/O operations to minimize SSD wear and write amplification. Supports cross-platform (Windows/macOS/Linux) file operations with write coalescing, LRU caching, memory-mapped files, and atomic writes. Ideal for codebase analysis, multi-file processing, and scenarios where reducing total I/O operations is critical.
metadata:
  version: 26.0.0-alpha.2
  author: GitHub@StarsailsClover
---

# OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

High-performance, SSD-friendly file I/O aggregator designed to minimize disk wear
by reducing total I/O operations while maintaining the same data throughput.

## When to Use

Use this skill when:

- You need to read **multiple files** from a codebase or project (batch read)
- You need to write **multiple files** in one operation (batch write)
- You need to inspect **binary files** (.dll, .so, .dylib, .exe) without loading full content
- You want to **reduce SSD wear** and write amplification from frequent small I/O operations
- You need to process files that Step Assistant cannot read (.ts, .toml, .dll, etc.)
- You want to **scan a directory** and get metadata for all matching files in one pass
- You need **cross-platform** file operations (Windows/macOS/Linux)

## Core Concepts

### Write Amplification Problem

SSD write amplification (WAF) occurs when small random writes trigger garbage collection
and page-aligned writes, causing the actual flash memory writes to be 3-8x larger than
the host writes. This is the root cause of the CodeX CLI disk wear issue.

### How OxygenIO Solves It

1. **Batch I/O**: N small operations → 1 large operation
2. **Write Coalescing**: Buffer multiple writes, flush in batches
3. **Sequential Ordering**: Sort paths to optimize disk access patterns
4. **Memory-Mapped Files**: mmap for large file reads (3-4x faster)
5. **Atomic Writes**: Temp file + rename, reducing filesystem journal overhead
6. **LRU Caching**: Avoid re-reading frequently accessed files

### Performance Impact

| Metric | Individual I/O | OxygenIO Batch | Improvement |
|--------|---------------|----------------|-------------|
| System calls | N | 1-2 | ~Nx fewer |
| Write amplification | 3-8x WAF | 1.1-1.5x WAF | ~70-85% less wear |
| Directory traversals | N | 1 | ~Nx fewer |
| Cache hit speed | - | ~10-100x | Sub-millisecond reads |

## Quick Start

### Batch Read Multiple Files

```python
from scripts.batch_io import BatchIOEngine

engine = BatchIOEngine(base_dir="/path/to/project")

# Read all TypeScript and TOML files
results = engine.batch_read(["**/*.ts", "**/*.toml"])

for path, result in results.items():
    if result.success:
        print(f"{path}: {result.size} bytes, {result.encoding}")
        # result.content contains the file content
```

### Batch Write Multiple Files

```python
from scripts.batch_io import BatchIOEngine

engine = BatchIOEngine(base_dir="/path/to/project")

files = {
    "src/config.ts": "export const config = { ... }",
    "docs/README.md": "# Project\n\n...",
    ".env": "API_KEY=xxx\nDEBUG=false"
}

results = engine.batch_write(files, create_dirs=True)
```

### Inspect a Binary File

```python
from scripts.binary_inspector import BinaryInspector

inspector = BinaryInspector()
info = inspector.inspect("/path/to/library.dll", deep=True)

print(f"Format: {info.format.value}")
print(f"Architecture: {info.architecture.value}")
print(f"64-bit: {info.is_64bit}")
print(f"Sections: {info.section_count}")
if info.version_info:
    print(f"Version: {info.version_info.get('FileVersion')}")
```

### Smart Cached I/O

```python
from scripts.smart_cache import CachedIO

cached_io = CachedIO(
    base_dir="/path/to/project",
    cache_size_mb=128,
    write_buffer_mb=64,
    flush_interval_ms=1000
)

# Reads are cached automatically
content = cached_io.read_file("src/main.ts")

# Writes are coalesced and flushed in batches
cached_io.write_file("src/config.ts", new_config)

# Force flush when needed
cached_io.flush_writes()

# Shutdown cleanly
cached_io.shutdown()
```

## CLI Usage

```bash
# Batch read
python scripts/oxygen_io.py batch-read "**/*.ts" "**/*.toml" --base-dir ./project

# Batch write (from JSON file)
python scripts/oxygen_io.py batch-write files.json --base-dir ./project

# Glob and stat
python scripts/oxygen_io.py glob-stat "**/*.py" --hash --json

# Inspect binary
python scripts/oxygen_io.py inspect ./lib.dll --deep

# Run benchmark
python scripts/oxygen_io.py benchmark --num-files 100 --file-size 4096

# Version info
python scripts/oxygen_io.py version
```

## Supported File Types

### Text Files (50+ extensions)

- **Code**: .py, .js, .ts, .tsx, .jsx, .c, .h, .cpp, .hpp, .java, .kt, .swift, .go, .rs, .rb, .php, .pl
- **Config**: .json, .yaml, .yml, .toml, .ini, .cfg, .conf, .env
- **Markup**: .md, .rst, .html, .htm, .xml
- **Styles**: .css, .scss, .less
- **Scripts**: .sh, .bash, .zsh, .fish, .bat, .cmd, .ps1, .vbs
- **Data**: .csv, .tsv, .sql, .graphql, .gql
- **Other**: .dockerfile, .makefile, .cmake, .gitignore

### Binary Files

- **PE (Windows)**: .dll, .exe, .sys, .ocx, .drv, .efi
- **ELF (Linux)**: .so, .so.*, .o, .a, executables (no extension)
- **Mach-O (macOS)**: .dylib, .o, .a, executables, .framework

## API Reference

### BatchIOEngine

Main batch I/O engine with cross-platform support.

#### Methods

- `batch_read(patterns, include_binary=True, max_size=None)` → Dict[str, ReadResult]
  - Read all files matching glob patterns in a single directory traversal
  - Auto-detects text vs binary and encoding
  - Uses mmap for files > 1MB

- `batch_write(files, create_dirs=True)` → Dict[str, WriteResult]
  - Write multiple files in sorted order (sequential optimization)
  - Atomic writes via temp file + rename
  - Auto-creates parent directories

- `glob_stat(patterns, compute_hash=False)` → Dict[str, FileInfo]
  - Single directory traversal returns all metadata
  - Optional SHA256 hash computation
  - File type detection without reading content

- `batch_delete(patterns)` → Dict[str, bool]
  - Delete multiple files matching patterns

### BinaryInspector

Binary file analysis supporting PE, ELF, and Mach-O formats.

#### Methods

- `inspect(file_path, deep=False)` → BinaryInfo
  - Analyze a single binary file
  - Deep mode includes section details and version info

- `batch_inspect(paths, deep=False)` → Dict[str, BinaryInfo]
  - Analyze multiple binary files

#### BinaryInfo Fields

- `format`: BinaryFormat (PE, ELF, MACHO, UNKNOWN)
- `architecture`: Architecture (X86, X86_64, ARM, ARM64, MIPS, PPC, UNKNOWN)
- `size`: File size in bytes
- `sha256`, `md5`: File hashes
- `is_64bit`: Whether 64-bit
- `is_executable`, `is_library`: File type flags
- `entry_point`: Entry point address
- `section_count`: Number of sections
- `version_info`: Version strings (PE only)
- `compile_time`: Compilation timestamp (PE only)

### CachedIO

High-level cached I/O interface combining LRU cache and write coalescing.

#### Methods

- `read_file(path, binary=False)` → str | bytes
  - Read with automatic caching
  - Validates cache against file mtime

- `write_file(path, content, binary=False, immediate=False)`
  - Write with optional write coalescing
  - Immediate mode bypasses coalescing

- `flush_writes()` → Tuple[int, int]
  - Flush all pending writes to disk

- `invalidate_cache(path=None)`
  - Invalidate specific file or entire cache

- `stats()` → Dict
  - Get cache and write buffer statistics

- `shutdown()`
  - Stop background threads and flush all writes

## Cross-Platform Support

### Windows
- NTFS optimization tips
- PowerShell batch operations
- PE binary format support
- Path normalization (backslash → forward slash)

### macOS
- APFS optimization
- F_BARRIERFSYNC for durable writes
- Mach-O binary format support
- SMB Client Signing configuration

### Linux
- O_DIRECT support (where applicable)
- fallocate for pre-allocation
- readahead for sequential reads
- sendfile for zero-copy transfers
- ELF binary format support

## Best Practices

### 1. Batch Your Reads
Instead of reading files one by one:
```python
# BAD: N separate reads
for file in file_list:
    content = read(file)

# GOOD: 1 batch read
results = engine.batch_read(["**/*.ts", "**/*.toml"])
```

### 2. Use Write Coalescing for Multiple Writes
```python
# Use CachedIO for write-heavy workloads
cached_io = CachedIO(base_dir=".", flush_interval_ms=1000)

for i in range(100):
    cached_io.write_file(f"output_{i}.txt", content)

# All writes coalesced into 1-2 flush operations
cached_io.flush_writes()
```

### 3. Leverage glob_stat for Directory Scans
```python
# Single traversal gets all metadata
files = engine.glob_stat(["**/*.py"], compute_hash=True)

# Filter by size, type, etc. without additional I/O
large_files = {p: f for p, f in files.items() if f.size > 100000}
```

### 4. Always Shutdown CachedIO
```python
try:
    cached_io = CachedIO()
    # ... do work ...
finally:
    cached_io.shutdown()  # Ensures all writes are flushed
```

### 5. Use Deep Inspection Sparingly
Deep binary analysis reads more of the file. Use `deep=False` (default)
when you only need basic metadata.

## Performance Benchmarks

Benchmarks run on Linux with 100 files × 4KB each:

| Operation | Individual I/O | Batch I/O | Speedup |
|-----------|---------------|-----------|---------|
| Write (100 files) | ~45ms | ~12ms | 3.75x |
| Read (100 files) | ~38ms | ~8ms | 4.75x |
| Glob + Stat | ~25ms | ~5ms | 5.0x |
| Cached Read | ~38ms | ~0.3ms | 127x |

**SSD wear reduction**: ~80-90% compared to random small I/O

## Limitations

- Alpha version: API may change in future releases
- Binary inspection is read-only (no modification)
- Write coalescing adds latency (configurable, default 1s)
- Cache memory usage must be monitored
- Very large files (>1GB) may not benefit from mmap on 32-bit systems

## See Also

- `references/api-reference.md` - Complete API documentation
- `references/performance-guide.md` - Performance tuning guide
- `references/binary-formats.md` - Binary format details

---

**OxygenIO Aggregator v26.0 Alpha 1**
Maintained by GitHub@StarsailsClover
