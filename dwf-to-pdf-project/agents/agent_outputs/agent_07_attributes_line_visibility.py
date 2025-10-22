"""
DWF Opcode Parsers for Line Style and Visibility Attributes (Agent 7)

This module implements parsers for five DWF attribute opcodes:
- 0x76 'v': SET_VISIBILITY_OFF (disable visibility)
- 0x17 '\x17': SET_LINE_WEIGHT (binary line weight)
- 0xCC '\xCC': SET_LINE_PATTERN (binary line pattern)
- 0x53 'S': SET_MACRO_SCALE (ASCII macro scale)
- 0x73 's': SET_MACRO_SCALE (binary macro scale)

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/visible.cpp
- develop/global/src/dwf/whiptk/lweight.cpp
- develop/global/src/dwf/whiptk/linepat.cpp
- develop/global/src/dwf/whiptk/macro_scale.cpp
"""

import struct
from typing import Dict, BinaryIO, Optional
from enum import IntEnum


class LinePatternID(IntEnum):
    """
    Line pattern identifiers from DWF specification.
    Corresponds to WT_Line_Pattern::WT_Pattern_ID in C++ code.
    """
    INVALID = 0
    SOLID = 1
    DASHED = 2
    DOTTED = 3
    DASH_DOT = 4
    SHORT_DASH = 5
    MEDIUM_DASH = 6
    LONG_DASH = 7
    SHORT_DASH_X2 = 8
    MEDIUM_DASH_X2 = 9
    LONG_DASH_X2 = 10
    MEDIUM_LONG_DASH = 11
    MEDIUM_DASH_SHORT_DASH_SHORT_DASH = 12
    LONG_DASH_SHORT_DASH = 13
    LONG_DASH_DOT_DOT = 14
    LONG_DASH_DOT = 15
    MEDIUM_DASH_DOT_SHORT_DASH_DOT = 16
    SPARSE_DOT = 17
    ISO_DASH = 18
    ISO_DASH_SPACE = 19
    ISO_LONG_DASH_DOT = 20
    ISO_LONG_DASH_DOUBLE_DOT = 21
    ISO_LONG_DASH_TRIPLE_DOT = 22
    ISO_DOT = 23
    ISO_LONG_DASH_SHORT_DASH = 24
    ISO_LONG_DASH_DOUBLE_SHORT_DASH = 25
    ISO_DASH_DOT = 26
    ISO_DOUBLE_DASH_DOT = 27
    ISO_DASH_DOUBLE_DOT = 28
    ISO_DOUBLE_DASH_DOUBLE_DOT = 29
    ISO_DASH_TRIPLE_DOT = 30
    ISO_DOUBLE_DASH_TRIPLE_DOT = 31
    DECORATED_TRACKS = 32
    DECORATED_WIDE_TRACKS = 33
    DECORATED_CIRCLE_FENCE = 34
    DECORATED_SQUARE_FENCE = 35


