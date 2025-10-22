"""
Agent 26: DWF Extended ASCII Structure and GUID Opcodes
=======================================================

This module implements 6 DWF Extended ASCII structure and GUID opcodes that handle
object organization, identification, and metadata in DWF files.

Opcodes Implemented:
-------------------
1. WD_EXAO_GUID (332) - `(Guid` - GUID identifier
2. WD_EXAO_GUID_LIST (361) - `(GuidList` - GUID list
3. WD_EXAO_BLOCKREF (351) - `(BlockRef` - Block reference
4. WD_EXAO_DIRECTORY (353) - `(Directory` - Directory
5. WD_EXAO_USERDATA (355) - `(UserData` - User-defined data
6. WD_EXAO_OBJECT_NODE (366) - `(Node` - Object node

GUID Format:
-----------
GUIDs follow the standard format: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
- Data1: 32-bit unsigned integer
- Data2: 16-bit unsigned integer
- Data3: 16-bit unsigned integer
- Data4: 8 bytes

Source Files:
------------
- blockref_defs.cpp: WT_Guid implementation (lines 1025-1236)
- guid_list.cpp: WT_Guid_List implementation (lines 1-307)
- blockref.cpp: WT_BlockRef implementation (lines 1-1106)
- directory.cpp: WT_Directory implementation (lines 1-452)
- userdata.cpp: WT_UserData implementation (lines 1-309)
- object_node.cpp: WT_Object_Node implementation (lines 1-353)

Author: Agent 26
Date: 2025-10-22
"""

import struct
import io
from typing import Dict, List, Any, Optional, Tuple


# ============================================================================
# GUID Structure and Utilities
# ============================================================================

class GUID:
    """
    Represents a GUID (Globally Unique Identifier).

    Format: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}

    Structure (from typedefs_defines.h:60-72):
    - Data1: 32-bit unsigned integer
    - Data2: 16-bit unsigned integer
    - Data3: 16-bit unsigned integer
    - Data4: 8 bytes
    """

    def __init__(self, data1: int = 0, data2: int = 0, data3: int = 0,
                 data4: bytes = b'\x00' * 8):
        """
        Initialize a GUID.

        Args:
            data1: 32-bit unsigned integer
            data2: 16-bit unsigned integer
            data3: 16-bit unsigned integer
            data4: 8 bytes
        """
        self.data1 = data1  # WT_Unsigned_Integer32
        self.data2 = data2  # WT_Unsigned_Integer16
        self.data3 = data3  # WT_Unsigned_Integer16
        self.data4 = data4 if isinstance(data4, bytes) else bytes(data4)  # 8 bytes

    def to_string(self) -> str:
        """
        Convert GUID to standard string format.

        Returns:
            String in format: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
        """
        # Format: {Data1-Data2-Data3-Data4[0:2]-Data4[2:8]}
        return (f"{{{self.data1:08x}-{self.data2:04x}-{self.data3:04x}-"
                f"{self.data4[0]:02x}{self.data4[1]:02x}-"
                f"{''.join(f'{b:02x}' for b in self.data4[2:8])}}}")

    @classmethod
    def from_string(cls, guid_str: str) -> 'GUID':
        """
        Parse a GUID from string format.

        Args:
            guid_str: String in format {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}

        Returns:
            GUID instance
        """
        # Remove braces if present
        guid_str = guid_str.strip('{}')
        parts = guid_str.split('-')

        if len(parts) != 5:
            raise ValueError(f"Invalid GUID format: {guid_str}")

        data1 = int(parts[0], 16)
        data2 = int(parts[1], 16)
        data3 = int(parts[2], 16)
        data4_part1 = bytes.fromhex(parts[3])
        data4_part2 = bytes.fromhex(parts[4])
        data4 = data4_part1 + data4_part2

        return cls(data1, data2, data3, data4)

    def __eq__(self, other):
        if not isinstance(other, GUID):
            return False
        return (self.data1 == other.data1 and self.data2 == other.data2 and
                self.data3 == other.data3 and self.data4 == other.data4)

    def __repr__(self):
        return f"GUID({self.to_string()})"


def parse_guid_ascii(stream: io.BytesIO) -> GUID:
    """
    Parse a GUID from Extended ASCII format.

    Format: data1 data2 data3 data4_hex

    Reference: blockref_defs.cpp:1147-1186

    Args:
        stream: Input stream

    Returns:
        Parsed GUID
    """
    # Read Data1 (32-bit)
    data1_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        data1_str += byte
    data1 = int(data1_str.decode('ascii'))

    # Skip whitespace
    _eat_whitespace(stream)

    # Read Data2 (16-bit)
    data2_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        data2_str += byte
    data2 = int(data2_str.decode('ascii'))

    # Skip whitespace
    _eat_whitespace(stream)

    # Read Data3 (16-bit)
    data3_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        data3_str += byte
    data3 = int(data3_str.decode('ascii'))

    # Skip whitespace
    _eat_whitespace(stream)

    # Read Data4 (8 bytes hex)
    data4_hex = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r)':
            if byte == b')':
                stream.seek(-1, io.SEEK_CUR)
            break
        data4_hex += byte

    data4 = bytes.fromhex(data4_hex.decode('ascii'))

    return GUID(data1, data2, data3, data4)


