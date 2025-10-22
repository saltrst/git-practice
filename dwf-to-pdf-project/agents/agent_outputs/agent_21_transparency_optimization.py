"""
DWF Extended ASCII Transparency/Optimization Opcodes (Agent 21)

This module implements parsers for 6 DWF Extended ASCII rendering mode opcodes:
- WD_EXAO_SET_TRANSPARENT (ID 311) - '(Transparent)' - Transparency setting
- WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING (ID 312) - '(PlotOptimized N)' - Plot optimization
- WD_EXAO_SET_PROJECTION (ID 283) - '(Projection "mode")' - Projection settings
- WD_EXAO_ORIENTATION (ID 326) - '(Orientation "type")' - Orientation
- WD_EXAO_ALIGNMENT (ID 328) - '(Alignment "type")' - Alignment
- WD_EXAO_DELINEATE (ID 379) - '(Delineate)' - Delineation flag

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/merge_control.cpp (transparent)
- develop/global/src/dwf/whiptk/plot_optimized.cpp
- develop/global/src/dwf/whiptk/projection.cpp
- develop/global/src/dwf/whiptk/blockref_defs.cpp (orientation, alignment)
- develop/global/src/dwf/whiptk/delineate.cpp

Opcode Specifications:
======================

1. SET_TRANSPARENT (311):
   Format: (Transparent)  [no arguments - sets transparency via merge control]
   Note: Part of merge_control opcode - alternate form of (LinesOverwrite "transparent")

2. SET_OPTIMIZED_FOR_PLOTTING (312):
   Format: (PlotOptimized <value>)
   - value: Integer (0=false, non-zero=true)

3. SET_PROJECTION (283):
   Format: (Projection "<mode>")
   - mode: "normal", "stretch", or "chop"

4. ORIENTATION (326):
   Format: (Orientation "<type>")
   - type: "Always_In_Sync  ", "Always_Different", or "Decoupled       "

5. ALIGNMENT (328):
   Format: (Alignment "<type>")
   - type: "Align_Center", "Align_Title_Block", "Align_Top", "Align_Bottom",
           "Align_Left", "Align_Right", "Align_Top_Left", "Align_Top_Right",
           "Align_Bottom_Left", "Align_Bottom_Right", or "Align_None"

6. DELINEATE (379):
   Format: (Delineate)  [no arguments - sets delineation flag to true]
"""

import struct
from typing import Dict, BinaryIO, Optional
from enum import IntEnum


class ProjectionType(IntEnum):
    """
    Projection type enumeration.
    Corresponds to WT_Projection::WT_Projection_Type in C++ code.
    """
    NORMAL = 0   # Normal projection
    STRETCH = 1  # Stretch to fit
    CHOP = 2     # Chop/clip to boundaries


class OrientationType(IntEnum):
    """
    Orientation type enumeration.
    Corresponds to WT_Orientation::WT_Orientation_Description in C++ code.
    """
    ALWAYS_IN_SYNC = 0x00000001      # Paper and image orientation always synchronized
    ALWAYS_DIFFERENT = 0x00000002    # Paper and image orientation always different
    DECOUPLED = 0x00000004           # Paper and image orientation decoupled


class AlignmentType(IntEnum):
    """
    Alignment type enumeration.
    Corresponds to WT_Alignment::WT_Alignment_Description in C++ code.
    """
    ALIGN_CENTER = 0x00000001        # Center alignment
    ALIGN_TITLE_BLOCK = 0x00000002   # Title block alignment
    ALIGN_TOP = 0x00000004           # Top alignment
    ALIGN_BOTTOM = 0x00000008        # Bottom alignment
    ALIGN_LEFT = 0x00000010          # Left alignment
    ALIGN_RIGHT = 0x00000020         # Right alignment
    ALIGN_TOP_LEFT = 0x00000040      # Top-left corner alignment
    ALIGN_TOP_RIGHT = 0x00000080     # Top-right corner alignment
    ALIGN_BOTTOM_LEFT = 0x00000100   # Bottom-left corner alignment
    ALIGN_BOTTOM_RIGHT = 0x00000200  # Bottom-right corner alignment
    ALIGN_NONE = 0x00000400          # No specific alignment


