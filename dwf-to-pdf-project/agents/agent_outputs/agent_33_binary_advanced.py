"""
Agent 33: Extended Binary Advanced/Misc Opcodes Implementation
================================================================

This module implements 6 Extended Binary advanced/miscellaneous opcodes for DWF format:
1. WD_EXBO_EMBEDDED_FONT (0x013E / 318) - Embedded font data
2. WD_EXBO_BLOCK_MEANING (0x0142 / 322) - Block semantic meaning
3. WD_EXBO_BLOCKREF (0x015E / 350) - Block reference
4. WD_EXBO_DIRECTORY (0x0160 / 352) - Directory of block references
5. WD_EXBO_USERDATA (0x0162 / 354) - User-defined data
6. WD_EXBO_MACRO_DEFINITION (0x0171 / 369) - Macro definition

Extended Binary Format:
    '{' (1 byte) + Size (4 bytes LE int32) + Opcode (2 bytes LE uint16) + Data + '}' (1 byte)

Source Files:
    - embedded_font.cpp
    - blockref_defs.cpp (block_meaning)
    - blockref.cpp
    - directory.cpp
    - userdata.cpp
    - macro_definition.cpp

Author: Agent 33
Date: 2025-10-22
"""

import struct
from typing import Dict, Any, List, Tuple, Optional
from io import BytesIO
from enum import IntEnum


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Opcode hex values (little-endian 16-bit)
WD_EXBO_EMBEDDED_FONT = 0x013E      # 318
WD_EXBO_BLOCK_MEANING = 0x0142      # 322
WD_EXBO_BLOCKREF = 0x015E           # 350
WD_EXBO_DIRECTORY = 0x0160          # 352
WD_EXBO_USERDATA = 0x0162           # 354
WD_EXBO_MACRO_DEFINITION = 0x0171   # 369


# ==============================================================================
# ENUMERATIONS
# ==============================================================================

class EmbeddedFontRequestType(IntEnum):
    """Embedded font request types (bit flags)"""
    RAW = 0x00000001
    SUBSET = 0x00000002
    COMPRESSED = 0x00000004
    FAIL_IF_VARIATIONS_SIMULATED = 0x00000008
    EUDC = 0x00000010
    VALIDATION_TESTS = 0x00000020
    WEB_OBJECT = 0x00000040
    ENCRYPT_DATA = 0x00000080


class EmbeddedFontPrivilege(IntEnum):
    """Embedded font privilege types"""
    PREVIEW_PRINT = 0x00
    EDITABLE = 0x01
    INSTALLABLE = 0x02
    NON_EMBEDDING = 0x03


class EmbeddedFontCharacterSetType(IntEnum):
    """Embedded font character set types"""
    UNICODE = 0x00
    SYMBOL = 0x01
    GLYPHIDX = 0x02


class BlockMeaningDescription(IntEnum):
    """Block meaning descriptions"""
    NONE = 0x00000001
    SEAL = 0x00000002
    STAMP = 0x00000004
    LABEL = 0x00000008
    REDLINE = 0x00000010
    RESERVED1 = 0x00000020
    RESERVED2 = 0x00000040


# ==============================================================================
# EXTENDED BINARY PARSER BASE
# ==============================================================================

class ExtendedBinaryParser:
    """Base parser for Extended Binary opcodes"""

    @staticmethod
    def parse_header(stream: BytesIO) -> Tuple[int, int, int]:
        """
        Parse Extended Binary opcode header.

        Args:
            stream: Input byte stream

        Returns:
            Tuple of (opcode_value, total_size, data_size)

        Format:
            '{' (1 byte) + Size (4 bytes LE) + Opcode (2 bytes LE) + ...
        """
        # Read opening brace
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{' for Extended Binary, got {opening!r}")

        # Read size (4 bytes, little-endian int32)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise ValueError("Unexpected EOF reading opcode size")
        total_size = struct.unpack('<I', size_bytes)[0]

        # Read opcode (2 bytes, little-endian uint16)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise ValueError("Unexpected EOF reading opcode value")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Data size = total_size - opcode (2 bytes) - closing '}' (1 byte)
        data_size = total_size - 2 - 1

        return opcode, total_size, data_size

    @staticmethod
    def verify_closing_brace(stream: BytesIO):
        """Verify closing '}' character"""
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}' at end of Extended Binary, got {closing!r}")

    @staticmethod
    def read_quoted_string(stream: BytesIO, max_length: int = 65535) -> str:
        """
        Read a quoted string from binary stream.
        Format: '"' + string_data + '"'
        """
        # Read opening quote
        quote = stream.read(1)
        if quote != b'"':
            raise ValueError(f"Expected opening quote, got {quote!r}")

        # Read until closing quote
        chars = []
        for _ in range(max_length):
            ch = stream.read(1)
            if not ch:
                raise ValueError("Unexpected EOF in quoted string")
            if ch == b'"':
                return b''.join(chars).decode('utf-8', errors='replace')
            chars.append(ch)

        raise ValueError("Quoted string too long")