def parse_guid_binary(stream: io.BytesIO) -> GUID:
    """
    Parse a GUID from Extended Binary format.

    Format: data1(4) data2(2) data3(2) data4(8)

    Reference: blockref_defs.cpp:1187-1226

    Args:
        stream: Input stream

    Returns:
        Parsed GUID
    """
    data1 = struct.unpack('<I', stream.read(4))[0]
    data2 = struct.unpack('<H', stream.read(2))[0]
    data3 = struct.unpack('<H', stream.read(2))[0]
    data4 = stream.read(8)

    return GUID(data1, data2, data3, data4)


def _eat_whitespace(stream: io.BytesIO):
    """Skip whitespace characters."""
    while True:
        byte = stream.read(1)
        if not byte or byte not in b' \t\n\r':
            if byte:
                stream.seek(-1, io.SEEK_CUR)
            break


def _skip_to_close_paren(stream: io.BytesIO):
    """Skip to the matching closing parenthesis."""
    depth = 1
    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF while skipping to close paren")
        if byte == b'(':
            depth += 1
        elif byte == b')':
            depth -= 1


# ============================================================================
# Opcode 1: WD_EXAO_GUID (332) - GUID Identifier
# ============================================================================

def handle_guid_ascii(stream: io.BytesIO) -> Dict[str, Any]:
    """
    Handle WD_EXAO_GUID opcode in Extended ASCII format.

    Format: (Guid data1 data2 data3 data4_hex)

    Reference: blockref_defs.cpp:1087-1117, 1143-1186

    Example:
        (Guid 123456789 4660 4660 00112233445566778899aabbccddeeff)

    Args:
        stream: Input stream positioned after "(Guid "

    Returns:
        Dictionary with opcode information
    """
    # Parse GUID
    guid = parse_guid_ascii(stream)

    # Skip closing paren
    _skip_to_close_paren(stream)

    return {
        'opcode': 'WD_EXAO_GUID',
        'opcode_id': 332,
        'type': 'extended_ascii',
        'guid': guid.to_string(),
        'data1': guid.data1,
        'data2': guid.data2,
        'data3': guid.data3,
        'data4': guid.data4.hex()
    }