# ============================================================================
# EXTENDED ASCII PARSING UTILITIES
# ============================================================================

def skip_whitespace(stream: BinaryIO) -> None:
    """
    Skip whitespace characters (space, tab, LF, CR) in the stream.

    Args:
        stream: Binary stream to read from
    """
    while True:
        pos = stream.tell()
        byte = stream.read(1)
        if not byte or byte not in (b' ', b'\t', b'\n', b'\r'):
            # Put back the non-whitespace byte
            if byte:
                stream.seek(pos)
            break


def read_quoted_string(stream: BinaryIO) -> str:
    """
    Read a quoted string from the stream.

    Format: "string_content"

    Args:
        stream: Binary stream positioned at or before the opening quote

    Returns:
        The unquoted string content

    Raises:
        ValueError: If string format is invalid
    """
    skip_whitespace(stream)

    # Read opening quote
    quote = stream.read(1)
    if quote != b'"':
        raise ValueError(f"Expected opening quote, got: {quote}")

    # Accumulate string content
    chars = []
    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF while reading quoted string")

        if byte == b'"':
            # Found closing quote
            return ''.join(chr(c) for c in chars)
        elif byte == b'\\':
            # Handle escape sequences (if any)
            next_byte = stream.read(1)
            if not next_byte:
                raise ValueError("Unexpected EOF after escape character")
            chars.append(next_byte[0])
        else:
            chars.append(byte[0])


def read_ascii_integer(stream: BinaryIO) -> int:
    """
    Read an ASCII-encoded integer from the stream.

    Reads digits until a non-digit character (typically whitespace or ')') is found.
    The terminating character is put back into the stream.

    Args:
        stream: Binary stream to read from

    Returns:
        The parsed integer value

    Raises:
        ValueError: If no valid integer is found
    """
    skip_whitespace(stream)

    chars = []
    sign = 1

    # Check for sign
    pos = stream.tell()
    first = stream.read(1)
    if first == b'-':
        sign = -1
    elif first == b'+':
        pass  # Positive sign, continue
    else:
        # Put it back, it's a digit
        if first:
            stream.seek(pos)

    # Read digits
    while True:
        pos = stream.tell()
        byte = stream.read(1)

        if not byte:
            break

        if b'0' <= byte <= b'9':
            chars.append(chr(byte[0]))
        else:
            # Non-digit found, put it back
            stream.seek(pos)
            break

    if not chars:
        raise ValueError("No ASCII integer found in stream")

    return sign * int(''.join(chars))


def skip_to_closing_paren(stream: BinaryIO) -> None:
    """
    Skip to the matching closing parenthesis ')'.

    Handles nested parentheses by tracking depth.

    Args:
        stream: Binary stream to read from

    Raises:
        ValueError: If EOF reached before closing paren
    """
    depth = 1
    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF while seeking closing parenthesis")

        if byte == b'(':
            depth += 1
        elif byte == b')':
            depth -= 1


# ============================================================================
# OPCODE PARSERS
# ============================================================================

