"""
Agent 31: DWF Extended Binary Structure Block Opcodes Translation (Part 1/2)

This module implements 6 Extended Binary structure header/block opcodes that define
DWF file section organization. These opcodes use BlockRef objects to organize graphics,
overlays, and redlines into structured sections.

CRITICAL: Extended Binary Format = { + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + }

Opcodes Implemented:
1. WD_EXBO_GRAPHICS_HDR (0x0012, ID 335) - Graphics header block
2. WD_EXBO_OVERLAY_HDR (0x0013, ID 336) - Overlay header block
3. WD_EXBO_REDLINE_HDR (0x0014, ID 337) - Redline header block
4. WD_EXBO_GRAPHICS (0x0020, ID 342) - Graphics block
5. WD_EXBO_OVERLAY (0x0021, ID 343) - Overlay block
6. WD_EXBO_REDLINE (0x0022, ID 344) - Redline block

References:
- DWF Toolkit: develop/global/src/dwf/whiptk/blockref.h
- DWF Toolkit: develop/global/src/dwf/whiptk/blockref.cpp
- Research: agents/agent_outputs/agent_13_extended_opcodes_research.md
"""

import struct
from typing import BinaryIO, Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import IntEnum


# =============================================================================
# CRITICAL SECTION 1: Opcode Definitions and Constants
# =============================================================================

class ExtendedBinaryOpcode(IntEnum):
    """Extended Binary opcode values (hex constants)"""
    GRAPHICS_HDR = 0x0012  # ID 335
    OVERLAY_HDR = 0x0013   # ID 336
    REDLINE_HDR = 0x0014   # ID 337
    GRAPHICS = 0x0020      # ID 342
    OVERLAY = 0x0021       # ID 343
    REDLINE = 0x0022       # ID 344


class BlockRefFormat(IntEnum):
    """BlockRef format types (matches WT_BlockRef::WT_BlockRef_Format)"""
    GRAPHICS_HDR = 335
    OVERLAY_HDR = 336
    REDLINE_HDR = 337
    THUMBNAIL = 338
    PREVIEW = 339
    OVERLAY_PREVIEW = 340
    FONT = 341
    GRAPHICS = 342
    OVERLAY = 343
    REDLINE = 344
    USER = 345
    NULL = 346
    GLOBAL_SHEET = 347
    GLOBAL = 348
    SIGNATURE = 349


class BlockMeaning(IntEnum):
    """Block meaning/description flags"""
    NONE = 0x00000001
    SEAL = 0x00000002
    STAMP = 0x00000004
    LABEL = 0x00000008
    REDLINE = 0x00000010
    RESERVED1 = 0x00000020
    RESERVED2 = 0x00000040


class Orientation(IntEnum):
    """Paper and image orientation relationship"""
    ALWAYS_IN_SYNC = 0x00000001
    ALWAYS_DIFFERENT = 0x00000002
    DECOUPLED = 0x00000004


class Alignment(IntEnum):
    """Graphics alignment on paper plot"""
    ALIGN_CENTER = 0x00000001
    ALIGN_TITLE_BLOCK = 0x00000002
    ALIGN_TOP = 0x00000004
    ALIGN_BOTTOM = 0x00000008
    ALIGN_LEFT = 0x00000010
    ALIGN_RIGHT = 0x00000020
    ALIGN_TOP_LEFT = 0x00000040
    ALIGN_TOP_RIGHT = 0x00000080
    ALIGN_BOTTOM_LEFT = 0x00000100
    ALIGN_BOTTOM_RIGHT = 0x00000200
    ALIGN_NONE = 0x00000400


# =============================================================================
# CRITICAL SECTION 2: Block Variable Relation Table
# =============================================================================
# This table defines which fields are applicable for each blockref format
# Rows = field indices, Columns = block types
# Based on BLOCK_VARIABLE_RELATION table in blockref.cpp lines 22-61

BLOCK_VARIABLE_RELATION = [
    # Fields                          Graphics_HDR  Overlay_HDR  Redline_HDR  Thumbnail  Preview  Overlay_Preview  Font   Graphics  Overlay  Redline  User   Null   Global_Sheet  Global  Signature
    # File_Offset
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True],
    # Block_Size
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True],
    # Block_Guid
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  False, True,  True,  True],
    # Creation_Time
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  False, True,  True,  True],
    # Modification_Time
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  False, True,  True,  True],
    # Encryption
    [True,  True,  True,  True,  True,  True,  False, False, False, False, False, False, False, False, False],
    # Validity
    [True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True,  True],
    # Visibility
    [True,  True,  True,  False, False, False, False, False, False, False, False, True,  False, False, False],
    # Block_Meaning
    [False, True,  False, False, False, False, False, False, False, False, False, False, False, False, False],
    # Parent_Block_Guid
    [False, True,  True,  True,  True,  True,  False, False, False, False, True,  False, False, False, True],
    # Related_Overlay_Hdr_Block_Guid
    [False, False, False, False, False, True,  False, False, False, False, False, False, False, False, False],
    # Sheet_Print_Sequence
    [False, False, False, False, False, False, False, False, False, False, False, False, True,  False, False],
    # Print_Sequence_Modified_Time
    [False, False, False, False, False, False, False, False, False, False, False, False, True,  False, False],
    # Plans_And_Specs_Website_Guid
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Last_Sync_Time
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Flag_Mini_Dwf
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Modified_Block_Timestamp
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Dwf_Container_Guid
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Container_Modified_Time
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Dwf_Discipline_Guid
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # Dwf_Discipline_Modified_Time
    [False, False, False, False, False, False, False, False, False, False, False, False, False, True,  False],
    # ZValue
    [True,  True,  True,  True,  True,  True,  False, False, False, False, False, False, False, False, False],
    # Scan_Flag
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Mirror_Flag
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Inversion_Flag
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Paper_Scale
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Orientation
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Rotation
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Alignment
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Inked_Area
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Dpi_Resolution
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Paper_Offset
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Clipping_Rectangle
    [True,  True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Password
    [False, True,  True,  False, False, False, False, False, False, False, False, False, False, False, False],
    # Image_Representation
    [False, False, False, True,  True,  True,  False, False, False, False, False, False, False, False, False],
    # Targeted_Matrix_Rep
    [False, False, False, True,  True,  True,  False, False, False, False, False, False, False, False, False],
]