def handle_guid_binary(stream: io.BytesIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXAO_GUID opcode in Extended Binary format.

    Format: {size opcode data1(4) data2(2) data3(2) data4(8) }

    Reference: blockref_defs.cpp:1087-1117, 1187-1226

    Args:
        stream: Input stream positioned after opcode
        data_size: Size of data to read

    Returns:
        Dictionary with opcode information
    """
    # Parse GUID
    guid = parse_guid_binary(stream)

    # Read closing brace
    closing = stream.read(1)
    if closing != b'}':
        raise ValueError(f"Expected '}}' but got {closing}")

    return {
        'opcode': 'WD_EXBO_GUID',
        'opcode_id': 330,
        'type': 'extended_binary',
        'guid': guid.to_string(),
        'data1': guid.data1,
        'data2': guid.data2,
        'data3': guid.data3,
        'data4': guid.data4.hex()
    }


# ============================================================================
# Opcode 2: WD_EXAO_GUID_LIST (361) - GUID List
# ============================================================================

def handle_guid_list_ascii(stream: io.BytesIO) -> Dict[str, Any]:
    """
    Handle WD_EXAO_GUID_LIST opcode in Extended ASCII format.

    Format: (GuidList count (Guid ...) (Guid ...) ...)

    Reference: guid_list.cpp:196-248

    Example:
        (GuidList 2 (Guid 1 2 3 0011223344556677) (Guid 4 5 6 8899aabbccddeeff))

    Args:
        stream: Input stream positioned after "(GuidList "

    Returns:
        Dictionary with opcode information
    """
    # Read count
    count_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        count_str += byte

    count = int(count_str.decode('ascii'))

    # Read GUIDs
    guids = []
    for _ in range(count):
        _eat_whitespace(stream)

        # Expect '(' for next GUID
        paren = stream.read(1)
        if paren != b'(':
            raise ValueError(f"Expected '(' for GUID, got {paren}")

        # Read "Guid"
        opcode_name = stream.read(4)
        if opcode_name != b'Guid':
            raise ValueError(f"Expected 'Guid' opcode, got {opcode_name}")

        # Skip space
        stream.read(1)

        # Parse GUID
        guid = parse_guid_ascii(stream)
        guids.append(guid)

        # Skip closing paren
        _skip_to_close_paren(stream)

    # Skip closing paren for GuidList
    _eat_whitespace(stream)
    _skip_to_close_paren(stream)

    return {
        'opcode': 'WD_EXAO_GUID_LIST',
        'opcode_id': 361,
        'type': 'extended_ascii',
        'count': count,
        'guids': [g.to_string() for g in guids]
    }


def handle_guid_list_binary(stream: io.BytesIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXAO_GUID_LIST opcode in Extended Binary format.

    Format: {size opcode count {guid} {guid} ... }

    Reference: guid_list.cpp:249-306

    Args:
        stream: Input stream positioned after opcode
        data_size: Size of data to read

    Returns:
        Dictionary with opcode information
    """
    # Read count
    count = struct.unpack('<i', stream.read(4))[0]

    # Read GUIDs
    guids = []
    for _ in range(count):
        # Each GUID is wrapped in Extended Binary format
        # Read opening brace
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{' for GUID, got {opening}")

        # Read size (not used for GUID)
        guid_size = struct.unpack('<I', stream.read(4))[0]

        # Read opcode (should be WD_EXBO_GUID)
        guid_opcode = struct.unpack('<H', stream.read(2))[0]

        # Parse GUID
        guid = parse_guid_binary(stream)
        guids.append(guid)

        # Read closing brace
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}' for GUID, got {closing}")

    # Read closing brace for GUID_LIST
    closing = stream.read(1)
    if closing != b'}':
        raise ValueError(f"Expected '}}' but got {closing}")

    return {
        'opcode': 'WD_EXBO_GUID_LIST',
        'opcode_id': 360,
        'type': 'extended_binary',
        'count': count,
        'guids': [g.to_string() for g in guids]
    }


# ============================================================================
# Opcode 3: WD_EXAO_BLOCKREF (351) - Block Reference
# ============================================================================

def handle_blockref_ascii(stream: io.BytesIO) -> Dict[str, Any]:
    """
    Handle WD_EXAO_BLOCKREF opcode in Extended ASCII format.

    Format: (BlockRef "format_name" file_offset block_size ...)

    Reference: blockref.cpp:575-699, 797-922

    Block formats include: Graphics_Hdr, Overlay_Hdr, Redline_Hdr, Thumbnail,
    Preview, Overlay_Preview, EmbedFont, Graphics, Overlay, Redline, User,
    Null, Global_Sheet, Global, Signature

    Args:
        stream: Input stream positioned after "(BlockRef "

    Returns:
        Dictionary with opcode information
    """
    # Read format name (quoted string)
    _eat_whitespace(stream)

    # Expect opening quote
    quote = stream.read(1)
    if quote != b'"':
        raise ValueError(f"Expected '\"' for format name, got {quote}")

    # Read format name
    format_name = b''
    while True:
        byte = stream.read(1)
        if not byte or byte == b'"':
            break
        format_name += byte

    format_str = format_name.decode('ascii').strip()

    # Read file_offset (when part of directory list)
    _eat_whitespace(stream)
    file_offset_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        file_offset_str += byte
    file_offset = int(file_offset_str.decode('ascii')) if file_offset_str else 0

    # Read block_size
    _eat_whitespace(stream)
    block_size_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r)':
            if byte == b')':
                stream.seek(-1, io.SEEK_CUR)
            break
        block_size_str += byte
    block_size = int(block_size_str.decode('ascii')) if block_size_str else 0

    # Note: Full implementation would parse all BlockRef fields
    # For simplicity, we skip to the closing paren
    _skip_to_close_paren(stream)

    return {
        'opcode': 'WD_EXAO_BLOCKREF',
        'opcode_id': 351,
        'type': 'extended_ascii',
        'format': format_str,
        'file_offset': file_offset,
        'block_size': block_size,
        'note': 'Simplified parsing - full BlockRef has many more fields'
    }


