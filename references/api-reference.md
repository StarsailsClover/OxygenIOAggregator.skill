# API Reference - OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

Complete API documentation for all OxygenIO Aggregator modules.

---

## Table of Contents

1. [BatchIOEngine](#batchioengine)
2. [BinaryInspector](#binaryinspector)
3. [CachedIO / SmartCache](#cachedio--smartcache)
4. [Data Classes](#data-classes)
5. [Enums](#enums)

---

## BatchIOEngine

Main batch I/O engine with cross-platform file operations.

### Constructor

```python
BatchIOEngine(
    base_dir: str = ".",
    atomic_writes: bool = True,
    mmap_threshold: int = 1024 * 1024,  # 1MB
    encoding: str = "utf-8"
)
```

**Parameters:**
- `base_dir`: Base directory for relative path resolution
- `atomic_writes`: Use atomic write pattern (temp file + rename)
- `mmap_threshold`: File size threshold for using mmap (bytes)
- `encoding`: Default text encoding

### Methods

#### batch_read()

```python
def batch_read(
    self,
    patterns: List[str],
    include_binary: bool = True,
    max_size: Optional[int] = None
) -> Dict[str, ReadResult]
```

Read all files matching glob patterns in a single directory traversal.

**Parameters:**
- `patterns`: List of glob patterns (e.g., `["**/*.ts", "**/*.toml"]`)
- `include_binary`: Whether to include binary files
- `max_size`: Maximum file size to read (bytes), None for no limit

**Returns:** Dictionary mapping relative paths to `ReadResult` objects.

**Example:**
```python
engine = BatchIOEngine(base_dir="./src")
results = engine.batch_read(["**/*.ts", "**/*.tsx"], max_size=500000)

for path, result in results.items():
    if result.success and result.file_type == FileType.TEXT:
        process_file(path, result.content)
```

#### batch_write()

```python
def batch_write(
    self,
    files: Dict[str, Union[str, bytes]],
    create_dirs: bool = True
) -> Dict[str, WriteResult]
```

Write multiple files in sorted order for sequential I/O optimization.

**Parameters:**
- `files`: Dictionary mapping paths to content (str or bytes)
- `create_dirs`: Auto-create parent directories

**Returns:** Dictionary mapping paths to `WriteResult` objects.

**Example:**
```python
files = {
    "config/app.toml": "[settings]\ndebug = true",
    "src/main.ts": "console.log('hello');",
    ".env": "API_KEY=secret"
}

results = engine.batch_write(files, create_dirs=True)
```

#### glob_stat()

```python
def glob_stat(
    self,
    patterns: List[str],
    compute_hash: bool = False
) -> Dict[str, FileInfo]
```

Single directory traversal returning metadata for all matching files.

**Parameters:**
- `patterns`: List of glob patterns
- `compute_hash`: Whether to compute SHA256 hashes

**Returns:** Dictionary mapping paths to `FileInfo` objects.

**Example:**
```python
# Get all Python files with their metadata
files = engine.glob_stat(["**/*.py"], compute_hash=True)

# Filter large files
large_files = {p: f for p, f in files.items() if f.size > 100000}
print(f"Found {len(large_files)} large Python files")
```

#### batch_delete()

```python
def batch_delete(
    self,
    patterns: List[str]
) -> Dict[str, bool]
```

Delete multiple files matching glob patterns.

**Parameters:**
- `patterns`: List of glob patterns

**Returns:** Dictionary mapping paths to success booleans.

---

## BinaryInspector

Binary file analysis supporting PE, ELF, and Mach-O formats.

### Constructor

```python
BinaryInspector()
```

No parameters required.

### Methods

#### inspect()

```python
def inspect(
    self,
    file_path: str,
    deep: bool = False
) -> BinaryInfo
```

Analyze a single binary file.

**Parameters:**
- `file_path`: Path to the binary file
- `deep`: Enable deep analysis (slower, more details)

**Returns:** `BinaryInfo` object with file metadata.

**Example:**
```python
inspector = BinaryInspector()
info = inspector.inspect("/usr/lib/libc.so.6", deep=True)

print(f"Format: {info.format.value}")
print(f"Architecture: {info.architecture.value}")
print(f"64-bit: {info.is_64bit}")
print(f"Sections: {info.section_count}")
```

#### batch_inspect()

```python
def batch_inspect(
    self,
    paths: List[str],
    deep: bool = False
) -> Dict[str, BinaryInfo]
```

Analyze multiple binary files.

**Parameters:**
- `paths`: List of file paths
- `deep`: Enable deep analysis

**Returns:** Dictionary mapping paths to `BinaryInfo` objects.

---

## CachedIO / SmartCache

High-level cached I/O interface combining LRU cache and write coalescing.

### Constructor

```python
CachedIO(
    base_dir: str = ".",
    cache_size_mb: int = 128,
    write_buffer_mb: int = 64,
    flush_interval_ms: int = 1000,
    use_write_coalescing: bool = True
)
```

**Parameters:**
- `base_dir`: Base directory for relative paths
- `cache_size_mb`: Maximum read cache size in megabytes
- `write_buffer_mb`: Write buffer size before auto-flush
- `flush_interval_ms`: Maximum time before auto-flush
- `use_write_coalescing`: Enable write coalescing

### Methods

#### read_file()

```python
def read_file(
    self,
    path: str,
    binary: bool = False
) -> Union[str, bytes]
```

Read a file with automatic caching.

**Parameters:**
- `path`: File path (relative or absolute)
- `binary`: Read as binary (bytes) instead of text

**Returns:** File content as str or bytes.

**Raises:** `FileNotFoundError` if file doesn't exist.

#### write_file()

```python
def write_file(
    self,
    path: str,
    content: Union[str, bytes],
    binary: bool = False,
    immediate: bool = False
) -> None
```

Write a file with optional write coalescing.

**Parameters:**
- `path`: File path
- `content`: Content to write
- `binary`: Content is binary
- `immediate`: Write immediately (don't coalesce)

#### flush_writes()

```python
def flush_writes(self) -> Tuple[int, int]
```

Flush all pending writes to disk.

**Returns:** Tuple of (files_written, total_bytes_written).

#### invalidate_cache()

```python
def invalidate_cache(self, path: Optional[str] = None) -> None
```

Invalidate cache entries.

**Parameters:**
- `path`: Specific path to invalidate, or None to clear all

#### stats()

```python
def stats(self) -> Dict[str, Any]
```

Get system statistics.

**Returns:** Dictionary with cache and write buffer stats.

**Example:**
```python
stats = cached_io.stats()
print(f"Cache entries: {stats['cache']['entries']}")
print(f"Cache size: {stats['cache']['size_mb']:.2f} MB")
print(f"Pending writes: {stats['write_coalescer']['pending_writes']}")
```

#### shutdown()

```python
def shutdown(self) -> None
```

Shut down the cached I/O system cleanly.
Stops background threads and flushes all pending writes.

**Always call this when done using CachedIO.**

---

## Data Classes

### ReadResult

```python
@dataclass
class ReadResult:
    path: str
    success: bool
    file_type: FileType
    content: Optional[str]
    binary_content: Optional[bytes]
    size: int
    encoding: Optional[str]
    error: Optional[str]
    read_method: str  # "standard", "mmap", "cached"
```

### WriteResult

```python
@dataclass
class WriteResult:
    path: str
    success: bool
    bytes_written: int
    atomic: bool
    error: Optional[str]
```

### FileInfo

```python
@dataclass
class FileInfo:
    path: str
    size: int
    mtime: float
    file_type: FileType
    encoding: Optional[str]
    sha256: Optional[str]
    permissions: Optional[int]
    error: Optional[str]
```

### BinaryInfo

```python
@dataclass
class BinaryInfo:
    path: str
    format: BinaryFormat
    architecture: Architecture
    size: int
    sha256: str
    md5: str
    is_64bit: bool
    is_executable: bool
    is_library: bool
    entry_point: Optional[int]
    section_count: int
    sections: List[Dict[str, Any]]
    imports: List[str]
    exports: List[str]
    dependencies: List[str]
    version_info: Optional[Dict[str, str]]
    compile_time: Optional[str]
    error: Optional[str]
```

### CacheEntry

```python
@dataclass
class CacheEntry:
    path: str
    content: Union[str, bytes]
    size: int
    mtime: float
    access_time: float
    access_count: int
    is_dirty: bool
    is_text: bool
```

---

## Enums

### FileType

```python
class FileType(Enum):
    TEXT = "text"
    BINARY = "binary"
    UNKNOWN = "unknown"
```

### BinaryFormat

```python
class BinaryFormat(Enum):
    PE = "pe"
    ELF = "elf"
    MACHO = "mach-o"
    UNKNOWN = "unknown"
```

### Architecture

```python
class Architecture(Enum):
    X86 = "x86"
    X86_64 = "x86_64"
    ARM = "arm"
    ARM64 = "arm64"
    MIPS = "mips"
    PPC = "powerpc"
    PPC64 = "powerpc64"
    UNKNOWN = "unknown"
```

### PlatformType

```python
class PlatformType(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    OTHER = "other"
```

---

## Import Paths

All modules are in the `scripts/` directory.

```python
# From the skill root directory
from scripts.batch_io import BatchIOEngine, ReadResult, FileInfo, FileType
from scripts.binary_inspector import BinaryInspector, BinaryInfo, BinaryFormat, Architecture
from scripts.smart_cache import CachedIO, LRUFileCache, WriteCoalescer
```

---

## Error Handling

All operations return result objects with `success` and `error` fields.
Exceptions are caught internally and converted to error messages.

**Pattern:**
```python
results = engine.batch_read(patterns)

for path, result in results.items():
    if result.success:
        process(result.content)
    else:
        log_error(f"Failed to read {path}: {result.error}")
```

---

**OxygenIO Aggregator v26.0 Alpha 1**
API Reference | GitHub@StarsailsClover
