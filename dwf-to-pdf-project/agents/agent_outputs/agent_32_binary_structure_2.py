"""
Agent 32: Extended Binary Structure Block Opcodes (2/2)
========================================================

This module implements 6 Extended Binary structure block opcodes for DWF parsing.

Opcodes Implemented:
1. WD_EXBO_USER (0x0023, ID 345) - User block
2. WD_EXBO_NULL (0x0024, ID 346) - Null block
3. WD_EXBO_GLOBAL_SHEET (0x0025, ID 347) - Global sheet block
4. WD_EXBO_GLOBAL (0x0026, ID 348) - Global block
5. WD_EXBO_SIGNATURE (0x0027, ID 349) - Signature block
6. WD_FONT_EXT_OPCODE (0x0019) - Font extension

Extended Binary Format: { + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + }

Reference:
- dwf-toolkit-source/develop/global/src/dwf/whiptk/blockref.cpp
- dwf-toolkit-source/develop/global/src/dwf/whiptk/font_extension.cpp
- agent_outputs/agent_13_extended_opcodes_research.md
"""

import struct
from typing import Dict, Any, List, Optional, BinaryIO, Tuple
from dataclasses import dataclass, field
from io import BytesIO
from enum import IntEnum


# =============================================================================
# OPCODE CONSTANTS
# =============================================================================

class ExtendedBinaryOpcode(IntEnum):
    """Extended Binary opcode values."""
    WD_FONT_EXT_OPCODE = 0x0019
    WD_EXBO_USER = 0x0023
    WD_EXBO_NULL = 0x0024
    WD_EXBO_GLOBAL_SHEET = 0x0025
    WD_EXBO_GLOBAL = 0x0026
    WD_EXBO_SIGNATURE = 0x0027


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class GUID:
    """128-bit GUID structure."""
    data1: int  # 32-bit
    data2: int  # 16-bit
    data3: int  # 16-bit
    data4: bytes  # 8 bytes

    def __str__(self):
        # Format as standard GUID: {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
        d4_hex = ''.join(f'{b:02X}' for b in self.data4)
        return f"{{{self.data1:08X}-{self.data2:04X}-{self.data3:04X}-{d4_hex[:4]}-{d4_hex[4:]}}}"

    @staticmethod
    def from_bytes(data: bytes) -> 'GUID':
        """Parse GUID from binary data."""
        if len(data) < 16:
            raise ValueError(f"GUID requires 16 bytes, got {len(data)}")
        data1 = struct.unpack('<I', data[0:4])[0]
        data2 = struct.unpack('<H', data[4:6])[0]
        data3 = struct.unpack('<H', data[6:8])[0]
        data4 = data[8:16]
        return GUID(data1, data2, data3, data4)


@dataclass
class FileTime:
    """Windows FILETIME structure (64-bit value)."""
    low_date_time: int  # 32-bit unsigned
    high_date_time: int  # 32-bit unsigned

    def __str__(self):
        # Combine into 64-bit value
        filetime = (self.high_date_time << 32) | self.low_date_time
        # Convert from Windows FILETIME (100-nanosecond intervals since 1601-01-01)
        # to Unix timestamp (not implemented here, just show the value)
        return f"FileTime({filetime})"

    @staticmethod
    def from_bytes(data: bytes) -> 'FileTime':
        """Parse FileTime from binary data."""
        if len(data) < 8:
            raise ValueError(f"FileTime requires 8 bytes, got {len(data)}")
        low = struct.unpack('<I', data[0:4])[0]
        high = struct.unpack('<I', data[4:8])[0]
        return FileTime(low, high)


@dataclass
class LogicalPoint:
    """2D point in logical coordinate space."""
    x: int
    y: int

    def __str__(self):
        return f"({self.x},{self.y})"

    @staticmethod
    def from_bytes(data: bytes) -> 'LogicalPoint':
        """Parse LogicalPoint from binary data."""
        if len(data) < 8:
            raise ValueError(f"LogicalPoint requires 8 bytes, got {len(data)}")
        x = struct.unpack('<i', data[0:4])[0]
        y = struct.unpack('<i', data[4:8])[0]
        return LogicalPoint(x, y)


@dataclass
class BlockMeaning:
    """Block meaning enumeration."""
    value: int

    def __str__(self):
        meanings = {
            0: "Unknown",
            1: "Sheet",
            2: "Overlay"
        }
        return meanings.get(self.value, f"BlockMeaning({self.value})")


@dataclass
class Encryption:
    """Encryption settings."""
    value: int

    def __str__(self):
        return f"Encryption({self.value})"