def handle_blockref_binary(stream: io.BytesIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXAO_BLOCKREF opcode in Extended Binary format.

    Format: {size format_id file_offset block_size ... }

    Reference: blockref.cpp:507-574, 723-795

    Args:
        stream: Input stream positioned after opcode
        data_size: Size of data to read

    Returns:
        Dictionary with opcode information
    """
    # Read format ID (already read as opcode in Extended Binary)
    # The format is encoded as the Extended Binary opcode value
    # Values: 0x0012 (Graphics_Hdr), 0x0013 (Overlay_Hdr), etc.

    # For simplicity, read file_offset and block_size
    file_offset = struct.unpack('<I', stream.read(4))[0]
    block_size = struct.unpack('<I', stream.read(4))[0]

    # Skip remaining data
    remaining = data_size - 8 - 1  # 8 bytes read, 1 for closing brace
    if remaining > 0:
        stream.read(remaining)

    # Read closing brace
    closing = stream.read(1)
    if closing != b'}':
        raise ValueError(f"Expected '}}' but got {closing}")

    return {
        'opcode': 'WD_EXBO_BLOCKREF',
        'opcode_id': 350,
        'type': 'extended_binary',
        'file_offset': file_offset,
        'block_size': block_size,
        'note': 'Simplified parsing - full BlockRef has many more fields'
    }


# ============================================================================
# Opcode 4: WD_EXAO_DIRECTORY (353) - Directory
# ============================================================================

def handle_directory_ascii(stream: io.BytesIO) -> Dict[str, Any]:
    """
    Handle WD_EXAO_DIRECTORY opcode in Extended ASCII format.

    Format: (Directory count (BlockRef ...) (BlockRef ...) ... file_offset)

    Reference: directory.cpp:213-317, 320-451

    Args:
        stream: Input stream positioned after "(Directory "

    Returns:
        Dictionary with opcode information
    """
    # Read count
    count_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        count_str += byte

    count = int(count_str.decode('ascii'))

    # Read BlockRefs
    blockrefs = []
    for _ in range(count):
        _eat_whitespace(stream)

        # Expect '(' for BlockRef
        paren = stream.read(1)
        if paren != b'(':
            raise ValueError(f"Expected '(' for BlockRef, got {paren}")

        # Read "BlockRef"
        opcode_name = stream.read(8)
        if opcode_name != b'BlockRef':
            raise ValueError(f"Expected 'BlockRef' opcode, got {opcode_name}")

        # Skip space
        stream.read(1)

        # Parse BlockRef (simplified)
        blockref = handle_blockref_ascii(stream)
        blockrefs.append(blockref)

    # Read directory file offset
    _eat_whitespace(stream)
    file_offset_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r)':
            if byte == b')':
                stream.seek(-1, io.SEEK_CUR)
            break
        file_offset_str += byte
    file_offset = int(file_offset_str.decode('ascii'))

    # Skip closing paren
    _skip_to_close_paren(stream)

    return {
        'opcode': 'WD_EXAO_DIRECTORY',
        'opcode_id': 353,
        'type': 'extended_ascii',
        'count': count,
        'blockrefs': blockrefs,
        'file_offset': file_offset
    }


def handle_directory_binary(stream: io.BytesIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXAO_DIRECTORY opcode in Extended Binary format.

    Format: {size opcode count {blockref} {blockref} ... file_offset }

    Reference: directory.cpp:231-270, 328-386

    Args:
        stream: Input stream positioned after opcode
        data_size: Size of data to read

    Returns:
        Dictionary with opcode information
    """
    # Read count
    count = struct.unpack('<i', stream.read(4))[0]

    # Read BlockRefs (simplified - skip for now)
    blockrefs = []
    for _ in range(count):
        # Each BlockRef is wrapped in Extended Binary format
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{' for BlockRef, got {opening}")

        # Read size
        blockref_size = struct.unpack('<I', stream.read(4))[0]

        # Read opcode (BlockRef format ID)
        blockref_opcode = struct.unpack('<H', stream.read(2))[0]

        # Skip BlockRef data
        blockref_data_size = blockref_size - 2 - 1
        stream.read(blockref_data_size)

        # Read closing brace
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}' for BlockRef, got {closing}")

        blockrefs.append({'format_id': blockref_opcode})

    # Read directory file offset
    file_offset = struct.unpack('<I', stream.read(4))[0]

    # Read closing brace
    closing = stream.read(1)
    if closing != b'}':
        raise ValueError(f"Expected '}}' but got {closing}")

    return {
        'opcode': 'WD_EXBO_DIRECTORY',
        'opcode_id': 352,
        'type': 'extended_binary',
        'count': count,
        'blockrefs': blockrefs,
        'file_offset': file_offset
    }


# ============================================================================
# Opcode 5: WD_EXAO_USERDATA (355) - User-Defined Data
# ============================================================================

def handle_userdata_ascii(stream: io.BytesIO) -> Dict[str, Any]:
    """
    Handle WD_EXAO_USERDATA opcode in Extended ASCII format.

    Format: (UserData "description" size hex_data)

    Reference: userdata.cpp:92-158, 167-283

    Example:
        (UserData "MyData" 4 0a0b0c0d)

    Args:
        stream: Input stream positioned after "(UserData "

    Returns:
        Dictionary with opcode information
    """
    # Read description (quoted string)
    _eat_whitespace(stream)

    # Expect opening quote
    quote = stream.read(1)
    if quote != b'"':
        raise ValueError(f"Expected '\"' for description, got {quote}")

    # Read description
    description = b''
    while True:
        byte = stream.read(1)
        if not byte or byte == b'"':
            break
        description += byte

    description_str = description.decode('ascii')

    # Read data size
    _eat_whitespace(stream)
    size_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r':
            break
        size_str += byte

    data_size = int(size_str.decode('ascii'))

    # Read hex data
    _eat_whitespace(stream)
    hex_data = b''
    bytes_to_read = data_size * 2  # Each byte is 2 hex chars
    for _ in range(bytes_to_read):
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r)':
            if byte == b')':
                stream.seek(-1, io.SEEK_CUR)
            break
        hex_data += byte

    # Convert hex to bytes
    if hex_data:
        user_data = bytes.fromhex(hex_data.decode('ascii'))
    else:
        user_data = b''

    # Skip closing paren
    _eat_whitespace(stream)
    _skip_to_close_paren(stream)

    return {
        'opcode': 'WD_EXAO_USERDATA',
        'opcode_id': 355,
        'type': 'extended_ascii',
        'description': description_str,
        'data_size': data_size,
        'data': user_data.hex() if user_data else ''
    }


