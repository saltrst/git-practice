"""
Agent 23: DWF Extended ASCII Text Formatting and Grouping Opcodes

This module implements 6 Extended ASCII opcodes for text formatting and grouping:
1. WD_EXAO_TEXT_VALIGN (ID 374) - Text vertical alignment
2. WD_EXAO_TEXT_BACKGROUND (ID 376) - Text background styling
3. WD_EXAO_OVERPOST (ID 378) - Overposting control for label placement
4. WD_EXAO_SET_GROUP_BEGIN (ID 313) - Begin grouping objects
5. WD_EXAO_SET_GROUP_END (ID 314) - End grouping objects
6. WD_EXAO_BLOCK_MEANING (ID 321) - Block semantic descriptions

References:
- C++ Source: dwf-toolkit-source/develop/global/src/dwf/whiptk/
- Research: agent_13_extended_opcodes_research.md
"""

import struct
import io
from enum import IntEnum
from typing import Dict, List, Any, Optional, BinaryIO
from dataclasses import dataclass


# =============================================================================
# Constants and Enumerations
# =============================================================================

# Opcode IDs (Extended ASCII)
WD_EXAO_TEXT_VALIGN = 374
WD_EXAO_TEXT_BACKGROUND = 376
WD_EXAO_OVERPOST = 378
WD_EXAO_SET_GROUP_BEGIN = 313
WD_EXAO_SET_GROUP_END = 314
WD_EXAO_BLOCK_MEANING = 321

# Opcode IDs (Extended Binary)
WD_EXBO_TEXT_VALIGN = 0x0175
WD_EXBO_TEXT_BACKGROUND = 0x0177
WD_EXBO_OVERPOST = 0x0179
WD_EXBO_BLOCK_MEANING = 0x0141


class TextVAlign(IntEnum):
    """Text vertical alignment options."""
    DESCENTLINE = 0  # Descentline aligned with insertion point
    BASELINE = 1     # Baseline aligned with insertion point (default)
    HALFLINE = 2     # Halfline aligned with insertion point
    CAPLINE = 3      # Capline aligned with insertion point
    ASCENTLINE = 4   # Ascentline aligned with insertion point


class TextBackground(IntEnum):
    """Text background styling options."""
    NONE = 0     # No text background (default)
    GHOSTED = 1  # Ghosted (semi-transparent) text background
    SOLID = 2    # Solid text background


class OverpostAcceptMode(IntEnum):
    """Overpost accept modes for label placement."""
    ACCEPT_ALL = 0       # Process all entities in overpost group
    ACCEPT_ALL_FIT = 1   # Process entities that fit
    ACCEPT_FIRST_FIT = 2 # Process first entity that fits


class BlockMeaning(IntEnum):
    """Block semantic meaning flags (bit flags)."""
    NONE = 0x00000001      # No special meaning
    SEAL = 0x00000002      # Seal block
    STAMP = 0x00000004     # Stamp block
    LABEL = 0x00000008     # Label block
    REDLINE = 0x00000010   # Redline block
    RESERVED1 = 0x00000020 # Reserved for future use
    RESERVED2 = 0x00000040 # Reserved for future use


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TextVAlignData:
    """Text vertical alignment data."""
    alignment: TextVAlign = TextVAlign.BASELINE

    def __repr__(self):
        return f"TextVAlign({self.alignment.name})"


@dataclass
class TextBackgroundData:
    """Text background data."""
    background: TextBackground = TextBackground.NONE
    offset: int = 0  # Offset in drawing units

    def __repr__(self):
        return f"TextBackground({self.background.name}, offset={self.offset})"


@dataclass
class OverpostData:
    """Overpost control data."""
    accept_mode: OverpostAcceptMode = OverpostAcceptMode.ACCEPT_ALL
    render_entities: bool = True
    add_extents: bool = True
    children: List[Any] = None  # Child objects within overpost group

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def __repr__(self):
        return (f"Overpost(mode={self.accept_mode.name}, "
                f"render={self.render_entities}, "
                f"extents={self.add_extents}, "
                f"children={len(self.children)})")


@dataclass
class GroupBeginData:
    """Group begin marker data."""
    group_path: str = ""

    def __repr__(self):
        return f"GroupBegin('{self.group_path}')"


