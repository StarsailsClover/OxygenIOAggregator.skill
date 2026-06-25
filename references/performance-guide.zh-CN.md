# 性能调优指南 - OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

优化OxygenIO Aggregator以获得最大性能和最小SSD磨损的指南。

---

## 理解写入放大

### 什么是写入放大？

写入放大系数（WAF）= 实际闪存写入量 / 主机写入量

**示例：** 如果您写入1MB数据，但SSD写入5MB到闪存，则WAF = 5倍。

### 为什么小写入不好

1. **页对齐**：SSD以页（通常4-16KB）写入。小写入会导致读-修改-写循环。
2. **垃圾回收**：在擦除块之前，必须重写有效页。
3. **磨损均衡**：额外写入以在闪存单元之间均匀分布磨损。
4. **文件系统日志**：每次文件操作的元数据写入。

### 典型WAF值

| 工作负载 | WAF |
|----------|-----|
| 顺序大写入 | 1.1 - 1.5 |
| 随机小写入 | 3 - 8 |
| 极端（SQLite、日志文件） | 10 - 20+ |

---

## OxygenIO如何降低WAF

### 1. 批量I/O

**之前（N个单独操作）：**
- N次open()系统调用
- N次read()/write()系统调用
- N次close()系统调用
- N次文件系统日志更新
- N次目录条目更新

**之后（1次批量操作）：**
- 1次目录遍历
- N次文件读/写，但经过优化排序
- 1组摊销的元数据更新
- 顺序访问模式

**WAF减少：约50-70%**

### 2. 写合并

**之前：**
- 1秒内100次小写入
- 100次单独的I/O操作
- 100次日志更新

**之后：**
- 100次写入缓存在内存中
- 每秒1次刷新操作
- 1次日志更新

**WAF减少：约80-95%（对于突发工作负载）**

### 3. 顺序排序

写入前按路径对文件排序。这可以：
- 减少磁盘磁头移动（HDD）
- 提高SSD垃圾回收效率
- 减少文件系统元数据碎片

**性能提升：约10-30%**

### 4. 内存映射文件（mmap）

对于大于1MB的文件，使用mmap进行读取：
- 消除系统调用开销
- 从内核到用户空间的零拷贝
- 操作系统自动处理缓存

**性能提升：大文件3-4倍**

### 5. 原子写入

使用临时文件+重命名模式：
- 减少日志开销（重命名是单个元数据操作）
- 崩溃安全：文件要么是旧的，要么是新的，从不部分
- 无需每次写入后都fsync

**WAF减少：元数据约20-40%**

---

## 配置调优

### 缓存大小调优

```python
# 小缓存（保守，低内存）
cached_io = CachedIO(cache_size_mb=32)

# 中等缓存（平衡）
cached_io = CachedIO(cache_size_mb=128)  # 默认

# 大缓存（最大性能）
cached_io = CachedIO(cache_size_mb=512)
```

**指南：**
- 代码分析：64-128MB通常足够
- 大型项目：256-512MB
- 内存受限：16-32MB

### 写缓冲区调优

```python
# 低延迟（频繁刷新）
cached_io = CachedIO(write_buffer_mb=16, flush_interval_ms=250)

# 平衡
cached_io = CachedIO(write_buffer_mb=64, flush_interval_ms=1000)  # 默认

# 最大吞吐量（不频繁刷新）
cached_io = CachedIO(write_buffer_mb=256, flush_interval_ms=5000)
```

**权衡：**
- 较小的缓冲区 = 较低延迟但更多I/O操作
- 较大的缓冲区 = 较高吞吐量但如果进程崩溃则更多数据风险
- 根据持久性要求调整

### mmap阈值

```python
# 对大于256KB的文件使用mmap
engine = BatchIOEngine(mmap_threshold=256 * 1024)

# 对大于4MB的文件使用mmap（更保守）
engine = BatchIOEngine(mmap_threshold=4 * 1024 * 1024)
```

**何时调整：**
- 较低阈值：许多中等大小文件（100KB-1MB）
- 较高阈值：主要是小文件，mmap开销不值得

---

## 工作负载特定优化

### 代码库分析

**场景：** 读取项目中的所有源文件。

```python
engine = BatchIOEngine(base_dir="./project")

# 单次遍历，先获取元数据
files = engine.glob_stat(["**/*.py", "**/*.ts", "**/*.js"])

# 然后只读取您需要的
small_files = {p: f for p, f in files.items() if f.size < 100000}
results = engine.batch_read(list(small_files.keys()))
```

**为什么这样更好：**
- 1次目录遍历而不是2次
- 读取前过滤，避免读取大文件
- 所有读取在一批中完成

### 批量文件生成

**场景：** 生成许多输出文件。

```python
cached_io = CachedIO(
    base_dir="./output",
    write_buffer_mb=128,
    flush_interval_ms=2000
)

try:
    for i in range(1000):
        content = generate_file_content(i)
        cached_io.write_file(f"output_{i:04d}.txt", content)
    
    # 完成后显式刷新
    cached_io.flush_writes()
finally:
    cached_io.shutdown()
```

**为什么这样更好：**
- 1000次写入合并为约1-5次刷新操作
- 写入经过排序以实现顺序访问
- 原子写入确保没有部分文件