def handle_userdata_binary(stream: io.BytesIO, data_size: int) -> Dict[str, Any]:
    """
    Handle WD_EXAO_USERDATA opcode in Extended Binary format.

    Format: {size opcode "description" data_size data }

    Reference: userdata.cpp:115-134, 171-219

    Args:
        stream: Input stream positioned after opcode
        data_size: Size of data to read

    Returns:
        Dictionary with opcode information
    """
    # Read description (quoted string)
    # Expect opening quote
    quote = stream.read(1)
    if quote != b'"':
        raise ValueError(f"Expected '\"' for description, got {quote}")

    # Read description
    description = b''
    while True:
        byte = stream.read(1)
        if not byte or byte == b'"':
            break
        description += byte

    description_str = description.decode('ascii')

    # Read data size
    user_data_size = struct.unpack('<i', stream.read(4))[0]

    # Read data
    if user_data_size > 0:
        user_data = stream.read(user_data_size)
    else:
        user_data = b''

    # Read closing brace
    closing = stream.read(1)
    if closing != b'}':
        raise ValueError(f"Expected '}}' but got {closing}")

    return {
        'opcode': 'WD_EXBO_USERDATA',
        'opcode_id': 354,
        'type': 'extended_binary',
        'description': description_str,
        'data_size': user_data_size,
        'data': user_data.hex() if user_data else ''
    }


# ============================================================================
# Opcode 6: WD_EXAO_OBJECT_NODE (366) - Object Node
# ============================================================================

def handle_object_node_ascii(stream: io.BytesIO) -> Dict[str, Any]:
    """
    Handle WD_EXAO_OBJECT_NODE opcode in Extended ASCII format.

    Format: (Node object_node_num [name])

    Reference: object_node.cpp:101-204, 256-315

    Example:
        (Node 42)
        (Node 42 "MyNode")

    Args:
        stream: Input stream positioned after "(Node "

    Returns:
        Dictionary with opcode information
    """
    # Read object node number
    node_num_str = b''
    while True:
        byte = stream.read(1)
        if not byte or byte in b' \t\n\r)':
            if byte == b')':
                stream.seek(-1, io.SEEK_CUR)
            break
        node_num_str += byte

    node_num = int(node_num_str.decode('ascii'))

    # Check for optional name
    _eat_whitespace(stream)

    # Peek at next byte
    next_byte = stream.read(1)
    if next_byte == b')':
        # No name, just node number
        stream.seek(-1, io.SEEK_CUR)
        node_name = None
    else:
        # Has a name (likely quoted string or raw string)
        stream.seek(-1, io.SEEK_CUR)

        # Read name - could be quoted or unquoted
        if next_byte == b'"':
            stream.read(1)  # Skip opening quote
            node_name_bytes = b''
            while True:
                byte = stream.read(1)
                if not byte or byte == b'"':
                    break
                node_name_bytes += byte
            node_name = node_name_bytes.decode('utf-8')
        else:
            # Unquoted name
            node_name_bytes = b''
            while True:
                byte = stream.read(1)
                if not byte or byte in b' \t\n\r)':
                    if byte == b')':
                        stream.seek(-1, io.SEEK_CUR)
                    break
                node_name_bytes += byte
            node_name = node_name_bytes.decode('utf-8') if node_name_bytes else None

    # Skip closing paren
    _skip_to_close_paren(stream)

    return {
        'opcode': 'WD_EXAO_OBJECT_NODE',
        'opcode_id': 366,
        'type': 'extended_ascii',
        'object_node_num': node_num,
        'object_node_name': node_name
    }