# Field indices for BLOCK_VARIABLE_RELATION table
class FieldIndex(IntEnum):
    """Field indices matching WT_BlockRef::WT_BlockRef_Variables enum"""
    FILE_OFFSET = 0
    BLOCK_SIZE = 1
    BLOCK_GUID = 2
    CREATION_TIME = 3
    MODIFICATION_TIME = 4
    ENCRYPTION = 5
    VALIDITY = 6
    VISIBILITY = 7
    BLOCK_MEANING = 8
    PARENT_BLOCK_GUID = 9
    RELATED_OVERLAY_HDR_BLOCK_GUID = 10
    SHEET_PRINT_SEQUENCE = 11
    PRINT_SEQUENCE_MODIFIED_TIME = 12
    PLANS_AND_SPECS_WEBSITE_GUID = 13
    LAST_SYNC_TIME = 14
    FLAG_MINI_DWF = 15
    MODIFIED_BLOCK_TIMESTAMP = 16
    DWF_CONTAINER_GUID = 17
    CONTAINER_MODIFIED_TIME = 18
    DWF_DISCIPLINE_GUID = 19
    DWF_DISCIPLINE_MODIFIED_TIME = 20
    ZVALUE = 21
    SCAN_FLAG = 22
    MIRROR_FLAG = 23
    INVERSION_FLAG = 24
    PAPER_SCALE = 25
    ORIENTATION = 26
    ROTATION = 27
    ALIGNMENT = 28
    INKED_AREA = 29
    DPI_RESOLUTION = 30
    PAPER_OFFSET = 31
    CLIPPING_RECTANGLE = 32
    PASSWORD = 33
    IMAGE_REPRESENTATION = 34
    TARGETED_MATRIX_REP = 35


def field_is_applicable(field: FieldIndex, block_format: BlockRefFormat) -> bool:
    """
    Check if a field is applicable for a given blockref format.

    Uses BLOCK_VARIABLE_RELATION table to determine field applicability.
    Based on Verify() macro in blockref.cpp.
    """
    # Get column index (offset from GRAPHICS_HDR = 335)
    col_idx = block_format - BlockRefFormat.GRAPHICS_HDR
    if col_idx < 0 or col_idx >= len(BLOCK_VARIABLE_RELATION[0]):
        return False
    return BLOCK_VARIABLE_RELATION[field][col_idx]


# =============================================================================
# CRITICAL SECTION 3: Data Structures
# =============================================================================

@dataclass
class GUID:
    """128-bit GUID structure (WD_GUID)"""
    data1: int  # 32-bit
    data2: int  # 16-bit
    data3: int  # 16-bit
    data4: bytes  # 8 bytes

    def __repr__(self) -> str:
        """Format GUID as standard string"""
        data4_hex = ''.join(f'{b:02x}' for b in self.data4)
        return f"{self.data1:08x}-{self.data2:04x}-{self.data3:04x}-{data4_hex[:4]}-{data4_hex[4:]}"


@dataclass
class FileTime:
    """Windows FILETIME structure (WT_FileTime)"""
    low_date_time: int  # 32-bit
    high_date_time: int  # 32-bit

    def to_timestamp(self) -> int:
        """Convert to 64-bit timestamp"""
        return (self.high_date_time << 32) | self.low_date_time


@dataclass
class LogicalPoint:
    """2D point in logical coordinates (WT_Logical_Point)"""
    x: int  # 32-bit signed
    y: int  # 32-bit signed


@dataclass
class Matrix:
    """4x4 transformation matrix"""
    elements: List[float]  # 16 doubles

    def __post_init__(self):
        if len(self.elements) != 16:
            raise ValueError("Matrix must have exactly 16 elements")


@dataclass
class BlockRef:
    """
    DWF BlockRef structure (WT_BlockRef).

    Represents a structured block in DWF file that can contain graphics,
    overlays, redlines, or other content. Fields present depend on format type.

    CRITICAL: This is a deprecated structure from DWF 00.55, but still required
    for backward compatibility. Modern DWF files use package format instead.
    """
    format: BlockRefFormat

    # Always present fields
    file_offset: Optional[int] = None  # Not always serialized
    block_size: int = 0

    # Optional fields (presence determined by BLOCK_VARIABLE_RELATION table)
    block_guid: Optional[GUID] = None
    creation_time: Optional[FileTime] = None
    modification_time: Optional[FileTime] = None
    encryption: int = 1  # Default = None (0x00000001)
    validity: bool = False
    visibility: bool = False
    block_meaning: Optional[int] = None  # BlockMeaning flags
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
    z_value: int = 0
    scan_flag: bool = False
    mirror_flag: bool = False
    inversion_flag: bool = False
    paper_scale: float = 0.0
    orientation: int = Orientation.ALWAYS_IN_SYNC
    rotation: int = 0  # 16-bit signed
    alignment: int = Alignment.ALIGN_NONE
    inked_area: Tuple[float, float] = (0.0, 0.0)
    dpi_resolution: int = 0  # 16-bit signed
    paper_offset: Tuple[float, float] = (0.0, 0.0)
    clipping_rectangle: Tuple[LogicalPoint, LogicalPoint] = None
    password: bytes = b''  # 32 bytes max
    image_representation: Tuple[int, int, int] = (0, 0, 0)
    targeted_matrix_rep: Optional[Matrix] = None


# =============================================================================
# CRITICAL SECTION 4: Extended Binary Parser
# =============================================================================