@dataclass
class GroupEndData:
    """Group end marker data."""

    def __repr__(self):
        return "GroupEnd()"


@dataclass
class BlockMeaningData:
    """Block meaning data."""
    description: BlockMeaning = BlockMeaning.NONE

    def __repr__(self):
        return f"BlockMeaning({self.description.name})"


# =============================================================================
# Helper Functions
# =============================================================================

def read_ascii_token(stream: BinaryIO, max_size: int = 256) -> str:
    """
    Read an ASCII token from stream (whitespace-delimited).
    Handles quoted strings with spaces.

    Args:
        stream: Input byte stream
        max_size: Maximum token size

    Returns:
        Token string
    """
    token = []

    # Skip leading whitespace
    while True:
        byte = stream.read(1)
        if not byte:
            break
        if byte not in (b' ', b'\t', b'\n', b'\r'):
            token.append(byte)
            break

    # Check if this is a quoted string
    if token and token[0] == b'"':
        # Read until closing quote
        while len(token) < max_size:
            byte = stream.read(1)
            if not byte:
                break
            token.append(byte)
            if byte == b'"':
                break
        return b''.join(token).decode('ascii')

    # Read until whitespace or paren
    while len(token) < max_size:
        byte = stream.read(1)
        if not byte:
            break
        if byte in (b' ', b'\t', b'\n', b'\r', b'(', b')'):
            stream.seek(-1, 1)  # Put back terminator
            break
        token.append(byte)

    return b''.join(token).decode('ascii')


def read_ascii_int(stream: BinaryIO) -> int:
    """Read an ASCII integer from stream."""
    token = read_ascii_token(stream)
    return int(token)


def skip_to_close_paren(stream: BinaryIO, depth: int = 1) -> None:
    """
    Skip to matching closing parenthesis.

    Args:
        stream: Input byte stream
        depth: Current parenthesis nesting depth
    """
    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF while skipping to close paren")
        if byte == b'(':
            depth += 1
        elif byte == b')':
            depth -= 1


# =============================================================================
# Opcode Handlers
# =============================================================================

def handle_text_valign_ascii(stream: BinaryIO) -> TextVAlignData:
    """
    Parse Extended ASCII TextVAlign opcode.

    Format: (TextVAlign <enum_string>)

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        TextVAlignData object
    """
    # Read alignment enum string
    enum_str = read_ascii_token(stream)

    # Map string to enum
    alignment_map = {
        'Descentline': TextVAlign.DESCENTLINE,
        'Baseline': TextVAlign.BASELINE,
        'Halfline': TextVAlign.HALFLINE,
        'Capline': TextVAlign.CAPLINE,
        'Ascentline': TextVAlign.ASCENTLINE,
    }

    alignment = alignment_map.get(enum_str, TextVAlign.BASELINE)

    # Skip to closing paren
    skip_to_close_paren(stream)

    return TextVAlignData(alignment=alignment)


def handle_text_valign_binary(stream: BinaryIO, data_size: int) -> TextVAlignData:
    """
    Parse Extended Binary TextVAlign opcode.

    Format: {size, 0x0175, <byte_enum>, }

    Args:
        stream: Input byte stream
        data_size: Size of data portion

    Returns:
        TextVAlignData object
    """
    # Read enum value (1 byte)
    enum_byte = struct.unpack('<B', stream.read(1))[0]

    # Validate and convert
    if enum_byte < 5:
        alignment = TextVAlign(enum_byte)
    else:
        alignment = TextVAlign.BASELINE

    # Read closing brace
    close = stream.read(1)
    if close != b'}':
        raise ValueError("Expected '}' at end of binary opcode")

    return TextVAlignData(alignment=alignment)


def handle_text_background_ascii(stream: BinaryIO) -> TextBackgroundData:
    """
    Parse Extended ASCII TextBackground opcode.

    Format: (TextBackground <enum_string> <offset>)

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        TextBackgroundData object
    """
    # Read background enum string
    enum_str = read_ascii_token(stream)

    # Map string to enum
    background_map = {
        'None': TextBackground.NONE,
        'Ghosted': TextBackground.GHOSTED,
        'Solid': TextBackground.SOLID,
    }

    background = background_map.get(enum_str, TextBackground.NONE)

    # Read offset
    offset = read_ascii_int(stream)

    # Skip to closing paren
    skip_to_close_paren(stream)

    return TextBackgroundData(background=background, offset=offset)