def handle_object_node_single_byte(opcode_byte: int, stream: io.BytesIO,
                                   previous_node_num: int = -1) -> Dict[str, Any]:
    """
    Handle WD_EXAO_OBJECT_NODE opcode in Single Byte format.

    Three optimizations (Reference: object_node.cpp:125-159, 260-282):
    - 0x0E: Auto-increment (previous + 1)
    - 0x6E: 16-bit signed offset from previous
    - 0x4E: 32-bit absolute value

    Args:
        opcode_byte: Single byte opcode (0x0E, 0x4E, or 0x6E)
        stream: Input stream
        previous_node_num: Previous object node number for delta calculation

    Returns:
        Dictionary with opcode information
    """
    if opcode_byte == 0x0E:
        # Auto-increment
        node_num = previous_node_num + 1

    elif opcode_byte == 0x6E:
        # 16-bit signed offset
        offset = struct.unpack('<h', stream.read(2))[0]
        node_num = previous_node_num + offset

    elif opcode_byte == 0x4E:
        # 32-bit absolute value
        node_num = struct.unpack('<i', stream.read(4))[0]

    else:
        raise ValueError(f"Invalid object node single byte opcode: 0x{opcode_byte:02x}")

    return {
        'opcode': 'WD_SBBO_OBJECT_NODE',
        'opcode_byte': f'0x{opcode_byte:02x}',
        'type': 'single_byte',
        'object_node_num': node_num,
        'object_node_name': None
    }


# ============================================================================
# Tests
# ============================================================================

def test_guid():
    """Test GUID parsing and formatting."""
    print("Testing GUID...")

    # Test 1: Create and format GUID
    guid = GUID(0x12345678, 0x1234, 0x5678, bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]))
    expected = "{12345678-1234-5678-0011-223344556677}"
    assert guid.to_string() == expected, f"Expected {expected}, got {guid.to_string()}"
    print(f"  ✓ GUID formatting: {guid.to_string()}")

    # Test 2: Parse GUID from string
    guid_str = "{abcdef00-1111-2222-3344-556677889900}"
    guid2 = GUID.from_string(guid_str)
    assert guid2.to_string() == guid_str, f"Expected {guid_str}, got {guid2.to_string()}"
    print(f"  ✓ GUID parsing: {guid2.to_string()}")

    # Test 3: GUID equality
    guid3 = GUID(0x12345678, 0x1234, 0x5678, bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]))
    assert guid == guid3, "GUIDs should be equal"
    print("  ✓ GUID equality")

    print()


def test_handle_guid_ascii():
    """Test WD_EXAO_GUID ASCII parsing."""
    print("Testing handle_guid_ascii...")

    # Test 1: Basic GUID
    data = b"123456789 4660 4660 00112233445566778899aabbccddeeff )"
    stream = io.BytesIO(data)
    result = handle_guid_ascii(stream)

    assert result['opcode'] == 'WD_EXAO_GUID'
    assert result['opcode_id'] == 332
    assert result['data1'] == 123456789
    assert result['data2'] == 4660
    assert result['data3'] == 4660
    print(f"  ✓ Basic GUID: {result['guid']}")

    # Test 2: Zero GUID
    data = b"0 0 0 0000000000000000 )"
    stream = io.BytesIO(data)
    result = handle_guid_ascii(stream)

    assert result['data1'] == 0
    assert result['data2'] == 0
    assert result['data3'] == 0
    print(f"  ✓ Zero GUID: {result['guid']}")

    print()


def test_handle_guid_list_ascii():
    """Test WD_EXAO_GUID_LIST ASCII parsing."""
    print("Testing handle_guid_list_ascii...")

    # Test: GUID list with 2 GUIDs
    data = b"""2
    (Guid 1 2 3 0011223344556677 )
    (Guid 4 5 6 8899aabbccddeeff )
    )"""
    stream = io.BytesIO(data)
    result = handle_guid_list_ascii(stream)

    assert result['opcode'] == 'WD_EXAO_GUID_LIST'
    assert result['opcode_id'] == 361
    assert result['count'] == 2
    assert len(result['guids']) == 2
    print(f"  ✓ GUID List with {result['count']} GUIDs")
    print(f"    - GUID 1: {result['guids'][0]}")
    print(f"    - GUID 2: {result['guids'][1]}")

    print()