class ExtendedBinaryParser:
    """
    Parser for Extended Binary opcodes.

    Format: { + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + }

    Based on WT_Opcode::get_opcode() in opcode.cpp and WT_BlockRef::materialize()
    in blockref.cpp.
    """

    @staticmethod
    def parse_header(stream: BinaryIO) -> Tuple[int, int, int]:
        """
        Parse Extended Binary opcode header.

        Returns:
            (opcode_value, total_size, data_size)

        Raises:
            ValueError: If format is invalid
        """
        # Read opening '{'
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{' for Extended Binary, got {opening}")

        # Read size (4 bytes, little-endian int32)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise ValueError("Unexpected EOF reading opcode size")
        total_size = struct.unpack('<I', size_bytes)[0]

        # Read opcode value (2 bytes, little-endian uint16)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise ValueError("Unexpected EOF reading opcode value")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Calculate data size
        # total_size includes: opcode (2) + data + closing '}' (1)
        data_size = total_size - 2 - 1

        return opcode, total_size, data_size

    @staticmethod
    def read_guid(stream: BinaryIO) -> GUID:
        """Read a GUID from Extended Binary format (nested opcode)"""
        # GUIDs are serialized as nested opcodes: { size opcode data }
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError("Expected '{' for GUID opcode")

        size_bytes = stream.read(4)
        size = struct.unpack('<I', size_bytes)[0]

        opcode_bytes = stream.read(2)
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Read GUID data
        data1 = struct.unpack('<I', stream.read(4))[0]
        data2 = struct.unpack('<H', stream.read(2))[0]
        data3 = struct.unpack('<H', stream.read(2))[0]
        data4 = stream.read(8)

        # Read closing '}'
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError("Expected '}' at end of GUID opcode")

        return GUID(data1, data2, data3, data4)

    @staticmethod
    def read_filetime(stream: BinaryIO) -> FileTime:
        """Read a FileTime from Extended Binary format (nested opcode)"""
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError("Expected '{' for FileTime opcode")

        size_bytes = stream.read(4)
        size = struct.unpack('<I', size_bytes)[0]

        opcode_bytes = stream.read(2)
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Read FileTime data
        low = struct.unpack('<I', stream.read(4))[0]
        high = struct.unpack('<I', stream.read(4))[0]

        closing = stream.read(1)
        if closing != b'}':
            raise ValueError("Expected '}' at end of FileTime opcode")

        return FileTime(low, high)

    @staticmethod
    def read_nested_opcode_uint16(stream: BinaryIO) -> int:
        """Read a nested opcode containing a uint16 value"""
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError("Expected '{' for nested opcode")

        size_bytes = stream.read(4)
        opcode_bytes = stream.read(2)

        # Read uint16 value
        value = struct.unpack('<H', stream.read(2))[0]

        closing = stream.read(1)
        if closing != b'}':
            raise ValueError("Expected '}' at end of nested opcode")

        return value

    @staticmethod
    def verify_closing_brace(stream: BinaryIO):
        """Verify closing brace of Extended Binary opcode"""
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}' at end of opcode, got {closing}")


# =============================================================================
# CRITICAL SECTION 5: BlockRef Parser
# =============================================================================