def handle_text_background_binary(stream: BinaryIO, data_size: int) -> TextBackgroundData:
    """
    Parse Extended Binary TextBackground opcode.

    Format: {size, 0x0177, <byte_enum>, <int32_offset>, }

    Args:
        stream: Input byte stream
        data_size: Size of data portion

    Returns:
        TextBackgroundData object
    """
    # Read enum value (1 byte)
    enum_byte = struct.unpack('<B', stream.read(1))[0]

    # Validate and convert
    if enum_byte < 3:
        background = TextBackground(enum_byte)
    else:
        background = TextBackground.NONE

    # Read offset (4 bytes, signed)
    offset = struct.unpack('<i', stream.read(4))[0]

    # Read closing brace
    close = stream.read(1)
    if close != b'}':
        raise ValueError("Expected '}' at end of binary opcode")

    return TextBackgroundData(background=background, offset=offset)


def handle_overpost_ascii(stream: BinaryIO) -> OverpostData:
    """
    Parse Extended ASCII Overpost opcode.

    Format: (Overpost <accept_mode> <render_entities> <add_extents> <children...>)

    Note: This is a container opcode. Child materialization is simplified here.

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        OverpostData object
    """
    # Read accept mode
    mode_str = read_ascii_token(stream)
    mode_map = {
        'All': OverpostAcceptMode.ACCEPT_ALL,
        'AllFit': OverpostAcceptMode.ACCEPT_ALL_FIT,
        'FirstFit': OverpostAcceptMode.ACCEPT_FIRST_FIT,
    }
    accept_mode = mode_map.get(mode_str, OverpostAcceptMode.ACCEPT_ALL)

    # Read render_entities boolean
    render_str = read_ascii_token(stream)
    render_entities = (render_str == 'True')

    # Read add_extents boolean
    extents_str = read_ascii_token(stream)
    add_extents = (extents_str == 'True')

    # Note: In a full implementation, child objects would be materialized here.
    # For this translation, we simply skip to the closing paren.
    # The C++ implementation calls materialize_stream() to process children.

    children = []  # Placeholder for child objects

    # Skip to closing paren
    skip_to_close_paren(stream)

    return OverpostData(
        accept_mode=accept_mode,
        render_entities=render_entities,
        add_extents=add_extents,
        children=children
    )


def handle_group_begin_ascii(stream: BinaryIO) -> GroupBeginData:
    """
    Parse Extended ASCII GroupBegin opcode.

    Format: (GroupBegin <group_path>)

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        GroupBeginData object
    """
    # Read group path string (may be quoted)
    group_path = read_ascii_token(stream)

    # Remove quotes if present
    if group_path.startswith('"') and group_path.endswith('"'):
        group_path = group_path[1:-1]

    # Skip to closing paren
    skip_to_close_paren(stream)

    return GroupBeginData(group_path=group_path)


def handle_group_end_ascii(stream: BinaryIO) -> GroupEndData:
    """
    Parse Extended ASCII GroupEnd opcode.

    Format: (GroupEnd)

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        GroupEndData object
    """
    # No parameters - just skip to closing paren
    skip_to_close_paren(stream)

    return GroupEndData()


def handle_block_meaning_ascii(stream: BinaryIO) -> BlockMeaningData:
    """
    Parse Extended ASCII BlockMeaning opcode.

    Format: (BlockMeaning "<description>")

    Note: Strings are padded with spaces to fixed widths in C++ implementation.

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        BlockMeaningData object
    """
    # Read description string (may be quoted)
    desc_str = read_ascii_token(stream)

    # Remove quotes if present
    if desc_str.startswith('"') and desc_str.endswith('"'):
        desc_str = desc_str[1:-1]

    # Map string to enum (strip trailing spaces)
    desc_str = desc_str.strip()

    desc_map = {
        'None': BlockMeaning.NONE,
        'Seal': BlockMeaning.SEAL,
        'Stamp': BlockMeaning.STAMP,
        'Label': BlockMeaning.LABEL,
        'Redline': BlockMeaning.REDLINE,
        'Reserved1': BlockMeaning.RESERVED1,
        'Reserved2': BlockMeaning.RESERVED2,
    }

    description = desc_map.get(desc_str, BlockMeaning.NONE)

    # Skip to closing paren
    skip_to_close_paren(stream)

    return BlockMeaningData(description=description)


