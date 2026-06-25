# Binary Format Reference - OxygenIO Aggregator

**v26.0 Alpha 1** | GitHub@StarsailsClover

Technical reference for binary file formats supported by the BinaryInspector.

---

## Supported Formats

| Format | Platform | Common Extensions |
|--------|----------|-------------------|
| PE (Portable Executable) | Windows | .dll, .exe, .sys, .ocx, .drv |
| ELF (Executable and Linkable Format) | Linux/Unix | .so, .o, .a, (no extension) |
| Mach-O | macOS / iOS | .dylib, .o, .a, (no extension) |

---

## PE Format (Windows)

### Overview

PE (Portable Executable) is the native executable format for Windows.
Derived from COFF (Common Object File Format).

### File Structure

```
DOS Header (64 bytes)
├── e_magic: "MZ" (0x5A4D)
├── e_lfanew: Offset to PE signature
└── ... (DOS stub)

PE Signature
└── "PE\0\0" (0x00004550)

COFF File Header (20 bytes)
├── Machine: Architecture type
├── NumberOfSections
├── TimeDateStamp
├── PointerToSymbolTable
├── NumberOfSymbols
├── SizeOfOptionalHeader
└── Characteristics

Optional Header (variable size)
├── Magic: PE32 (0x10B) or PE32+ (0x20B)
├── AddressOfEntryPoint
├── ImageBase
├── SectionAlignment
├── FileAlignment
├── ... (Windows-specific fields)
└── Data Directories (16 entries)

Section Headers (40 bytes each)
├── Name (8 bytes)
├── VirtualSize
├── VirtualAddress
├── SizeOfRawData
├── PointerToRawData
├── ...
└── Characteristics (flags)

Section Data
├── .text (code)
├── .data (initialized data)
├── .rdata (read-only data)
├── .bss (uninitialized data)
├── .idata (imports)
├── .edata (exports)
├── .rsrc (resources)
├── .reloc (relocations)
└── ...
```

### Machine Types (Architectures)

| Value | Architecture |
|-------|-------------|
| 0x014c | x86 (I386) |
| 0x8664 | x86_64 (AMD64) |
| 0xAA64 | ARM64 (AArch64) |
| 0x01c0 | ARM (ARMv7) |
| 0x01c4 | ARMv7 Thumb |
| 0x01c2 | ARMv7 Thumb-2 |

### Characteristics Flags

| Flag | Value | Description |
|------|-------|-------------|
| IMAGE_FILE_EXECUTABLE_IMAGE | 0x0002 | File is executable |
| IMAGE_FILE_LARGE_ADDRESS_AWARE | 0x0020 | Can handle >2GB addresses |
| IMAGE_FILE_DLL | 0x2000 | File is a DLL |
| IMAGE_FILE_DEBUG_STRIPPED | 0x0200 | Debug info removed |

### Common Sections

| Section | Description | Typical Attributes |
|---------|-------------|-------------------|
| .text | Executable code | Code, Executable, Readable |
| .data | Initialized data | Data, Readable, Writable |
| .rdata | Read-only data | Data, Readable |
| .bss | Uninitialized data | Data, Readable, Writable |
| .idata | Import table | Data, Readable |
| .edata | Export table | Data, Readable |
| .rsrc | Resources | Data, Readable |
| .reloc | Relocation table | Data, Readable, Discardable |
| .pdata | Exception handling | Data, Readable |
| .tls | Thread-local storage | Data, Readable, Writable |

### Version Information

PE files can contain version info resources:
- FileVersion
- ProductVersion
- CompanyName
- FileDescription
- LegalCopyright
- OriginalFilename
- ProductName

---

## ELF Format (Linux/Unix)

### Overview

ELF (Executable and Linkable Format) is the standard executable format
for Linux and most Unix-like systems.

### File Structure

