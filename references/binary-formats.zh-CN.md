# 二进制格式参考 - OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

BinaryInspector支持的二进制文件格式技术参考。

---

## 支持的格式

| 格式 | 平台 | 常见扩展名 |
|------|------|-----------|
| PE (可移植可执行文件) | Windows | .dll, .exe, .sys, .ocx, .drv |
| ELF (可执行与可链接格式) | Linux/Unix | .so, .o, .a, (无扩展名) |
| Mach-O | macOS / iOS | .dylib, .o, .a, (无扩展名) |

---

## PE 格式 (Windows)

### 概述

PE（可移植可执行文件）是Windows的原生可执行格式。
源自COFF（通用对象文件格式）。

### 文件结构

```
DOS头 (64字节)
├── e_magic: "MZ" (0x5A4D)
├── e_lfanew: PE签名偏移
└── ... (DOS存根)

PE签名
└── "PE\0\0" (0x00004550)

COFF文件头 (20字节)
├── Machine: 架构类型
├── NumberOfSections: 节数量
├── TimeDateStamp: 时间戳
├── PointerToSymbolTable: 符号表指针
├── NumberOfSymbols: 符号数量
├── SizeOfOptionalHeader: 可选头大小
└── Characteristics: 特征标志

可选头 (可变大小)
├── Magic: PE32 (0x10B) 或 PE32+ (0x20B)
├── AddressOfEntryPoint: 入口点地址
├── ImageBase: 镜像基址
├── SectionAlignment: 节对齐
├── FileAlignment: 文件对齐
├── ... (Windows特定字段)
└── 数据目录 (16个条目)

节头 (每个40字节)
├── 名称 (8字节)
├── VirtualSize: 虚拟大小
├── VirtualAddress: 虚拟地址
├── SizeOfRawData: 原始数据大小
├── PointerToRawData: 原始数据指针
├── ...
└── Characteristics: 标志

节数据
├── .text (代码)
├── .data (已初始化数据)
├── .rdata (只读数据)
├── .bss (未初始化数据)
├── .idata (导入表)
├── .edata (导出表)
├── .rsrc (资源)
├── .reloc (重定位)
└── ...
```

### 机器类型（架构）

| 值 | 架构 |
|----|------|
| 0x014c | x86 (I386) |
| 0x8664 | x86_64 (AMD64) |
| 0xAA64 | ARM64 (AArch64) |
| 0x01c0 | ARM (ARMv7) |
| 0x01c4 | ARMv7 Thumb |
| 0x01c2 | ARMv7 Thumb-2 |

### 特征标志

| 标志 | 值 | 描述 |
|------|----|------|
| IMAGE_FILE_EXECUTABLE_IMAGE | 0x0002 | 文件是可执行的 |
| IMAGE_FILE_LARGE_ADDRESS_AWARE | 0x0020 | 可处理>2GB地址 |
| IMAGE_FILE_DLL | 0x2000 | 文件是DLL |
| IMAGE_FILE_DEBUG_STRIPPED | 0x0200 | 调试信息已移除 |

### 常见节

| 节 | 描述 | 典型属性 |
|----|------|---------|
| .text | 可执行代码 | 代码、可执行、可读 |
| .data | 已初始化数据 | 数据、可读、可写 |
| .rdata | 只读数据 | 数据、可读 |
| .bss | 未初始化数据 | 数据、可读、可写 |
| .idata | 导入表 | 数据、可读 |
| .edata | 导出表 | 数据、可读 |
| .rsrc | 资源 | 数据、可读 |
| .reloc | 重定位表 | 数据、可读、可丢弃 |
| .pdata | 异常处理 | 数据、可读 |
| .tls | 线程本地存储 | 数据、可读、可写 |

### 版本信息

PE文件可以包含版本信息资源：
- FileVersion（文件版本）
- ProductVersion（产品版本）
- CompanyName（公司名称）
- FileDescription（文件描述）
- LegalCopyright（版权）
- OriginalFilename（原始文件名）
- ProductName（产品名称）

---

## ELF 格式 (Linux/Unix)

### 概述

ELF（可执行与可链接格式）是Linux和大多数类Unix系统的标准可执行格式。

### 文件结构