def test_handle_userdata_ascii():
    """Test WD_EXAO_USERDATA ASCII parsing."""
    print("Testing handle_userdata_ascii...")

    # Test 1: Basic user data
    data = b'"MyCustomData" 4 0a0b0c0d )'
    stream = io.BytesIO(data)
    result = handle_userdata_ascii(stream)

    assert result['opcode'] == 'WD_EXAO_USERDATA'
    assert result['opcode_id'] == 355
    assert result['description'] == 'MyCustomData'
    assert result['data_size'] == 4
    assert result['data'] == '0a0b0c0d'
    print(f"  ✓ UserData: '{result['description']}', size={result['data_size']}, data={result['data']}")

    # Test 2: Empty user data
    data = b'"EmptyData" 0 )'
    stream = io.BytesIO(data)
    result = handle_userdata_ascii(stream)

    assert result['description'] == 'EmptyData'
    assert result['data_size'] == 0
    assert result['data'] == ''
    print(f"  ✓ Empty UserData: '{result['description']}'")

    print()


def test_handle_object_node_ascii():
    """Test WD_EXAO_OBJECT_NODE ASCII parsing."""
    print("Testing handle_object_node_ascii...")

    # Test 1: Object node without name
    data = b"42 )"
    stream = io.BytesIO(data)
    result = handle_object_node_ascii(stream)

    assert result['opcode'] == 'WD_EXAO_OBJECT_NODE'
    assert result['opcode_id'] == 366
    assert result['object_node_num'] == 42
    assert result['object_node_name'] is None
    print(f"  ✓ Object Node (no name): num={result['object_node_num']}")

    # Test 2: Object node with name
    data = b'100 "MyNode" )'
    stream = io.BytesIO(data)
    result = handle_object_node_ascii(stream)

    assert result['object_node_num'] == 100
    assert result['object_node_name'] == 'MyNode'
    print(f"  ✓ Object Node (with name): num={result['object_node_num']}, name='{result['object_node_name']}'")

    print()


def test_handle_object_node_single_byte():
    """Test WD_EXAO_OBJECT_NODE single byte parsing."""
    print("Testing handle_object_node_single_byte...")

    # Test 1: Auto-increment (0x0E)
    stream = io.BytesIO(b"")
    result = handle_object_node_single_byte(0x0E, stream, previous_node_num=41)

    assert result['opcode_byte'] == '0x0e'
    assert result['object_node_num'] == 42
    print(f"  ✓ Auto-increment: 41 -> {result['object_node_num']}")

    # Test 2: 16-bit offset (0x6E)
    stream = io.BytesIO(struct.pack('<h', 10))
    result = handle_object_node_single_byte(0x6E, stream, previous_node_num=30)

    assert result['object_node_num'] == 40
    print(f"  ✓ 16-bit offset: 30 + 10 = {result['object_node_num']}")

    # Test 3: 32-bit absolute (0x4E)
    stream = io.BytesIO(struct.pack('<i', 12345))
    result = handle_object_node_single_byte(0x4E, stream)

    assert result['object_node_num'] == 12345
    print(f"  ✓ 32-bit absolute: {result['object_node_num']}")

    print()


def test_handle_blockref_ascii():
    """Test WD_EXAO_BLOCKREF ASCII parsing."""
    print("Testing handle_blockref_ascii...")

    # Test: Basic BlockRef
    data = b'"Graphics_Hdr" 1000 5000 )'
    stream = io.BytesIO(data)
    result = handle_blockref_ascii(stream)

    assert result['opcode'] == 'WD_EXAO_BLOCKREF'
    assert result['opcode_id'] == 351
    assert result['format'] == 'Graphics_Hdr'
    assert result['file_offset'] == 1000
    assert result['block_size'] == 5000
    print(f"  ✓ BlockRef: format={result['format']}, offset={result['file_offset']}, size={result['block_size']}")

    print()


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("Agent 26: DWF Structure/GUID Opcodes - Test Suite")
    print("=" * 70)
    print()

    test_guid()
    test_handle_guid_ascii()
    test_handle_guid_list_ascii()
    test_handle_userdata_ascii()
    test_handle_object_node_ascii()
    test_handle_object_node_single_byte()
    test_handle_blockref_ascii()

    print("=" * 70)
    print("All tests passed!")
    print("=" * 70)


# ============================================================================
# Documentation
# ============================================================================

