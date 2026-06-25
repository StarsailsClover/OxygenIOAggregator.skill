# API 参考 - OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

所有OxygenIO Aggregator模块的完整API文档。

---

## 目录

1. [BatchIOEngine](#batchioengine)
2. [BinaryInspector](#binaryinspector)
3. [CachedIO / SmartCache](#cachedio--smartcache)
4. [数据类](#数据类)
5. [枚举](#枚举)

---

## BatchIOEngine

主批量I/O引擎，支持跨平台文件操作。

### 构造函数

```python
BatchIOEngine(
    base_dir: str = ".",
    atomic_writes: bool = True,
    mmap_threshold: int = 1024 * 1024,  # 1MB
    encoding: str = "utf-8"
)
```

**参数：**
- `base_dir`: 相对路径解析的基础目录
- `atomic_writes`: 使用原子写入模式（临时文件+重命名）
- `mmap_threshold`: 使用mmap的文件大小阈值（字节）
- `encoding`: 默认文本编码

### 方法

#### batch_read()

```python
def batch_read(
    self,
    patterns: List[str],
    include_binary: bool = True,
    max_size: Optional[int] = None
) -> Dict[str, ReadResult]
```

在单次目录遍历中读取所有匹配glob模式的文件。

**参数：**
- `patterns`: glob模式列表（例如 `["**/*.ts", "**/*.toml"]`）
- `include_binary`: 是否包含二进制文件
- `max_size`: 最大读取文件大小（字节），None表示无限制

**返回：** 字典，映射相对路径到 `ReadResult` 对象。

**示例：**
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

按排序顺序写入多个文件，优化顺序I/O。

**参数：**
- `files`: 字典，映射路径到内容（str或bytes）
- `create_dirs`: 自动创建父目录

**返回：** 字典，映射路径到 `WriteResult` 对象。

**示例：**
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

单次目录遍历返回所有匹配文件的元数据。

**参数：**
- `patterns`: glob模式列表
- `compute_hash`: 是否计算SHA256哈希

**返回：** 字典，映射路径到 `FileInfo` 对象。

**示例：**
```python
# 获取所有Python文件及其元数据
files = engine.glob_stat(["**/*.py"], compute_hash=True)

# 过滤大文件
large_files = {p: f for p, f in files.items() if f.size > 100000}
print(f"找到 {len(large_files)} 个大Python文件")
```

#### batch_delete()

```python
def batch_delete(
    self,
    patterns: List[str]
) -> Dict[str, bool]
```

删除匹配glob模式的多个文件。

**参数：**
- `patterns`: glob模式列表

**返回：** 字典，映射路径到成功布尔值。

---

## BinaryInspector

二进制文件分析，支持PE、ELF和Mach-O格式。

### 构造函数

```python
BinaryInspector()
```

无需参数。

### 方法

#### inspect()

```python
def inspect(
    self,
    file_path: str,
    deep: bool = False
) -> BinaryInfo
```

分析单个二进制文件。

**参数：**
- `file_path`: 二进制文件路径
- `deep`: 启用深度分析（较慢，更多详情）

**返回：** `BinaryInfo` 对象，包含文件元数据。

**示例：**
```python
inspector = BinaryInspector()
info = inspector.inspect("/usr/lib/libc.so.6", deep=True)

print(f"格式: {info.format.value}")
print(f"架构: {info.architecture.value}")
print(f"64位: {info.is_64bit}")
print(f"节数: {info.section_count}")
```

#### batch_inspect()

```python
def batch_inspect(
    self,
    paths: List[str],
    deep: bool = False
) -> Dict[str, BinaryInfo]
```

分析多个二进制文件。

**参数：**
- `paths`: 文件路径列表
- `deep`: 启用深度分析

**返回：** 字典，映射路径到 `BinaryInfo` 对象。

---

## CachedIO / SmartCache

高级缓存I/O接口，结合了LRU缓存和写合并。

### 构造函数

```python
CachedIO(
    base_dir: str = ".",
    cache_size_mb: int = 128,
    write_buffer_mb: int = 64,
    flush_interval_ms: int = 1000,
    use_write_coalescing: bool = True
)
```

**参数：**
- `base_dir`: 相对路径的基础目录
- `cache_size_mb`: 最大读取缓存大小（兆字节）
- `write_buffer_mb`: 自动刷新前的写缓冲区大小
- `flush_interval_ms`: 自动刷新前的最大时间
- `use_write_coalescing`: 启用写合并

### 方法

#### read_file()

```python
def read_file(
    self,
    path: str,
    binary: bool = False
) -> Union[str, bytes]
```

读取文件，自动缓存。

**参数：**
- `path`: 文件路径（相对或绝对）
- `binary`: 以二进制（bytes）而非文本读取

**返回：** 文件内容，str或bytes。

**抛出：** 如果文件不存在则抛出 `FileNotFoundError`。

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

写入文件，可选写合并。

**参数：**
- `path`: 文件路径
- `content`: 要写入的内容
- `binary`: 内容是二进制
- `immediate`: 立即写入（不合并）

#### flush_writes()

```python
def flush_writes(self) -> Tuple[int, int]
```

将所有待写入刷新到磁盘。

**返回：** 元组 (写入的文件数, 总写入字节数)。

#### invalidate_cache()

```python
def invalidate_cache(self, path: Optional[str] = None) -> None
```

使缓存条目失效。

**参数：**
- `path`: 要失效的特定路径，或None清除全部

#### stats()

```python
def stats(self) -> Dict[str, Any]
```

获取系统统计信息。

**返回：** 包含缓存和写缓冲区统计的字典。

**示例：**
```python
stats = cached_io.stats()
print(f"缓存条目: {stats['cache']['entries']}")
print(f"缓存大小: {stats['cache']['size_mb']:.2f} MB")
print(f"待写入: {stats['write_coalescer']['pending_writes']}")
```

#### shutdown()

```python
def shutdown(self) -> None
```

干净地关闭缓存I/O系统。
停止后台线程并刷新所有待写入。

**使用完CachedIO后务必调用此方法。**

---

## 数据类

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

## 枚举

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

## 导入路径

所有模块都在 `scripts/` 目录中。

```python
# 从技能根目录
from scripts.batch_io import BatchIOEngine, ReadResult, FileInfo, FileType
from scripts.binary_inspector import BinaryInspector, BinaryInfo, BinaryFormat, Architecture
from scripts.smart_cache import CachedIO, LRUFileCache, WriteCoalescer
```

---

## 错误处理

所有操作都返回带有 `success` 和 `error` 字段的结果对象。
异常在内部捕获并转换为错误消息。

**模式：**
```python
results = engine.batch_read(patterns)

for path, result in results.items():
    if result.success:
        process(result.content)
    else:
        log_error(f"读取失败 {path}: {result.error}")
```

---

**OxygenIO Aggregator v26.0 Alpha 1**
API 参考 | GitHub@StarsailsClover