```
ELF Header (52 bytes for 64-bit, 52 bytes for 32-bit)
├── e_ident[16]: Identification
│   ├── Magic: 0x7f 'E' 'L' 'F'
│   ├── EI_CLASS: 1 = 32-bit, 2 = 64-bit
│   ├── EI_DATA: 1 = little-endian, 2 = big-endian
│   ├── EI_VERSION: 1 (current)
│   └── EI_OSABI: OS/ABI identification
├── e_type: Object file type
├── e_machine: Architecture
├── e_version: Version
├── e_entry: Entry point address
├── e_phoff: Program header offset
├── e_shoff: Section header offset
├── e_flags: Processor-specific flags
├── e_ehsize: ELF header size
├── e_phentsize: Program header entry size
├── e_phnum: Number of program headers
├── e_shentsize: Section header entry size
├── e_shnum: Number of section headers
└── e_shstrndx: Section name string table index

Program Headers (for execution)
├── PT_LOAD: Loadable segment
├── PT_DYNAMIC: Dynamic linking info
├── PT_INTERP: Program interpreter
├── PT_NOTE: Auxiliary info
└── ...

Section Headers (for linking)
├── .text (code)
├── .data (initialized data)
├── .bss (uninitialized data)
├── .symtab (symbol table)
├── .strtab (string table)
├── .dynsym (dynamic symbol table)
├── .dynstr (dynamic string table)
├── .rel.* (relocation entries)
├── .plt (procedure linkage table)
├── .got (global offset table)
├── .rodata (read-only data)
├── .init / .fini (init/fini code)
└── ...
```

### ELF Types (e_type)

| Value | Type | Description |
|-------|------|-------------|
| 0 | ET_NONE | No type |
| 1 | ET_REL | Relocatable file (.o) |
| 2 | ET_EXEC | Executable file |
| 3 | ET_DYN | Shared object (.so) |
| 4 | ET_CORE | Core dump |

### Machine Types (Architectures)

| Value | Architecture |
|-------|-------------|
| 0x03 | x86 (EM_386) |
| 0x3E | x86_64 (EM_X86_64) |
| 0xB7 | ARM64 / AArch64 (EM_AARCH64) |
| 0x28 | ARM (EM_ARM) |
| 0x08 | MIPS (EM_MIPS) |
| 0x14 | PowerPC (EM_PPC) |
| 0x15 | PowerPC 64-bit (EM_PPC64) |
| 0xF3 | RISC-V (EM_RISCV) |

### Common Sections

| Section | Description |
|---------|-------------|
| .text | Executable code |
| .data | Initialized data |
| .bss | Uninitialized data (zero-initialized at load) |
| .rodata | Read-only data |
| .symtab | Symbol table (static) |
| .strtab | String table for symbol names |
| .dynsym | Dynamic symbol table |
| .dynstr | String table for dynamic symbols |
| .hash | Symbol hash table |
| .rela.* | Relocation entries with addends |
| .rel.* | Relocation entries without addends |
| .plt | Procedure Linkage Table |
| .got | Global Offset Table |
| .init | Initialization code |
| .fini | Finalization code |
| .eh_frame | Exception handling frames |
| .comment | Compiler version info |
| .note.* | Notes/metadata |

---

## Mach-O Format (macOS)

### Overview

Mach-O is the native executable format for macOS, iOS, watchOS, and tvOS.
Derived from the Mach operating system.

### File Structure

```
Mach Header (28 bytes for 32-bit, 32 bytes for 64-bit)
├── magic: Magic number
├── cputype: CPU type
├── cpusubtype: CPU subtype
├── filetype: File type
├── ncmds: Number of load commands
├── sizeofcmds: Size of all load commands
└── flags: Flags

Load Commands (variable)
├── LC_SEGMENT / LC_SEGMENT_64: Segment definition
│   ├── Segment name
│   ├── VM address and size
│   ├── File offset and size
│   ├── Maximum protection
│   ├── Initial protection
│   ├── Number of sections
│   └── Sections...
├── LC_SYMTAB: Symbol table
├── LC_DYSYMTAB: Dynamic symbol table
├── LC_LOAD_DYLIB: Load a shared library
├── LC_ID_DYLIB: Identify as shared library
├── LC_MAIN: Entry point (replaces LC_UNIXTHREAD)
├── LC_UNIXTHREAD: Unix thread state
├── LC_DYLD_INFO / LC_DYLD_INFO_ONLY: Dyld info
├── LC_CODE_SIGNATURE: Code signature
├── LC_SEGMENT_SPLIT_INFO: Split seg info
├── LC_FUNCTION_STARTS: Function start addresses
├── LC_DATA_IN_CODE: Data-in-code entries
└── ... (many more load command types)

Segments
├── __TEXT: Code and read-only data
│   ├── __text: Main code
│   ├── __stubs: Symbol stubs
│   ├── __cstring: C strings
│   └── ...
├── __DATA: Read-write data
│   ├── __data: Initialized data
│   ├── __bss: Uninitialized data
│   ├── __la_symbol_ptr: Lazy symbol pointers
│   └── ...
├── __LINKEDIT: Linker edit info
│   ├── Symbol table
│   ├── String table
│   ├── Code signature
│   └── ...
└── ... (other segments)
```