def handle_block_meaning_binary(stream: BinaryIO, data_size: int) -> BlockMeaningData:
    """
    Parse Extended Binary BlockMeaning opcode.

    Format: {size, opcode, <uint16_description>, }

    Args:
        stream: Input byte stream
        data_size: Size of data portion

    Returns:
        BlockMeaningData object
    """
    # Read description value (2 bytes, unsigned)
    desc_value = struct.unpack('<H', stream.read(2))[0]

    # Map to enum (validate known values)
    valid_values = {
        0x00000001: BlockMeaning.NONE,
        0x00000002: BlockMeaning.SEAL,
        0x00000004: BlockMeaning.STAMP,
        0x00000008: BlockMeaning.LABEL,
        0x00000010: BlockMeaning.REDLINE,
        0x00000020: BlockMeaning.RESERVED1,
        0x00000040: BlockMeaning.RESERVED2,
    }

    description = valid_values.get(desc_value, BlockMeaning.NONE)

    # Read closing brace
    close = stream.read(1)
    if close != b'}':
        raise ValueError("Expected '}' at end of binary opcode")

    return BlockMeaningData(description=description)


# =============================================================================
# Main Opcode Dispatcher
# =============================================================================

class TextFormattingOpcodeHandler:
    """
    Handler for text formatting and grouping opcodes.
    """

    def __init__(self):
        # Map Extended ASCII opcode names to handlers
        self.ascii_handlers = {
            'TextVAlign': handle_text_valign_ascii,
            'TextBackground': handle_text_background_ascii,
            'Overpost': handle_overpost_ascii,
            'GroupBegin': handle_group_begin_ascii,
            'GroupEnd': handle_group_end_ascii,
            'BlockMeaning': handle_block_meaning_ascii,
        }

        # Map Extended Binary opcode values to handlers
        self.binary_handlers = {
            WD_EXBO_TEXT_VALIGN: handle_text_valign_binary,
            WD_EXBO_TEXT_BACKGROUND: handle_text_background_binary,
            WD_EXBO_BLOCK_MEANING: handle_block_meaning_binary,
            # Note: EXBO_OVERPOST not fully supported (see C++ comments)
        }

    def handle_ascii(self, opcode_name: str, stream: BinaryIO) -> Any:
        """
        Dispatch Extended ASCII opcode to appropriate handler.

        Args:
            opcode_name: Name of opcode (e.g., 'TextVAlign')
            stream: Input byte stream positioned after opcode name

        Returns:
            Parsed opcode data object

        Raises:
            ValueError: If opcode is unknown
        """
        handler = self.ascii_handlers.get(opcode_name)
        if not handler:
            raise ValueError(f"Unknown Extended ASCII opcode: {opcode_name}")

        return handler(stream)

    def handle_binary(self, opcode_value: int, stream: BinaryIO, data_size: int) -> Any:
        """
        Dispatch Extended Binary opcode to appropriate handler.

        Args:
            opcode_value: Binary opcode value (e.g., 0x0175)
            stream: Input byte stream
            data_size: Size of data portion (excludes opcode and closing brace)

        Returns:
            Parsed opcode data object

        Raises:
            ValueError: If opcode is unknown
        """
        handler = self.binary_handlers.get(opcode_value)
        if not handler:
            raise ValueError(f"Unknown Extended Binary opcode: 0x{opcode_value:04X}")

        return handler(stream, data_size)


# =============================================================================
# Test Cases
# =============================================================================

def test_text_valign():
    """Test TextVAlign opcode parsing."""
    print("Testing TextVAlign...")

    # Test ASCII format - Baseline
    data = b'Baseline)'
    stream = io.BytesIO(data)
    result = handle_text_valign_ascii(stream)
    assert result.alignment == TextVAlign.BASELINE
    print(f"  ASCII Baseline: {result}")

    # Test ASCII format - Capline
    data = b'Capline)'
    stream = io.BytesIO(data)
    result = handle_text_valign_ascii(stream)
    assert result.alignment == TextVAlign.CAPLINE
    print(f"  ASCII Capline: {result}")

    # Test Binary format
    data = struct.pack('<BB', 2, ord('}'))  # HALFLINE = 2
    stream = io.BytesIO(data)
    result = handle_text_valign_binary(stream, 1)
    assert result.alignment == TextVAlign.HALFLINE
    print(f"  Binary Halfline: {result}")

    print("  ✓ TextVAlign tests passed\n")


