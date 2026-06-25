# 源氧读写聚合器 (OIA)

面向 AI Agent 的高性能批量文件 I/O 引擎。

## 核心特性

- 批量读写：一次调用处理数百个文件
- 写合并：小写入合并为顺序 I/O，减少 SSD 损耗
- LRU 缓存：热点文件自动缓存
- 内存映射：大文件 mmap 加速读取
- 原子写入：临时文件 + 重命名，防崩溃丢数据
- 二进制检测：自动识别 PE/ELF/Mach-O 格式
- 跨平台：Windows / macOS / Linux

## 安装

```bash
pip install oxygen-io-aggregator
```

## 版本

v26.0.0-alpha.2 | 作者: StarsailsClover | 协议: MIT