class BlockRefParser:
    """
    Parser for BlockRef structures in Extended Binary format.

    Based on WT_BlockRef::materialize() in blockref.cpp lines 709-939.
    """

    def __init__(self, parser: ExtendedBinaryParser):
        self.parser = parser

    def parse_blockref(self, stream: BinaryIO, block_format: BlockRefFormat,
                      as_part_of_list: bool = False) -> BlockRef:
        """
        Parse a BlockRef from Extended Binary format.

        Args:
            stream: Input stream positioned after opcode header
            block_format: BlockRef format type
            as_part_of_list: Whether this is part of a directory list

        Returns:
            Parsed BlockRef object
        """
        blockref = BlockRef(format=block_format)

        # File offset (only if part of directory list)
        if as_part_of_list and field_is_applicable(FieldIndex.FILE_OFFSET, block_format):
            blockref.file_offset = struct.unpack('<I', stream.read(4))[0]

        # Block size (always present)
        if field_is_applicable(FieldIndex.BLOCK_SIZE, block_format):
            blockref.block_size = struct.unpack('<I', stream.read(4))[0]

        # Block GUID
        if field_is_applicable(FieldIndex.BLOCK_GUID, block_format):
            blockref.block_guid = self.parser.read_guid(stream)

        # Creation time
        if field_is_applicable(FieldIndex.CREATION_TIME, block_format):
            blockref.creation_time = self.parser.read_filetime(stream)

        # Modification time
        if field_is_applicable(FieldIndex.MODIFICATION_TIME, block_format):
            blockref.modification_time = self.parser.read_filetime(stream)

        # Encryption
        if field_is_applicable(FieldIndex.ENCRYPTION, block_format):
            blockref.encryption = self.parser.read_nested_opcode_uint16(stream)

        # Validity flag
        if field_is_applicable(FieldIndex.VALIDITY, block_format):
            flag = stream.read(1)
            blockref.validity = (flag == b'1')

        # Visibility flag
        if field_is_applicable(FieldIndex.VISIBILITY, block_format):
            flag = stream.read(1)
            blockref.visibility = (flag == b'1')

        # Block meaning
        if field_is_applicable(FieldIndex.BLOCK_MEANING, block_format):
            blockref.block_meaning = self.parser.read_nested_opcode_uint16(stream)

        # Parent block GUID
        if field_is_applicable(FieldIndex.PARENT_BLOCK_GUID, block_format):
            blockref.parent_block_guid = self.parser.read_guid(stream)

        # Related overlay header block GUID
        if field_is_applicable(FieldIndex.RELATED_OVERLAY_HDR_BLOCK_GUID, block_format):
            blockref.related_overlay_hdr_block_guid = self.parser.read_guid(stream)

        # Sheet print sequence
        if field_is_applicable(FieldIndex.SHEET_PRINT_SEQUENCE, block_format):
            blockref.sheet_print_sequence = struct.unpack('<i', stream.read(4))[0]

        # Print sequence modified time
        if field_is_applicable(FieldIndex.PRINT_SEQUENCE_MODIFIED_TIME, block_format):
            blockref.print_sequence_modified_time = self.parser.read_filetime(stream)

        # Plans and specs website GUID
        if field_is_applicable(FieldIndex.PLANS_AND_SPECS_WEBSITE_GUID, block_format):
            blockref.plans_and_specs_website_guid = self.parser.read_guid(stream)

        # Last sync time
        if field_is_applicable(FieldIndex.LAST_SYNC_TIME, block_format):
            blockref.last_sync_time = self.parser.read_filetime(stream)

        # Mini DWF flag
        if field_is_applicable(FieldIndex.FLAG_MINI_DWF, block_format):
            flag = stream.read(1)
            blockref.flag_mini_dwf = (flag == b'1')

        # Modified block timestamp
        if field_is_applicable(FieldIndex.MODIFIED_BLOCK_TIMESTAMP, block_format):
            blockref.modified_block_timestamp = self.parser.read_filetime(stream)

        # DWF container GUID
        if field_is_applicable(FieldIndex.DWF_CONTAINER_GUID, block_format):
            blockref.dwf_container_guid = self.parser.read_guid(stream)

        # Container modified time
        if field_is_applicable(FieldIndex.CONTAINER_MODIFIED_TIME, block_format):
            blockref.container_modified_time = self.parser.read_filetime(stream)

        # DWF discipline GUID
        if field_is_applicable(FieldIndex.DWF_DISCIPLINE_GUID, block_format):
            blockref.dwf_discipline_guid = self.parser.read_guid(stream)

        # DWF discipline modified time
        if field_is_applicable(FieldIndex.DWF_DISCIPLINE_MODIFIED_TIME, block_format):
            blockref.dwf_discipline_modified_time = self.parser.read_filetime(stream)

        # Z-value
        if field_is_applicable(FieldIndex.ZVALUE, block_format):
            blockref.z_value = struct.unpack('<i', stream.read(4))[0]

        # Scan flag
        if field_is_applicable(FieldIndex.SCAN_FLAG, block_format):
            flag = stream.read(1)
            blockref.scan_flag = (flag == b'1')

        # Mirror flag
        if field_is_applicable(FieldIndex.MIRROR_FLAG, block_format):
            flag = stream.read(1)
            blockref.mirror_flag = (flag == b'1')

        # Inversion flag
        if field_is_applicable(FieldIndex.INVERSION_FLAG, block_format):
            flag = stream.read(1)
            blockref.inversion_flag = (flag == b'1')

        # Paper scale (double)
        if field_is_applicable(FieldIndex.PAPER_SCALE, block_format):
            blockref.paper_scale = struct.unpack('<d', stream.read(8))[0]

        # Orientation
        if field_is_applicable(FieldIndex.ORIENTATION, block_format):
            blockref.orientation = self.parser.read_nested_opcode_uint16(stream)

        # Rotation
        if field_is_applicable(FieldIndex.ROTATION, block_format):
            blockref.rotation = struct.unpack('<h', stream.read(2))[0]

        # Alignment
        if field_is_applicable(FieldIndex.ALIGNMENT, block_format):
            blockref.alignment = self.parser.read_nested_opcode_uint16(stream)

        # Inked area (2 doubles)
        if field_is_applicable(FieldIndex.INKED_AREA, block_format):
            area0 = struct.unpack('<d', stream.read(8))[0]
            area1 = struct.unpack('<d', stream.read(8))[0]
            blockref.inked_area = (area0, area1)

        # DPI resolution
        if field_is_applicable(FieldIndex.DPI_RESOLUTION, block_format):
            blockref.dpi_resolution = struct.unpack('<h', stream.read(2))[0]

        # Paper offset (2 doubles)
        if field_is_applicable(FieldIndex.PAPER_OFFSET, block_format):
            offset0 = struct.unpack('<d', stream.read(8))[0]
            offset1 = struct.unpack('<d', stream.read(8))[0]
            blockref.paper_offset = (offset0, offset1)

        # Clipping rectangle (2 WT_Logical_Point)
        if field_is_applicable(FieldIndex.CLIPPING_RECTANGLE, block_format):
            x1 = struct.unpack('<i', stream.read(4))[0]
            y1 = struct.unpack('<i', stream.read(4))[0]
            x2 = struct.unpack('<i', stream.read(4))[0]
            y2 = struct.unpack('<i', stream.read(4))[0]
            blockref.clipping_rectangle = (LogicalPoint(x1, y1), LogicalPoint(x2, y2))

        # Password
        if field_is_applicable(FieldIndex.PASSWORD, block_format):
            # Password is a nested opcode with 32 bytes
            opening = stream.read(1)
            if opening == b'{':
                stream.read(4)  # size
                stream.read(2)  # opcode
                blockref.password = stream.read(32)
                stream.read(1)  # closing '}'

        # Image representation (3 int32)
        if field_is_applicable(FieldIndex.IMAGE_REPRESENTATION, block_format):
            img0 = struct.unpack('<i', stream.read(4))[0]
            img1 = struct.unpack('<i', stream.read(4))[0]
            img2 = struct.unpack('<i', stream.read(4))[0]
            blockref.image_representation = (img0, img1, img2)

        # Targeted matrix representation (16 doubles)
        if field_is_applicable(FieldIndex.TARGETED_MATRIX_REP, block_format):
            elements = []
            for _ in range(16):
                elements.append(struct.unpack('<d', stream.read(8))[0])
            blockref.targeted_matrix_rep = Matrix(elements)

        # Verify closing brace
        self.parser.verify_closing_brace(stream)

        return blockref


# =============================================================================
# CRITICAL SECTION 6: Opcode Handlers
# =============================================================================