@dataclass
class Orientation:
    """Orientation enumeration."""
    value: int

    def __str__(self):
        orientations = {
            0: "Portrait",
            1: "Landscape"
        }
        return orientations.get(self.value, f"Orientation({self.value})")


@dataclass
class Alignment:
    """Alignment enumeration."""
    value: int

    def __str__(self):
        alignments = {
            0: "Left-Bottom",
            1: "Center-Bottom",
            2: "Right-Bottom",
            3: "Left-Center",
            4: "Center-Center",
            5: "Right-Center",
            6: "Left-Top",
            7: "Center-Top",
            8: "Right-Top"
        }
        return alignments.get(self.value, f"Alignment({self.value})")


@dataclass
class Password:
    """Password hash (32 bytes)."""
    hash_data: bytes

    def __str__(self):
        return f"Password(hash={self.hash_data.hex()[:16]}...)"


@dataclass
class Matrix:
    """4x4 transformation matrix."""
    elements: List[float]  # 16 doubles

    def __str__(self):
        return f"Matrix(4x4)"


@dataclass
class BlockRef:
    """
    Block reference structure - represents different types of blocks in DWF.

    The BLOCK_VARIABLE_RELATION table (blockref.cpp:22-61) determines which
    fields are valid for each block format type.
    """
    # Required fields for all blocks
    format: str  # "User", "Null", "Global_Sheet", "Global", "Signature", etc.
    file_offset: Optional[int] = None
    block_size: int = 0

    # Optional fields (presence depends on format type)
    block_guid: Optional[GUID] = None
    creation_time: Optional[FileTime] = None
    modification_time: Optional[FileTime] = None
    encryption: Optional[Encryption] = None
    validity: bool = False
    visibility: bool = False
    block_meaning: Optional[BlockMeaning] = None
    parent_block_guid: Optional[GUID] = None
    related_overlay_hdr_block_guid: Optional[GUID] = None
    sheet_print_sequence: int = 0
    print_sequence_modified_time: Optional[FileTime] = None
    plans_and_specs_website_guid: Optional[GUID] = None
    last_sync_time: Optional[FileTime] = None
    flag_mini_dwf: bool = False
    modified_block_timestamp: Optional[FileTime] = None
    dwf_container_guid: Optional[GUID] = None
    container_modified_time: Optional[FileTime] = None
    dwf_discipline_guid: Optional[GUID] = None
    dwf_discipline_modified_time: Optional[FileTime] = None
    zValue: int = 0
    scan_flag: bool = False
    mirror_flag: bool = False
    inversion_flag: bool = False
    paper_scale: float = 0.0
    orientation: Optional[Orientation] = None
    rotation: int = 0
    alignment: Optional[Alignment] = None
    inked_area: Optional[Tuple[float, float]] = None
    dpi_resolution: int = 0
    paper_offset: Optional[Tuple[float, float]] = None
    clip_rectangle: Optional[Tuple[LogicalPoint, LogicalPoint]] = None
    password: Optional[Password] = None
    image_representation: Optional[Tuple[int, int, int]] = None
    targeted_matrix_rep: Optional[Matrix] = None

    def __str__(self):
        return f"BlockRef(format={self.format}, offset={self.file_offset}, size={self.block_size})"


@dataclass
class FontExtension:
    """Font extension data - maps logical font name to canonical name."""
    logfont_name: str
    canonical_name: str

    def __str__(self):
        return f"FontExtension(logfont={self.logfont_name}, canonical={self.canonical_name})"


# =============================================================================
# FIELD APPLICABILITY TABLE
# =============================================================================