def print_documentation():
    """Print detailed documentation for all opcodes."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║       Agent 26: DWF Structure/GUID Opcodes Documentation            ║
╚══════════════════════════════════════════════════════════════════════╝

This module implements 6 DWF Extended ASCII structure and GUID opcodes.

┌──────────────────────────────────────────────────────────────────────┐
│ 1. WD_EXAO_GUID (ID 332) - GUID Identifier                          │
└──────────────────────────────────────────────────────────────────────┘

   Description:
   Stores a Globally Unique Identifier in standard GUID format.

   ASCII Format: (Guid data1 data2 data3 data4_hex)
   Binary Format: {size opcode data1(4) data2(2) data3(2) data4(8) }

   Example:
   (Guid 123456789 4660 4660 00112233445566778899aabbccddeeff)

   GUID Structure:
   - Data1: 32-bit unsigned integer
   - Data2: 16-bit unsigned integer
   - Data3: 16-bit unsigned integer
   - Data4: 8 bytes

   String Format: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}

┌──────────────────────────────────────────────────────────────────────┐
│ 2. WD_EXAO_GUID_LIST (ID 361) - GUID List                           │
└──────────────────────────────────────────────────────────────────────┘

   Description:
   Stores a list of GUIDs for object identification and tracking.

   ASCII Format: (GuidList count (Guid ...) (Guid ...) ...)
   Binary Format: {size opcode count {guid} {guid} ... }

   Example:
   (GuidList 2 (Guid 1 2 3 0011223344556677) (Guid 4 5 6 8899aabbccddeeff))

┌──────────────────────────────────────────────────────────────────────┐
│ 3. WD_EXAO_BLOCKREF (ID 351) - Block Reference                      │
└──────────────────────────────────────────────────────────────────────┘

   Description:
   References a block of data within the DWF file structure.

   ASCII Format: (BlockRef "format_name" file_offset block_size ...)
   Binary Format: {size format_id file_offset block_size ... }

   Block Formats:
   - Graphics_Hdr, Overlay_Hdr, Redline_Hdr
   - Thumbnail, Preview, Overlay_Preview
   - EmbedFont, Graphics, Overlay, Redline, User
   - Null, Global_Sheet, Global, Signature

   Example:
   (BlockRef "Graphics_Hdr" 1000 5000)

   Note: Full BlockRef contains many additional fields including GUIDs,
   timestamps, encryption info, etc.

┌──────────────────────────────────────────────────────────────────────┐
│ 4. WD_EXAO_DIRECTORY (ID 353) - Directory                           │
└──────────────────────────────────────────────────────────────────────┘

   Description:
   Directory of block references in the DWF file.

   ASCII Format: (Directory count (BlockRef ...) (BlockRef ...) ... offset)
   Binary Format: {size opcode count {blockref} {blockref} ... offset }

   Example:
   (Directory 2 (BlockRef "Graphics" 0 1000) (BlockRef "User" 1000 500) 2000)

┌──────────────────────────────────────────────────────────────────────┐
│ 5. WD_EXAO_USERDATA (ID 355) - User-Defined Data                    │
└──────────────────────────────────────────────────────────────────────┘

   Description:
   Stores custom user-defined data with a description.

   ASCII Format: (UserData "description" size hex_data)
   Binary Format: {size opcode "description" data_size data }

   Example:
   (UserData "MyCustomData" 4 0a0b0c0d)

┌──────────────────────────────────────────────────────────────────────┐
│ 6. WD_EXAO_OBJECT_NODE (ID 366) - Object Node                       │
└──────────────────────────────────────────────────────────────────────┘

   Description:
   Identifies an object node in the scene graph.

   ASCII Format: (Node object_node_num [name])
   Single Byte Formats:
   - 0x0E: Auto-increment (previous + 1)
   - 0x6E: 16-bit signed offset from previous
   - 0x4E: 32-bit absolute value

   Examples:
   (Node 42)
   (Node 100 "MyNode")
   0x0E (auto-increment from 41 to 42)

╔══════════════════════════════════════════════════════════════════════╗
║                        Implementation Notes                          ║
╚══════════════════════════════════════════════════════════════════════╝

GUID Binary Size:
   4 (Data1) + 2 (Data2) + 2 (Data3) + 8 (Data4) = 16 bytes

   Plus Extended Binary wrapper:
   1 ('{') + 4 (size) + 2 (opcode) + 16 (GUID) + 1 ('}') = 24 bytes total

BlockRef Complexity:
   BlockRef is one of the most complex DWF structures with 36 possible
   fields depending on the format type. The simplified implementation
   here extracts only the core fields.

Object Node Optimization:
   Object nodes use single-byte opcodes for efficient encoding when
   node numbers are sequential or close together.

Reference Files:
   - blockref_defs.cpp (lines 1025-1236): WT_Guid
   - guid_list.cpp (lines 1-307): WT_Guid_List
   - blockref.cpp (lines 1-1106): WT_BlockRef
   - directory.cpp (lines 1-452): WT_Directory
   - userdata.cpp (lines 1-309): WT_UserData
   - object_node.cpp (lines 1-353): WT_Object_Node
    """)


if __name__ == '__main__':
    print_documentation()
    print()
    run_all_tests()