def parse_exao_set_transparent(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended ASCII opcode WD_EXAO_SET_TRANSPARENT (ID 311).

    This opcode sets the transparency mode via the merge control system.
    It is equivalent to (LinesOverwrite "transparent").

    Format: (Transparent)
    - No arguments
    - Simply sets transparency flag

    Args:
        stream: Binary stream positioned after "(Transparent" token

    Returns:
        Dictionary containing:
            - 'merge_mode': String, always 'transparent'
            - 'transparent': Boolean, always True
            - 'description': Human-readable description

    Example:
        >>> import io
        >>> stream = io.BytesIO(b')')  # Just closing paren
        >>> result = parse_exao_set_transparent(stream)
        >>> result['transparent']
        True
        >>> result['merge_mode']
        'transparent'

    Notes:
        - Part of merge_control.cpp functionality
        - Sets transparency rendering mode for subsequent operations
        - Corresponds to WT_Merge_Control with mode set to Transparent
    """
    skip_to_closing_paren(stream)

    return {
        'merge_mode': 'transparent',
        'transparent': True,
        'description': 'Transparency mode enabled'
    }


def parse_exao_set_optimized_for_plotting(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended ASCII opcode WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING (ID 312).

    This opcode sets whether the drawing is optimized for plotting output.

    Format: (PlotOptimized <value>)
    - value: Integer (0 = not optimized, non-zero = optimized)

    Args:
        stream: Binary stream positioned after "(PlotOptimized" token

    Returns:
        Dictionary containing:
            - 'plot_optimized': Boolean indicating optimization state
            - 'value': Original integer value
            - 'description': Human-readable description

    Raises:
        ValueError: If value cannot be parsed

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'1)')
        >>> result = parse_exao_set_optimized_for_plotting(stream)
        >>> result['plot_optimized']
        True
        >>> result['value']
        1

    Notes:
        - Corresponds to WT_Plot_Optimized::materialize() in C++
        - Non-zero values are treated as True
        - Affects rendering optimizations for print/plot output
    """
    value = read_ascii_integer(stream)
    skip_to_closing_paren(stream)

    return {
        'plot_optimized': value != 0,
        'value': value,
        'description': f'Plot optimization {"enabled" if value != 0 else "disabled"}'
    }


def parse_exao_set_projection(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended ASCII opcode WD_EXAO_SET_PROJECTION (ID 283).

    This opcode sets the projection mode for rendering.

    Format: (Projection "<mode>")
    - mode: One of "normal", "stretch", or "chop"

    Args:
        stream: Binary stream positioned after "(Projection" token

    Returns:
        Dictionary containing:
            - 'projection_type': ProjectionType enum value
            - 'mode_string': Original mode string
            - 'description': Human-readable description

    Raises:
        ValueError: If mode string is invalid

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'"normal")')
        >>> result = parse_exao_set_projection(stream)
        >>> result['projection_type']
        <ProjectionType.NORMAL: 0>
        >>> result['mode_string']
        'normal'

    Notes:
        - Corresponds to WT_Projection::materialize() in C++
        - Normal: Standard projection without modification
        - Stretch: Stretch content to fit viewport
        - Chop: Clip/chop content at viewport boundaries
    """
    mode_string = read_quoted_string(stream)
    skip_to_closing_paren(stream)

    # Map string to enum
    mode_map = {
        'normal': ProjectionType.NORMAL,
        'stretch': ProjectionType.STRETCH,
        'chop': ProjectionType.CHOP
    }

    if mode_string not in mode_map:
        raise ValueError(f"Invalid projection mode: {mode_string}")

    projection_type = mode_map[mode_string]

    return {
        'projection_type': projection_type,
        'mode_string': mode_string,
        'description': f'Projection mode set to {mode_string}'
    }


def parse_exao_orientation(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended ASCII opcode WD_EXAO_ORIENTATION (ID 326).

    This opcode sets the orientation relationship between paper and image.

    Format: (Orientation "<type>")
    - type: "Always_In_Sync  ", "Always_Different", or "Decoupled       "

    Args:
        stream: Binary stream positioned after "(Orientation" token

    Returns:
        Dictionary containing:
            - 'orientation_type': OrientationType enum value
            - 'type_string': Original type string (stripped)
            - 'description': Human-readable description

    Raises:
        ValueError: If type string is invalid

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'"Always_In_Sync  ")')
        >>> result = parse_exao_orientation(stream)
        >>> result['orientation_type']
        <OrientationType.ALWAYS_IN_SYNC: 1>

    Notes:
        - Corresponds to WT_Orientation::materialize() in C++
        - Used in BlockRef structures for DWF 00.55 compatibility
        - Always_In_Sync: Paper and image orientation always match
        - Always_Different: Paper and image orientation always differ by 90°
        - Decoupled: Paper and image orientations are independent
    """
    type_string_raw = read_quoted_string(stream)
    type_string = type_string_raw.strip()  # Remove trailing spaces
    skip_to_closing_paren(stream)

    # Map string to enum (C++ strings have trailing spaces for formatting)
    type_map = {
        'Always_In_Sync': OrientationType.ALWAYS_IN_SYNC,
        'Always_Different': OrientationType.ALWAYS_DIFFERENT,
        'Decoupled': OrientationType.DECOUPLED
    }

    if type_string not in type_map:
        raise ValueError(f"Invalid orientation type: {type_string}")

    orientation_type = type_map[type_string]

    return {
        'orientation_type': orientation_type,
        'type_string': type_string,
        'description': f'Orientation set to {type_string}'
    }


def parse_exao_alignment(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended ASCII opcode WD_EXAO_ALIGNMENT (ID 328).

    This opcode sets the alignment of graphics on the paper plot.

    Format: (Alignment "<type>")
    - type: One of 11 alignment options (see AlignmentType enum)

    Args:
        stream: Binary stream positioned after "(Alignment" token

    Returns:
        Dictionary containing:
            - 'alignment_type': AlignmentType enum value
            - 'type_string': Original type string (stripped)
            - 'description': Human-readable description

    Raises:
        ValueError: If type string is invalid

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'"Align_Center      ")')
        >>> result = parse_exao_alignment(stream)
        >>> result['alignment_type']
        <AlignmentType.ALIGN_CENTER: 1>
        >>> result['type_string']
        'Align_Center'

    Notes:
        - Corresponds to WT_Alignment::materialize() in C++
        - Used in BlockRef structures for DWF 00.55 compatibility
        - Controls how graphics are positioned on paper during plotting
        - Align_None means no specific alignment constraint
    """
    type_string_raw = read_quoted_string(stream)
    type_string = type_string_raw.strip()  # Remove trailing spaces
    skip_to_closing_paren(stream)

    # Map string to enum (C++ strings have trailing spaces for formatting)
    type_map = {
        'Align_Center': AlignmentType.ALIGN_CENTER,
        'Align_Title_Block': AlignmentType.ALIGN_TITLE_BLOCK,
        'Align_Top': AlignmentType.ALIGN_TOP,
        'Align_Bottom': AlignmentType.ALIGN_BOTTOM,
        'Align_Left': AlignmentType.ALIGN_LEFT,
        'Align_Right': AlignmentType.ALIGN_RIGHT,
        'Align_Top_Left': AlignmentType.ALIGN_TOP_LEFT,
        'Align_Top_Right': AlignmentType.ALIGN_TOP_RIGHT,
        'Align_Bottom_Left': AlignmentType.ALIGN_BOTTOM_LEFT,
        'Align_Bottom_Right': AlignmentType.ALIGN_BOTTOM_RIGHT,
        'Align_None': AlignmentType.ALIGN_NONE
    }

    if type_string not in type_map:
        raise ValueError(f"Invalid alignment type: {type_string}")

    alignment_type = type_map[type_string]

    return {
        'alignment_type': alignment_type,
        'type_string': type_string,
        'description': f'Alignment set to {type_string}'
    }


def parse_exao_delineate(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended ASCII opcode WD_EXAO_DELINEATE (ID 379).

    This opcode sets the delineation flag, which affects how filled areas are rendered.
    When delineate is true, filled areas are drawn with outlines only (no fill).

    Format: (Delineate)
    - No arguments
    - Sets delineate flag to true

    Args:
        stream: Binary stream positioned after "(Delineate" token

    Returns:
        Dictionary containing:
            - 'delineate': Boolean, always True
            - 'description': Human-readable description

    Example:
        >>> import io
        >>> stream = io.BytesIO(b')')  # Just closing paren
        >>> result = parse_exao_delineate(stream)
        >>> result['delineate']
        True

    Notes:
        - Corresponds to WT_Delineate::materialize() in C++
        - Only supported in DWF version 6.01 and later
        - When delineate is true, fill mode is automatically disabled
        - Used to show outlines of filled areas without the fill itself
        - Opcode is only written when value is true (no "delineate off" opcode)
    """
    skip_to_closing_paren(stream)

    return {
        'delineate': True,
        'description': 'Delineation enabled (fill disabled, outlines only)'
    }


# ============================================================================
# EXTENDED ASCII OPCODE DISPATCHER
# ============================================================================

# Opcode name to handler mapping
EXTENDED_ASCII_HANDLERS = {
    'Transparent': parse_exao_set_transparent,
    'PlotOptimized': parse_exao_set_optimized_for_plotting,
    'Projection': parse_exao_set_projection,
    'Orientation': parse_exao_orientation,
    'Alignment': parse_exao_alignment,
    'Delineate': parse_exao_delineate
}


def dispatch_extended_ascii_opcode(opcode_name: str, stream: BinaryIO) -> Dict:
    """
    Dispatch an Extended ASCII opcode to its appropriate handler.

    Args:
        opcode_name: The opcode name (e.g., "PlotOptimized")
        stream: Binary stream positioned after the opcode name

    Returns:
        Result dictionary from the handler

    Raises:
        ValueError: If opcode name is not recognized
    """
    if opcode_name not in EXTENDED_ASCII_HANDLERS:
        raise ValueError(f"Unknown Extended ASCII opcode: {opcode_name}")

    handler = EXTENDED_ASCII_HANDLERS[opcode_name]
    return handler(stream)


# ============================================================================
# TEST SUITE
# ============================================================================

def test_exao_set_transparent():
    """Test suite for WD_EXAO_SET_TRANSPARENT opcode."""
    import io

    print("=" * 70)
    print("TESTING WD_EXAO_SET_TRANSPARENT (ID 311)")
    print("=" * 70)

    # Test 1: Basic transparent mode
    print("\nTest 1: Basic transparent mode")
    stream = io.BytesIO(b')')
    result = parse_exao_set_transparent(stream)

    assert result['transparent'] == True
    assert result['merge_mode'] == 'transparent'
    print(f"  PASS: {result}")

    # Test 2: Verify closing paren consumed
    print("\nTest 2: Verify closing paren consumed")
    stream = io.BytesIO(b')extra')
    result = parse_exao_set_transparent(stream)
    remaining = stream.read()
    assert remaining == b'extra'
    print(f"  PASS: Stream correctly positioned after closing paren")

    # Test 3: With whitespace before closing paren
    print("\nTest 3: With whitespace before closing paren")
    stream = io.BytesIO(b'  \t  )')
    result = parse_exao_set_transparent(stream)
    assert result['transparent'] == True
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("WD_EXAO_SET_TRANSPARENT: ALL TESTS PASSED")
    print("=" * 70)


def test_exao_set_optimized_for_plotting():
    """Test suite for WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING (ID 312)")
    print("=" * 70)

    # Test 1: Plot optimization enabled (value = 1)
    print("\nTest 1: Plot optimization enabled (value=1)")
    stream = io.BytesIO(b'1)')
    result = parse_exao_set_optimized_for_plotting(stream)

    assert result['plot_optimized'] == True
    assert result['value'] == 1
    print(f"  PASS: {result}")

    # Test 2: Plot optimization disabled (value = 0)
    print("\nTest 2: Plot optimization disabled (value=0)")
    stream = io.BytesIO(b'0)')
    result = parse_exao_set_optimized_for_plotting(stream)

    assert result['plot_optimized'] == False
    assert result['value'] == 0
    print(f"  PASS: {result}")

    # Test 3: Non-zero value (should be treated as True)
    print("\nTest 3: Non-zero value (value=5)")
    stream = io.BytesIO(b'5)')
    result = parse_exao_set_optimized_for_plotting(stream)

    assert result['plot_optimized'] == True
    assert result['value'] == 5
    print(f"  PASS: {result}")

    # Test 4: With whitespace
    print("\nTest 4: With whitespace")
    stream = io.BytesIO(b'  100  )')
    result = parse_exao_set_optimized_for_plotting(stream)

    assert result['value'] == 100
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING: ALL TESTS PASSED")
    print("=" * 70)


def test_exao_set_projection():
    """Test suite for WD_EXAO_SET_PROJECTION opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING WD_EXAO_SET_PROJECTION (ID 283)")
    print("=" * 70)

    # Test 1: Normal projection
    print("\nTest 1: Normal projection")
    stream = io.BytesIO(b'"normal")')
    result = parse_exao_set_projection(stream)

    assert result['projection_type'] == ProjectionType.NORMAL
    assert result['mode_string'] == 'normal'
    print(f"  PASS: {result}")

    # Test 2: Stretch projection
    print("\nTest 2: Stretch projection")
    stream = io.BytesIO(b'"stretch")')
    result = parse_exao_set_projection(stream)

    assert result['projection_type'] == ProjectionType.STRETCH
    assert result['mode_string'] == 'stretch'
    print(f"  PASS: {result}")

    # Test 3: Chop projection
    print("\nTest 3: Chop projection")
    stream = io.BytesIO(b'"chop")')
    result = parse_exao_set_projection(stream)

    assert result['projection_type'] == ProjectionType.CHOP
    assert result['mode_string'] == 'chop'
    print(f"  PASS: {result}")

    # Test 4: With whitespace
    print("\nTest 4: With whitespace")
    stream = io.BytesIO(b'  "normal"  )')
    result = parse_exao_set_projection(stream)

    assert result['projection_type'] == ProjectionType.NORMAL
    print(f"  PASS: {result}")

    # Test 5: Invalid projection mode
    print("\nTest 5: Invalid projection mode")
    stream = io.BytesIO(b'"invalid")')
    try:
        result = parse_exao_set_projection(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("WD_EXAO_SET_PROJECTION: ALL TESTS PASSED")
    print("=" * 70)


def test_exao_orientation():
    """Test suite for WD_EXAO_ORIENTATION opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING WD_EXAO_ORIENTATION (ID 326)")
    print("=" * 70)

    # Test 1: Always In Sync
    print("\nTest 1: Always_In_Sync orientation")
    stream = io.BytesIO(b'"Always_In_Sync  ")')
    result = parse_exao_orientation(stream)

    assert result['orientation_type'] == OrientationType.ALWAYS_IN_SYNC
    assert result['type_string'] == 'Always_In_Sync'
    print(f"  PASS: {result}")

    # Test 2: Always Different
    print("\nTest 2: Always_Different orientation")
    stream = io.BytesIO(b'"Always_Different")')
    result = parse_exao_orientation(stream)

    assert result['orientation_type'] == OrientationType.ALWAYS_DIFFERENT
    assert result['type_string'] == 'Always_Different'
    print(f"  PASS: {result}")

    # Test 3: Decoupled
    print("\nTest 3: Decoupled orientation")
    stream = io.BytesIO(b'"Decoupled       ")')
    result = parse_exao_orientation(stream)

    assert result['orientation_type'] == OrientationType.DECOUPLED
    assert result['type_string'] == 'Decoupled'
    print(f"  PASS: {result}")

    # Test 4: Invalid orientation
    print("\nTest 4: Invalid orientation type")
    stream = io.BytesIO(b'"Invalid")')
    try:
        result = parse_exao_orientation(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("WD_EXAO_ORIENTATION: ALL TESTS PASSED")
    print("=" * 70)


def test_exao_alignment():
    """Test suite for WD_EXAO_ALIGNMENT opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING WD_EXAO_ALIGNMENT (ID 328)")
    print("=" * 70)

    # Test 1: Center alignment
    print("\nTest 1: Align_Center")
    stream = io.BytesIO(b'"Align_Center      ")')
    result = parse_exao_alignment(stream)

    assert result['alignment_type'] == AlignmentType.ALIGN_CENTER
    assert result['type_string'] == 'Align_Center'
    print(f"  PASS: {result}")

    # Test 2: Title block alignment
    print("\nTest 2: Align_Title_Block")
    stream = io.BytesIO(b'"Align_Title_Block ")')
    result = parse_exao_alignment(stream)

    assert result['alignment_type'] == AlignmentType.ALIGN_TITLE_BLOCK
    assert result['type_string'] == 'Align_Title_Block'
    print(f"  PASS: {result}")

    # Test 3: Top-left alignment
    print("\nTest 3: Align_Top_Left")
    stream = io.BytesIO(b'"Align_Top_Left    ")')
    result = parse_exao_alignment(stream)

    assert result['alignment_type'] == AlignmentType.ALIGN_TOP_LEFT
    assert result['type_string'] == 'Align_Top_Left'
    print(f"  PASS: {result}")

    # Test 4: Bottom-right alignment
    print("\nTest 4: Align_Bottom_Right")
    stream = io.BytesIO(b'"Align_Bottom_Right")')
    result = parse_exao_alignment(stream)

    assert result['alignment_type'] == AlignmentType.ALIGN_BOTTOM_RIGHT
    assert result['type_string'] == 'Align_Bottom_Right'
    print(f"  PASS: {result}")

    # Test 5: No alignment
    print("\nTest 5: Align_None")
    stream = io.BytesIO(b'"Align_None        ")')
    result = parse_exao_alignment(stream)

    assert result['alignment_type'] == AlignmentType.ALIGN_NONE
    assert result['type_string'] == 'Align_None'
    print(f"  PASS: {result}")

    # Test 6: Invalid alignment
    print("\nTest 6: Invalid alignment type")
    stream = io.BytesIO(b'"Align_Invalid")')
    try:
        result = parse_exao_alignment(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("WD_EXAO_ALIGNMENT: ALL TESTS PASSED")
    print("=" * 70)


def test_exao_delineate():
    """Test suite for WD_EXAO_DELINEATE opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING WD_EXAO_DELINEATE (ID 379)")
    print("=" * 70)

    # Test 1: Basic delineate
    print("\nTest 1: Basic delineate mode")
    stream = io.BytesIO(b')')
    result = parse_exao_delineate(stream)

    assert result['delineate'] == True
    print(f"  PASS: {result}")

    # Test 2: With whitespace
    print("\nTest 2: With whitespace before closing paren")
    stream = io.BytesIO(b'  \t\n  )')
    result = parse_exao_delineate(stream)

    assert result['delineate'] == True
    print(f"  PASS: {result}")

    # Test 3: Verify stream position
    print("\nTest 3: Verify stream position after parsing")
    stream = io.BytesIO(b')remaining')
    result = parse_exao_delineate(stream)
    remaining = stream.read()
    assert remaining == b'remaining'
    print(f"  PASS: Stream correctly positioned")

    print("\n" + "=" * 70)
    print("WD_EXAO_DELINEATE: ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Extended ASCII transparency/optimization opcodes."""
    print("\n" + "=" * 70)
    print("AGENT 21: EXTENDED ASCII TRANSPARENCY/OPTIMIZATION OPCODES")
    print("Running Complete Test Suite")
    print("=" * 70)

    test_exao_set_transparent()
    test_exao_set_optimized_for_plotting()
    test_exao_set_projection()
    test_exao_orientation()
    test_exao_alignment()
    test_exao_delineate()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - WD_EXAO_SET_TRANSPARENT (311): 3 tests passed")
    print("  - WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING (312): 4 tests passed")
    print("  - WD_EXAO_SET_PROJECTION (283): 5 tests passed")
    print("  - WD_EXAO_ORIENTATION (326): 4 tests passed")
    print("  - WD_EXAO_ALIGNMENT (328): 6 tests passed")
    print("  - WD_EXAO_DELINEATE (379): 3 tests passed")
    print("  Total: 25 tests passed")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
