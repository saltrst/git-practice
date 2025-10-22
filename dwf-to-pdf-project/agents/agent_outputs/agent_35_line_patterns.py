"""
DWF Line Styling Opcodes - Agent 35

This module implements parsers for 3 DWF opcodes related to line styling:
- 0x4C 'L': SET_LINE_CAP (ASCII/binary format)
- 0x6C 'l': SET_LINE_JOIN (binary format)
- 0x57 'W': SET_PEN_WIDTH (ASCII format)

These opcodes control how line endpoints and corners are rendered, as well
as the width of lines in the drawing.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/line_style.cpp
- develop/global/src/dwf/whiptk/penwidth.cpp

Author: Agent 35 (Line Pattern Specialist)
"""

import struct
from typing import Dict, BinaryIO
from enum import IntEnum


class LineCapStyle(IntEnum):
    """
    Line cap style enumeration for line endpoints.
    Corresponds to WT_Line_Style::WT_Cap_Type in C++ code.
    """
    BUTT = 0
    ROUND = 1
    SQUARE = 2


class LineJoinStyle(IntEnum):
    """
    Line join style enumeration for line corners.
    Corresponds to WT_Line_Style::WT_Join_Type in C++ code.
    """
    MITER = 0
    ROUND = 1
    BEVEL = 2


# Mapping of cap codes to cap style names
CAP_CODE_TO_NAME = {
    LineCapStyle.BUTT: "butt",
    LineCapStyle.ROUND: "round",
    LineCapStyle.SQUARE: "square"
}

# Mapping of cap names to cap codes
CAP_NAME_TO_CODE = {v: k for k, v in CAP_CODE_TO_NAME.items()}

# Mapping of join codes to join style names
JOIN_CODE_TO_NAME = {
    LineJoinStyle.MITER: "miter",
    LineJoinStyle.ROUND: "round",
    LineJoinStyle.BEVEL: "bevel"
}

# Mapping of join names to join codes
JOIN_NAME_TO_CODE = {v: k for k, v in JOIN_CODE_TO_NAME.items()}


# =============================================================================
# OPCODE 0x4C 'L' - SET_LINE_CAP
# =============================================================================