# ==============================================================================
# OPCODE HANDLERS
# ==============================================================================

class EmbeddedFontHandler:
    """Handler for WD_EXBO_EMBEDDED_FONT (0x013E / 318)"""

    OPCODE = WD_EXBO_EMBEDDED_FONT

    @staticmethod
    def parse(stream: BytesIO, data_size: int) -> Dict[str, Any]:
        """
        Parse embedded font opcode.

        Binary Format:
            - request_type: int32 (4 bytes)
            - privilege: byte (1 byte)
            - character_set_type: byte (1 byte)
            - font_type_face_name_length: int32 (4 bytes)
            - font_type_face_name_string: bytes (variable)
            - font_logfont_name_length: int32 (4 bytes)
            - font_logfont_name_string: bytes (variable)
            - data_size: int32 (4 bytes)
            - data: bytes (variable)
        """
        start_pos = stream.tell()

        # Read request type (4 bytes)
        request_type = struct.unpack('<I', stream.read(4))[0]

        # Read privilege (1 byte)
        privilege = struct.unpack('<B', stream.read(1))[0]

        # Read character set type (1 byte)
        character_set_type = struct.unpack('<B', stream.read(1))[0]

        # Read font type face name
        font_type_face_name_length = struct.unpack('<I', stream.read(4))[0]
        font_type_face_name = stream.read(font_type_face_name_length).decode('utf-8', errors='replace')

        # Read font logfont name
        font_logfont_name_length = struct.unpack('<I', stream.read(4))[0]
        font_logfont_name = stream.read(font_logfont_name_length).decode('utf-8', errors='replace')

        # Read font data
        font_data_size = struct.unpack('<I', stream.read(4))[0]
        font_data = stream.read(font_data_size)

        # Verify closing brace
        ExtendedBinaryParser.verify_closing_brace(stream)

        return {
            'opcode': 'WD_EXBO_EMBEDDED_FONT',
            'opcode_value': WD_EXBO_EMBEDDED_FONT,
            'request_type': request_type,
            'request_flags': EmbeddedFontHandler._decode_request_flags(request_type),
            'privilege': privilege,
            'privilege_name': EmbeddedFontPrivilege(privilege).name if privilege in [e.value for e in EmbeddedFontPrivilege] else 'UNKNOWN',
            'character_set_type': character_set_type,
            'character_set_name': EmbeddedFontCharacterSetType(character_set_type).name if character_set_type in [e.value for e in EmbeddedFontCharacterSetType] else 'UNKNOWN',
            'font_type_face_name': font_type_face_name,
            'font_logfont_name': font_logfont_name,
            'font_data_size': font_data_size,
            'font_data': font_data[:100],  # First 100 bytes for inspection
            'font_data_full_size': len(font_data)
        }

    @staticmethod
    def _decode_request_flags(request_type: int) -> List[str]:
        """Decode request type bit flags"""
        flags = []
        for flag in EmbeddedFontRequestType:
            if request_type & flag.value:
                flags.append(flag.name)
        return flags


class BlockMeaningHandler:
    """Handler for WD_EXBO_BLOCK_MEANING (0x0142 / 322)"""

    OPCODE = WD_EXBO_BLOCK_MEANING

    @staticmethod
    def parse(stream: BytesIO, data_size: int) -> Dict[str, Any]:
        """
        Parse block meaning opcode.

        Binary Format:
            - description: uint16 (2 bytes) - enum value
        """
        # Read description (2 bytes)
        description = struct.unpack('<H', stream.read(2))[0]

        # Verify closing brace
        ExtendedBinaryParser.verify_closing_brace(stream)

        # Map to enum name
        try:
            desc_name = BlockMeaningDescription(description).name
        except ValueError:
            desc_name = f'UNKNOWN_0x{description:04X}'

        return {
            'opcode': 'WD_EXBO_BLOCK_MEANING',
            'opcode_value': WD_EXBO_BLOCK_MEANING,
            'description': description,
            'description_name': desc_name
        }