def handle_graphics_hdr(stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_GRAPHICS_HDR (0x0012, ID 335).

    Graphics header block - defines a graphics section header with metadata
    about the graphics content that follows.

    Args:
        stream: Input stream positioned after opcode header
        opcode: Opcode value (0x0012)
        data_size: Size of data portion

    Returns:
        Dictionary with parsed graphics header data
    """
    parser = ExtendedBinaryParser()
    blockref_parser = BlockRefParser(parser)

    blockref = blockref_parser.parse_blockref(
        stream,
        BlockRefFormat.GRAPHICS_HDR,
        as_part_of_list=False
    )

    return {
        'opcode': 'GRAPHICS_HDR',
        'opcode_id': 335,
        'hex_value': '0x0012',
        'format': 'Graphics_Hdr',
        'block_size': blockref.block_size,
        'block_guid': str(blockref.block_guid) if blockref.block_guid else None,
        'creation_time': blockref.creation_time,
        'modification_time': blockref.modification_time,
        'validity': blockref.validity,
        'visibility': blockref.visibility,
        'z_value': blockref.z_value,
        'scan_flag': blockref.scan_flag,
        'mirror_flag': blockref.mirror_flag,
        'inversion_flag': blockref.inversion_flag,
        'paper_scale': blockref.paper_scale,
        'orientation': blockref.orientation,
        'rotation': blockref.rotation,
        'alignment': blockref.alignment,
        'inked_area': blockref.inked_area,
        'dpi_resolution': blockref.dpi_resolution,
        'paper_offset': blockref.paper_offset,
        'clipping_rectangle': blockref.clipping_rectangle,
        'encryption': blockref.encryption,
        'full_blockref': blockref
    }


def handle_overlay_hdr(stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_OVERLAY_HDR (0x0013, ID 336).

    Overlay header block - defines an overlay section header. Overlays are
    additional graphics layers that can be toggled on/off.

    Args:
        stream: Input stream positioned after opcode header
        opcode: Opcode value (0x0013)
        data_size: Size of data portion

    Returns:
        Dictionary with parsed overlay header data
    """
    parser = ExtendedBinaryParser()
    blockref_parser = BlockRefParser(parser)

    blockref = blockref_parser.parse_blockref(
        stream,
        BlockRefFormat.OVERLAY_HDR,
        as_part_of_list=False
    )

    return {
        'opcode': 'OVERLAY_HDR',
        'opcode_id': 336,
        'hex_value': '0x0013',
        'format': 'Overlay_Hdr',
        'block_size': blockref.block_size,
        'block_guid': str(blockref.block_guid) if blockref.block_guid else None,
        'creation_time': blockref.creation_time,
        'modification_time': blockref.modification_time,
        'validity': blockref.validity,
        'visibility': blockref.visibility,
        'block_meaning': blockref.block_meaning,
        'parent_block_guid': str(blockref.parent_block_guid) if blockref.parent_block_guid else None,
        'z_value': blockref.z_value,
        'scan_flag': blockref.scan_flag,
        'mirror_flag': blockref.mirror_flag,
        'inversion_flag': blockref.inversion_flag,
        'paper_scale': blockref.paper_scale,
        'orientation': blockref.orientation,
        'rotation': blockref.rotation,
        'alignment': blockref.alignment,
        'inked_area': blockref.inked_area,
        'dpi_resolution': blockref.dpi_resolution,
        'paper_offset': blockref.paper_offset,
        'clipping_rectangle': blockref.clipping_rectangle,
        'password': blockref.password,
        'encryption': blockref.encryption,
        'full_blockref': blockref
    }


def handle_redline_hdr(stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_REDLINE_HDR (0x0014, ID 337).

    Redline header block - defines a redline section header. Redlines are
    markup/annotation layers typically used for review and comments.

    Args:
        stream: Input stream positioned after opcode header
        opcode: Opcode value (0x0014)
        data_size: Size of data portion

    Returns:
        Dictionary with parsed redline header data
    """
    parser = ExtendedBinaryParser()
    blockref_parser = BlockRefParser(parser)

    blockref = blockref_parser.parse_blockref(
        stream,
        BlockRefFormat.REDLINE_HDR,
        as_part_of_list=False
    )

    return {
        'opcode': 'REDLINE_HDR',
        'opcode_id': 337,
        'hex_value': '0x0014',
        'format': 'Redline_Hdr',
        'block_size': blockref.block_size,
        'block_guid': str(blockref.block_guid) if blockref.block_guid else None,
        'creation_time': blockref.creation_time,
        'modification_time': blockref.modification_time,
        'validity': blockref.validity,
        'visibility': blockref.visibility,
        'parent_block_guid': str(blockref.parent_block_guid) if blockref.parent_block_guid else None,
        'z_value': blockref.z_value,
        'scan_flag': blockref.scan_flag,
        'mirror_flag': blockref.mirror_flag,
        'inversion_flag': blockref.inversion_flag,
        'paper_scale': blockref.paper_scale,
        'orientation': blockref.orientation,
        'rotation': blockref.rotation,
        'alignment': blockref.alignment,
        'inked_area': blockref.inked_area,
        'dpi_resolution': blockref.dpi_resolution,
        'paper_offset': blockref.paper_offset,
        'clipping_rectangle': blockref.clipping_rectangle,
        'password': blockref.password,
        'encryption': blockref.encryption,
        'full_blockref': blockref
    }


def handle_graphics(stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_GRAPHICS (0x0020, ID 342).

    Graphics block - contains the actual graphics data for a graphics section.
    This follows a GRAPHICS_HDR and contains drawing opcodes.

    Args:
        stream: Input stream positioned after opcode header
        opcode: Opcode value (0x0020)
        data_size: Size of data portion

    Returns:
        Dictionary with parsed graphics block data
    """
    parser = ExtendedBinaryParser()
    blockref_parser = BlockRefParser(parser)

    blockref = blockref_parser.parse_blockref(
        stream,
        BlockRefFormat.GRAPHICS,
        as_part_of_list=False
    )

    return {
        'opcode': 'GRAPHICS',
        'opcode_id': 342,
        'hex_value': '0x0020',
        'format': 'Graphics',
        'block_size': blockref.block_size,
        'block_guid': str(blockref.block_guid) if blockref.block_guid else None,
        'creation_time': blockref.creation_time,
        'modification_time': blockref.modification_time,
        'validity': blockref.validity,
        'full_blockref': blockref
    }


def handle_overlay(stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_OVERLAY (0x0021, ID 343).

    Overlay block - contains the actual overlay graphics data. This follows
    an OVERLAY_HDR and contains drawing opcodes for overlay content.

    Args:
        stream: Input stream positioned after opcode header
        opcode: Opcode value (0x0021)
        data_size: Size of data portion

    Returns:
        Dictionary with parsed overlay block data
    """
    parser = ExtendedBinaryParser()
    blockref_parser = BlockRefParser(parser)

    blockref = blockref_parser.parse_blockref(
        stream,
        BlockRefFormat.OVERLAY,
        as_part_of_list=False
    )

    return {
        'opcode': 'OVERLAY',
        'opcode_id': 343,
        'hex_value': '0x0021',
        'format': 'Overlay',
        'block_size': blockref.block_size,
        'block_guid': str(blockref.block_guid) if blockref.block_guid else None,
        'creation_time': blockref.creation_time,
        'modification_time': blockref.modification_time,
        'validity': blockref.validity,
        'full_blockref': blockref
    }


def handle_redline(stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXBO_REDLINE (0x0022, ID 344).

    Redline block - contains the actual redline/markup data. This follows
    a REDLINE_HDR and contains drawing opcodes for redline annotations.

    Args:
        stream: Input stream positioned after opcode header
        opcode: Opcode value (0x0022)
        data_size: Size of data portion

    Returns:
        Dictionary with parsed redline block data
    """
    parser = ExtendedBinaryParser()
    blockref_parser = BlockRefParser(parser)

    blockref = blockref_parser.parse_blockref(
        stream,
        BlockRefFormat.REDLINE,
        as_part_of_list=False
    )

    return {
        'opcode': 'REDLINE',
        'opcode_id': 344,
        'hex_value': '0x0022',
        'format': 'Redline',
        'block_size': blockref.block_size,
        'block_guid': str(blockref.block_guid) if blockref.block_guid else None,
        'creation_time': blockref.creation_time,
        'modification_time': blockref.modification_time,
        'validity': blockref.validity,
        'full_blockref': blockref
    }


# =============================================================================
# CRITICAL SECTION 7: Opcode Dispatcher
# =============================================================================

OPCODE_HANDLERS = {
    0x0012: handle_graphics_hdr,
    0x0013: handle_overlay_hdr,
    0x0014: handle_redline_hdr,
    0x0020: handle_graphics,
    0x0021: handle_overlay,
    0x0022: handle_redline,
}


def dispatch_opcode(stream: BinaryIO) -> Dict[str, Any]:
    """
    Dispatch an Extended Binary opcode to the appropriate handler.

    Args:
        stream: Input stream positioned at start of opcode ('{')

    Returns:
        Parsed opcode data

    Raises:
        ValueError: If opcode is unknown or invalid
    """
    parser = ExtendedBinaryParser()
    opcode, total_size, data_size = parser.parse_header(stream)

    handler = OPCODE_HANDLERS.get(opcode)
    if not handler:
        raise ValueError(f"Unknown Extended Binary opcode: 0x{opcode:04x}")

    return handler(stream, opcode, data_size)


# =============================================================================
# TESTS
# =============================================================================

def test_graphics_hdr_minimal():
    """Test GRAPHICS_HDR with minimal data"""
    from io import BytesIO

    # Build test data: { + size + opcode + minimal BlockRef + }
    data = BytesIO()
    data.write(b'{')

    # Calculate size (we'll build content first, then update)
    content = BytesIO()

    # Write block size (required field)
    content.write(struct.pack('<I', 1024))  # block_size = 1024

    # Block GUID (required for GRAPHICS_HDR)
    content.write(b'{')
    guid_size = 2 + 16 + 1  # opcode + data + }
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))  # GUID opcode
    content.write(struct.pack('<I', 0x12345678))  # data1
    content.write(struct.pack('<H', 0xABCD))  # data2
    content.write(struct.pack('<H', 0xEF01))  # data3
    content.write(b'\x01\x02\x03\x04\x05\x06\x07\x08')  # data4
    content.write(b'}')

    # Creation time (required)
    content.write(b'{')
    ft_size = 2 + 8 + 1  # opcode + low + high + }
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))  # FileTime opcode
    content.write(struct.pack('<I', 0x11111111))  # low
    content.write(struct.pack('<I', 0x22222222))  # high
    content.write(b'}')

    # Modification time (required)
    content.write(b'{')
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))  # FileTime opcode
    content.write(struct.pack('<I', 0x33333333))  # low
    content.write(struct.pack('<I', 0x44444444))  # high
    content.write(b'}')

    # Encryption (required for GRAPHICS_HDR)
    content.write(b'{')
    enc_size = 2 + 2 + 1  # opcode + value + }
    content.write(struct.pack('<I', enc_size))
    content.write(struct.pack('<H', 0x0324))  # Encryption opcode
    content.write(struct.pack('<H', 1))  # None
    content.write(b'}')

    # Write validity flag (required)
    content.write(b'1')  # validity = true

    # Write visibility flag (required)
    content.write(b'0')  # visibility = false

    # Write z_value (required for GRAPHICS_HDR)
    content.write(struct.pack('<i', 10))  # z_value = 10

    # Write scan_flag
    content.write(b'0')

    # Write mirror_flag
    content.write(b'0')

    # Write inversion_flag
    content.write(b'0')

    # Write paper_scale (double)
    content.write(struct.pack('<d', 1.0))

    # Orientation (nested opcode)
    content.write(b'{')
    or_size = 2 + 2 + 1
    content.write(struct.pack('<I', or_size))
    content.write(struct.pack('<H', 0x0326))  # Orientation opcode
    content.write(struct.pack('<H', 1))  # Always_In_Sync
    content.write(b'}')

    # Write rotation (int16)
    content.write(struct.pack('<h', 0))

    # Alignment (nested opcode)
    content.write(b'{')
    al_size = 2 + 2 + 1
    content.write(struct.pack('<I', al_size))
    content.write(struct.pack('<H', 0x0328))  # Alignment opcode
    content.write(struct.pack('<H', 0x400))  # ALIGN_NONE
    content.write(b'}')

    # Write inked_area (2 doubles)
    content.write(struct.pack('<d', 0.0))
    content.write(struct.pack('<d', 0.0))

    # Write dpi_resolution (int16)
    content.write(struct.pack('<h', 300))

    # Write paper_offset (2 doubles)
    content.write(struct.pack('<d', 0.0))
    content.write(struct.pack('<d', 0.0))

    # Write clipping_rectangle (2 LogicalPoints = 4 int32)
    for _ in range(4):
        content.write(struct.pack('<i', 0))

    # Closing brace
    content.write(b'}')

    # Now write size and opcode
    content_bytes = content.getvalue()
    size = 2 + len(content_bytes)  # opcode (2) + content

    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', 0x0012))  # GRAPHICS_HDR opcode
    data.write(content_bytes)

    # Parse
    data.seek(0)
    result = dispatch_opcode(data)

    assert result['opcode'] == 'GRAPHICS_HDR'
    assert result['opcode_id'] == 335
    assert result['block_size'] == 1024
    assert result['validity'] == True
    assert result['z_value'] == 10
    assert result['dpi_resolution'] == 300

    print("✓ test_graphics_hdr_minimal passed")


