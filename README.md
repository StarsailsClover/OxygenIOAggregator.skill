# OxygenIO Aggregator (OIA)

High-performance, SSD-friendly batch file I/O engine for AI agents.

## Features

- **Batch Read/Write**: Read/write hundreds of files in one call
- **Write Coalescing**: Merge small writes into sequential I/O
- **LRU Cache**: Hot file caching with size/entry limits
- **Memory-Mapped I/O**: Fast reads for large files (mmap)
- **Atomic Writes**: Temp-file + rename for crash safety
- **Binary Inspection**: Detect PE/ELF/Mach-O formats
- **Cross-Platform**: Windows/macOS/Linux

## Quick Start

```python
from batch_io import BatchIOEngine

engine = BatchIOEngine(base_dir="/project", use_mmap=True, atomic_writes=True)

# Write
engine.batch_write({"main.py": "print('hello')", "util.py": "def helper(): ..."})

# Read
pages = engine.batch_read(["**/*.py"])

# Stats
print(engine.get_stats())
```

## Version

v26.0.0-alpha.2 | Author: StarsailsClover | License: MIT