class BlockRefHandler:
    """Handler for WD_EXBO_BLOCKREF (0x015E / 350)"""

    OPCODE = WD_EXBO_BLOCKREF

    # BlockRef format types (matching C++ enum)
    BLOCKREF_FORMATS = {
        0x0012: 'GRAPHICS_HDR',
        0x0013: 'OVERLAY_HDR',
        0x0014: 'REDLINE_HDR',
        0x0015: 'THUMBNAIL',
        0x0016: 'PREVIEW',
        0x0017: 'OVERLAY_THUMBNAIL',
        0x0018: 'OVERLAY_PREVIEW',
        0x0019: 'FONT',
        0x0020: 'GRAPHICS',
        0x0021: 'OVERLAY',
        0x0022: 'REDLINE',
        0x0023: 'USER',
        0x0024: 'NULL',
        0x0025: 'GLOBAL_SHEET',
        0x0026: 'GLOBAL',
        0x0027: 'SIGNATURE',
        0x015E: 'BLOCKREF'
    }

    @staticmethod
    def parse(stream: BytesIO, data_size: int) -> Dict[str, Any]:
        """
        Parse blockref opcode.

        Note: BlockRef has a complex variable structure depending on format.
        This is a simplified implementation that reads basic fields.

        Binary Format (common fields):
            - file_offset: int64 (8 bytes)
            - block_size: int64 (8 bytes)
            - ... (many optional fields based on format)
        """
        start_pos = stream.tell()

        # Read basic fields
        file_offset = struct.unpack('<Q', stream.read(8))[0]  # 8-byte unsigned int
        block_size = struct.unpack('<Q', stream.read(8))[0]   # 8-byte unsigned int

        # Skip remaining data for now (complex structure)
        bytes_read = 16  # file_offset + block_size
        remaining = data_size - bytes_read

        if remaining > 0:
            remaining_data = stream.read(remaining)
        else:
            remaining_data = b''

        # Verify closing brace
        ExtendedBinaryParser.verify_closing_brace(stream)

        return {
            'opcode': 'WD_EXBO_BLOCKREF',
            'opcode_value': WD_EXBO_BLOCKREF,
            'file_offset': file_offset,
            'block_size': block_size,
            'remaining_data_size': len(remaining_data),
            'note': 'BlockRef has complex variable structure - full parsing requires format-specific logic'
        }


class DirectoryHandler:
    """Handler for WD_EXBO_DIRECTORY (0x0160 / 352)"""

    OPCODE = WD_EXBO_DIRECTORY

    @staticmethod
    def parse(stream: BytesIO, data_size: int) -> Dict[str, Any]:
        """
        Parse directory opcode.

        Binary Format:
            - item_count: int32 (4 bytes)
            - blockrefs: array of BlockRef opcodes
            - file_offset: uint32 (4 bytes)
        """
        start_pos = stream.tell()

        # Read item count
        item_count = struct.unpack('<I', stream.read(4))[0]

        # Note: Each blockref is a nested Extended Binary opcode
        # For now, we'll just record the count and skip the detailed parsing
        # In a full implementation, we'd parse each blockref here

        blockrefs = []
        for i in range(item_count):
            # Each blockref starts with '{' and contains format-specific data
            # This would require recursive opcode parsing
            blockrefs.append({'index': i, 'note': 'BlockRef parsing not fully implemented'})

        # Read file offset (should be at end)
        # For now, skip to near end of data
        bytes_read = 4  # item_count
        remaining = data_size - bytes_read - 4  # leave 4 bytes for file_offset

        if remaining > 0:
            skipped_data = stream.read(remaining)

        file_offset = struct.unpack('<I', stream.read(4))[0]

        # Verify closing brace
        ExtendedBinaryParser.verify_closing_brace(stream)

        return {
            'opcode': 'WD_EXBO_DIRECTORY',
            'opcode_value': WD_EXBO_DIRECTORY,
            'item_count': item_count,
            'blockrefs': blockrefs,
            'file_offset': file_offset,
            'note': 'Directory contains nested BlockRef opcodes - simplified parsing'
        }