def test_overlay_hdr_with_guid():
    """Test OVERLAY_HDR with GUID"""
    from io import BytesIO

    # Build test with a GUID
    data = BytesIO()
    data.write(b'{')

    content = BytesIO()

    # Block size
    content.write(struct.pack('<I', 2048))

    # GUID (nested opcode)
    content.write(b'{')
    guid_size = 2 + 4 + 2 + 2 + 8 + 1  # opcode + data1 + data2 + data3 + data4 + }
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))  # GUID opcode
    content.write(struct.pack('<I', 0x12345678))  # data1
    content.write(struct.pack('<H', 0xABCD))  # data2
    content.write(struct.pack('<H', 0xEF01))  # data3
    content.write(b'\x01\x02\x03\x04\x05\x06\x07\x08')  # data4
    content.write(b'}')

    # Creation time (nested opcode)
    content.write(b'{')
    ft_size = 2 + 4 + 4 + 1  # opcode + low + high + }
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))  # FileTime opcode
    content.write(struct.pack('<I', 0x11111111))  # low
    content.write(struct.pack('<I', 0x22222222))  # high
    content.write(b'}')

    # Modification time (nested opcode)
    content.write(b'{')
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))  # FileTime opcode
    content.write(struct.pack('<I', 0x33333333))  # low
    content.write(struct.pack('<I', 0x44444444))  # high
    content.write(b'}')

    # Encryption (nested opcode with uint16)
    content.write(b'{')
    enc_size = 2 + 2 + 1  # opcode + value + }
    content.write(struct.pack('<I', enc_size))
    content.write(struct.pack('<H', 0x0324))  # Encryption opcode
    content.write(struct.pack('<H', 1))  # None
    content.write(b'}')

    # Validity
    content.write(b'1')

    # Visibility
    content.write(b'1')

    # Block meaning (nested opcode with uint16)
    content.write(b'{')
    bm_size = 2 + 2 + 1
    content.write(struct.pack('<I', bm_size))
    content.write(struct.pack('<H', 0x0321))  # BlockMeaning opcode
    content.write(struct.pack('<H', BlockMeaning.REDLINE))
    content.write(b'}')

    # Parent block GUID
    content.write(b'{')
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))
    content.write(struct.pack('<I', 0xAABBCCDD))
    content.write(struct.pack('<H', 0x1122))
    content.write(struct.pack('<H', 0x3344))
    content.write(b'\xAA\xBB\xCC\xDD\xEE\xFF\x00\x11')
    content.write(b'}')

    # Z-value
    content.write(struct.pack('<i', 5))

    # Flags
    content.write(b'1')  # scan
    content.write(b'0')  # mirror
    content.write(b'1')  # inversion

    # Paper scale
    content.write(struct.pack('<d', 2.5))

    # Orientation (nested)
    content.write(b'{')
    or_size = 2 + 2 + 1
    content.write(struct.pack('<I', or_size))
    content.write(struct.pack('<H', 0x0326))  # Orientation opcode
    content.write(struct.pack('<H', Orientation.DECOUPLED))
    content.write(b'}')

    # Rotation
    content.write(struct.pack('<h', 90))

    # Alignment (nested)
    content.write(b'{')
    al_size = 2 + 2 + 1
    content.write(struct.pack('<I', al_size))
    content.write(struct.pack('<H', 0x0328))  # Alignment opcode
    content.write(struct.pack('<H', Alignment.ALIGN_CENTER))
    content.write(b'}')

    # Inked area
    content.write(struct.pack('<d', 100.5))
    content.write(struct.pack('<d', 200.5))

    # DPI
    content.write(struct.pack('<h', 600))

    # Paper offset
    content.write(struct.pack('<d', 10.0))
    content.write(struct.pack('<d', 20.0))

    # Clipping rectangle
    for val in [100, 200, 300, 400]:
        content.write(struct.pack('<i', val))

    # Password (nested with 32 bytes)
    content.write(b'{')
    pw_size = 2 + 32 + 1
    content.write(struct.pack('<I', pw_size))
    content.write(struct.pack('<H', 0x0331))  # Password opcode
    content.write(b'secret_password_123' + b'\x00' * 13)
    content.write(b'}')

    # Closing
    content.write(b'}')

    # Write header
    content_bytes = content.getvalue()
    size = 2 + len(content_bytes)
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', 0x0013))  # OVERLAY_HDR
    data.write(content_bytes)

    # Parse
    data.seek(0)
    result = dispatch_opcode(data)

    assert result['opcode'] == 'OVERLAY_HDR'
    assert result['opcode_id'] == 336
    assert result['block_size'] == 2048
    assert result['validity'] == True
    assert result['visibility'] == True
    assert '12345678' in result['block_guid']
    assert result['z_value'] == 5
    assert result['paper_scale'] == 2.5
    assert result['rotation'] == 90
    assert result['dpi_resolution'] == 600

    print("✓ test_overlay_hdr_with_guid passed")