def parse_opcode_0x4C_line_cap(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x4C 'L' (SET_LINE_CAP) - Set line cap style.

    This opcode sets the style for how line endpoints are drawn. It can appear
    in either ASCII format L(cap_style) or binary format (1 byte cap code).

    Format Specification:
    - ASCII Format: L(cap_style) where cap_style is "butt", "round", or "square"
    - Binary Format: 1 byte (uint8) cap code (0-2)
    - Opcode: 0x4C (1 byte, 'L' in ASCII, not included in data stream)

    Cap Styles:
    - 0 (butt): Line ends exactly at endpoint (flat)
    - 1 (round): Line ends with rounded cap extending beyond endpoint
    - 2 (square): Line ends with square cap extending beyond endpoint

    C++ Reference:
    From line_style.cpp - WT_Line_Style::materialize():
        case 'L':  // Line cap style
            if (next_byte == '(') {
                // ASCII format: L(cap_style)
                read ASCII cap name
            } else {
                // Binary format: single byte cap code
                WT_Byte cap_code;
                file.read(cap_code);
                m_cap = (WT_Cap_Type)cap_code;
            }

    Args:
        stream: Binary stream positioned after the 0x4C 'L' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_line_cap'
            - 'cap_code': Cap code (0-2)
            - 'cap_style': Cap style name string
            - 'format': 'ascii' or 'binary'

    Raises:
        ValueError: If stream doesn't contain expected data or cap code is invalid

    Example:
        >>> import io
        >>> # Binary format: round cap
        >>> data = struct.pack('<B', 1)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x4C_line_cap(stream)
        >>> result['cap_code']
        1
        >>> result['cap_style']
        'round'

        >>> # ASCII format: square cap
        >>> stream = io.BytesIO(b'(square)')
        >>> result = parse_opcode_0x4C_line_cap(stream)
        >>> result['cap_style']
        'square'

    Notes:
        - Corresponds to WT_Line_Style::materialize() with opcode 'L' in C++
        - Cap style affects how line ends appear in rendered output
        - Butt cap is most common and efficient (no extension)
        - Round and square caps extend beyond the endpoint
    """
    # Peek at first byte to determine format
    first_byte = stream.read(1)
    if not first_byte:
        raise ValueError("Expected data after opcode 0x4C (SET_LINE_CAP)")

    if first_byte == b'(':
        # ASCII format: (cap_name)
        chars = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise ValueError("Unexpected end of stream while reading line cap (ASCII)")

            char = byte.decode('ascii', errors='ignore')
            if char == ')':
                break

            if char.isalpha():
                chars.append(char)

        if not chars:
            raise ValueError("Empty cap style in parentheses")

        cap_name = ''.join(chars).lower()

        # Map cap name to cap code
        if cap_name in CAP_NAME_TO_CODE:
            cap_code = CAP_NAME_TO_CODE[cap_name]
        else:
            raise ValueError(f"Unknown cap style: {cap_name}")

        return {
            'type': 'set_line_cap',
            'cap_code': cap_code,
            'cap_style': cap_name,
            'format': 'ascii'
        }
    else:
        # Binary format: single byte cap code
        cap_code = struct.unpack('<B', first_byte)[0]

        # Validate cap code
        if cap_code not in CAP_CODE_TO_NAME:
            raise ValueError(f"Invalid cap code: {cap_code} (must be 0-2)")

        cap_style = CAP_CODE_TO_NAME[cap_code]

        return {
            'type': 'set_line_cap',
            'cap_code': cap_code,
            'cap_style': cap_style,
            'format': 'binary'
        }


# =============================================================================
# OPCODE 0x6C 'l' - SET_LINE_JOIN
# =============================================================================

def parse_opcode_0x6C_line_join(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x6C 'l' (SET_LINE_JOIN) - Set line join style.

    This opcode sets the style for how line corners (joins) are drawn when
    two line segments meet at an angle.

    Format Specification:
    - Opcode: 0x6C (1 byte, 'l' in ASCII, not included in data stream)
    - Join code: uint8 (1 byte, unsigned)
    - Total data: 1 byte

    Join Styles:
    - 0 (miter): Sharp pointed corner extending to a point
    - 1 (round): Rounded corner with circular arc
    - 2 (bevel): Flat corner with diagonal cut

    C++ Reference:
    From line_style.cpp - WT_Line_Style::materialize():
        case 'l':  // Line join style
            WT_Byte join_code;
            WD_CHECK(file.read(join_code));
            m_join = (WT_Join_Type)join_code;

    From line_style.cpp - WT_Join_Type enum:
        enum WT_Join_Type {
            Miter = 0,
            Round = 1,
            Bevel = 2
        };

    Args:
        stream: Binary stream positioned after the 0x6C 'l' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_line_join'
            - 'join_code': Join code (0-2)
            - 'join_style': Join style name string

    Raises:
        ValueError: If stream doesn't contain 1 byte or join code is invalid

    Example:
        >>> import io
        >>> data = struct.pack('<B', 1)  # Round join
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x6C_line_join(stream)
        >>> result['join_code']
        1
        >>> result['join_style']
        'round'

    Notes:
        - Corresponds to WT_Line_Style::materialize() with opcode 'l' in C++
        - Join style affects appearance of corners in polylines and polygons
        - Miter joins can create sharp points that extend beyond corner
        - Round joins create smooth curves at corners
        - Bevel joins create flat diagonal cuts at corners
    """
    data = stream.read(1)

    if len(data) != 1:
        raise ValueError(f"Expected 1 byte for opcode 0x6C (SET_LINE_JOIN), got {len(data)} bytes")

    join_code = struct.unpack('<B', data)[0]

    # Validate join code and get join style name
    if join_code not in JOIN_CODE_TO_NAME:
        raise ValueError(f"Invalid join code: {join_code} (must be 0-2)")

    join_style = JOIN_CODE_TO_NAME[join_code]

    return {
        'type': 'set_line_join',
        'join_code': join_code,
        'join_style': join_style
    }


# =============================================================================
# OPCODE 0x57 'W' - SET_PEN_WIDTH
# =============================================================================

def parse_opcode_0x57_pen_width_ascii(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x57 'W' (SET_PEN_WIDTH - ASCII format).

    This opcode sets the pen width (line thickness) for subsequent drawing
    operations in ASCII format. The width value is enclosed in parentheses.

    Format Specification:
    - Opcode: 0x57 (1 byte, 'W' in ASCII, not included in data stream)
    - Format: (width) where width is an ASCII integer value
    - Parentheses are required
    - Terminated by closing parenthesis ')'

    C++ Reference:
    From penwidth.cpp - WT_Pen_Width::materialize():
        case 'W':  // ASCII format
            // Format is (width_value)
            WD_CHECK(file.eat_whitespace());
            WD_CHECK(file.read_ascii(m_width));

    Args:
        stream: Binary stream positioned after the 0x57 'W' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_pen_width'
            - 'width': Pen width as integer
            - 'format': 'ascii'
            - 'description': Human-readable description

    Raises:
        ValueError: If format is invalid or parentheses are missing

    Example:
        >>> import io
        >>> data = b'(5)'
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x57_pen_width_ascii(stream)
        >>> result['width']
        5

    Notes:
        - Corresponds to WT_Pen_Width::materialize() with opcode 'W' in C++
        - Width value affects thickness of all subsequent line drawing
        - Width is in drawing units (affected by units setting)
        - Typical values range from 1 to 100+ depending on scale
        - Width of 0 typically means "hairline" or thinnest possible line
    """
    # Read until we find opening parenthesis
    chars = []
    found_open_paren = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream while reading pen width (ASCII)")

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
                chars.append(char)

    if not found_open_paren:
        raise ValueError("Expected opening parenthesis '(' in pen width (ASCII) format")

    if not chars:
        raise ValueError("Empty width value in parentheses")

    width_string = ''.join(chars)

    try:
        width = int(width_string)
    except ValueError:
        raise ValueError(f"Invalid width value: {width_string}")

    return {
        'type': 'set_pen_width',
        'width': width,
        'format': 'ascii',
        'description': f'Pen width set to {width} (ASCII format)'
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x4C_line_cap():
    """Test suite for opcode 0x4C (SET_LINE_CAP)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x4C 'L' (SET_LINE_CAP)")
    print("=" * 70)

    # Test 1: Binary format - butt cap (code 0)
    print("\nTest 1: Binary format - butt cap (code 0)")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x4C_line_cap(stream)

    assert result['type'] == 'set_line_cap', f"Expected type='set_line_cap', got {result['type']}"
    assert result['cap_code'] == 0, f"Expected cap_code=0, got {result['cap_code']}"
    assert result['cap_style'] == 'butt', f"Expected cap_style='butt', got {result['cap_style']}"
    assert result['format'] == 'binary'
    print(f"  PASS: {result}")

    # Test 2: Binary format - round cap (code 1)
    print("\nTest 2: Binary format - round cap (code 1)")
    data = struct.pack('<B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x4C_line_cap(stream)

    assert result['cap_code'] == 1
    assert result['cap_style'] == 'round'
    assert result['format'] == 'binary'
    print(f"  PASS: {result}")

    # Test 3: Binary format - square cap (code 2)
    print("\nTest 3: Binary format - square cap (code 2)")
    data = struct.pack('<B', 2)
    stream = io.BytesIO(data)
    result = parse_opcode_0x4C_line_cap(stream)

    assert result['cap_code'] == 2
    assert result['cap_style'] == 'square'
    assert result['format'] == 'binary'
    print(f"  PASS: {result}")

    # Test 4: ASCII format - butt cap
    print("\nTest 4: ASCII format - butt cap")
    data = b'(butt)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4C_line_cap(stream)

    assert result['cap_code'] == 0
    assert result['cap_style'] == 'butt'
    assert result['format'] == 'ascii'
    print(f"  PASS: {result}")

    # Test 5: ASCII format - round cap
    print("\nTest 5: ASCII format - round cap")
    data = b'(round)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4C_line_cap(stream)

    assert result['cap_code'] == 1
    assert result['cap_style'] == 'round'
    assert result['format'] == 'ascii'
    print(f"  PASS: {result}")

    # Test 6: ASCII format - square cap
    print("\nTest 6: ASCII format - square cap")
    data = b'(square)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4C_line_cap(stream)

    assert result['cap_code'] == 2
    assert result['cap_style'] == 'square'
    assert result['format'] == 'ascii'
    print(f"  PASS: {result}")

    # Test 7: Error handling - invalid binary cap code
    print("\nTest 7: Error handling - invalid binary cap code")
    data = struct.pack('<B', 5)  # Invalid code
    stream = io.BytesIO(data)
    try:
        result = parse_opcode_0x4C_line_cap(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 8: Error handling - invalid ASCII cap name
    print("\nTest 8: Error handling - invalid ASCII cap name")
    data = b'(invalid)'
    stream = io.BytesIO(data)
    try:
        result = parse_opcode_0x4C_line_cap(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 9: Error handling - empty stream
    print("\nTest 9: Error handling - empty stream")
    stream = io.BytesIO(b'')
    try:
        result = parse_opcode_0x4C_line_cap(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x4C 'L' (SET_LINE_CAP): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x6C_line_join():
    """Test suite for opcode 0x6C (SET_LINE_JOIN)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x6C 'l' (SET_LINE_JOIN)")
    print("=" * 70)

    # Test 1: Miter join (code 0)
    print("\nTest 1: Miter join (code 0)")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6C_line_join(stream)

    assert result['type'] == 'set_line_join', f"Expected type='set_line_join', got {result['type']}"
    assert result['join_code'] == 0, f"Expected join_code=0, got {result['join_code']}"
    assert result['join_style'] == 'miter', f"Expected join_style='miter', got {result['join_style']}"
    print(f"  PASS: {result}")

    # Test 2: Round join (code 1)
    print("\nTest 2: Round join (code 1)")
    data = struct.pack('<B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6C_line_join(stream)

    assert result['join_code'] == 1
    assert result['join_style'] == 'round'
    print(f"  PASS: {result}")

    # Test 3: Bevel join (code 2)
    print("\nTest 3: Bevel join (code 2)")
    data = struct.pack('<B', 2)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6C_line_join(stream)

    assert result['join_code'] == 2
    assert result['join_style'] == 'bevel'
    print(f"  PASS: {result}")

    # Test 4: All join styles verification
    print("\nTest 4: Verify all join styles")
    for code, expected_style in JOIN_CODE_TO_NAME.items():
        data = struct.pack('<B', code)
        stream = io.BytesIO(data)
        result = parse_opcode_0x6C_line_join(stream)
        assert result['join_code'] == code
        assert result['join_style'] == expected_style
    print(f"  PASS: All {len(JOIN_CODE_TO_NAME)} join styles verified")

    # Test 5: Error handling - invalid join code
    print("\nTest 5: Error handling - invalid join code")
    data = struct.pack('<B', 5)  # Invalid code
    stream = io.BytesIO(data)
    try:
        result = parse_opcode_0x6C_line_join(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'')  # Empty stream
    try:
        result = parse_opcode_0x6C_line_join(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x6C 'l' (SET_LINE_JOIN): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x57_pen_width_ascii():
    """Test suite for opcode 0x57 (SET_PEN_WIDTH ASCII)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x57 'W' (SET_PEN_WIDTH ASCII)")
    print("=" * 70)

    # Test 1: Basic width value
    print("\nTest 1: Basic width value (5)")
    data = b'(5)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x57_pen_width_ascii(stream)

    assert result['type'] == 'set_pen_width', f"Expected type='set_pen_width', got {result['type']}"
    assert result['width'] == 5, f"Expected width=5, got {result['width']}"
    assert result['format'] == 'ascii'
    print(f"  PASS: {result}")

    # Test 2: Zero width (hairline)
    print("\nTest 2: Zero width (hairline)")
    data = b'(0)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x57_pen_width_ascii(stream)

    assert result['width'] == 0
    print(f"  PASS: {result}")

    # Test 3: Large width value
    print("\nTest 3: Large width value (1000)")
    data = b'(1000)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x57_pen_width_ascii(stream)

    assert result['width'] == 1000
    print(f"  PASS: {result}")

    # Test 4: Small width value
    print("\nTest 4: Small width value (1)")
    data = b'(1)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x57_pen_width_ascii(stream)

    assert result['width'] == 1
    print(f"  PASS: {result}")

    # Test 5: Medium width value
    print("\nTest 5: Medium width value (25)")
    data = b'(25)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x57_pen_width_ascii(stream)

    assert result['width'] == 25
    print(f"  PASS: {result}")

    # Test 6: Negative width (edge case)
    print("\nTest 6: Negative width (-5)")
    data = b'(-5)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x57_pen_width_ascii(stream)

    assert result['width'] == -5
    print(f"  PASS: {result}")

    # Test 7: Error handling - missing opening parenthesis
    print("\nTest 7: Error handling - missing parentheses")
    stream = io.BytesIO(b'5)')
    try:
        result = parse_opcode_0x57_pen_width_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 8: Error handling - empty width value
    print("\nTest 8: Error handling - empty width value")
    stream = io.BytesIO(b'()')
    try:
        result = parse_opcode_0x57_pen_width_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 9: Error handling - unexpected end of stream
    print("\nTest 9: Error handling - unexpected end of stream")
    stream = io.BytesIO(b'(123')  # Missing closing parenthesis
    try:
        result = parse_opcode_0x57_pen_width_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x57 'W' (SET_PEN_WIDTH ASCII): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 35 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 35: LINE PATTERNS TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x4C 'L': SET_LINE_CAP (ASCII/binary)")
    print("  - 0x6C 'l': SET_LINE_JOIN (binary)")
    print("  - 0x57 'W': SET_PEN_WIDTH (ASCII)")
    print("=" * 70)

    test_opcode_0x4C_line_cap()
    test_opcode_0x6C_line_join()
    test_opcode_0x57_pen_width_ascii()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x4C 'L' (SET_LINE_CAP): 9 tests passed")
    print("  - Opcode 0x6C 'l' (SET_LINE_JOIN): 6 tests passed")
    print("  - Opcode 0x57 'W' (SET_PEN_WIDTH ASCII): 9 tests passed")
    print("  - Total: 24 tests passed")
    print("\nEdge Cases Handled:")
    print("  - Binary and ASCII format parsing for line cap")
    print("  - All cap styles: butt, round, square")
    print("  - All join styles: miter, round, bevel")
    print("  - Invalid cap/join codes detection")
    print("  - Zero, negative, and large width values")
    print("  - Invalid ASCII format detection")
    print("  - Missing parentheses detection")
    print("  - Empty values detection")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