```
ELF头 (64位52字节，32位52字节)
├── e_ident[16]: 标识
│   ├── 魔数: 0x7f 'E' 'L' 'F'
│   ├── EI_CLASS: 1 = 32位, 2 = 64位
│   ├── EI_DATA: 1 = 小端序, 2 = 大端序
│   ├── EI_VERSION: 1 (当前)
│   └── EI_OSABI: 操作系统/ABI标识
├── e_type: 对象文件类型
├── e_machine: 架构
├── e_version: 版本
├── e_entry: 入口点地址
├── e_phoff: 程序头偏移
├── e_shoff: 节头偏移
├── e_flags: 处理器特定标志
├── e_ehsize: ELF头大小
├── e_phentsize: 程序头条目大小
├── e_phnum: 程序头数量
├── e_shentsize: 节头条目大小
├── e_shnum: 节头数量
└── e_shstrndx: 节名字符串表索引

程序头 (用于执行)
├── PT_LOAD: 可加载段
├── PT_DYNAMIC: 动态链接信息
├── PT_INTERP: 程序解释器
├── PT_NOTE: 辅助信息
└── ...

节头 (用于链接)
├── .text (代码)
├── .data (已初始化数据)
├── .bss (未初始化数据)
├── .symtab (符号表)
├── .strtab (字符串表)
├── .dynsym (动态符号表)
├── .dynstr (动态字符串表)
├── .rel.* (重定位条目)
├── .plt (过程链接表)
├── .got (全局偏移表)
├── .rodata (只读数据)
├── .init / .fini (初始化/结束代码)
└── ...
```

### ELF类型 (e_type)

| 值 | 类型 | 描述 |
|----|------|------|
| 0 | ET_NONE | 无类型 |
| 1 | ET_REL | 可重定位文件 (.o) |
| 2 | ET_EXEC | 可执行文件 |
| 3 | ET_DYN | 共享对象 (.so) |
| 4 | ET_CORE | 核心转储 |

### 机器类型（架构）

| 值 | 架构 |
|----|------|
| 0x03 | x86 (EM_386) |
| 0x3E | x86_64 (EM_X86_64) |
| 0xB7 | ARM64 / AArch64 (EM_AARCH64) |
| 0x28 | ARM (EM_ARM) |
| 0x08 | MIPS (EM_MIPS) |
| 0x14 | PowerPC (EM_PPC) |
| 0x15 | PowerPC 64位 (EM_PPC64) |
| 0xF3 | RISC-V (EM_RISCV) |

### 常见节

| 节 | 描述 |
|----|------|
| .text | 可执行代码 |
| .data | 已初始化数据 |
| .bss | 未初始化数据（加载时零初始化） |
| .rodata | 只读数据 |
| .symtab | 符号表（静态） |
| .strtab | 符号名字符串表 |
| .dynsym | 动态符号表 |
| .dynstr | 动态符号字符串表 |
| .hash | 符号哈希表 |
| .rela.* | 带加数的重定位条目 |
| .rel.* | 不带加数的重定位条目 |
| .plt | 过程链接表 |
| .got | 全局偏移表 |
| .init | 初始化代码 |
| .fini | 结束代码 |
| .eh_frame | 异常处理帧 |
| .comment | 编译器版本信息 |
| .note.* | 备注/元数据 |

---

## Mach-O 格式 (macOS)

### 概述

Mach-O是macOS、iOS、watchOS和tvOS的原生可执行格式。
源自Mach操作系统。

### 文件结构

```
Mach头 (32位28字节，64位32字节)
├── magic: 魔数
├── cputype: CPU类型
├── cpusubtype: CPU子类型
├── filetype: 文件类型
├── ncmds: 加载命令数量
├── sizeofcmds: 所有加载命令大小
└── flags: 标志

加载命令 (可变)
├── LC_SEGMENT / LC_SEGMENT_64: 段定义
│   ├── 段名称
│   ├── VM地址和大小
│   ├── 文件偏移和大小
│   ├── 最大保护
│   ├── 初始保护
│   ├── 节数量
│   └── 节...
├── LC_SYMTAB: 符号表
├── LC_DYSYMTAB: 动态符号表
├── LC_LOAD_DYLIB: 加载共享库
├── LC_ID_DYLIB: 标识为共享库
├── LC_MAIN: 入口点（替代LC_UNIXTHREAD）
├── LC_UNIXTHREAD: Unix线程状态
├── LC_DYLD_INFO / LC_DYLD_INFO_ONLY: Dyld信息
├── LC_CODE_SIGNATURE: 代码签名
├── LC_SEGMENT_SPLIT_INFO: 分段信息
├── LC_FUNCTION_STARTS: 函数起始地址
├── LC_DATA_IN_CODE: 代码中数据条目
└── ... (更多加载命令类型)

段
├── __TEXT: 代码和只读数据
│   ├── __text: 主代码
│   ├── __stubs: 符号存根
│   ├── __cstring: C字符串
│   └── ...
├── __DATA: 读写数据
│   ├── __data: 已初始化数据
│   ├── __bss: 未初始化数据
│   ├── __la_symbol_ptr: 延迟符号指针
│   └── ...
├── __LINKEDIT: 链接器编辑信息
│   ├── 符号表
│   ├── 字符串表
│   ├── 代码签名
│   └── ...
└── ... (其他段)
```

