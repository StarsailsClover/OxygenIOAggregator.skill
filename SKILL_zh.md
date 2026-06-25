---
name: oxygen-io-aggregator
description: 高性能、对SSD友好的文件I/O聚合器技能。当您需要批量读取多个文件（特别是 .ts、.toml、.json、.yaml 等代码/配置文件）、批量写入多个文件、检查二进制文件（.dll、.so、.dylib、.exe），或减少磁盘I/O操作以最小化SSD磨损和写入放大时使用。支持跨平台（Windows/macOS/Linux）文件操作，具备写合并、LRU缓存、内存映射文件和原子写入功能。适用于代码库分析、多文件处理以及减少总I/O操作数至关重要的场景。
metadata:
  version: 26.0.0-alpha.2
  author: GitHub@StarsailsClover
---

# OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

高性能、对SSD友好的文件I/O聚合器，旨在通过减少总I/O操作数同时保持相同的数据吞吐量来最小化磁盘磨损。

## 何时使用

在以下情况下使用此技能：

- 您需要从代码库或项目中**批量读取多个文件**
- 您需要在一次操作中**批量写入多个文件**
- 您需要在不加载全部内容的情况下**检查二进制文件**（.dll、.so、.dylib、.exe）
- 您希望通过频繁的小I/O操作**减少SSD磨损**和写入放大
- 您需要处理Step Assistant无法读取的文件（.ts、.toml、.dll等）
- 您希望**扫描目录**并在一次遍历中获取所有匹配文件的元数据
- 您需要**跨平台**文件操作（Windows/macOS/Linux）

## 核心概念

### 写入放大问题

SSD写入放大（WAF）发生在小型随机写入触发垃圾回收和页对齐写入时，导致实际闪存写入量是主机写入量的3-8倍。这是CodeX CLI磁盘磨损问题的根本原因。

### OxygenIO如何解决

1. **批量I/O**：N次小操作 → 1次大操作
2. **写合并**：缓冲多次写入，批量刷新
3. **顺序排序**：对路径排序以优化磁盘访问模式
4. **内存映射文件**：大文件读取使用mmap（快3-4倍）
5. **原子写入**：临时文件+重命名，减少文件系统日志开销
6. **LRU缓存**：避免重复读取频繁访问的文件

### 性能影响

| 指标 | 单独I/O | OxygenIO批量 | 提升 |
|------|---------|--------------|------|
| 系统调用 | N次 | 1-2次 | 减少约N倍 |
| 写入放大 | 3-8倍 WAF | 1.1-1.5倍 WAF | 磨损减少约70-85% |
| 目录遍历 | N次 | 1次 | 减少约N倍 |
| 缓存命中速度 | - | 约10-100倍 | 亚毫秒级读取 |

## 快速开始

### 批量读取多个文件

```python
from scripts.batch_io import BatchIOEngine

engine = BatchIOEngine(base_dir="/path/to/project")

# 读取所有TypeScript和TOML文件
results = engine.batch_read(["**/*.ts", "**/*.toml"])

for path, result in results.items():
    if result.success:
        print(f"{path}: {result.size} 字节, {result.encoding}")
        # result.content 包含文件内容
```

### 批量写入多个文件

```python
from scripts.batch_io import BatchIOEngine

engine = BatchIOEngine(base_dir="/path/to/project")

files = {
    "src/config.ts": "export const config = { ... }",
    "docs/README.md": "# 项目\n\n...",
    ".env": "API_KEY=xxx\nDEBUG=false"
}

results = engine.batch_write(files, create_dirs=True)
```

### 检查二进制文件

```python
from scripts.binary_inspector import BinaryInspector

inspector = BinaryInspector()
info = inspector.inspect("/path/to/library.dll", deep=True)

print(f"格式: {info.format.value}")
print(f"架构: {info.architecture.value}")
print(f"64位: {info.is_64bit}")
print(f"节数: {info.section_count}")
if info.version_info:
    print(f"版本: {info.version_info.get('FileVersion')}")
```

### 智能缓存I/O

```python
from scripts.smart_cache import CachedIO

cached_io = CachedIO(
    base_dir="/path/to/project",
    cache_size_mb=128,
    write_buffer_mb=64,
    flush_interval_ms=1000
)

# 读取自动缓存
content = cached_io.read_file("src/main.ts")

# 写入合并并批量刷新
cached_io.write_file("src/config.ts", new_config)

# 需要时强制刷新
cached_io.flush_writes()

# 优雅关闭
cached_io.shutdown()
```

## CLI 用法

```bash
# 批量读取
python scripts/oxygen_io.py batch-read "**/*.ts" "**/*.toml" --base-dir ./project

# 批量写入（从JSON文件）
python scripts/oxygen_io.py batch-write files.json --base-dir ./project

# 目录扫描和元数据
python scripts/oxygen_io.py glob-stat "**/*.py" --hash --json

# 检查二进制文件
python scripts/oxygen_io.py inspect ./lib.dll --deep

# 运行基准测试
python scripts/oxygen_io.py benchmark --num-files 100 --file-size 4096

# 版本信息
python scripts/oxygen_io.py version
```

## 支持的文件类型

### 文本文件（50+种扩展名）

- **代码**: .py, .js, .ts, .tsx, .jsx, .c, .h, .cpp, .hpp, .java, .kt, .swift, .go, .rs, .rb, .php, .pl
- **配置**: .json, .yaml, .yml, .toml, .ini, .cfg, .conf, .env
- **标记语言**: .md, .rst, .html, .htm, .xml
- **样式表**: .css, .scss, .less
- **脚本**: .sh, .bash, .zsh, .fish, .bat, .cmd, .ps1, .vbs
- **数据**: .csv, .tsv, .sql, .graphql, .gql
- **其他**: .dockerfile, .makefile, .cmake, .gitignore

