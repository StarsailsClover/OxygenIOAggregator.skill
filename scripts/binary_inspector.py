#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenIO Aggregator - Binary File Inspector
GitHub@StarsailsClover
v26.0 Alpha 1

Cross-platform binary file analyzer supporting PE (Windows DLL/EXE),
ELF (Linux .so), and Mach-O (macOS .dylib) formats.
Provides structured metadata extraction without loading full file content.
"""

import struct
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class BinaryFormat(Enum):
    PE = "pe"           # Windows PE32/PE32+ (DLL, EXE, SYS, etc.)
    ELF = "elf"         # Linux ELF (.so, .o, executable)
    MACHO = "mach-o"    # macOS Mach-O (.dylib, .o, executable)
    UNKNOWN = "unknown"


class Architecture(Enum):
    X86 = "x86"
    X86_64 = "x86_64"
    ARM = "arm"
    ARM64 = "arm64"
    MIPS = "mips"
    PPC = "powerpc"
    PPC64 = "powerpc64"
    UNKNOWN = "unknown"


@dataclass
class BinaryInfo:
    """Structured information about a binary file."""
    path: str
    format: BinaryFormat
    architecture: Architecture
    size: int
    sha256: str
    md5: str
    is_64bit: bool = False
    is_executable: bool = False
    is_library: bool = False
    entry_point: Optional[int] = None
    section_count: int = 0
    sections: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    version_info: Optional[Dict[str, str]] = None
    compile_time: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the inspection was successful (no error)."""
        return self.error is None