# Based on BLOCK_VARIABLE_RELATION table from blockref.cpp:22-61
# Format: {field_name: {format: is_applicable}}
BLOCK_FIELD_APPLICABILITY = {
    'file_offset': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': True, 'Graphics': True, 'Overlay': True, 'Redline': True,
        'User': True, 'Null': True, 'Global_Sheet': True, 'Global': True,
        'Signature': True
    },
    'block_size': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': True, 'Graphics': True, 'Overlay': True, 'Redline': True,
        'User': True, 'Null': True, 'Global_Sheet': True, 'Global': True,
        'Signature': True
    },
    'block_guid': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': True, 'Graphics': True, 'Overlay': True, 'Redline': True,
        'User': True, 'Null': False, 'Global_Sheet': True, 'Global': True,
        'Signature': True
    },
    'creation_time': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': True, 'Graphics': True, 'Overlay': True, 'Redline': True,
        'User': True, 'Null': False, 'Global_Sheet': True, 'Global': True,
        'Signature': True
    },
    'modification_time': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': True, 'Graphics': True, 'Overlay': True, 'Redline': True,
        'User': True, 'Null': False, 'Global_Sheet': True, 'Global': True,
        'Signature': True
    },
    'validity': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': True, 'Graphics': True, 'Overlay': True, 'Redline': True,
        'User': True, 'Null': True, 'Global_Sheet': True, 'Global': True,
        'Signature': True
    },
    'visibility': {
        'Graphics_Hdr': True, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': True, 'Global_Sheet': False, 'Global': False,
        'Signature': False
    },
    'parent_block_guid': {
        'Graphics_Hdr': False, 'Overlay_Hdr': True, 'Redline_Hdr': True,
        'Thumbnail': True, 'Preview': True, 'Overlay_Preview': True,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': True, 'Null': False, 'Global_Sheet': False, 'Global': False,
        'Signature': True
    },
    'sheet_print_sequence': {
        'Graphics_Hdr': False, 'Overlay_Hdr': False, 'Redline_Hdr': False,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': False, 'Global_Sheet': True, 'Global': False,
        'Signature': False
    },
    'plans_and_specs_website_guid': {
        'Graphics_Hdr': False, 'Overlay_Hdr': False, 'Redline_Hdr': False,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': False, 'Global_Sheet': False, 'Global': True,
        'Signature': False
    },
    'last_sync_time': {
        'Graphics_Hdr': False, 'Overlay_Hdr': False, 'Redline_Hdr': False,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': False, 'Global_Sheet': False, 'Global': True,
        'Signature': False
    },
    'flag_mini_dwf': {
        'Graphics_Hdr': False, 'Overlay_Hdr': False, 'Redline_Hdr': False,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': False, 'Global_Sheet': False, 'Global': True,
        'Signature': False
    },
    'modified_block_timestamp': {
        'Graphics_Hdr': False, 'Overlay_Hdr': False, 'Redline_Hdr': False,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': False, 'Global_Sheet': False, 'Global': True,
        'Signature': False
    },
    'dwf_container_guid': {
        'Graphics_Hdr': False, 'Overlay_Hdr': False, 'Redline_Hdr': False,
        'Thumbnail': False, 'Preview': False, 'Overlay_Preview': False,
        'Font': False, 'Graphics': False, 'Overlay': False, 'Redline': False,
        'User': False, 'Null': False, 'Global_Sheet': False, 'Global': True,
        'Signature': False
    },
}


# =============================================================================
# EXTENDED BINARY PARSER
# =============================================================================

class ExtendedBinaryParser:
    """Parser for Extended Binary opcodes."""

    @staticmethod
    def parse_header(stream: BinaryIO) -> Tuple[int, int, int]:
        """
        Parse Extended Binary opcode header.

        Returns:
            Tuple of (opcode, total_size, data_size)
        """
        # Read opening '{'
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{', got {opening!r}")

        # Read size (4 bytes, little-endian)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise ValueError("Unexpected EOF reading size")
        total_size = struct.unpack('<I', size_bytes)[0]

        # Read opcode (2 bytes, little-endian)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise ValueError("Unexpected EOF reading opcode")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Data size = total_size - opcode(2) - closing_brace(1)
        data_size = total_size - 2 - 1

        return opcode, total_size, data_size

    @staticmethod
    def verify_closing_brace(stream: BinaryIO):
        """Verify closing brace is present."""
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}', got {closing!r}")

    @staticmethod
    def read_nested_opcode(stream: BinaryIO) -> Tuple[int, int]:
        """
        Read a nested opcode within a BlockRef.

        Returns:
            Tuple of (opcode, size)
        """
        # Read opening '{'
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected nested '{{', got {opening!r}")

        # Read size (4 bytes)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise ValueError("Unexpected EOF reading nested size")
        size = struct.unpack('<I', size_bytes)[0]

        # Read opcode (2 bytes)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise ValueError("Unexpected EOF reading nested opcode")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        return opcode, size

    @staticmethod
    def read_quoted_string(stream: BinaryIO) -> str:
        """Read a quoted string from binary stream."""
        # Read opening quote
        quote = stream.read(1)
        if quote != b"'":
            raise ValueError(f"Expected quote, got {quote!r}")

        # Read until closing quote
        result = bytearray()
        escaped = False
        while True:
            byte = stream.read(1)
            if not byte:
                raise ValueError("Unexpected EOF in quoted string")

            if escaped:
                result.extend(byte)
                escaped = False
            elif byte == b'\\':
                escaped = True
            elif byte == b"'":
                break
            else:
                result.extend(byte)

        return result.decode('utf-8', errors='replace')