def test_redline_hdr():
    """Test REDLINE_HDR opcode"""
    from io import BytesIO

    data = BytesIO()
    data.write(b'{')

    content = BytesIO()

    # Block size
    content.write(struct.pack('<I', 512))

    # Block GUID
    content.write(b'{')
    guid_size = 2 + 16 + 1
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))
    content.write(struct.pack('<I', 0xDEADBEEF))
    content.write(struct.pack('<H', 0xCAFE))
    content.write(struct.pack('<H', 0xBABE))
    content.write(b'\x00\x11\x22\x33\x44\x55\x66\x77')
    content.write(b'}')

    # Creation time
    content.write(b'{')
    ft_size = 2 + 8 + 1
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))
    content.write(struct.pack('<I', 0xAAAAAAAA))
    content.write(struct.pack('<I', 0xBBBBBBBB))
    content.write(b'}')

    # Modification time
    content.write(b'{')
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))
    content.write(struct.pack('<I', 0xCCCCCCCC))
    content.write(struct.pack('<I', 0xDDDDDDDD))
    content.write(b'}')

    # Encryption
    content.write(b'{')
    enc_size = 2 + 2 + 1
    content.write(struct.pack('<I', enc_size))
    content.write(struct.pack('<H', 0x0324))
    content.write(struct.pack('<H', 1))
    content.write(b'}')

    # Validity
    content.write(b'1')

    # Visibility
    content.write(b'0')

    # Parent GUID
    content.write(b'{')
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))
    content.write(struct.pack('<I', 0x11111111))
    content.write(struct.pack('<H', 0x2222))
    content.write(struct.pack('<H', 0x3333))
    content.write(b'\x44\x55\x66\x77\x88\x99\xAA\xBB')
    content.write(b'}')

    # Z-value
    content.write(struct.pack('<i', -5))

    # Flags
    content.write(b'0' * 3)

    # Paper scale
    content.write(struct.pack('<d', 1.5))

    # Orientation
    content.write(b'{')
    or_size = 2 + 2 + 1
    content.write(struct.pack('<I', or_size))
    content.write(struct.pack('<H', 0x0326))
    content.write(struct.pack('<H', 1))
    content.write(b'}')

    # Rotation
    content.write(struct.pack('<h', 0))

    # Alignment
    content.write(b'{')
    al_size = 2 + 2 + 1
    content.write(struct.pack('<I', al_size))
    content.write(struct.pack('<H', 0x0328))
    content.write(struct.pack('<H', 0x400))
    content.write(b'}')

    # Inked area, DPI, paper offset, clipping rect
    content.write(struct.pack('<d', 0.0))
    content.write(struct.pack('<d', 0.0))
    content.write(struct.pack('<h', 72))
    content.write(struct.pack('<d', 0.0))
    content.write(struct.pack('<d', 0.0))
    for _ in range(4):
        content.write(struct.pack('<i', 0))

    # Password
    content.write(b'{')
    pw_size = 2 + 32 + 1
    content.write(struct.pack('<I', pw_size))
    content.write(struct.pack('<H', 0x0331))
    content.write(b'redline_pw' + b'\x00' * 22)
    content.write(b'}')

    content.write(b'}')

    # Write header
    content_bytes = content.getvalue()
    size = 2 + len(content_bytes)
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', 0x0014))  # REDLINE_HDR
    data.write(content_bytes)

    # Parse
    data.seek(0)
    result = dispatch_opcode(data)

    assert result['opcode'] == 'REDLINE_HDR'
    assert result['opcode_id'] == 337
    assert result['block_size'] == 512
    assert result['z_value'] == -5

    print("✓ test_redline_hdr passed")