class BinaryInspector:
    """
    Binary file inspector supporting multiple formats.
    
    Features:
    - PE (Portable Executable): DLL, EXE, SYS, OCX
    - ELF (Executable and Linkable Format): .so, executables, .o
    - Mach-O: .dylib, executables, .o
    - Architecture detection
    - Import/Export symbol extraction (limited)
    - Version info extraction (PE)
    - Hash computation
    """
    
    # Magic numbers for format detection
    MAGIC_PE = b'PE\x00\x00'
    MAGIC_MZ = b'MZ'  # DOS header, PE starts with MZ
    MAGIC_ELF = b'\x7fELF'
    MAGIC_MACHO_32 = b'\xfe\xed\xfa\xce'  # 32-bit big-endian
    MAGIC_MACHO_64 = b'\xfe\xed\xfa\xcf'  # 64-bit big-endian
    MAGIC_MACHO_32_LE = b'\xce\xfa\xed\xfe'  # 32-bit little-endian
    MAGIC_MACHO_64_LE = b'\xcf\xfa\xed\xfe'  # 64-bit little-endian
    MAGIC_FAT = b'\xca\xfe\xba\xbe'  # Universal binary fat header
    
    def __init__(self):
        pass
    
    def inspect(self, file_path: str, deep: bool = False) -> BinaryInfo:
        """
        Inspect a binary file and return structured information.
        
        Args:
            file_path: Path to the binary file
            deep: Whether to perform deep analysis (slower, more details)
            
        Returns:
            BinaryInfo object with file metadata
        """
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return BinaryInfo(
                path=str(path),
                format=BinaryFormat.UNKNOWN,
                architecture=Architecture.UNKNOWN,
                size=0,
                sha256="",
                md5="",
                error=f"File not found: {file_path}"
            )

        try:
            size = path.stat().st_size
        except OSError as e:
            return BinaryInfo(
                path=str(path),
                format=BinaryFormat.UNKNOWN,
                architecture=Architecture.UNKNOWN,
                size=0,
                sha256="",
                md5="",
                error=f"Cannot stat file: {str(e)}"
            )

        # Compute hashes
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()

        try:
            with open(path, 'rb') as f:
                # Read first 4096 bytes for format detection
                header = f.read(4096)

                # Compute hashes while reading
                f.seek(0)
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    md5_hash.update(chunk)
                    sha256_hash.update(chunk)
        except OSError as e:
            return BinaryInfo(
                path=str(path),
                format=BinaryFormat.UNKNOWN,
                architecture=Architecture.UNKNOWN,
                size=size,
                sha256="",
                md5="",
                error=f"Cannot read file: {str(e)}"
            )

        info = BinaryInfo(
            path=str(path),
            format=BinaryFormat.UNKNOWN,
            architecture=Architecture.UNKNOWN,
            size=size,
            sha256=sha256_hash.hexdigest(),
            md5=md5_hash.hexdigest()
        )

        # Detect format
        fmt = self._detect_format(header)
        info.format = fmt

        # Parse based on format
        try:
            if fmt == BinaryFormat.PE:
                self._parse_pe(path, header, info, deep)
            elif fmt == BinaryFormat.ELF:
                self._parse_elf(path, header, info, deep)
            elif fmt == BinaryFormat.MACHO:
                self._parse_macho(path, header, info, deep)
        except Exception as e:
            info.error = f"Parse error: {str(e)}"

        return info
    
    def _detect_format(self, header: bytes) -> BinaryFormat:
        """Detect binary format from magic numbers."""
        # Check ELF
        if header[:4] == self.MAGIC_ELF:
            return BinaryFormat.ELF
        
        # Check Mach-O
        if (header[:4] in (self.MAGIC_MACHO_32, self.MAGIC_MACHO_64,
                           self.MAGIC_MACHO_32_LE, self.MAGIC_MACHO_64_LE,
                           self.MAGIC_FAT)):
            return BinaryFormat.MACHO
        
        # Check PE (starts with MZ DOS header)
        if header[:2] == self.MAGIC_MZ:
            # Check if PE signature exists
            if len(header) > 0x3C + 4:
                pe_offset = struct.unpack_from('<I', header, 0x3C)[0]
                if pe_offset + 4 <= len(header):
                    if header[pe_offset:pe_offset+4] == self.MAGIC_PE:
                        return BinaryFormat.PE
            # Even without PE signature, MZ is Windows/DOS
            return BinaryFormat.PE
        
        return BinaryFormat.UNKNOWN
    
    def _parse_pe(self, path: Path, header: bytes, info: BinaryInfo, deep: bool):
        """Parse PE (Portable Executable) format."""
        # Read DOS header to get PE offset
        pe_offset = struct.unpack_from('<I', header, 0x3C)[0]
        
        # Read PE signature and COFF header
        pe_sig = header[pe_offset:pe_offset+4]
        if pe_sig != self.MAGIC_PE:
            info.error = "Invalid PE signature"
            return
        
        coff_offset = pe_offset + 4
        
        # COFF File Header
        machine = struct.unpack_from('<H', header, coff_offset)[0]
        num_sections = struct.unpack_from('<H', header, coff_offset + 2)[0]
        timestamp = struct.unpack_from('<I', header, coff_offset + 4)[0]
        
        info.section_count = num_sections
        
        # Architecture detection
        if machine == 0x8664:  # AMD64
            info.architecture = Architecture.X86_64
            info.is_64bit = True
        elif machine == 0x014c:  # I386
            info.architecture = Architecture.X86
            info.is_64bit = False
        elif machine == 0xAA64:  # ARM64
            info.architecture = Architecture.ARM64
            info.is_64bit = True
        elif machine == 0x01c0:  # ARM
            info.architecture = Architecture.ARM
            info.is_64bit = False
        else:
            info.architecture = Architecture.UNKNOWN
        
        # Optional header
        opt_header_offset = coff_offset + 20
        if len(header) > opt_header_offset + 2:
            magic = struct.unpack_from('<H', header, opt_header_offset)[0]
            
            if magic == 0x20B:  # PE32+
                info.is_64bit = True
                # PE32+ optional header
                if len(header) > opt_header_offset + 16 + 8:
                    info.entry_point = struct.unpack_from('<I', header, opt_header_offset + 16)[0]
                # Check if DLL
                if len(header) > opt_header_offset + 20 + 2:
                    characteristics = struct.unpack_from('<H', header, opt_header_offset + 20)[0]
                    info.is_library = bool(characteristics & 0x2000)  # IMAGE_FILE_DLL
                    info.is_executable = bool(characteristics & 0x0002)  # IMAGE_FILE_EXECUTABLE_IMAGE
                
            elif magic == 0x10B:  # PE32
                info.is_64bit = False
                # PE32 optional header
                if len(header) > opt_header_offset + 16 + 4:
                    info.entry_point = struct.unpack_from('<I', header, opt_header_offset + 16)[0]
                # Check if DLL
                if len(header) > opt_header_offset + 20 + 2:
                    characteristics = struct.unpack_from('<H', header, opt_header_offset + 20)[0]
                    info.is_library = bool(characteristics & 0x2000)
                    info.is_executable = bool(characteristics & 0x0002)
        
        # Compile timestamp
        if timestamp > 0:
            import datetime
            try:
                info.compile_time = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).isoformat()
            except Exception:
                pass
        
        # Deep analysis: sections, imports, exports
        if deep:
            self._parse_pe_sections(path, pe_offset, num_sections, info)
            self._parse_pe_version_info(path, header, pe_offset, info)
    
    def _parse_pe_sections(self, path: Path, pe_offset: int, num_sections: int, info: BinaryInfo):
        """Parse PE section headers."""
        try:
            with open(path, 'rb') as f:
                # Section headers start after optional header
                # First get size of optional header
                f.seek(pe_offset + 4 + 16)  # COFF header: SizeOfOptionalHeader
                opt_header_size = struct.unpack('<H', f.read(2))[0]
                
                section_table_offset = pe_offset + 4 + 20 + opt_header_size
                f.seek(section_table_offset)
                
                for i in range(min(num_sections, 96)):  # Limit to 96 sections
                    section_header = f.read(40)
                    if len(section_header) < 40:
                        break
                    
                    name = section_header[:8].rstrip(b'\x00').decode('ascii', errors='replace')
                    virtual_size = struct.unpack_from('<I', section_header, 8)[0]
                    virtual_addr = struct.unpack_from('<I', section_header, 12)[0]
                    raw_size = struct.unpack_from('<I', section_header, 16)[0]
                    raw_offset = struct.unpack_from('<I', section_header, 20)[0]
                    characteristics = struct.unpack_from('<I', section_header, 36)[0]
                    
                    # Determine section characteristics
                    flags = []
                    if characteristics & 0x00000020:
                        flags.append('code')
                    if characteristics & 0x00000040:
                        flags.append('data')
                    if characteristics & 0x20000000:
                        flags.append('executable')
                    if characteristics & 0x40000000:
                        flags.append('readable')
                    if characteristics & 0x80000000:
                        flags.append('writable')
                    
                    info.sections.append({
                        'name': name,
                        'virtual_size': virtual_size,
                        'virtual_address': virtual_addr,
                        'raw_size': raw_size,
                        'raw_offset': raw_offset,
                        'flags': flags
                    })
        except Exception:
            pass
    
    def _parse_pe_version_info(self, path: Path, header: bytes, pe_offset: int, info: BinaryInfo):
        """Extract PE version info resource."""
        try:
            # This is simplified - full version info parsing is complex
            # Look for VS_VERSION_INFO signature in the file
            with open(path, 'rb') as f:
                # Read more of the file to find version resources
                f.seek(0)
                content = f.read(min(path.stat().st_size, 10 * 1024 * 1024))  # 10MB max
                
                # Look for VS_VERSION_INFO signature
                vs_signature = b'\xbd\x04\xef\xfe'  # VS_VERSION_INFO signature
                pos = content.find(vs_signature)
                
                if pos > 0:
                    # Try to extract file version around this area
                    # This is heuristic-based, not full parsing
                    version_info = {}
                    
                    # Search for common version strings after signature
                    search_area = content[pos:pos+4096]
                    
                    # Look for FileVersion
                    fv_pos = search_area.find(b'FileVersion')
                    if fv_pos > 0:
                        # Extract version string
                        str_start = fv_pos + 12
                        str_end = search_area.find(b'\x00\x00', str_start)
                        if str_end > str_start:
                            try:
                                version_str = search_area[str_start:str_end].decode('utf-16-le', errors='replace').rstrip('\x00')
                                if version_str:
                                    version_info['FileVersion'] = version_str
                            except:
                                pass
                    
                    # Look for ProductVersion
                    pv_pos = search_area.find(b'ProductVersion')
                    if pv_pos > 0:
                        str_start = pv_pos + 14
                        str_end = search_area.find(b'\x00\x00', str_start)
                        if str_end > str_start:
                            try:
                                version_str = search_area[str_start:str_end].decode('utf-16-le', errors='replace').rstrip('\x00')
                                if version_str:
                                    version_info['ProductVersion'] = version_str
                            except:
                                pass
                    
                    # Look for CompanyName
                    cn_pos = search_area.find(b'CompanyName')
                    if cn_pos > 0:
                        str_start = cn_pos + 12
                        str_end = search_area.find(b'\x00\x00', str_start)
                        if str_end > str_start:
                            try:
                                name_str = search_area[str_start:str_end].decode('utf-16-le', errors='replace').rstrip('\x00')
                                if name_str:
                                    version_info['CompanyName'] = name_str
                            except:
                                pass
                    
                    if version_info:
                        info.version_info = version_info
        except Exception:
            pass
    
    def _parse_elf(self, path: Path, header: bytes, info: BinaryInfo, deep: bool):
        """Parse ELF format."""
        # ELF identification
        ei_class = header[4]  # 1 = 32-bit, 2 = 64-bit
        ei_data = header[5]   # 1 = little-endian, 2 = big-endian
        
        info.is_64bit = (ei_class == 2)
        
        # Endianness
        if ei_data == 1:
            endian = '<'  # little-endian
        else:
            endian = '>'  # big-endian
        
        # e_machine field
        if info.is_64bit:
            e_machine_offset = 18
        else:
            e_machine_offset = 18
        
        if len(header) > e_machine_offset + 2:
            machine = struct.unpack_from(endian + 'H', header, e_machine_offset)[0]
            
            if machine == 0x3E:  # EM_X86_64
                info.architecture = Architecture.X86_64
            elif machine == 0x03:  # EM_386
                info.architecture = Architecture.X86
            elif machine == 0xB7:  # EM_AARCH64
                info.architecture = Architecture.ARM64
            elif machine == 0x28:  # EM_ARM
                info.architecture = Architecture.ARM
            elif machine == 0x08:  # EM_MIPS
                info.architecture = Architecture.MIPS
            elif machine == 0x14:  # EM_PPC
                info.architecture = Architecture.PPC
            elif machine == 0x15:  # EM_PPC64
                info.architecture = Architecture.PPC64
            else:
                info.architecture = Architecture.UNKNOWN
        
        # Entry point
        if info.is_64bit:
            if len(header) > 24 + 8:
                info.entry_point = struct.unpack_from(endian + 'Q', header, 24)[0]
        else:
            if len(header) > 24 + 4:
                info.entry_point = struct.unpack_from(endian + 'I', header, 24)[0]
        
        # Type
        if len(header) > 16 + 2:
            e_type = struct.unpack_from(endian + 'H', header, 16)[0]
            if e_type == 2:  # ET_EXEC
                info.is_executable = True
            elif e_type == 3:  # ET_DYN
                info.is_library = True
                info.is_executable = True  # Shared objects can be executables
            elif e_type == 1:  # ET_REL
                info.is_executable = False

        # Section count (from header, available even in shallow mode)
        if info.is_64bit:
            shnum_offset = 60  # e_shnum in Elf64_Ehdr
        else:
            shnum_offset = 48  # e_shnum in Elf32_Ehdr
        if len(header) > shnum_offset + 2:
            info.section_count = struct.unpack_from(endian + 'H', header, shnum_offset)[0]

        # Deep analysis
        if deep:
            self._parse_elf_sections(path, header, endian, info)
    
    def _parse_elf_sections(self, path: Path, header: bytes, endian: str, info: BinaryInfo):
        """Parse ELF section headers."""
        try:
            is_64 = info.is_64bit
            
            with open(path, 'rb') as f:
                # Get section header offset and count
                if is_64:
                    f.seek(40)  # e_shoff
                    shoff = struct.unpack(endian + 'Q', f.read(8))[0]
                    f.seek(58)  # e_shnum
                    shnum = struct.unpack(endian + 'H', f.read(2))[0]
                    shentsize = 64  # sizeof(Elf64_Shdr)
                else:
                    f.seek(32)  # e_shoff
                    shoff = struct.unpack(endian + 'I', f.read(4))[0]
                    f.seek(48)  # e_shnum
                    shnum = struct.unpack(endian + 'H', f.read(2))[0]
                    shentsize = 40  # sizeof(Elf32_Shdr)
                
                info.section_count = shnum
                
                # Read section headers (limit to 64 for performance)
                shnum = min(shnum, 64)
                f.seek(shoff)
                
                for i in range(shnum):
                    f.seek(shoff + i * shentsize)
                    shdr = f.read(shentsize)
                    if len(shdr) < shentsize:
                        break
                    
                    if is_64:
                        sh_name = struct.unpack_from(endian + 'I', shdr, 0)[0]
                        sh_type = struct.unpack_from(endian + 'I', shdr, 4)[0]
                        sh_size = struct.unpack_from(endian + 'Q', shdr, 32)[0]
                    else:
                        sh_name = struct.unpack_from(endian + 'I', shdr, 0)[0]
                        sh_type = struct.unpack_from(endian + 'I', shdr, 4)[0]
                        sh_size = struct.unpack_from(endian + 'I', shdr, 16)[0]
                    
                    type_names = {
                        0: 'SHT_NULL', 1: 'SHT_PROGBITS', 2: 'SHT_SYMTAB',
                        3: 'SHT_STRTAB', 8: 'SHT_NOBITS', 11: 'SHT_DYNSYM'
                    }
                    
                    info.sections.append({
                        'name_offset': sh_name,
                        'type': type_names.get(sh_type, f'SHT_{sh_type}'),
                        'size': sh_size
                    })
        except Exception:
            pass
    
    def _parse_macho(self, path: Path, header: bytes, info: BinaryInfo, deep: bool):
        """Parse Mach-O format."""
        magic = header[:4]
        
        # Determine endianness and bitness
        if magic in (self.MAGIC_MACHO_32, self.MAGIC_MACHO_64):
            endian = '>'  # big-endian
            info.is_64bit = (magic == self.MAGIC_MACHO_64)
        else:
            endian = '<'  # little-endian
            info.is_64bit = (magic == self.MAGIC_MACHO_64_LE)
        
        # Check for fat binary
        if magic == self.MAGIC_FAT:
            # Fat binary - just note it, don't parse all slices
            info.architecture = Architecture.UNKNOWN
            info.is_executable = True
            return
        
        # CPU type
        cputype_offset = 4
        if len(header) > cputype_offset + 4:
            cputype = struct.unpack_from(endian + 'i', header, cputype_offset)[0]
            
            # Mask out the ABI mask
            cpu_type_mask = 0xFFFFFF
            cputype &= cpu_type_mask
            
            if cputype == 7:  # CPU_TYPE_X86
                info.architecture = Architecture.X86
            elif cputype == 0x01000007:  # CPU_TYPE_X86_64
                info.architecture = Architecture.X86_64
                info.is_64bit = True
            elif cputype == 12:  # CPU_TYPE_ARM
                info.architecture = Architecture.ARM
            elif cputype == 0x0100000C:  # CPU_TYPE_ARM64
                info.architecture = Architecture.ARM64
                info.is_64bit = True
            elif cputype == 18:  # CPU_TYPE_POWERPC
                info.architecture = Architecture.PPC
            elif cputype == 0x01000012:  # CPU_TYPE_POWERPC64
                info.architecture = Architecture.PPC64
                info.is_64bit = True
            else:
                info.architecture = Architecture.UNKNOWN
        
        # File type
        filetype_offset = 12
        if len(header) > filetype_offset + 4:
            filetype = struct.unpack_from(endian + 'I', header, filetype_offset)[0]
            
            if filetype == 1:  # MH_OBJECT
                info.is_executable = False
            elif filetype == 2:  # MH_EXECUTE
                info.is_executable = True
            elif filetype == 6:  # MH_DYLIB
                info.is_library = True
                info.is_executable = True
        
        # Deep analysis
        if deep:
            self._parse_macho_load_commands(path, header, endian, info)
    
    def _parse_macho_load_commands(self, path: Path, header: bytes, endian: str, info: BinaryInfo):
        """Parse Mach-O load commands."""
        try:
            is_64 = info.is_64bit
            
            # Number of load commands
            if is_64:
                ncmds_offset = 32
                sizeofcmds_offset = 36
            else:
                ncmds_offset = 28
                sizeofcmds_offset = 32
            
            if len(header) < sizeofcmds_offset + 4:
                return
            
            ncmds = struct.unpack_from(endian + 'I', header, ncmds_offset)[0]
            sizeofcmds = struct.unpack_from(endian + 'I', header, sizeofcmds_offset)[0]
            
            info.section_count = 0  # Will count from load commands
            
            # Read load commands
            with open(path, 'rb') as f:
                if is_64:
                    lc_start = 32 + 32  # mach_header_64 size
                else:
                    lc_start = 28  # mach_header size
                
                f.seek(lc_start)
                
                for i in range(min(ncmds, 100)):  # Limit to 100 load commands
                    lc_header = f.read(8)
                    if len(lc_header) < 8:
                        break
                    
                    cmd, cmdsize = struct.unpack(endian + 'II', lc_header)
                    
                    # LC_SEGMENT or LC_SEGMENT_64
                    if cmd == 1 or cmd == 0x19:  # LC_SEGMENT, LC_SEGMENT_64
                        # Read segment name
                        seg_data = f.read(cmdsize - 8)
                        if len(seg_data) >= 16:
                            seg_name = seg_data[:16].rstrip(b'\x00').decode('ascii', errors='replace')
                            
                            # Number of sections in this segment
                            if cmd == 0x19:  # 64-bit
                                nsects = struct.unpack_from(endian + 'I', seg_data, 64)[0]
                            else:  # 32-bit
                                nsects = struct.unpack_from(endian + 'I', seg_data, 48)[0]
                            
                            info.section_count += nsects
                            
                            info.sections.append({
                                'name': seg_name,
                                'type': 'segment',
                                'sections': nsects
                            })
                    
                    # LC_ID_DYLIB - indicates this is a dylib
                    elif cmd == 13:  # LC_ID_DYLIB
                        info.is_library = True
                        f.seek(cmdsize - 8, 1)  # Skip rest of command
                    
                    else:
                        f.seek(cmdsize - 8, 1)  # Skip rest of command
                        
        except Exception:
            pass
    
    def batch_inspect(self, paths: List[str], deep: bool = False) -> Dict[str, BinaryInfo]:
        """
        Inspect multiple binary files in batch.
        
        Args:
            paths: List of file paths
            deep: Whether to perform deep analysis
            
        Returns:
            Dictionary mapping paths to BinaryInfo objects
        """
        results = {}
        for path in paths:
            try:
                results[path] = self.inspect(path, deep)
            except Exception as e:
                results[path] = BinaryInfo(
                    path=path,
                    format=BinaryFormat.UNKNOWN,
                    architecture=Architecture.UNKNOWN,
                    size=0,
                    sha256="",
                    md5="",
                    error=str(e)
                )
        return results


def main():
    """CLI entry point for testing."""
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: binary_inspector.py <file> [--deep]")
        return
    
    inspector = BinaryInspector()
    deep = '--deep' in sys.argv
    
    for path in sys.argv[1:]:
        if path == '--deep':
            continue
        print(f"Inspecting: {path}")
        info = inspector.inspect(path, deep)
        
        print(f"  Format: {info.format.value}")
        print(f"  Architecture: {info.architecture.value}")
        print(f"  64-bit: {info.is_64bit}")
        print(f"  Size: {info.size} bytes")
        print(f"  SHA256: {info.sha256}")
        print(f"  Executable: {info.is_executable}")
        print(f"  Library: {info.is_library}")
        if info.entry_point:
            print(f"  Entry point: 0x{info.entry_point:x}")
        if info.section_count:
            print(f"  Sections: {info.section_count}")
        if info.version_info:
            print(f"  Version info: {json.dumps(info.version_info, indent=4)}")
        if info.error:
            print(f"  Error: {info.error}")
        print()


if __name__ == "__main__":
    main()