class UserDataHandler:
    """Handler for WD_EXBO_USERDATA (0x0162 / 354)"""

    OPCODE = WD_EXBO_USERDATA

    @staticmethod
    def parse(stream: BytesIO, data_size: int) -> Dict[str, Any]:
        """
        Parse user data opcode.

        Binary Format:
            - data_description: quoted string
            - data_size: int32 (4 bytes)
            - data: bytes (variable)
        """
        # Read quoted data description
        data_description = ExtendedBinaryParser.read_quoted_string(stream)

        # Read data size
        user_data_size = struct.unpack('<I', stream.read(4))[0]

        # Read user data
        user_data = stream.read(user_data_size) if user_data_size > 0 else b''

        # Verify closing brace
        ExtendedBinaryParser.verify_closing_brace(stream)

        return {
            'opcode': 'WD_EXBO_USERDATA',
            'opcode_value': WD_EXBO_USERDATA,
            'data_description': data_description,
            'data_size': user_data_size,
            'data': user_data[:100] if len(user_data) > 100 else user_data,  # First 100 bytes
            'data_full_size': len(user_data),
            'data_preview': user_data[:50].hex() if user_data else ''
        }


class MacroDefinitionHandler:
    """Handler for WD_EXBO_MACRO_DEFINITION (0x0171 / 369)"""

    OPCODE = WD_EXBO_MACRO_DEFINITION

    @staticmethod
    def parse(stream: BytesIO, data_size: int) -> Dict[str, Any]:
        """
        Parse macro definition opcode.

        Note: The C++ code shows this opcode is ASCII-only in practice.
        Binary format is commented out in macro_definition.cpp.

        Binary Format (if it were used):
            - index: uint16 (2 bytes)
            - scale_units: int32 (4 bytes)
            - objects: stream of serialized objects
        """
        start_pos = stream.tell()

        # Read index (2 bytes)
        index = struct.unpack('<H', stream.read(2))[0]

        # Read scale units (4 bytes)
        scale_units = struct.unpack('<I', stream.read(4))[0]

        # Remaining data would be serialized objects
        bytes_read = 6  # index + scale_units
        remaining = data_size - bytes_read

        if remaining > 0:
            object_data = stream.read(remaining)
        else:
            object_data = b''

        # Verify closing brace
        ExtendedBinaryParser.verify_closing_brace(stream)

        return {
            'opcode': 'WD_EXBO_MACRO_DEFINITION',
            'opcode_value': WD_EXBO_MACRO_DEFINITION,
            'index': index,
            'scale_units': scale_units,
            'object_data_size': len(object_data),
            'note': 'Macro Definition is typically ASCII-only; binary format rarely used'
        }


# ==============================================================================
# OPCODE DISPATCHER
# ==============================================================================