### 魔数

| 魔数 | 描述 |
|------|------|
| 0xFEEDFACE | 32位大端序 |
| 0xFEEDFACF | 64位大端序 |
| 0xCEFAEDFE | 32位小端序 |
| 0xCFFAEDFE | 64位小端序 |
| 0xCAFEBABE | 胖二进制（通用） |

### CPU类型

| 值 | CPU类型 |
|----|---------|
| 0x00000007 | x86 (CPU_TYPE_X86) |
| 0x01000007 | x86_64 (CPU_TYPE_X86_64) |
| 0x0000000C | ARM (CPU_TYPE_ARM) |
| 0x0100000C | ARM64 (CPU_TYPE_ARM64) |
| 0x00000012 | PowerPC (CPU_TYPE_POWERPC) |
| 0x01000012 | PowerPC 64位 |

### 文件类型

| 值 | 类型 | 描述 |
|----|------|------|
| 1 | MH_OBJECT | 可重定位对象文件 (.o) |
| 2 | MH_EXECUTE | 标准可执行文件 |
| 3 | MH_FVMLIB | 固定VM共享库 |
| 4 | MH_CORE | 核心转储 |
| 5 | MH_PRELOAD | 预加载可执行文件 |
| 6 | MH_DYLIB | 动态共享库 (.dylib) |
| 7 | MH_DYLINKER | 动态链接器 |
| 8 | MH_BUNDLE | 包 / 插件 |
| 9 | MH_DYLIB_STUB | 共享库存根 |
| 10 | MH_DSYM | 调试符号 (dSYM) |
| 11 | MH_KEXT_BUNDLE | 内核扩展 |

### 胖二进制（通用二进制）

Mach-O支持包含多个架构切片的"胖"二进制文件：

```
胖头
├── magic: 0xCAFEBABE
└── nfat_arch: 架构数量

胖架构条目
├── cputype: CPU类型
├── cpusubtype: CPU子类型
├── offset: Mach-O数据偏移
├── size: Mach-O数据大小
└── align: 对齐（2的幂）

Mach-O切片1 (例如 x86_64)
Mach-O切片2 (例如 arm64)
...
```

---

## 魔数参考

格式检测快速参考：

| 格式 | 魔数 | 偏移 |
|------|------|------|
| ELF | `\x7fELF` | 0x00 |
| PE (DOS存根) | `MZ` | 0x00 |
| PE签名 | `PE\0\0` | e_lfanew |
| Mach-O 32 LE | `\xce\xfa\xed\xfe` | 0x00 |
| Mach-O 64 LE | `\xcf\xfa\xed\xfe` | 0x00 |
| Mach-O 32 BE | `\xfe\xed\xfa\xce` | 0x00 |
| Mach-O 64 BE | `\xfe\xed\xfa\xcf` | 0x00 |
| Mach-O 胖 | `\xca\xfe\xba\xbe` | 0x00 |

---

## BinaryInspector 深度分析

当向 `inspect()` 传递 `deep=True` 时，会提取以下额外数据：

### PE深度分析
- 带有标志的完整节表
- 版本信息资源（FileVersion、ProductVersion、CompanyName）
- 编译时间戳
- 导入/导出表位置

### ELF深度分析
- 节头表
- 节类型和大小
- 程序头位置

### Mach-O深度分析
- 段加载命令
- 每个段的节计数
- 动态库标识

---

## 限制

### 当前Alpha版本
- 导入/导出符号名称提取有限
- 不支持完整反汇编
- 不支持二进制文件的修改/写入
- 资源解析是基于启发式的（PE）
- 不支持：
  - COFF对象文件 (.obj)
  - OMF格式
  - a.out格式
  - Java .class文件
  - WebAssembly (.wasm)

### 未来计划
- 完整的导入/导出符号枚举
- 从二进制文件中提取字符串
- 依赖树分析
- 校验和验证
- 签名验证

---

## 扩展阅读

- [PE格式规范](https://learn.microsoft.com/zh-cn/windows/win32/debug/pe-format)
- [ELF规范](https://refspecs.linuxfoundation.org/elf/elf.pdf)
- [Mach-O格式参考](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/MachOTopics/0-Introduction/introduction.html)
- [OSDev Wiki - 可执行格式](https://wiki.osdev.org/Executable_Formats)

---

**OxygenIO Aggregator v26.0 Alpha 1**
二进制格式参考 | GitHub@StarsailsClover