### Magic Numbers

| Magic | Description |
|-------|-------------|
| 0xFEEDFACE | 32-bit big-endian |
| 0xFEEDFACF | 64-bit big-endian |
| 0xCEFAEDFE | 32-bit little-endian |
| 0xCFFAEDFE | 64-bit little-endian |
| 0xCAFEBABE | Fat binary (universal) |

### CPU Types

| Value | CPU Type |
|-------|----------|
| 0x00000007 | x86 (CPU_TYPE_X86) |
| 0x01000007 | x86_64 (CPU_TYPE_X86_64) |
| 0x0000000C | ARM (CPU_TYPE_ARM) |
| 0x0100000C | ARM64 (CPU_TYPE_ARM64) |
| 0x00000012 | PowerPC (CPU_TYPE_POWERPC) |
| 0x01000012 | PowerPC 64-bit |

### File Types

| Value | Type | Description |
|-------|------|-------------|
| 1 | MH_OBJECT | Relocatable object file (.o) |
| 2 | MH_EXECUTE | Standard executable |
| 3 | MH_FVMLIB | Fixed VM shared library |
| 4 | MH_CORE | Core dump |
| 5 | MH_PRELOAD | Preloaded executable |
| 6 | MH_DYLIB | Dynamic shared library (.dylib) |
| 7 | MH_DYLINKER | Dynamic linker |
| 8 | MH_BUNDLE | Bundle / plugin |
| 9 | MH_DYLIB_STUB | Shared library stub |
| 10 | MH_DSYM | Debug symbols (dSYM) |
| 11 | MH_KEXT_BUNDLE | Kernel extension |

### Fat Binaries (Universal Binaries)

Mach-O supports "fat" binaries containing multiple architecture slices:

```
Fat Header
├── magic: 0xCAFEBABE
└── nfat_arch: Number of architectures

Fat Architecture Entries
├── cputype: CPU type
├── cpusubtype: CPU subtype
├── offset: Offset to Mach-O data
├── size: Size of Mach-O data
└── align: Alignment (power of 2)

Mach-O Slice 1 (e.g., x86_64)
Mach-O Slice 2 (e.g., arm64)
...
```

---

## Magic Number Reference

Quick reference for format detection:

| Format | Magic | Offset |
|--------|-------|--------|
| ELF | `\x7fELF` | 0x00 |
| PE (DOS stub) | `MZ` | 0x00 |
| PE signature | `PE\0\0` | e_lfanew |
| Mach-O 32 LE | `\xce\xfa\xed\xfe` | 0x00 |
| Mach-O 64 LE | `\xcf\xfa\xed\xfe` | 0x00 |
| Mach-O 32 BE | `\xfe\xed\xfa\xce` | 0x00 |
| Mach-O 64 BE | `\xfe\xed\xfa\xcf` | 0x00 |
| Mach-O Fat | `\xca\xfe\xba\xbe` | 0x00 |

---

## BinaryInspector Deep Analysis

When `deep=True` is passed to `inspect()`, the following additional data is extracted:

### PE Deep Analysis
- Full section table with flags
- Version info resources (FileVersion, ProductVersion, CompanyName)
- Compilation timestamp
- Import/Export table locations

### ELF Deep Analysis
- Section header table
- Section types and sizes
- Program header locations

### Mach-O Deep Analysis
- Segment load commands
- Section counts per segment
- Dylib identification

---

## Limitations

### Current Alpha Version
- Import/Export symbol name extraction is limited
- Full disassembly is not supported
- No modification/writing of binary files
- Resource parsing is heuristic-based (PE)
- No support for:
  - COFF object files (.obj)
  - OMF format
  - a.out format
  - Java .class files
  - WebAssembly (.wasm)

### Future Plans
- Full import/export symbol enumeration
- String extraction from binaries
- Dependency tree analysis
- Checksum verification
- Signature validation

---

## Further Reading

- [PE Format Specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
- [ELF Specification](https://refspecs.linuxfoundation.org/elf/elf.pdf)
- [Mach-O Format Reference](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/MachOTopics/0-Introduction/introduction.html)
- [OSDev Wiki - Executable Formats](https://wiki.osdev.org/Executable_Formats)

---

**OxygenIO Aggregator v26.0 Alpha 1**
Binary Format Reference | GitHub@StarsailsClover