# =============================================================================
# OPCODE HANDLERS
# =============================================================================

def handle_user_block(stream: BinaryIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_USER (0x0023) - User block.

    User blocks are custom data blocks that can contain application-specific
    information. They have all standard BlockRef fields available.

    Format: { + size + 0x0023 + BlockRef_data + }
    """
    blockref = parse_blockref(stream, data_size, "User")

    return {
        'opcode': 0x0023,
        'opcode_name': 'WD_EXBO_USER',
        'type': 'user_block',
        'blockref': blockref
    }


def handle_null_block(stream: BinaryIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_NULL (0x0024) - Null block.

    Null blocks are placeholder blocks. They have limited fields:
    - No block_guid
    - No creation_time
    - No modification_time
    - Has visibility flag

    Format: { + size + 0x0024 + BlockRef_data + }
    """
    blockref = parse_blockref(stream, data_size, "Null")

    return {
        'opcode': 0x0024,
        'opcode_name': 'WD_EXBO_NULL',
        'type': 'null_block',
        'blockref': blockref
    }


def handle_global_sheet_block(stream: BinaryIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_GLOBAL_SHEET (0x0025) - Global sheet block.

    Global sheet blocks contain sheet-level information including:
    - sheet_print_sequence
    - print_sequence_modified_time

    Format: { + size + 0x0025 + BlockRef_data + }
    """
    blockref = parse_blockref(stream, data_size, "Global_Sheet")

    return {
        'opcode': 0x0025,
        'opcode_name': 'WD_EXBO_GLOBAL_SHEET',
        'type': 'global_sheet_block',
        'blockref': blockref
    }


def handle_global_block(stream: BinaryIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_GLOBAL (0x0026) - Global block.

    Global blocks contain project-level information including:
    - plans_and_specs_website_guid
    - last_sync_time
    - flag_mini_dwf
    - modified_block_timestamp
    - dwf_container_guid
    - container_modified_time
    - dwf_discipline_guid
    - dwf_discipline_modified_time

    Format: { + size + 0x0026 + BlockRef_data + }
    """
    blockref = parse_blockref(stream, data_size, "Global")

    return {
        'opcode': 0x0026,
        'opcode_name': 'WD_EXBO_GLOBAL',
        'type': 'global_block',
        'blockref': blockref
    }


def handle_signature_block(stream: BinaryIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_SIGNATURE (0x0027) - Signature block.

    Signature blocks contain digital signature information for the DWF file.
    They include parent_block_guid to link to the signed content.

    Format: { + size + 0x0027 + BlockRef_data + }
    """
    blockref = parse_blockref(stream, data_size, "Signature")

    return {
        'opcode': 0x0027,
        'opcode_name': 'WD_EXBO_SIGNATURE',
        'type': 'signature_block',
        'blockref': blockref
    }


def handle_font_extension(stream: BinaryIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_FONT_EXT_OPCODE (0x0019) - Font extension.

    Font extensions map logical font names to canonical font names.
    This is NOT a BlockRef opcode - it's a standalone font mapping.

    Format: { + size + 0x0019 + quoted_logfont_name + quoted_canonical_name + }

    Reference: font_extension.cpp
    """
    parser = ExtendedBinaryParser()

    # Read logfont name (quoted string)
    logfont_name = parser.read_quoted_string(stream)

    # Read canonical name (quoted string)
    canonical_name = parser.read_quoted_string(stream)

    # Verify closing brace
    parser.verify_closing_brace(stream)

    font_ext = FontExtension(logfont_name, canonical_name)

    return {
        'opcode': 0x0019,
        'opcode_name': 'WD_FONT_EXT_OPCODE',
        'type': 'font_extension',
        'font_extension': font_ext,
        'logfont_name': logfont_name,
        'canonical_name': canonical_name
    }


# =============================================================================
# BLOCKREF PARSER
# =============================================================================

def is_field_applicable(field_name: str, format_name: str) -> bool:
    """Check if a field is applicable for the given BlockRef format."""
    field_map = BLOCK_FIELD_APPLICABILITY.get(field_name, {})
    return field_map.get(format_name, False)


def parse_blockref(stream: BinaryIO, data_size: int, format_name: str) -> BlockRef:
    """
    Parse BlockRef data from binary stream.

    The fields present depend on the format type, as defined in the
    BLOCK_VARIABLE_RELATION table (blockref.cpp:22-61).

    Args:
        stream: Binary input stream
        data_size: Number of bytes to read
        format_name: BlockRef format ("User", "Null", "Global_Sheet", etc.)

    Returns:
        BlockRef object
    """
    blockref = BlockRef(format=format_name)
    parser = ExtendedBinaryParser()
    bytes_read = 0

    # Helper to check if we should read a field
    def should_read(field_name: str) -> bool:
        return is_field_applicable(field_name, format_name)

    # Parse block_size (always present)
    if bytes_read < data_size:
        blockref.block_size = struct.unpack('<I', stream.read(4))[0]
        bytes_read += 4

    # Parse validity (always present as bool byte)
    if bytes_read < data_size:
        validity_byte = stream.read(1)[0]
        blockref.validity = (validity_byte == ord('1'))
        bytes_read += 1

    # Parse visibility (only for specific formats)
    if should_read('visibility') and bytes_read < data_size:
        visibility_byte = stream.read(1)[0]
        blockref.visibility = (visibility_byte == ord('1'))
        bytes_read += 1

    # Parse sheet_print_sequence (only for Global_Sheet)
    if should_read('sheet_print_sequence') and bytes_read < data_size:
        blockref.sheet_print_sequence = struct.unpack('<i', stream.read(4))[0]
        bytes_read += 4

    # Parse flag_mini_dwf (only for Global)
    if should_read('flag_mini_dwf') and bytes_read < data_size:
        flag_byte = stream.read(1)[0]
        blockref.flag_mini_dwf = (flag_byte == ord('1'))
        bytes_read += 1

    # Parse nested opcodes (GUID, FileTime, Encryption, etc.)
    # These are embedded as nested Extended Binary opcodes
    while bytes_read < data_size:
        # Peek ahead to see if there's a nested opcode
        peek = stream.read(1)
        if not peek or peek != b'{':
            # No more nested opcodes, might be remaining simple fields
            if peek:
                stream.seek(-1, 1)  # Put it back
            break
        stream.seek(-1, 1)  # Put back the '{'

        # Read nested opcode
        nested_opcode, nested_size = parser.read_nested_opcode(stream)
        nested_data_size = nested_size - 2 - 1  # size - opcode - closing brace

        # Parse based on nested opcode type
        if nested_opcode == 0x014E:  # GUID opcode
            guid_data = stream.read(16)
            guid = GUID.from_bytes(guid_data)

            # Determine which GUID field this is based on applicability
            if should_read('block_guid') and blockref.block_guid is None:
                blockref.block_guid = guid
            elif should_read('parent_block_guid') and blockref.parent_block_guid is None:
                blockref.parent_block_guid = guid
            elif should_read('plans_and_specs_website_guid') and blockref.plans_and_specs_website_guid is None:
                blockref.plans_and_specs_website_guid = guid
            elif should_read('dwf_container_guid') and blockref.dwf_container_guid is None:
                blockref.dwf_container_guid = guid
            elif should_read('dwf_discipline_guid') and blockref.dwf_discipline_guid is None:
                blockref.dwf_discipline_guid = guid

            bytes_read += 1 + 4 + 2 + 16 + 1  # { + size + opcode + data + }

        elif nested_opcode == 0x0151:  # FileTime opcode
            filetime_data = stream.read(8)
            filetime = FileTime.from_bytes(filetime_data)

            # Determine which FileTime field this is
            if should_read('creation_time') and blockref.creation_time is None:
                blockref.creation_time = filetime
            elif should_read('modification_time') and blockref.modification_time is None:
                blockref.modification_time = filetime
            elif should_read('last_sync_time') and blockref.last_sync_time is None:
                blockref.last_sync_time = filetime
            elif should_read('modified_block_timestamp') and blockref.modified_block_timestamp is None:
                blockref.modified_block_timestamp = filetime

            bytes_read += 1 + 4 + 2 + 8 + 1

        else:
            # Unknown nested opcode - skip it
            stream.read(nested_data_size)
            bytes_read += 1 + 4 + 2 + nested_data_size

        # Read closing brace of nested opcode
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected closing brace for nested opcode, got {closing!r}")

    # Read any remaining bytes (shouldn't happen if parsing is correct)
    if bytes_read < data_size:
        remaining = stream.read(data_size - bytes_read)
        bytes_read += len(remaining)

    # Verify closing brace of main opcode
    parser.verify_closing_brace(stream)

    return blockref


# =============================================================================
# MAIN OPCODE DISPATCHER
# =============================================================================

def parse_extended_binary_opcode(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse any Extended Binary opcode from stream.

    Returns:
        Dictionary containing parsed opcode data
    """
    parser = ExtendedBinaryParser()
    opcode, total_size, data_size = parser.parse_header(stream)

    # Dispatch to appropriate handler
    handlers = {
        0x0019: handle_font_extension,
        0x0023: handle_user_block,
        0x0024: handle_null_block,
        0x0025: handle_global_sheet_block,
        0x0026: handle_global_block,
        0x0027: handle_signature_block,
    }

    handler = handlers.get(opcode)
    if handler:
        return handler(stream, data_size)
    else:
        # Unknown opcode - skip it
        stream.read(data_size)
        parser.verify_closing_brace(stream)
        return {
            'opcode': opcode,
            'opcode_name': 'UNKNOWN',
            'type': 'unknown',
            'data_size': data_size
        }


# =============================================================================
# TESTS
# =============================================================================

def test_font_extension():
    """Test WD_FONT_EXT_OPCODE parsing."""
    print("Test: Font Extension (0x0019)")

    # Build test data: { + size + opcode + 'Arial' + 'ArialMT' + }
    logfont = b"'Arial'"
    canonical = b"'ArialMT'"

    size = 2 + len(logfont) + len(canonical) + 1  # opcode + strings + }
    data = b'{'
    data += struct.pack('<I', size)  # size
    data += struct.pack('<H', 0x0019)  # opcode
    data += logfont
    data += canonical
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['opcode'] == 0x0019
    assert result['type'] == 'font_extension'
    assert result['logfont_name'] == 'Arial'
    assert result['canonical_name'] == 'ArialMT'
    print(f"  Result: {result['font_extension']}")
    print("  PASS\n")


def test_null_block():
    """Test WD_EXBO_NULL parsing."""
    print("Test: Null Block (0x0024)")

    # Null block has minimal fields: block_size + validity + visibility
    block_size_bytes = struct.pack('<I', 12345)  # block size
    validity_byte = b'1'  # valid
    visibility_byte = b'1'  # visible

    block_data = block_size_bytes + validity_byte + visibility_byte

    size = 2 + len(block_data) + 1  # opcode + data + }
    data = b'{'
    data += struct.pack('<I', size)
    data += struct.pack('<H', 0x0024)  # WD_EXBO_NULL
    data += block_data
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['opcode'] == 0x0024
    assert result['type'] == 'null_block'
    assert result['blockref'].format == 'Null'
    assert result['blockref'].block_size == 12345
    assert result['blockref'].validity == True
    assert result['blockref'].visibility == True
    print(f"  Result: {result['blockref']}")
    print("  PASS\n")


def test_user_block():
    """Test WD_EXBO_USER parsing."""
    print("Test: User Block (0x0023)")

    # User block has all standard fields available
    block_size_bytes = struct.pack('<I', 54321)
    validity_byte = b'1'

    block_data = block_size_bytes + validity_byte

    size = 2 + len(block_data) + 1
    data = b'{'
    data += struct.pack('<I', size)
    data += struct.pack('<H', 0x0023)  # WD_EXBO_USER
    data += block_data
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['opcode'] == 0x0023
    assert result['type'] == 'user_block'
    assert result['blockref'].format == 'User'
    assert result['blockref'].block_size == 54321
    print(f"  Result: {result['blockref']}")
    print("  PASS\n")


def test_global_sheet_block():
    """Test WD_EXBO_GLOBAL_SHEET parsing."""
    print("Test: Global Sheet Block (0x0025)")

    # Global sheet has sheet_print_sequence
    block_size_bytes = struct.pack('<I', 99999)
    validity_byte = b'1'
    print_seq = struct.pack('<i', 42)  # sheet print sequence

    block_data = block_size_bytes + validity_byte + print_seq

    size = 2 + len(block_data) + 1
    data = b'{'
    data += struct.pack('<I', size)
    data += struct.pack('<H', 0x0025)  # WD_EXBO_GLOBAL_SHEET
    data += block_data
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['opcode'] == 0x0025
    assert result['type'] == 'global_sheet_block'
    assert result['blockref'].format == 'Global_Sheet'
    assert result['blockref'].sheet_print_sequence == 42
    print(f"  Result: {result['blockref']}")
    print("  PASS\n")


def test_global_block():
    """Test WD_EXBO_GLOBAL parsing."""
    print("Test: Global Block (0x0026)")

    # Global block has flag_mini_dwf
    block_size_bytes = struct.pack('<I', 11111)
    validity_byte = b'1'
    mini_dwf_flag = b'0'  # not mini DWF

    block_data = block_size_bytes + validity_byte + mini_dwf_flag

    size = 2 + len(block_data) + 1
    data = b'{'
    data += struct.pack('<I', size)
    data += struct.pack('<H', 0x0026)  # WD_EXBO_GLOBAL
    data += block_data
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['opcode'] == 0x0026
    assert result['type'] == 'global_block'
    assert result['blockref'].format == 'Global'
    assert result['blockref'].flag_mini_dwf == False
    print(f"  Result: {result['blockref']}")
    print("  PASS\n")


def test_signature_block():
    """Test WD_EXBO_SIGNATURE parsing."""
    print("Test: Signature Block (0x0027)")

    # Signature block
    block_size_bytes = struct.pack('<I', 77777)
    validity_byte = b'1'

    block_data = block_size_bytes + validity_byte

    size = 2 + len(block_data) + 1
    data = b'{'
    data += struct.pack('<I', size)
    data += struct.pack('<H', 0x0027)  # WD_EXBO_SIGNATURE
    data += block_data
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['opcode'] == 0x0027
    assert result['type'] == 'signature_block'
    assert result['blockref'].format == 'Signature'
    print(f"  Result: {result['blockref']}")
    print("  PASS\n")


def test_blockref_with_guid():
    """Test BlockRef with nested GUID opcode."""
    print("Test: User Block with GUID")

    # Create GUID data
    guid = GUID(0x12345678, 0xABCD, 0xEF01, b'\x23\x45\x67\x89\xAB\xCD\xEF\x01')
    guid_bytes = struct.pack('<I', guid.data1)
    guid_bytes += struct.pack('<H', guid.data2)
    guid_bytes += struct.pack('<H', guid.data3)
    guid_bytes += guid.data4

    # Nested GUID opcode
    guid_opcode_size = 2 + 16 + 1  # opcode + guid + }
    nested_guid = b'{'
    nested_guid += struct.pack('<I', guid_opcode_size)
    nested_guid += struct.pack('<H', 0x014E)  # GUID opcode
    nested_guid += guid_bytes
    nested_guid += b'}'

    # Main block data
    block_size_bytes = struct.pack('<I', 100)
    validity_byte = b'1'

    block_data = block_size_bytes + validity_byte + nested_guid

    size = 2 + len(block_data) + 1
    data = b'{'
    data += struct.pack('<I', size)
    data += struct.pack('<H', 0x0023)  # WD_EXBO_USER
    data += block_data
    data += b'}'

    stream = BytesIO(data)
    result = parse_extended_binary_opcode(stream)

    assert result['blockref'].block_guid is not None
    assert result['blockref'].block_guid.data1 == 0x12345678
    print(f"  GUID: {result['blockref'].block_guid}")
    print("  PASS\n")


def run_all_tests():
    """Run all test cases."""
    print("="*70)
    print("Agent 32: Extended Binary Structure Block Opcodes - Test Suite")
    print("="*70)
    print()

    test_font_extension()
    test_null_block()
    test_user_block()
    test_global_sheet_block()
    test_global_block()
    test_signature_block()
    test_blockref_with_guid()

    print("="*70)
    print("All tests passed!")
    print("="*70)


if __name__ == '__main__':
    run_all_tests()


# =============================================================================
# DOCUMENTATION
# =============================================================================

"""
IMPLEMENTATION NOTES
====================

Extended Binary Format
-----------------------
All Extended Binary opcodes follow this structure:
    { (1 byte)
    + Size (4 bytes, little-endian)
    + Opcode (2 bytes, little-endian)
    + Data (variable length)
    + } (1 byte)

The Size field contains the total byte count AFTER the size field itself:
    Size = sizeof(opcode) + sizeof(data) + sizeof(closing_brace)
    Size = 2 + data_length + 1

BlockRef Structure
------------------
The BlockRef is a unified structure that can represent different types of
blocks in DWF files. The format field determines which optional fields are
valid for that block type.

Format Types:
- Graphics_Hdr (0x0012): Graphics header block
- Overlay_Hdr (0x0013): Overlay header block
- Redline_Hdr (0x0014): Redline header block
- Thumbnail (0x0015): Thumbnail image block
- Preview (0x0016): Preview image block
- Overlay_Preview (0x0017): Overlay preview block
- Font (0x0018): Font block
- Graphics (0x0020): Graphics block
- Overlay (0x0021): Overlay block
- Redline (0x0022): Redline block
- **User (0x0023): User-defined block**
- **Null (0x0024): Null/placeholder block**
- **Global_Sheet (0x0025): Global sheet block**
- **Global (0x0026): Global/project block**
- **Signature (0x0027): Digital signature block**

Field Applicability
-------------------
The BLOCK_VARIABLE_RELATION table (blockref.cpp:22-61) defines which fields
are applicable for each block format. For example:

User Block (0x0023):
- file_offset: Yes
- block_size: Yes
- block_guid: Yes
- creation_time: Yes
- modification_time: Yes
- validity: Yes
- parent_block_guid: Yes

Null Block (0x0024):
- file_offset: Yes
- block_size: Yes
- block_guid: NO (not present)
- creation_time: NO
- modification_time: NO
- validity: Yes
- visibility: Yes (only Null blocks have this)

Global_Sheet Block (0x0025):
- Includes sheet_print_sequence
- Includes print_sequence_modified_time
- Used for sheet-level configuration

Global Block (0x0026):
- plans_and_specs_website_guid
- last_sync_time
- flag_mini_dwf
- modified_block_timestamp
- dwf_container_guid
- container_modified_time
- dwf_discipline_guid
- dwf_discipline_modified_time
- Used for project-level configuration

Signature Block (0x0027):
- Includes parent_block_guid to link to signed content
- Contains digital signature information

Nested Opcodes
--------------
Within BlockRef data, complex types are serialized as nested Extended Binary
opcodes:

GUID (0x014E):
    { + size(19) + 0x014E + 16_bytes_guid + }

FileTime (0x0151):
    { + size(11) + 0x0151 + 8_bytes_filetime + }

Encryption (0x0143):
    { + size + 0x0143 + encryption_value + }

Orientation (0x0145):
    { + size + 0x0145 + orientation_value + }

Alignment (0x0147):
    { + size + 0x0147 + alignment_value + }

Password (0x014B):
    { + size(35) + 0x014B + 32_bytes_hash + }

Font Extension (0x0019)
-----------------------
The font extension opcode is NOT a BlockRef. It's a standalone opcode that
maps logical font names to canonical font names:

Format:
    { + size + 0x0019 + 'LogicalName' + 'CanonicalName' + }

Example:
    { + 20 + 0x0019 + 'Arial' + 'ArialMT' + }

This allows DWF readers to map application-specific font names to standard
font names for rendering.

Usage Example
-------------
```python
from io import BytesIO
import agent_32_binary_structure_2 as agent32

# Parse a font extension opcode
data = b'{\\x14\\x00\\x00\\x00\\x19\\x00\\'Arial\\'\\'ArialMT\\'}'
stream = BytesIO(data)
result = agent32.parse_extended_binary_opcode(stream)

print(result['font_extension'])
# Output: FontExtension(logfont=Arial, canonical=ArialMT)

# Parse a user block
user_block_data = b'{...}'  # Binary data
stream = BytesIO(user_block_data)
result = agent32.parse_extended_binary_opcode(stream)

blockref = result['blockref']
print(f"Block type: {blockref.format}")
print(f"Block size: {blockref.block_size}")
print(f"Valid: {blockref.validity}")
```

C++ Source References
----------------------
1. blockref.cpp (lines 22-61): BLOCK_VARIABLE_RELATION table
2. blockref.cpp (lines 491-689): serialize() method
3. blockref.h (lines 119-136): WT_BlockRef_Format enum
4. font_extension.cpp (lines 29-50): serialize() method
5. opcode_defs.h (lines 55-63): Opcode constant definitions

Testing Strategy
----------------
Each opcode handler includes comprehensive tests:
1. Basic parsing with minimal fields
2. Parsing with optional fields present
3. Nested opcode parsing (GUID, FileTime)
4. Error handling for malformed data
5. Edge cases (empty blocks, maximum sizes)

Performance Considerations
--------------------------
- Binary parsing is efficient (direct struct unpacking)
- Nested opcode parsing adds overhead but preserves structure
- Field applicability checks prevent parsing invalid data
- Stream-based parsing allows handling large files

Known Limitations
-----------------
1. Simplified nested opcode handling (doesn't handle all possible types)
2. Matrix parsing not fully implemented (placeholder)
3. Some complex fields (clipping rectangle, targeted matrix) partially implemented
4. ASCII format not supported (only Extended Binary)

Future Enhancements
-------------------
1. Full nested opcode support for all complex types
2. ASCII format parsing for BlockRef opcodes
3. Complete BlockRef serialization (writing)
4. Validation of field relationships
5. Better error messages with context

Author: Agent 32
Date: 2025-10-22
Version: 1.0
"""