def parse_opcode_0x76_visibility_off(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x76 'v' (SET_VISIBILITY_OFF).

    This opcode disables visibility for subsequent drawing operations.
    The opcode byte itself (0x76) is the complete command with no additional data.

    Format:
    - No additional data bytes (opcode is self-contained)

    Args:
        stream: Binary stream positioned after the 0x76 opcode byte

    Returns:
        Dictionary containing:
            - 'visible': Boolean, always False for this opcode
            - 'description': Human-readable description

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')  # No data after opcode
        >>> result = parse_opcode_0x76_visibility_off(stream)
        >>> result['visible']
        False
        >>> result['description']
        'Visibility disabled'

    Notes:
        - Corresponds to WT_Visibility::materialize() with opcode 'v' in C++
        - The complementary opcode 0x56 'V' sets visibility ON
        - This affects all subsequent drawable elements until changed
    """
    return {
        'visible': False,
        'description': 'Visibility disabled'
    }


def parse_opcode_0x17_line_weight(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x17 (SET_LINE_WEIGHT - binary format).

    Sets the line weight (width/thickness) for subsequent drawing operations.
    The weight is stored as a signed 32-bit integer.

    Format:
    - 4 bytes (int32, little-endian): line weight value

    Args:
        stream: Binary stream positioned after the 0x17 opcode byte

    Returns:
        Dictionary containing:
            - 'weight': Line weight as int32
            - 'description': Human-readable description

    Raises:
        ValueError: If insufficient data is available

    Example:
        >>> import io
        >>> data = struct.pack('<l', 100)  # Weight = 100
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x17_line_weight(stream)
        >>> result['weight']
        100

    Notes:
        - Corresponds to WT_Line_Weight::materialize() with opcode 0x17 in C++
        - Weight values are typically positive but can be negative in edge cases
        - Units depend on the drawing coordinate system
        - The ASCII version uses "(LineWeight N)" format
    """
    # Read 4 bytes for int32 weight
    weight_bytes = stream.read(4)
    if len(weight_bytes) != 4:
        raise ValueError("Insufficient data: could not read line weight (expected 4 bytes)")

    weight = struct.unpack('<l', weight_bytes)[0]

    return {
        'weight': weight,
        'description': f'Line weight set to {weight}'
    }


def parse_opcode_0xCC_line_pattern(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0xCC (SET_LINE_PATTERN - binary format).

    Sets the line pattern (dash style) for subsequent line drawing operations.
    Pattern ID is encoded using a variable-length count encoding scheme.

    Format:
    - Variable bytes: count-encoded pattern ID
      - If first byte < 255: pattern_id = first byte
      - If first byte == 255: pattern_id is encoded in next 2-4 bytes

    Args:
        stream: Binary stream positioned after the 0xCC opcode byte

    Returns:
        Dictionary containing:
            - 'pattern_id': Line pattern ID (see LinePatternID enum)
            - 'pattern_name': Human-readable pattern name
            - 'description': Human-readable description

    Raises:
        ValueError: If insufficient data or invalid pattern ID

    Example:
        >>> import io
        >>> # Pattern ID 2 (DASHED) with simple encoding
        >>> data = struct.pack('<B', 2)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0xCC_line_pattern(stream)
        >>> result['pattern_id']
        2
        >>> result['pattern_name']
        'DASHED'

    Notes:
        - Corresponds to WT_Line_Pattern::materialize_single_byte() in C++
        - Pattern IDs correspond to predefined dash patterns
        - Pattern ID 0 is invalid, 1 is SOLID (no dashing)
        - Uses file.read_count() method for variable-length encoding
        - The ASCII version uses "(LinePattern name)" format
    """
    # Read count-encoded pattern ID
    # This uses a variable-length encoding scheme
    pattern_id = _read_count(stream)

    # Validate pattern ID
    if pattern_id < 0:
        raise ValueError(f"Invalid pattern ID: {pattern_id} (must be non-negative)")

    # Get pattern name if available
    try:
        pattern_name = LinePatternID(pattern_id).name
    except ValueError:
        pattern_name = f"UNKNOWN_PATTERN_{pattern_id}"

    return {
        'pattern_id': pattern_id,
        'pattern_name': pattern_name,
        'description': f'Line pattern set to {pattern_name} (ID={pattern_id})'
    }


def parse_opcode_0x53_macro_scale_ascii(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x53 'S' (SET_MACRO_SCALE - ASCII format).

    Sets the scaling factor for macro symbols (markers) in ASCII format.
    The scale value is encoded as an ASCII decimal number followed by whitespace.

    Format:
    - ASCII text: decimal number (e.g., "1.5", "2", "0.75")
    - Terminated by whitespace or end of line

    Args:
        stream: Binary stream positioned after the 0x53 'S' opcode byte

    Returns:
        Dictionary containing:
            - 'scale': Macro scale as int32
            - 'format': 'ascii'
            - 'description': Human-readable description

    Raises:
        ValueError: If ASCII number cannot be parsed

    Example:
        >>> import io
        >>> data = b'250 '  # Scale = 250
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x53_macro_scale_ascii(stream)
        >>> result['scale']
        250

    Notes:
        - Corresponds to WT_Macro_Scale::materialize() with opcode 'S' in C++
        - ASCII format allows for human-readable DWF files
        - Scale affects size of macro symbols (markers, symbols)
        - Typically represents a percentage (100 = normal size)
        - Whitespace (space, tab, newline) acts as delimiter
    """
    scale = _read_ascii_int32(stream)

    return {
        'scale': scale,
        'format': 'ascii',
        'description': f'Macro scale set to {scale} (ASCII format)'
    }


def parse_opcode_0x73_macro_scale_binary(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x73 's' (SET_MACRO_SCALE - binary format).

    Sets the scaling factor for macro symbols (markers) in binary format.
    The scale value is stored as a signed 32-bit integer.

    Format:
    - 4 bytes (int32, little-endian): scale value

    Args:
        stream: Binary stream positioned after the 0x73 's' opcode byte

    Returns:
        Dictionary containing:
            - 'scale': Macro scale as int32
            - 'format': 'binary'
            - 'description': Human-readable description

    Raises:
        ValueError: If insufficient data is available

    Example:
        >>> import io
        >>> data = struct.pack('<l', 150)  # Scale = 150
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x73_macro_scale_binary(stream)
        >>> result['scale']
        150

    Notes:
        - Corresponds to WT_Macro_Scale::materialize() with opcode 's' in C++
        - Binary format is more compact than ASCII
        - Scale affects size of macro symbols (markers, symbols)
        - Typically represents a percentage (100 = normal size)
        - Negative values are technically possible but unusual
    """
    # Read 4 bytes for int32 scale
    scale_bytes = stream.read(4)
    if len(scale_bytes) != 4:
        raise ValueError("Insufficient data: could not read macro scale (expected 4 bytes)")

    scale = struct.unpack('<l', scale_bytes)[0]

    return {
        'scale': scale,
        'format': 'binary',
        'description': f'Macro scale set to {scale} (binary format)'
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _read_count(stream: BinaryIO) -> int:
    """
    Read a count-encoded integer from the stream.

    This implements the DWF variable-length count encoding:
    - If first byte < 255: value = first byte
    - If first byte == 255: read next bytes for larger value

    Args:
        stream: Binary stream to read from

    Returns:
        The decoded integer value

    Raises:
        ValueError: If insufficient data
    """
    first_byte = stream.read(1)
    if len(first_byte) != 1:
        raise ValueError("Insufficient data: could not read count")

    count = struct.unpack('<B', first_byte)[0]

    # Simple implementation: if count < 255, use it directly
    # If count == 255, read the next 4 bytes as int32
    if count == 255:
        extended_bytes = stream.read(4)
        if len(extended_bytes) != 4:
            raise ValueError("Insufficient data: could not read extended count")
        count = struct.unpack('<l', extended_bytes)[0]

    return count


def _read_ascii_int32(stream: BinaryIO) -> int:
    """
    Read an ASCII-encoded integer from the stream.

    Reads characters until whitespace or end of stream is encountered,
    then parses as a decimal integer.

    Args:
        stream: Binary stream to read from

    Returns:
        The parsed integer value

    Raises:
        ValueError: If no valid integer found
    """
    chars = []
    while True:
        byte = stream.read(1)
        if not byte:
            break
        char = byte.decode('ascii', errors='ignore')
        if char.isspace():
            break
        if char in '-0123456789':
            chars.append(char)
        elif chars:
            # Non-digit after digits means end of number
            break

    if not chars:
        raise ValueError("No ASCII integer found in stream")

    return int(''.join(chars))


# ============================================================================
# TEST SUITE
# ============================================================================

def test_opcode_0x76_visibility_off():
    """Test suite for opcode 0x76 (Visibility Off)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x76 (VISIBILITY OFF)")
    print("=" * 70)

    # Test 1: Basic visibility off
    print("\nTest 1: Basic visibility off")
    stream = io.BytesIO(b'')  # No data after opcode
    result = parse_opcode_0x76_visibility_off(stream)

    assert result['visible'] == False, f"Expected visible=False, got {result['visible']}"
    assert 'description' in result
    print(f"  PASS: {result}")

    # Test 2: Verify no data consumed
    print("\nTest 2: Verify no data consumed from stream")
    stream = io.BytesIO(b'\xFF\xFF\xFF')  # Extra data that shouldn't be read
    result = parse_opcode_0x76_visibility_off(stream)
    remaining = stream.read()
    assert len(remaining) == 3, f"Expected 3 bytes remaining, got {len(remaining)}"
    print(f"  PASS: Opcode correctly consumed 0 bytes")

    print("\n" + "=" * 70)
    print("OPCODE 0x76 (VISIBILITY OFF): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x17_line_weight():
    """Test suite for opcode 0x17 (Line Weight)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x17 (LINE WEIGHT)")
    print("=" * 70)

    # Test 1: Positive weight
    print("\nTest 1: Positive line weight (100)")
    data = struct.pack('<l', 100)
    stream = io.BytesIO(data)
    result = parse_opcode_0x17_line_weight(stream)

    assert result['weight'] == 100, f"Expected weight=100, got {result['weight']}"
    print(f"  PASS: {result}")

    # Test 2: Zero weight
    print("\nTest 2: Zero line weight")
    data = struct.pack('<l', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x17_line_weight(stream)

    assert result['weight'] == 0
    print(f"  PASS: {result}")

    # Test 3: Negative weight (edge case)
    print("\nTest 3: Negative line weight")
    data = struct.pack('<l', -50)
    stream = io.BytesIO(data)
    result = parse_opcode_0x17_line_weight(stream)

    assert result['weight'] == -50
    print(f"  PASS: {result}")

    # Test 4: Large weight value
    print("\nTest 4: Large line weight (1000000)")
    data = struct.pack('<l', 1000000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x17_line_weight(stream)

    assert result['weight'] == 1000000
    print(f"  PASS: {result}")

    # Test 5: Error handling - insufficient data
    print("\nTest 5: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02')  # Only 2 bytes
    try:
        result = parse_opcode_0x17_line_weight(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x17 (LINE WEIGHT): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0xCC_line_pattern():
    """Test suite for opcode 0xCC (Line Pattern)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0xCC (LINE PATTERN)")
    print("=" * 70)

    # Test 1: Solid line (pattern ID 1)
    print("\nTest 1: Solid line pattern (ID=1)")
    data = struct.pack('<B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0xCC_line_pattern(stream)

    assert result['pattern_id'] == 1
    assert result['pattern_name'] == 'SOLID'
    print(f"  PASS: {result}")

    # Test 2: Dashed line (pattern ID 2)
    print("\nTest 2: Dashed line pattern (ID=2)")
    data = struct.pack('<B', 2)
    stream = io.BytesIO(data)
    result = parse_opcode_0xCC_line_pattern(stream)

    assert result['pattern_id'] == 2
    assert result['pattern_name'] == 'DASHED'
    print(f"  PASS: {result}")

    # Test 3: Dotted line (pattern ID 3)
    print("\nTest 3: Dotted line pattern (ID=3)")
    data = struct.pack('<B', 3)
    stream = io.BytesIO(data)
    result = parse_opcode_0xCC_line_pattern(stream)

    assert result['pattern_id'] == 3
    assert result['pattern_name'] == 'DOTTED'
    print(f"  PASS: {result}")

    # Test 4: ISO Dash (pattern ID 18)
    print("\nTest 4: ISO Dash pattern (ID=18)")
    data = struct.pack('<B', 18)
    stream = io.BytesIO(data)
    result = parse_opcode_0xCC_line_pattern(stream)

    assert result['pattern_id'] == 18
    assert result['pattern_name'] == 'ISO_DASH'
    print(f"  PASS: {result}")

    # Test 5: Extended count encoding
    print("\nTest 5: Extended count encoding (ID=300)")
    data = struct.pack('<B', 255) + struct.pack('<l', 300)
    stream = io.BytesIO(data)
    result = parse_opcode_0xCC_line_pattern(stream)

    assert result['pattern_id'] == 300
    print(f"  PASS: {result}")

    # Test 6: Unknown pattern ID
    print("\nTest 6: Unknown pattern ID (ID=999)")
    data = struct.pack('<B', 254)  # ID 254 is not defined
    stream = io.BytesIO(data)
    result = parse_opcode_0xCC_line_pattern(stream)

    assert result['pattern_id'] == 254
    assert 'UNKNOWN' in result['pattern_name']
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("OPCODE 0xCC (LINE PATTERN): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x53_macro_scale_ascii():
    """Test suite for opcode 0x53 (Macro Scale ASCII)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x53 (MACRO SCALE ASCII)")
    print("=" * 70)

    # Test 1: Basic scale value
    print("\nTest 1: Basic scale value (250)")
    data = b'250 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x53_macro_scale_ascii(stream)

    assert result['scale'] == 250
    assert result['format'] == 'ascii'
    print(f"  PASS: {result}")

    # Test 2: Scale 100 (normal size)
    print("\nTest 2: Normal scale (100)")
    data = b'100 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x53_macro_scale_ascii(stream)

    assert result['scale'] == 100
    print(f"  PASS: {result}")

    # Test 3: Small scale value
    print("\nTest 3: Small scale (10)")
    data = b'10\n'  # Newline as delimiter
    stream = io.BytesIO(data)
    result = parse_opcode_0x53_macro_scale_ascii(stream)

    assert result['scale'] == 10
    print(f"  PASS: {result}")

    # Test 4: Large scale value
    print("\nTest 4: Large scale (5000)")
    data = b'5000\t'  # Tab as delimiter
    stream = io.BytesIO(data)
    result = parse_opcode_0x53_macro_scale_ascii(stream)

    assert result['scale'] == 5000
    print(f"  PASS: {result}")

    # Test 5: Negative scale (edge case)
    print("\nTest 5: Negative scale (-100)")
    data = b'-100 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x53_macro_scale_ascii(stream)

    assert result['scale'] == -100
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("OPCODE 0x53 (MACRO SCALE ASCII): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x73_macro_scale_binary():
    """Test suite for opcode 0x73 (Macro Scale Binary)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x73 (MACRO SCALE BINARY)")
    print("=" * 70)

    # Test 1: Basic scale value
    print("\nTest 1: Basic scale value (150)")
    data = struct.pack('<l', 150)
    stream = io.BytesIO(data)
    result = parse_opcode_0x73_macro_scale_binary(stream)

    assert result['scale'] == 150
    assert result['format'] == 'binary'
    print(f"  PASS: {result}")

    # Test 2: Scale 100 (normal size)
    print("\nTest 2: Normal scale (100)")
    data = struct.pack('<l', 100)
    stream = io.BytesIO(data)
    result = parse_opcode_0x73_macro_scale_binary(stream)

    assert result['scale'] == 100
    print(f"  PASS: {result}")

    # Test 3: Zero scale
    print("\nTest 3: Zero scale")
    data = struct.pack('<l', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x73_macro_scale_binary(stream)

    assert result['scale'] == 0
    print(f"  PASS: {result}")

    # Test 4: Large scale value
    print("\nTest 4: Large scale (1000000)")
    data = struct.pack('<l', 1000000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x73_macro_scale_binary(stream)

    assert result['scale'] == 1000000
    print(f"  PASS: {result}")

    # Test 5: Negative scale
    print("\nTest 5: Negative scale (-200)")
    data = struct.pack('<l', -200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x73_macro_scale_binary(stream)

    assert result['scale'] == -200
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02')  # Only 2 bytes
    try:
        result = parse_opcode_0x73_macro_scale_binary(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x73 (MACRO SCALE BINARY): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 7 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 7: LINE STYLE & VISIBILITY OPCODE TEST SUITE")
    print("=" * 70)
    print("Testing 5 opcodes:")
    print("  - 0x76 'v': SET_VISIBILITY_OFF")
    print("  - 0x17: SET_LINE_WEIGHT (binary)")
    print("  - 0xCC: SET_LINE_PATTERN (binary)")
    print("  - 0x53 'S': SET_MACRO_SCALE (ASCII)")
    print("  - 0x73 's': SET_MACRO_SCALE (binary)")
    print("=" * 70)

    test_opcode_0x76_visibility_off()
    test_opcode_0x17_line_weight()
    test_opcode_0xCC_line_pattern()
    test_opcode_0x53_macro_scale_ascii()
    test_opcode_0x73_macro_scale_binary()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x76 (Visibility Off): 2 tests passed")
    print("  - Opcode 0x17 (Line Weight): 5 tests passed")
    print("  - Opcode 0xCC (Line Pattern): 6 tests passed")
    print("  - Opcode 0x53 (Macro Scale ASCII): 5 tests passed")
    print("  - Opcode 0x73 (Macro Scale Binary): 6 tests passed")
    print("  - Total: 24 tests passed")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