class ExtendedBinaryOpcodeDispatcher:
    """Dispatcher for Extended Binary opcodes"""

    HANDLERS = {
        WD_EXBO_EMBEDDED_FONT: EmbeddedFontHandler,
        WD_EXBO_BLOCK_MEANING: BlockMeaningHandler,
        WD_EXBO_BLOCKREF: BlockRefHandler,
        WD_EXBO_DIRECTORY: DirectoryHandler,
        WD_EXBO_USERDATA: UserDataHandler,
        WD_EXBO_MACRO_DEFINITION: MacroDefinitionHandler
    }

    @classmethod
    def parse_opcode(cls, stream: BytesIO) -> Dict[str, Any]:
        """
        Parse an Extended Binary opcode from stream.

        Args:
            stream: Input byte stream positioned at '{' character

        Returns:
            Dictionary with parsed opcode data
        """
        # Parse header
        opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

        # Get handler
        handler = cls.HANDLERS.get(opcode)

        if handler:
            return handler.parse(stream, data_size)
        else:
            # Unknown opcode - skip data and closing brace
            stream.read(data_size)
            ExtendedBinaryParser.verify_closing_brace(stream)
            return {
                'opcode': 'UNKNOWN',
                'opcode_value': opcode,
                'opcode_hex': f'0x{opcode:04X}',
                'data_size': data_size,
                'error': 'Unknown Extended Binary opcode'
            }


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def parse_extended_binary_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse all Extended Binary opcodes from a DWF file.

    Args:
        file_path: Path to DWF file

    Returns:
        List of parsed opcodes
    """
    opcodes = []

    with open(file_path, 'rb') as f:
        content = f.read()

    stream = BytesIO(content)

    # Search for Extended Binary opcodes (start with '{')
    while True:
        byte = stream.read(1)
        if not byte:
            break

        if byte == b'{':
            # Rewind to start of opcode
            stream.seek(-1, 1)

            try:
                opcode_data = ExtendedBinaryOpcodeDispatcher.parse_opcode(stream)
                opcodes.append(opcode_data)
            except Exception as e:
                # Record error and continue
                opcodes.append({
                    'error': str(e),
                    'position': stream.tell()
                })

    return opcodes


def format_opcode_summary(opcode_data: Dict[str, Any]) -> str:
    """Format opcode data as human-readable summary"""
    lines = []
    lines.append(f"Opcode: {opcode_data.get('opcode', 'UNKNOWN')}")
    lines.append(f"  Value: 0x{opcode_data.get('opcode_value', 0):04X}")

    for key, value in opcode_data.items():
        if key not in ['opcode', 'opcode_value', 'font_data', 'data', 'object_data']:
            if isinstance(value, bytes):
                lines.append(f"  {key}: {value.hex()[:80]}...")
            elif isinstance(value, list):
                lines.append(f"  {key}: [{len(value)} items]")
            else:
                lines.append(f"  {key}: {value}")

    return '\n'.join(lines)


# ==============================================================================
# TESTS
# ==============================================================================

def test_embedded_font_parser():
    """Test WD_EXBO_EMBEDDED_FONT parser"""
    print("Testing Embedded Font Parser...")

    # Create test data
    request_type = EmbeddedFontRequestType.SUBSET | EmbeddedFontRequestType.COMPRESSED
    privilege = EmbeddedFontPrivilege.EDITABLE
    charset = EmbeddedFontCharacterSetType.UNICODE
    typeface_name = b"Arial"
    logfont_name = b"ArialMT"
    font_data = b"FAKE_FONT_DATA_" * 10

    # Build binary structure
    data = BytesIO()
    data.write(b'{')  # Opening brace

    # Calculate size
    size = (2 +  # opcode
            4 +  # request_type
            1 +  # privilege
            1 +  # charset
            4 + len(typeface_name) +  # typeface name
            4 + len(logfont_name) +   # logfont name
            4 + len(font_data) +      # font data
            1)  # closing brace

    data.write(struct.pack('<I', size))  # Size
    data.write(struct.pack('<H', WD_EXBO_EMBEDDED_FONT))  # Opcode
    data.write(struct.pack('<I', request_type))  # Request type
    data.write(struct.pack('<B', privilege))  # Privilege
    data.write(struct.pack('<B', charset))  # Charset
    data.write(struct.pack('<I', len(typeface_name)))
    data.write(typeface_name)
    data.write(struct.pack('<I', len(logfont_name)))
    data.write(logfont_name)
    data.write(struct.pack('<I', len(font_data)))
    data.write(font_data)
    data.write(b'}')  # Closing brace

    # Parse
    data.seek(0)
    result = ExtendedBinaryOpcodeDispatcher.parse_opcode(data)

    # Verify
    assert result['opcode'] == 'WD_EXBO_EMBEDDED_FONT'
    assert result['font_type_face_name'] == 'Arial'
    assert result['font_logfont_name'] == 'ArialMT'
    assert 'SUBSET' in result['request_flags']
    assert 'COMPRESSED' in result['request_flags']
    assert result['privilege_name'] == 'EDITABLE'

    print("✓ Embedded Font test passed")
    print(format_opcode_summary(result))


def test_block_meaning_parser():
    """Test WD_EXBO_BLOCK_MEANING parser"""
    print("\nTesting Block Meaning Parser...")

    # Create test data
    description = BlockMeaningDescription.SEAL

    # Build binary structure
    data = BytesIO()
    data.write(b'{')
    size = 2 + 2 + 1  # opcode + description + closing
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', WD_EXBO_BLOCK_MEANING))
    data.write(struct.pack('<H', description))
    data.write(b'}')

    # Parse
    data.seek(0)
    result = ExtendedBinaryOpcodeDispatcher.parse_opcode(data)

    # Verify
    assert result['opcode'] == 'WD_EXBO_BLOCK_MEANING'
    assert result['description_name'] == 'SEAL'

    print("✓ Block Meaning test passed")
    print(format_opcode_summary(result))


def test_userdata_parser():
    """Test WD_EXBO_USERDATA parser"""
    print("\nTesting User Data Parser...")

    # Create test data
    description = "MyCustomData"
    user_data = b"Custom application data here"

    # Build binary structure
    data = BytesIO()
    data.write(b'{')
    quoted_desc = f'"{description}"'.encode('utf-8')
    size = 2 + len(quoted_desc) + 4 + len(user_data) + 1
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', WD_EXBO_USERDATA))
    data.write(quoted_desc)
    data.write(struct.pack('<I', len(user_data)))
    data.write(user_data)
    data.write(b'}')

    # Parse
    data.seek(0)
    result = ExtendedBinaryOpcodeDispatcher.parse_opcode(data)

    # Verify
    assert result['opcode'] == 'WD_EXBO_USERDATA'
    assert result['data_description'] == description
    assert result['data_size'] == len(user_data)

    print("✓ User Data test passed")
    print(format_opcode_summary(result))


def test_blockref_parser():
    """Test WD_EXBO_BLOCKREF parser"""
    print("\nTesting BlockRef Parser...")

    # Create test data
    file_offset = 0x1000
    block_size = 0x5000

    # Build binary structure
    data = BytesIO()
    data.write(b'{')
    size = 2 + 8 + 8 + 1  # opcode + file_offset + block_size + closing
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', WD_EXBO_BLOCKREF))
    data.write(struct.pack('<Q', file_offset))
    data.write(struct.pack('<Q', block_size))
    data.write(b'}')

    # Parse
    data.seek(0)
    result = ExtendedBinaryOpcodeDispatcher.parse_opcode(data)

    # Verify
    assert result['opcode'] == 'WD_EXBO_BLOCKREF'
    assert result['file_offset'] == file_offset
    assert result['block_size'] == block_size

    print("✓ BlockRef test passed")
    print(format_opcode_summary(result))


def test_directory_parser():
    """Test WD_EXBO_DIRECTORY parser"""
    print("\nTesting Directory Parser...")

    # Create test data
    item_count = 3
    file_offset = 0x10000

    # Build binary structure (simplified - no actual blockrefs)
    data = BytesIO()
    data.write(b'{')
    size = 2 + 4 + 4 + 1  # opcode + item_count + file_offset + closing
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', WD_EXBO_DIRECTORY))
    data.write(struct.pack('<I', item_count))
    data.write(struct.pack('<I', file_offset))
    data.write(b'}')

    # Parse
    data.seek(0)
    result = ExtendedBinaryOpcodeDispatcher.parse_opcode(data)

    # Verify
    assert result['opcode'] == 'WD_EXBO_DIRECTORY'
    assert result['item_count'] == item_count
    assert result['file_offset'] == file_offset

    print("✓ Directory test passed")
    print(format_opcode_summary(result))


def test_macro_definition_parser():
    """Test WD_EXBO_MACRO_DEFINITION parser"""
    print("\nTesting Macro Definition Parser...")

    # Create test data
    index = 42
    scale_units = 1000

    # Build binary structure
    data = BytesIO()
    data.write(b'{')
    size = 2 + 2 + 4 + 1  # opcode + index + scale_units + closing
    data.write(struct.pack('<I', size))
    data.write(struct.pack('<H', WD_EXBO_MACRO_DEFINITION))
    data.write(struct.pack('<H', index))
    data.write(struct.pack('<I', scale_units))
    data.write(b'}')

    # Parse
    data.seek(0)
    result = ExtendedBinaryOpcodeDispatcher.parse_opcode(data)

    # Verify
    assert result['opcode'] == 'WD_EXBO_MACRO_DEFINITION'
    assert result['index'] == index
    assert result['scale_units'] == scale_units

    print("✓ Macro Definition test passed")
    print(format_opcode_summary(result))


def run_all_tests():
    """Run all opcode parser tests"""
    print("=" * 80)
    print("Agent 33: Extended Binary Advanced Opcodes - Test Suite")
    print("=" * 80)

    try:
        test_embedded_font_parser()
        test_block_meaning_parser()
        test_userdata_parser()
        test_blockref_parser()
        test_directory_parser()
        test_macro_definition_parser()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise


# ==============================================================================
# DOCUMENTATION
# ==============================================================================

OPCODE_DOCUMENTATION = """
===============================================================================
EXTENDED BINARY ADVANCED OPCODES - DOCUMENTATION
===============================================================================