### 二进制文件

- **PE (Windows)**: .dll, .exe, .sys, .ocx, .drv, .efi
- **ELF (Linux)**: .so, .so.*, .o, .a, 可执行文件（无扩展名）
- **Mach-O (macOS)**: .dylib, .o, .a, 可执行文件, .framework

## API 参考

### BatchIOEngine

主批量I/O引擎，支持跨平台。

#### 方法

- `batch_read(patterns, include_binary=True, max_size=None)` → Dict[str, ReadResult]
  - 在单次目录遍历中读取所有匹配glob模式的文件
  - 自动检测文本vs二进制和编码
  - 大于1MB的文件使用mmap

- `batch_write(files, create_dirs=True)` → Dict[str, WriteResult]
  - 按排序顺序写入多个文件（顺序优化）
  - 通过临时文件+重命名实现原子写入
  - 自动创建父目录

- `glob_stat(patterns, compute_hash=False)` → Dict[str, FileInfo]
  - 单次目录遍历返回所有元数据
  - 可选SHA256哈希计算
  - 无需读取内容即可检测文件类型

- `batch_delete(patterns)` → Dict[str, bool]
  - 删除匹配模式的多个文件

### BinaryInspector

二进制文件分析，支持PE、ELF和Mach-O格式。

#### 方法

- `inspect(file_path, deep=False)` → BinaryInfo
  - 分析单个二进制文件
  - 深度模式包含节详情和版本信息

- `batch_inspect(paths, deep=False)` → Dict[str, BinaryInfo]
  - 分析多个二进制文件

#### BinaryInfo 字段

- `format`: BinaryFormat (PE, ELF, MACHO, UNKNOWN)
- `architecture`: Architecture (X86, X86_64, ARM, ARM64, MIPS, PPC, UNKNOWN)
- `size`: 文件大小（字节）
- `sha256`, `md5`: 文件哈希
- `is_64bit`: 是否64位
- `is_executable`, `is_library`: 文件类型标志
- `entry_point`: 入口点地址
- `section_count`: 节数量
- `version_info`: 版本字符串（仅限PE）
- `compile_time`: 编译时间戳（仅限PE）

### CachedIO

高级缓存I/O接口，结合了LRU缓存和写合并。

#### 方法

- `read_file(path, binary=False)` → str | bytes
  - 带自动缓存的读取
  - 根据文件mtime验证缓存

- `write_file(path, content, binary=False, immediate=False)`
  - 带可选写合并的写入
  - 立即模式绕过合并

- `flush_writes()` → Tuple[int, int]
  - 将所有待写入刷新到磁盘

- `invalidate_cache(path=None)`
  - 使特定文件或整个缓存失效

- `stats()` → Dict
  - 获取缓存和写缓冲区统计信息

- `shutdown()`
  - 停止后台线程并刷新所有写入

## 跨平台支持

### Windows
- NTFS优化技巧
- PowerShell批量操作
- PE二进制格式支持
- 路径归一化（反斜杠 → 正斜杠）

### macOS
- APFS优化
- F_BARRIERFSYNC持久化写入
- Mach-O二进制格式支持
- SMB客户端签名配置

### Linux
- O_DIRECT支持（如适用）
- fallocate预分配
- readahead顺序读取
- sendfile零拷贝传输
- ELF二进制格式支持

## 最佳实践

### 1. 批量读取
不要逐个读取文件：
```python
# 不好：N次单独读取
for file in file_list:
    content = read(file)

# 好：1次批量读取
results = engine.batch_read(["**/*.ts", "**/*.toml"])
```

### 2. 多次写入使用写合并
```python
# 写入密集型工作负载使用CachedIO
cached_io = CachedIO(base_dir=".", flush_interval_ms=1000)

for i in range(100):
    cached_io.write_file(f"output_{i}.txt", content)

# 所有写入合并为1-2次刷新操作
cached_io.flush_writes()
```

### 3. 利用glob_stat进行目录扫描
```python
# 单次遍历获取所有元数据
files = engine.glob_stat(["**/*.py"], compute_hash=True)

# 按大小、类型等过滤，无需额外I/O
large_files = {p: f for p, f in files.items() if f.size > 100000}
```

### 4. 始终关闭CachedIO
```python
try:
    cached_io = CachedIO()
    # ... 执行工作 ...
finally:
    cached_io.shutdown()  # 确保所有写入都已刷新
```

### 5. 谨慎使用深度检查
深度二进制分析会读取更多文件内容。当您只需要基本元数据时，使用 `deep=False`（默认值）。

## 性能基准

在Linux上运行的基准测试，100个文件 × 每个4KB：

| 操作 | 单独I/O | 批量I/O | 加速比 |
|------|---------|---------|--------|
| 写入（100个文件） | ~45ms | ~12ms | 3.75倍 |
| 读取（100个文件） | ~38ms | ~8ms | 4.75倍 |
| 目录扫描+统计 | ~25ms | ~5ms | 5.0倍 |
| 缓存读取 | ~38ms | ~0.3ms | 127倍 |

**SSD磨损减少**：与随机小I/O相比约80-90%

## 限制

- Alpha版本：API可能在未来版本中更改
- 二进制检查是只读的（不支持修改）
- 写合并增加延迟（可配置，默认1秒）
- 必须监控缓存内存使用情况
- 非常大的文件（>1GB）在32位系统上可能无法从mmap中受益

## 另请参阅

- `references/api-reference.md` - 完整API文档
- `references/performance-guide.md` - 性能调优指南
- `references/binary-formats.md` - 二进制格式详情

---

**OxygenIO Aggregator v26.0 Alpha 1**
维护者 GitHub@StarsailsClover
