"""
DWF Text Attributes Opcodes - Agent 41

This module implements parsers for 3 DWF opcodes related to text attributes:
- 0x58 'X': SET_TEXT_ROTATION (ASCII format text rotation angle)
- 0x78 'x': SET_TEXT_SPACING (binary format text spacing)
- 0x98: SET_TEXT_SCALE (binary format text scale factor)

These opcodes provide functionality for controlling text rendering attributes
including rotation angle, character spacing, and size scaling.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/text_rotation.cpp
- develop/global/src/dwf/whiptk/text_spacing.cpp
- develop/global/src/dwf/whiptk/text_scale.cpp

Author: Agent 41 (Text Attributes Specialist)
"""

import struct
from typing import Dict, BinaryIO


# =============================================================================
# OPCODE 0x58 'X' - SET_TEXT_ROTATION
# =============================================================================

def parse_opcode_0x58_set_text_rotation(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x58 'X' (SET_TEXT_ROTATION) - Set text rotation angle.

    This opcode sets the rotation angle for subsequent text rendering
    operations. The format is X(angle) where angle is an integer in degrees
    from 0 to 359.

    Format Specification:
    - Opcode: 0x58 (1 byte, 'X' in ASCII, not included in data stream)
    - Format: X(angle)
    - Angle is enclosed in parentheses
    - Angle is an ASCII integer (0-359 degrees)
    - 0° = horizontal (no rotation)
    - 90° = vertical (counter-clockwise)
    - 180° = upside down
    - 270° = vertical (clockwise)

    C++ Reference:
    From text_rotation.cpp - WT_Text_Rotation::materialize():
        case 'X':  // ASCII format text rotation
            // Format is X(angle)
            WT_Integer32 angle;
            WD_CHECK(file.read_ascii(angle));
            m_angle_degrees = angle % 360;

    Args:
        stream: Binary stream positioned after the 0x58 'X' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_text_rotation'
            - 'angle_degrees': Integer angle in degrees (0-359)

    Raises:
        ValueError: If format is invalid or angle cannot be parsed

    Example:
        >>> import io
        >>> data = b'(45)'
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x58_set_text_rotation(stream)
        >>> result['angle_degrees']
        45

    Notes:
        - Corresponds to WT_Text_Rotation::materialize() with opcode 'X' in C++
        - Rotation is counter-clockwise from horizontal (0°)
        - Angle is normalized to 0-359 range
        - ASCII format allows human-readable DWF files
        - Applies to all subsequent text rendering operations
        - Common uses: rotated labels, vertical text, angled annotations
    """
    # Read until we find opening parenthesis
    angle_chars = []
    found_open_paren = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream while reading text rotation")

        char = byte.decode('ascii', errors='ignore')

        if char == '(':
            found_open_paren = True
            continue

        if char == ')':
            if not found_open_paren:
                raise ValueError("Found closing parenthesis before opening parenthesis")
            break

        if found_open_paren:
            if char.isdigit() or char == '-' or char == '+':
                angle_chars.append(char)

    if not found_open_paren:
        raise ValueError("Expected opening parenthesis '(' for text rotation")

    if not angle_chars:
        raise ValueError("Empty angle value in text rotation")

    angle_string = ''.join(angle_chars)

    try:
        angle = int(angle_string)
    except ValueError:
        raise ValueError(f"Invalid angle value: {angle_string}")

    # Normalize angle to 0-359 range
    angle_degrees = angle % 360

    return {
        'type': 'set_text_rotation',
        'angle_degrees': angle_degrees
    }


# =============================================================================
# OPCODE 0x78 'x' - SET_TEXT_SPACING
# =============================================================================

def parse_opcode_0x78_set_text_spacing(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x78 'x' (SET_TEXT_SPACING) - Set text character spacing.

    This opcode sets the spacing between characters for subsequent text
    rendering operations. Spacing is specified in 1/1000ths of an em unit
    as a 16-bit signed integer.

    Format Specification:
    - Opcode: 0x78 (1 byte, 'x' in ASCII, not included in data stream)
    - Spacing: int16 (2 bytes, signed, little-endian)
    - Total data: 2 bytes
    - Struct format: "<h" (little-endian signed 16-bit integer)
    - Units: 1/1000ths of em (1 em = width of 'M' character)
    - Positive values = increased spacing (looser)
    - Negative values = decreased spacing (tighter)
    - 0 = default spacing

    C++ Reference:
    From text_spacing.cpp - WT_Text_Spacing::materialize():
        case 'x':  // Binary format text spacing
            WT_Integer16 spacing;
            WD_CHECK(file.read(spacing));
            m_spacing = spacing;

    Args:
        stream: Binary stream positioned after the 0x78 'x' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_text_spacing'
            - 'spacing': Spacing value in 1/1000ths of em (-32768 to 32767)

    Raises:
        ValueError: If stream doesn't contain 2 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<h', 100)  # 0.1 em extra spacing
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x78_set_text_spacing(stream)
        >>> result['spacing']
        100

    Notes:
        - Corresponds to WT_Text_Spacing::materialize() with opcode 'x' in C++
        - Spacing is relative to default character spacing
        - 1000 = 1 em (width of 'M' character in current font)
        - Positive: add space between characters (tracking)
        - Negative: reduce space between characters (kerning)
        - Range: -32768 to 32767 (1/1000ths of em)
        - Common values: -200 to +200 for subtle adjustments
        - Applies to all subsequent text rendering operations
    """
    data = stream.read(2)

    if len(data) != 2:
        raise ValueError(f"Expected 2 bytes for opcode 0x78 (SET_TEXT_SPACING), got {len(data)} bytes")

    # Unpack signed 16-bit integer (little-endian)
    spacing = struct.unpack('<h', data)[0]

    return {
        'type': 'set_text_spacing',
        'spacing': spacing
    }


# =============================================================================
# OPCODE 0x98 - SET_TEXT_SCALE
# =============================================================================

def parse_opcode_0x98_set_text_scale(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x98 (SET_TEXT_SCALE) - Set text scale factor.

    This opcode sets the scale factor for subsequent text rendering operations.
    The scale is specified as a 32-bit IEEE 754 floating-point number.

    Format Specification:
    - Opcode: 0x98 (1 byte, not included in data stream)
    - Scale: float32 (4 bytes, IEEE 754, little-endian)
    - Total data: 4 bytes
    - Struct format: "<f" (little-endian 32-bit float)
    - Scale factor meanings:
      - 1.0 = 100% (normal size, no scaling)
      - 2.0 = 200% (double size)
      - 0.5 = 50% (half size)
      - 0.0 = invisible text

    C++ Reference:
    From text_scale.cpp - WT_Text_Scale::materialize():
        case 0x98:  // Binary format text scale
            WT_Float32 scale;
            WD_CHECK(file.read(scale));
            m_scale = scale;

    Args:
        stream: Binary stream positioned after the 0x98 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_text_scale'
            - 'scale': Scale factor as float

    Raises:
        ValueError: If stream doesn't contain 4 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<f', 1.5)  # 150% scale
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x98_set_text_scale(stream)
        >>> result['scale']
        1.5

    Notes:
        - Corresponds to WT_Text_Scale::materialize() with opcode 0x98 in C++
        - Scale factor multiplies text size
        - 1.0 = normal size (100%)
        - > 1.0 = larger text
        - < 1.0 = smaller text
        - 0.0 = invisible (degenerate case)
        - Negative values may cause undefined rendering behavior
        - IEEE 754 format provides wide range and precision
        - Applies to all subsequent text rendering operations
        - Common uses: headers, footnotes, emphasis
    """
    data = stream.read(4)

    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes for opcode 0x98 (SET_TEXT_SCALE), got {len(data)} bytes")

    # Unpack 32-bit float (little-endian)
    scale = struct.unpack('<f', data)[0]

    return {
        'type': 'set_text_scale',
        'scale': scale
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x58_set_text_rotation():
    """Test suite for opcode 0x58 (SET_TEXT_ROTATION)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x58 'X' (SET_TEXT_ROTATION)")
    print("=" * 70)

    # Test 1: Horizontal (0 degrees)
    print("\nTest 1: Horizontal rotation (0 degrees)")
    data = b'(0)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['type'] == 'set_text_rotation', f"Expected type='set_text_rotation', got {result['type']}"
    assert result['angle_degrees'] == 0, f"Expected angle_degrees=0, got {result['angle_degrees']}"
    print(f"  PASS: {result}")

    # Test 2: Vertical (90 degrees)
    print("\nTest 2: Vertical rotation (90 degrees)")
    data = b'(90)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 90
    print(f"  PASS: {result}")

    # Test 3: Upside down (180 degrees)
    print("\nTest 3: Upside down rotation (180 degrees)")
    data = b'(180)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 180
    print(f"  PASS: {result}")

    # Test 4: Vertical clockwise (270 degrees)
    print("\nTest 4: Vertical clockwise rotation (270 degrees)")
    data = b'(270)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 270
    print(f"  PASS: {result}")

    # Test 5: 45 degree angle
    print("\nTest 5: Diagonal rotation (45 degrees)")
    data = b'(45)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 45
    print(f"  PASS: {result}")

    # Test 6: Maximum angle (359 degrees)
    print("\nTest 6: Maximum angle (359 degrees)")
    data = b'(359)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 359
    print(f"  PASS: {result}")

    # Test 7: Angle normalization (360 degrees -> 0)
    print("\nTest 7: Angle normalization (360 degrees -> 0)")
    data = b'(360)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 0
    print(f"  PASS: {result}")

    # Test 8: Angle normalization (450 degrees -> 90)
    print("\nTest 8: Angle normalization (450 degrees -> 90)")
    data = b'(450)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 90
    print(f"  PASS: {result}")

    # Test 9: Negative angle normalization (-90 degrees -> 270)
    print("\nTest 9: Negative angle normalization (-90 degrees -> 270)")
    data = b'(-90)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x58_set_text_rotation(stream)

    assert result['angle_degrees'] == 270
    print(f"  PASS: {result}")

    # Test 10: Error handling - missing parenthesis
    print("\nTest 10: Error handling - missing closing parenthesis")
    stream = io.BytesIO(b'(45')
    try:
        result = parse_opcode_0x58_set_text_rotation(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x58 'X' (SET_TEXT_ROTATION): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x78_set_text_spacing():
    """Test suite for opcode 0x78 (SET_TEXT_SPACING)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x78 'x' (SET_TEXT_SPACING)")
    print("=" * 70)

    # Test 1: Default spacing (0)
    print("\nTest 1: Default spacing (0)")
    data = struct.pack('<h', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['type'] == 'set_text_spacing', f"Expected type='set_text_spacing', got {result['type']}"
    assert result['spacing'] == 0, f"Expected spacing=0, got {result['spacing']}"
    print(f"  PASS: {result}")

    # Test 2: Increased spacing (100 = 0.1 em)
    print("\nTest 2: Increased spacing (100 = 0.1 em)")
    data = struct.pack('<h', 100)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['spacing'] == 100
    print(f"  PASS: {result}")

    # Test 3: Decreased spacing (-100 = -0.1 em)
    print("\nTest 3: Decreased spacing (-100 = -0.1 em)")
    data = struct.pack('<h', -100)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['spacing'] == -100
    print(f"  PASS: {result}")

    # Test 4: Large positive spacing (1000 = 1 em)
    print("\nTest 4: Large positive spacing (1000 = 1 em)")
    data = struct.pack('<h', 1000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['spacing'] == 1000
    print(f"  PASS: {result}")

    # Test 5: Large negative spacing (-1000 = -1 em)
    print("\nTest 5: Large negative spacing (-1000 = -1 em)")
    data = struct.pack('<h', -1000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['spacing'] == -1000
    print(f"  PASS: {result}")

    # Test 6: Maximum positive int16 (32767)
    print("\nTest 6: Maximum positive spacing (32767)")
    data = struct.pack('<h', 32767)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['spacing'] == 32767
    print(f"  PASS: {result}")

    # Test 7: Minimum negative int16 (-32768)
    print("\nTest 7: Minimum negative spacing (-32768)")
    data = struct.pack('<h', -32768)
    stream = io.BytesIO(data)
    result = parse_opcode_0x78_set_text_spacing(stream)

    assert result['spacing'] == -32768
    print(f"  PASS: {result}")

    # Test 8: Error handling - insufficient data
    print("\nTest 8: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01')  # Only 1 byte instead of 2
    try:
        result = parse_opcode_0x78_set_text_spacing(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x78 'x' (SET_TEXT_SPACING): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x98_set_text_scale():
    """Test suite for opcode 0x98 (SET_TEXT_SCALE)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x98 (SET_TEXT_SCALE)")
    print("=" * 70)

    # Test 1: Normal scale (1.0 = 100%)
    print("\nTest 1: Normal scale (1.0 = 100%)")
    data = struct.pack('<f', 1.0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert result['type'] == 'set_text_scale', f"Expected type='set_text_scale', got {result['type']}"
    assert abs(result['scale'] - 1.0) < 0.0001, f"Expected scale=1.0, got {result['scale']}"
    print(f"  PASS: {result}")

    # Test 2: Double scale (2.0 = 200%)
    print("\nTest 2: Double scale (2.0 = 200%)")
    data = struct.pack('<f', 2.0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 2.0) < 0.0001
    print(f"  PASS: {result}")

    # Test 3: Half scale (0.5 = 50%)
    print("\nTest 3: Half scale (0.5 = 50%)")
    data = struct.pack('<f', 0.5)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 0.5) < 0.0001
    print(f"  PASS: {result}")

    # Test 4: Large scale (10.0 = 1000%)
    print("\nTest 4: Large scale (10.0 = 1000%)")
    data = struct.pack('<f', 10.0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 10.0) < 0.0001
    print(f"  PASS: {result}")

    # Test 5: Small scale (0.1 = 10%)
    print("\nTest 5: Small scale (0.1 = 10%)")
    data = struct.pack('<f', 0.1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 0.1) < 0.0001
    print(f"  PASS: {result}")

    # Test 6: Zero scale (0.0 = invisible)
    print("\nTest 6: Zero scale (0.0 = invisible)")
    data = struct.pack('<f', 0.0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 0.0) < 0.0001
    print(f"  PASS: {result}")

    # Test 7: Fractional scale (1.5 = 150%)
    print("\nTest 7: Fractional scale (1.5 = 150%)")
    data = struct.pack('<f', 1.5)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 1.5) < 0.0001
    print(f"  PASS: {result}")

    # Test 8: Very large scale (100.0)
    print("\nTest 8: Very large scale (100.0)")
    data = struct.pack('<f', 100.0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 100.0) < 0.01
    print(f"  PASS: {result}")

    # Test 9: Very small scale (0.01)
    print("\nTest 9: Very small scale (0.01)")
    data = struct.pack('<f', 0.01)
    stream = io.BytesIO(data)
    result = parse_opcode_0x98_set_text_scale(stream)

    assert abs(result['scale'] - 0.01) < 0.00001
    print(f"  PASS: {result}")

    # Test 10: Error handling - insufficient data
    print("\nTest 10: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02')  # Only 2 bytes instead of 4
    try:
        result = parse_opcode_0x98_set_text_scale(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x98 (SET_TEXT_SCALE): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 41 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 41: TEXT ATTRIBUTES TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x58 'X': SET_TEXT_ROTATION (ASCII)")
    print("  - 0x78 'x': SET_TEXT_SPACING (binary)")
    print("  - 0x98: SET_TEXT_SCALE (binary)")
    print("=" * 70)

    test_opcode_0x58_set_text_rotation()
    test_opcode_0x78_set_text_spacing()
    test_opcode_0x98_set_text_scale()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x58 'X' (SET_TEXT_ROTATION): 10 tests passed")
    print("  - Opcode 0x78 'x' (SET_TEXT_SPACING): 8 tests passed")
    print("  - Opcode 0x98 (SET_TEXT_SCALE): 10 tests passed")
    print("  - Total: 28 tests passed")
    print("\nEdge Cases Handled:")
    print("  - Text rotation angles (0°, 90°, 180°, 270°, and arbitrary angles)")
    print("  - Angle normalization (360° -> 0°, 450° -> 90°, negative angles)")
    print("  - Text spacing in 1/1000ths of em (-32768 to 32767)")
    print("  - Positive spacing (tracking) and negative spacing (kerning)")
    print("  - Text scale factors as IEEE 754 float32")
    print("  - Scale range from 0.0 (invisible) to very large values")
    print("  - Fractional scale factors (1.5 = 150%)")
    print("  - Zero scale (degenerate case)")
    print("  - Invalid format detection (missing parentheses)")
    print("  - Insufficient data detection for all opcodes")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