1. WD_EXBO_EMBEDDED_FONT (0x013E / 318)
   Purpose: Embeds font data directly in the DWF file
   Use Cases: Custom fonts, ensuring consistent rendering
   Binary Structure:
     - request_type (4 bytes): Bit flags for font request
     - privilege (1 byte): Font embedding privilege level
     - character_set_type (1 byte): Unicode/Symbol/Glyphidx
     - font_type_face_name_length (4 bytes)
     - font_type_face_name_string (variable)
     - font_logfont_name_length (4 bytes)
     - font_logfont_name_string (variable)
     - data_size (4 bytes)
     - data (variable): Actual font data

2. WD_EXBO_BLOCK_MEANING (0x0142 / 322)
   Purpose: Defines semantic meaning of a block
   Use Cases: Distinguishing seals, stamps, labels, redlines
   Binary Structure:
     - description (2 bytes): Enum value
       * None = 0x01
       * Seal = 0x02
       * Stamp = 0x04
       * Label = 0x08
       * Redline = 0x10
       * Reserved1 = 0x20
       * Reserved2 = 0x40

3. WD_EXBO_BLOCKREF (0x015E / 350)
   Purpose: References to content blocks in DWF file
   Use Cases: Graphics, overlays, thumbnails, signatures
   Binary Structure:
     - file_offset (8 bytes): Location in file
     - block_size (8 bytes): Size of referenced block
     - ... (many optional fields based on block format)
   Note: Complex variable structure depending on block type