### 二进制文件检查

**场景：** 分析许多DLL/SO文件。

```python
inspector = BinaryInspector()

# 先快速扫描（浅层）
results = inspector.batch_inspect(file_paths, deep=False)

# 然后只对感兴趣的文件进行深度分析
for path, info in results.items():
    if info.format == BinaryFormat.PE and info.is_library:
        deep_info = inspector.inspect(path, deep=True)
        analyze_version_info(deep_info)
```

**为什么这样更好：**
- 浅层检查很快（只读取头部）
- 深度分析很昂贵（解析所有节）
- 只为您关心的文件付出全部代价

---

## 测量性能

### 使用内置基准测试

```bash
python scripts/oxygen_io.py benchmark --num-files 100 --file-size 4096
```

### 自定义基准测试

```python
import time
from scripts.batch_io import BatchIOEngine

engine = BatchIOEngine(base_dir="./test")

# 计时批量写入
start = time.time()
results = engine.batch_write(files)
write_time = time.time() - start

# 计算指标
total_bytes = sum(r.bytes_written for r in results.values() if r.success)
throughput_mbps = total_bytes / write_time / 1024 / 1024

print(f"写入吞吐量: {throughput_mbps:.2f} MB/s")
```

### 监控缓存统计

```python
stats = cached_io.stats()

print(f"缓存命中率估计: ...")
print(f"缓存利用率: {stats['cache']['size_mb'] / stats['cache']['max_size_mb'] * 100:.1f}%")
print(f"写缓冲区待处理: {stats['write_coalescer']['pending_writes']} 个文件")
```

---

## 平台特定技巧

### Linux

1. **使用 `noatime` 挂载选项**：防止访问时间写入
2. **启用TRIM**：`fstrim` 或 `discard` 挂载选项
3. **I/O调度器**：对SSD使用 `mq-deadline` 或 `none`
4. **vm.dirty_ratio**：调整以减少回写频率

```bash
# 检查当前调度器
cat /sys/block/sda/queue/scheduler

# 检查TRIM支持
sudo hdparm -I /dev/sda | grep TRIM
```

### macOS

1. **APFS优化**：写时复制减少了一些写入放大
2. **F_BARRIERFSYNC**：OxygenIO用于持久化写入
3. **禁用SMB签名**（如果安全允许）用于网络驱动器
4. **启用TRIM**：`sudo trimforce enable`

### Windows

1. **NTFS压缩**：可以减少总写入（但有CPU成本）
2. **禁用上次访问时间**：`fsutil behavior set disablelastaccess 1`
3. **启用TRIM**：Windows 7+通常自动启用
4. **电源计划**：使用"高性能"以获得一致的延迟

---

## 常见陷阱

### 1. 忘记关闭CachedIO

```python
# 不好：如果进程退出，写入可能丢失
cached_io = CachedIO()
cached_io.write_file("data.txt", content)
# 进程退出...

# 好：始终关闭
try:
    cached_io = CachedIO()
    # ... 工作 ...
finally:
    cached_io.shutdown()
```

### 2. 太多小批量

```python
# 不好：违背批量处理的目的
for pattern in patterns:
    results = engine.batch_read([pattern])  # N次单独遍历

# 好：一批包含所有模式
results = engine.batch_read(patterns)  # 1次遍历
```

### 3. 读取代码时忽略二进制文件

```python
# 不好：包含.pyc、.so、.dll、图像
results = engine.batch_read(["**/*"])

# 好：只有文本/代码文件
results = engine.batch_read(["**/*.py", "**/*.ts", "**/*.md"])
```

### 4. 过度使用深度二进制检查

```python
# 不好：对所有文件进行深度分析
results = inspector.batch_inspect(paths, deep=True)

# 好：先浅层，需要时再深层
results = inspector.batch_inspect(paths, deep=False)
for path, info in results.items():
    if interesting(info):
        deep = inspector.inspect(path, deep=True)
```

---

## 预期性能提升

| 工作负载 | I/O减少 | 加速比 | WAF减少 |
|----------|---------|--------|---------|
| 100个文件读取 | 减少90%系统调用 | 3-5倍 | 约60% |
| 100个文件写入 | 减少95%操作 | 3-4倍 | 约75% |
| 目录扫描 | 减少90%stat | 4-6倍 | 约80% |
| 缓存读取 | 100%磁盘读取减少 | 50-200倍 | 100% |
| 写合并 | 减少90-99%刷新 | 2-10倍 | 约85-95% |

**实际结果会因以下因素而异：**
- 文件大小分布
- 存储硬件（SSD型号、NVMe与SATA）
- 文件系统（ext4、NTFS、APFS、XFS）
- 系统负载和内存压力

---

## 扩展阅读

- [SSD写入放大解释](https://en.wikipedia.org/wiki/Write_amplification)
- [Linux存储栈文档](https://www.kernel.org/doc/html/latest/block/index.html)
- [APFS和SSD优化](https://developer.apple.com/documentation/file_system)
- [NTFS性能调优](https://learn.microsoft.com/zh-cn/windows-server/administration/performance-tuning/storage/)

---

**OxygenIO Aggregator v26.0 Alpha 1**
性能指南 | GitHub@StarsailsClover