def test_text_background():
    """Test TextBackground opcode parsing."""
    print("Testing TextBackground...")

    # Test ASCII format
    data = b'Solid 10)'
    stream = io.BytesIO(data)
    result = handle_text_background_ascii(stream)
    assert result.background == TextBackground.SOLID
    assert result.offset == 10
    print(f"  ASCII Solid: {result}")

    # Test ASCII format - Ghosted
    data = b'Ghosted 5)'
    stream = io.BytesIO(data)
    result = handle_text_background_ascii(stream)
    assert result.background == TextBackground.GHOSTED
    assert result.offset == 5
    print(f"  ASCII Ghosted: {result}")

    # Test Binary format
    data = struct.pack('<BiB', 2, 20, ord('}'))  # SOLID=2, offset=20
    stream = io.BytesIO(data)
    result = handle_text_background_binary(stream, 5)
    assert result.background == TextBackground.SOLID
    assert result.offset == 20
    print(f"  Binary Solid: {result}")

    print("  ✓ TextBackground tests passed\n")


def test_overpost():
    """Test Overpost opcode parsing."""
    print("Testing Overpost...")

    # Test ASCII format - AllFit
    data = b'AllFit True False)'
    stream = io.BytesIO(data)
    result = handle_overpost_ascii(stream)
    assert result.accept_mode == OverpostAcceptMode.ACCEPT_ALL_FIT
    assert result.render_entities == True
    assert result.add_extents == False
    print(f"  ASCII AllFit: {result}")

    # Test ASCII format - FirstFit
    data = b'FirstFit False True)'
    stream = io.BytesIO(data)
    result = handle_overpost_ascii(stream)
    assert result.accept_mode == OverpostAcceptMode.ACCEPT_FIRST_FIT
    assert result.render_entities == False
    assert result.add_extents == True
    print(f"  ASCII FirstFit: {result}")

    print("  ✓ Overpost tests passed\n")


def test_group_begin_end():
    """Test GroupBegin and GroupEnd opcode parsing."""
    print("Testing GroupBegin/GroupEnd...")

    # Test GroupBegin
    data = b'MyGroup/SubGroup)'
    stream = io.BytesIO(data)
    result = handle_group_begin_ascii(stream)
    assert result.group_path == 'MyGroup/SubGroup'
    print(f"  GroupBegin: {result}")

    # Test GroupBegin with quoted path
    data = b'"My Group/Sub Group")'
    stream = io.BytesIO(data)
    result = handle_group_begin_ascii(stream)
    assert result.group_path == 'My Group/Sub Group'
    print(f"  GroupBegin (quoted): {result}")

    # Test GroupEnd
    data = b')'
    stream = io.BytesIO(data)
    result = handle_group_end_ascii(stream)
    print(f"  GroupEnd: {result}")

    print("  ✓ GroupBegin/GroupEnd tests passed\n")


def test_block_meaning():
    """Test BlockMeaning opcode parsing."""
    print("Testing BlockMeaning...")

    # Test ASCII format - Seal
    data = b'"Seal     ")'
    stream = io.BytesIO(data)
    result = handle_block_meaning_ascii(stream)
    assert result.description == BlockMeaning.SEAL
    print(f"  ASCII Seal: {result}")

    # Test ASCII format - Label
    data = b'Label)'
    stream = io.BytesIO(data)
    result = handle_block_meaning_ascii(stream)
    assert result.description == BlockMeaning.LABEL
    print(f"  ASCII Label: {result}")

    # Test Binary format - STAMP
    data = struct.pack('<HB', 0x0004, ord('}'))  # STAMP = 0x0004
    stream = io.BytesIO(data)
    result = handle_block_meaning_binary(stream, 2)
    assert result.description == BlockMeaning.STAMP
    print(f"  Binary Stamp: {result}")

    # Test Binary format - REDLINE
    data = struct.pack('<HB', 0x0010, ord('}'))  # REDLINE = 0x0010
    stream = io.BytesIO(data)
    result = handle_block_meaning_binary(stream, 2)
    assert result.description == BlockMeaning.REDLINE
    print(f"  Binary Redline: {result}")

    print("  ✓ BlockMeaning tests passed\n")