4. WD_EXBO_DIRECTORY (0x0160 / 352)
   Purpose: Directory of block references
   Use Cases: Table of contents for DWF sections
   Binary Structure:
     - item_count (4 bytes): Number of block references
     - blockrefs (variable): Array of nested BlockRef opcodes
     - file_offset (4 bytes): Directory location

5. WD_EXBO_USERDATA (0x0162 / 354)
   Purpose: Custom application-specific data
   Use Cases: Metadata, custom attributes, extensions
   Binary Structure:
     - data_description (quoted string): Description of data
     - data_size (4 bytes): Size of user data
     - data (variable): Raw user data

6. WD_EXBO_MACRO_DEFINITION (0x0171 / 369)
   Purpose: Define reusable graphic macros
   Use Cases: Repeated symbols, markers, patterns
   Binary Structure (rarely used - typically ASCII):
     - index (2 bytes): Macro identifier
     - scale_units (4 bytes): Scaling factor
     - objects (variable): Stream of serialized objects
   Note: C++ implementation shows binary format is commented out

===============================================================================
EXTENDED BINARY FORMAT SPECIFICATION
===============================================================================

All Extended Binary opcodes follow this structure:

  +----------------+
  | '{' (1 byte)   |  Opening delimiter
  +----------------+
  | Size (4 bytes) |  LE int32: size of everything after this field
  +----------------+
  | Opcode (2 bytes|  LE uint16: opcode identifier
  +----------------+
  | Data (variable)|  Opcode-specific data
  +----------------+
  | '}' (1 byte)   |  Closing delimiter
  +----------------+

Size Calculation:
  size = sizeof(opcode) + sizeof(data) + sizeof('}')
       = 2 + data_length + 1

===============================================================================
SOURCE FILES REFERENCE
===============================================================================

C++ Implementation Files:
  - embedded_font.cpp (lines 83-160)
  - blockref_defs.cpp (lines 49-200)
  - blockref.cpp (complex structure)
  - directory.cpp (lines 85-150)
  - userdata.cpp (lines 115-250)
  - macro_definition.cpp (lines 72-137, binary commented out)

Header Files:
  - opcode_defs.h (lines 193, 197, 225, 227, 229, 244)
  - blockref_defs.h (block meaning, encryption, orientation, alignment)
  - embedded_font.h
  - userdata.h
  - macro_definition.h

===============================================================================
"""


if __name__ == '__main__':
    # Run all tests
    run_all_tests()

    # Print documentation
    print("\n")
    print(OPCODE_DOCUMENTATION)