def test_graphics_block():
    """Test GRAPHICS block opcode (simplified content block)"""
    from io import BytesIO

    data = BytesIO()
    data.write(b'{')

    content = BytesIO()

    # Graphics blocks have fewer fields
    content.write(struct.pack('<I', 4096))  # block_size

    # GUID
    content.write(b'{')
    guid_size = 2 + 16 + 1
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))
    content.write(struct.pack('<I', 0x99999999))
    content.write(struct.pack('<H', 0x8888))
    content.write(struct.pack('<H', 0x7777))
    content.write(b'\xFF\xEE\xDD\xCC\xBB\xAA\x99\x88')
    content.write(b'}')

    # Creation time
    content.write(b'{')
    ft_size = 2 + 8 + 1
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))
    content.write(struct.pack('<I', 0x12345678))
    content.write(struct.pack('<I', 0x9ABCDEF0))
    content.write(b'}')

    # Modification time
    content.write(b'{')
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))
    content.write(struct.pack('<I', 0x11111111))
    content.write(struct.pack('<I', 0x22222222))
    content.write(b'}')

    # Validity
    content.write(b'1')

    content.write(b'}')

    # Write header
    content_bytes = content.getvalue()
    size = 2 + len(content_bytes)
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', 0x0020))  # GRAPHICS
    data.write(content_bytes)

    # Parse
    data.seek(0)
    result = dispatch_opcode(data)

    assert result['opcode'] == 'GRAPHICS'
    assert result['opcode_id'] == 342
    assert result['block_size'] == 4096
    assert result['validity'] == True

    print("✓ test_graphics_block passed")


def test_overlay_block():
    """Test OVERLAY block opcode"""
    from io import BytesIO

    data = BytesIO()
    data.write(b'{')

    content = BytesIO()
    content.write(struct.pack('<I', 2048))

    # GUID
    content.write(b'{')
    guid_size = 2 + 16 + 1
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))
    content.write(b'\x00' * 16)
    content.write(b'}')

    # Times
    content.write(b'{')
    ft_size = 2 + 8 + 1
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))
    content.write(struct.pack('<Q', 0))
    content.write(b'}')

    content.write(b'{')
    content.write(struct.pack('<I', ft_size))
    content.write(struct.pack('<H', 0x0334))
    content.write(struct.pack('<Q', 0))
    content.write(b'}')

    # Validity
    content.write(b'0')

    content.write(b'}')

    content_bytes = content.getvalue()
    size = 2 + len(content_bytes)
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', 0x0021))  # OVERLAY
    data.write(content_bytes)

    data.seek(0)
    result = dispatch_opcode(data)

    assert result['opcode'] == 'OVERLAY'
    assert result['opcode_id'] == 343
    assert result['validity'] == False

    print("✓ test_overlay_block passed")


def test_redline_block():
    """Test REDLINE block opcode"""
    from io import BytesIO

    data = BytesIO()
    data.write(b'{')

    content = BytesIO()
    content.write(struct.pack('<I', 1024))

    # GUID
    content.write(b'{')
    guid_size = 2 + 16 + 1
    content.write(struct.pack('<I', guid_size))
    content.write(struct.pack('<H', 0x0330))
    content.write(struct.pack('<I', 0xFFFFFFFF))
    content.write(struct.pack('<I', 0xEEEEEEEE))
    content.write(struct.pack('<Q', 0xDDDDDDDDCCCCCCCC))
    content.write(b'}')

    # Times
    ft_size = 2 + 8 + 1
    for _ in range(2):
        content.write(b'{')
        content.write(struct.pack('<I', ft_size))
        content.write(struct.pack('<H', 0x0334))
        content.write(struct.pack('<Q', 123456789))
        content.write(b'}')

    # Validity
    content.write(b'1')

    content.write(b'}')

    content_bytes = content.getvalue()
    size = 2 + len(content_bytes)
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', 0x0022))  # REDLINE
    data.write(content_bytes)

    data.seek(0)
    result = dispatch_opcode(data)

    assert result['opcode'] == 'REDLINE'
    assert result['opcode_id'] == 344
    assert result['block_size'] == 1024

    print("✓ test_redline_block passed")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*70)
    print("Agent 31: Extended Binary Structure Opcodes - Test Suite")
    print("="*70 + "\n")

    test_graphics_hdr_minimal()
    test_overlay_hdr_with_guid()
    test_redline_hdr()
    test_graphics_block()
    test_overlay_block()
    test_redline_block()

    print("\n" + "="*70)
    print("All tests passed! 6 opcodes successfully implemented.")
    print("="*70 + "\n")


if __name__ == '__main__':
    run_all_tests()