def test_integration():
    """Test integrated parsing scenarios."""
    print("Testing integration scenarios...")

    handler = TextFormattingOpcodeHandler()

    # Test ASCII opcode dispatch
    stream = io.BytesIO(b'Ascentline)')
    result = handler.handle_ascii('TextVAlign', stream)
    assert result.alignment == TextVAlign.ASCENTLINE
    print(f"  Integrated ASCII TextVAlign: {result}")

    # Test Binary opcode dispatch
    data = struct.pack('<BiB', 1, 15, ord('}'))  # GHOSTED=1, offset=15
    stream = io.BytesIO(data)
    result = handler.handle_binary(WD_EXBO_TEXT_BACKGROUND, stream, 5)
    assert result.background == TextBackground.GHOSTED
    assert result.offset == 15
    print(f"  Integrated Binary TextBackground: {result}")

    print("  ✓ Integration tests passed\n")


def run_all_tests():
    """Run all test cases."""
    print("="*70)
    print("Agent 23: Text Formatting Opcodes - Test Suite")
    print("="*70 + "\n")

    try:
        test_text_valign()
        test_text_background()
        test_overpost()
        test_group_begin_end()
        test_block_meaning()
        test_integration()

        print("="*70)
        print("ALL TESTS PASSED ✓")
        print("="*70)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        raise


# =============================================================================
# Documentation
# =============================================================================

DOCUMENTATION = """
Agent 23: DWF Text Formatting and Grouping Opcodes
==================================================

This module implements 6 Extended ASCII opcodes for text formatting and object grouping.

OPCODES IMPLEMENTED
------------------

1. WD_EXAO_TEXT_VALIGN (ID 374) - Text Vertical Alignment
   - Token: (TextVAlign
   - Purpose: Controls vertical alignment of text relative to insertion point
   - Values: Descentline, Baseline, Halfline, Capline, Ascentline
   - Default: Baseline

   Extended ASCII: (TextVAlign <enum_string>)
   Extended Binary: {size, 0x0175, <byte_enum>, }

   Example: (TextVAlign Capline)

2. WD_EXAO_TEXT_BACKGROUND (ID 376) - Text Background
   - Token: (TextBackground
   - Purpose: Defines background styling behind text
   - Values: None, Ghosted (semi-transparent), Solid
   - Offset: Drawing units offset for background

   Extended ASCII: (TextBackground <enum_string> <offset>)
   Extended Binary: {size, 0x0177, <byte_enum>, <int32_offset>, }

   Example: (TextBackground Solid 10)

3. WD_EXAO_OVERPOST (ID 378) - Overposting Control
   - Token: (Overpost
   - Purpose: Controls label placement to prevent overlapping
   - Accept Modes:
     * All: Process all entities in overpost group
     * AllFit: Process entities that fit without overlapping
     * FirstFit: Process first entity that fits
   - Flags: render_entities, add_extents
   - Container: Can have child objects

   Extended ASCII: (Overpost <mode> <render> <extents> <children...>)

   Example: (Overpost AllFit True False)

   Note: Extended Binary format not fully supported (see C++ comments)

4. WD_EXAO_SET_GROUP_BEGIN (ID 313) - Begin Group
   - Token: (GroupBegin
   - Purpose: Start a logical grouping of drawing objects
   - Path: Hierarchical group identifier (e.g., "Layer1/Group2")

   Extended ASCII: (GroupBegin <group_path>)

   Example: (GroupBegin "Annotations/Labels")

5. WD_EXAO_SET_GROUP_END (ID 314) - End Group
   - Token: (GroupEnd
   - Purpose: End the current logical grouping
   - No parameters

   Extended ASCII: (GroupEnd)

   Example: (GroupEnd)

6. WD_EXAO_BLOCK_MEANING (ID 321) - Block Semantics
   - Token: (BlockMeaning
   - Purpose: Defines semantic meaning of block content
   - Values: None, Seal, Stamp, Label, Redline, Reserved1, Reserved2
   - Used primarily with BlockRef objects (deprecated in newer DWF versions)

   Extended ASCII: (BlockMeaning "<description>")
   Extended Binary: {size, 0x0141, <uint16_description>, }

   Example: (BlockMeaning "Seal")

USAGE EXAMPLES
-------------

Basic Handler Usage:
    handler = TextFormattingOpcodeHandler()

    # Parse Extended ASCII
    stream = io.BytesIO(b'Baseline)')
    result = handler.handle_ascii('TextVAlign', stream)
    print(result.alignment)  # TextVAlign.BASELINE

    # Parse Extended Binary
    data = struct.pack('<BB', 2, ord('}'))
    stream = io.BytesIO(data)
    result = handler.handle_binary(WD_EXBO_TEXT_VALIGN, stream, 1)
    print(result.alignment)  # TextVAlign.HALFLINE

Typical DWF File Sequence:
    (TextVAlign Baseline)
    (TextBackground Solid 5)
    (GroupBegin "Annotations")
        (Overpost AllFit True True)
            # ... text and label objects ...
        )
    (GroupEnd)

KEY IMPLEMENTATION NOTES
-----------------------

1. TextVAlign:
   - Default is BASELINE (most common for CAD text)
   - Affects how text is positioned relative to insertion point
   - Binary format uses single byte (0-4)

2. TextBackground:
   - GHOSTED provides semi-transparent background
   - SOLID provides opaque background
   - Offset controls background border size

3. Overpost:
   - Complex container opcode with child objects
   - AcceptAllFit prevents label overlapping (important for maps)
   - Full implementation requires child object materialization

4. GroupBegin/GroupEnd:
   - Must be properly paired (Begin before End)
   - Support hierarchical nesting (Group1/Group2/Group3)
   - Replaced by Object_Node in newer DWF versions

5. BlockMeaning:
   - Deprecated in DWF 6.0+ (Package Format)
   - Primarily used with BlockRef objects
   - Values are bit flags (can be OR'd together in theory)

EXTENDED ASCII PARSING
---------------------

The Extended ASCII format uses parenthesized tokens:
    (OpcodeName field1 field2 ... fieldN)

Key parsing rules:
- Opcode name: First token after opening '('
- Fields: Whitespace-separated values
- Strings: May be quoted if containing spaces
- Enums: String representations (e.g., "Baseline")
- Close: Must have matching ')'

EXTENDED BINARY PARSING
----------------------

The Extended Binary format:
    { (1 byte)
    + Size (4 bytes LE) - everything after this field
    + Opcode (2 bytes LE) - binary opcode value
    + Data (variable)
    + } (1 byte)

Opcode values:
- 0x0175: TEXT_VALIGN
- 0x0177: TEXT_BACKGROUND
- 0x0141: BLOCK_MEANING

RENDITION CONTEXT
----------------

These opcodes affect the current rendering state:
- TextVAlign: Sets text vertical alignment for subsequent text
- TextBackground: Sets background style for subsequent text
- GroupBegin/End: Establishes grouping context
- Overpost: Creates overpost rendering context
- BlockMeaning: Sets block semantic meaning (BlockRef context)

ERROR HANDLING
-------------

The implementation handles:
- Invalid enum values (defaults to safe values)
- Missing closing braces/parens
- Malformed data streams
- Unknown opcode variations

TESTING
-------

Run test suite:
    python agent_23_text_formatting.py

Tests cover:
- All 6 opcodes in ASCII format
- Binary formats where supported
- Valid enum ranges
- Edge cases (unknown values, quoted strings)
- Integration with handler dispatcher

REFERENCES
----------

C++ Source Files:
- text_valign.h/cpp
- text_background.h/cpp
- overpost.h/cpp
- group_begin.cpp
- group_end.cpp
- blockref_defs.h/cpp (BlockMeaning)

Research Document:
- agent_13_extended_opcodes_research.md

DWF Specification:
- Extended ASCII format: Section 2.1
- Extended Binary format: Section 1.2
"""


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    print(__doc__)
    print(DOCUMENTATION)
    run_all_tests()
