"""
DWF Coordinate Transform and Units Opcodes - Agent 34

This module implements parsers for 3 DWF opcodes related to coordinate
transformations and drawing units:
- 0x6F 'o': SET_ORIGIN_16R (16-bit relative origin)
- 0x55 'U': SET_UNITS (ASCII format)
- 0x75 'u': SET_UNITS_BINARY (binary format)

These opcodes control the coordinate system origin point and the measurement
units used in the drawing.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/origin.cpp
- develop/global/src/dwf/whiptk/units.cpp

Author: Agent 34 (Coordinate Transform Specialist)
"""

import struct
from typing import Dict, BinaryIO
from enum import IntEnum


class UnitCode(IntEnum):
    """
    Unit code enumeration for binary units opcode.
    Corresponds to WT_Units::WT_Unit_Name in C++ code.
    """
    NONE = 0
    INCHES = 1
    FEET = 2
    MILLIMETERS = 3
    CENTIMETERS = 4
    METERS = 5


# Mapping of unit codes to unit name strings
UNIT_CODE_TO_NAME = {
    UnitCode.NONE: "none",
    UnitCode.INCHES: "in",
    UnitCode.FEET: "ft",
    UnitCode.MILLIMETERS: "mm",
    UnitCode.CENTIMETERS: "cm",
    UnitCode.METERS: "m"
}

# Mapping of unit name strings to unit codes
UNIT_NAME_TO_CODE = {v: k for k, v in UNIT_CODE_TO_NAME.items()}


# =============================================================================
# OPCODE 0x6F 'o' - SET_ORIGIN_16R
# =============================================================================

def parse_opcode_0x6F_origin_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x6F 'o' (SET_ORIGIN_16R) - Set coordinate origin with 16-bit relative coordinates.

    This opcode sets the origin point of the coordinate system using 16-bit signed
    integer offsets. All subsequent drawing coordinates are relative to this origin.

    Format Specification:
    - Opcode: 0x6F (1 byte, 'o' in ASCII, not included in data stream)
    - X coordinate: int16 (2 bytes, signed, little-endian)
    - Y coordinate: int16 (2 bytes, signed, little-endian)
    - Total data: 4 bytes
    - Struct format: "<hh" (little-endian, 2 signed 16-bit integers)

    C++ Reference:
    From origin.cpp - WT_Origin::materialize():
        case 'o':  // 16-bit relative coordinates
            WT_Logical_Point_16 pos;
            WD_CHECK (file.read(1, &pos));
            m_origin = pos;

    From pointset.cpp - WT_Logical_Point_16 structure:
        struct WT_Logical_Point_16 {
            WT_Integer16 m_x;
            WT_Integer16 m_y;
        };

    Args:
        stream: Binary stream positioned after the 0x6F opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_origin'
            - 'x': X coordinate (int16)
            - 'y': Y coordinate (int16)
            - 'coordinate_format': '16bit_relative'
            - 'bytes_read': 4

    Raises:
        ValueError: If stream doesn't contain 4 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<hh', 100, 200)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x6F_origin_16r(stream)
        >>> result['x']
        100
        >>> result['y']
        200

    Notes:
        - Corresponds to WT_Origin::materialize() with opcode 'o' in C++
        - The origin affects all subsequent coordinate-based drawing operations
        - Coordinates are signed, so negative offsets are valid
        - This is the 16-bit version; opcode 'O' (0x4F) uses 32-bit coordinates
    """
    data = stream.read(4)

    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes for opcode 0x6F (SET_ORIGIN_16R), got {len(data)} bytes")

    # Unpack two signed 16-bit integers (little-endian)
    x, y = struct.unpack('<hh', data)

    return {
        'type': 'set_origin',
        'x': x,
        'y': y,
        'coordinate_format': '16bit_relative',
        'bytes_read': 4
    }


# =============================================================================
# OPCODE 0x55 'U' - SET_UNITS (ASCII)
# =============================================================================

def parse_opcode_0x55_units_ascii(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x55 'U' (SET_UNITS - ASCII format).

    This opcode sets the drawing units in ASCII format. The unit identifier
    is enclosed in parentheses following the 'U' opcode.

    Format Specification:
    - Opcode: 0x55 (1 byte, 'U' in ASCII, not included in data stream)
    - Format: (unit_string) where unit_string is the unit identifier
    - Unit strings: "ft", "m", "mm", "in", "cm", "none"
    - Parentheses are required
    - Terminated by closing parenthesis ')'

    C++ Reference:
    From units.cpp - WT_Units::materialize():
        case 'U':  // ASCII format
            // Format is (unit_name)
            WD_CHECK(file.eat_whitespace());
            WD_CHECK(file.read_ascii(m_units));

    Common Unit Identifiers:
    - "in" - inches
    - "ft" - feet
    - "mm" - millimeters
    - "cm" - centimeters
    - "m" - meters
    - "none" - no units specified

    Args:
        stream: Binary stream positioned after the 0x55 'U' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_units'
            - 'units': Unit identifier string
            - 'format': 'ascii'
            - 'description': Human-readable description

    Raises:
        ValueError: If format is invalid or parentheses are missing

    Example:
        >>> import io
        >>> data = b'(mm)'
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x55_units_ascii(stream)
        >>> result['units']
        'mm'

    Notes:
        - Corresponds to WT_Units::materialize() with opcode 'U' in C++
        - ASCII format allows human-readable DWF files
        - The binary version uses opcode 'u' (0x75)
        - Units affect interpretation of coordinate values
    """
    # Read until we find opening parenthesis
    chars = []
    found_open_paren = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream while reading units (ASCII)")

        char = byte.decode('ascii', errors='ignore')

        if char == '(':
            found_open_paren = True
            continue

        if char == ')':
            if not found_open_paren:
                raise ValueError("Found closing parenthesis before opening parenthesis")
            break

        if found_open_paren:
            if char.isalnum() or char == '_':
                chars.append(char)

    if not found_open_paren:
        raise ValueError("Expected opening parenthesis '(' in units (ASCII) format")

    if not chars:
        raise ValueError("Empty unit string in parentheses")

    unit_string = ''.join(chars)

    return {
        'type': 'set_units',
        'units': unit_string,
        'format': 'ascii',
        'description': f'Drawing units set to {unit_string} (ASCII format)'
    }


# =============================================================================
# OPCODE 0x75 'u' - SET_UNITS_BINARY
# =============================================================================

def parse_opcode_0x75_units_binary(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x75 'u' (SET_UNITS_BINARY) - Set drawing units in binary format.

    This opcode sets the drawing units using a single-byte unit code.
    This is the compact binary version of the ASCII units opcode.

    Format Specification:
    - Opcode: 0x75 (1 byte, 'u' in ASCII, not included in data stream)
    - Unit code: uint8 (1 byte, unsigned)
    - Total data: 1 byte

    Unit Codes:
    - 0: None (no units specified)
    - 1: Inches (in)
    - 2: Feet (ft)
    - 3: Millimeters (mm)
    - 4: Centimeters (cm)
    - 5: Meters (m)

    C++ Reference:
    From units.cpp - WT_Units::materialize():
        case 'u':  // Binary format
            WT_Byte unit_code;
            WD_CHECK(file.read(unit_code));
            m_units = (WT_Unit_Name)unit_code;

    From units.cpp - WT_Unit_Name enum:
        enum WT_Unit_Name {
            None = 0,
            Inches = 1,
            Feet = 2,
            Millimeters = 3,
            Centimeters = 4,
            Meters = 5
        };

    Args:
        stream: Binary stream positioned after the 0x75 'u' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_units'
            - 'unit_code': Unit code (0-5)
            - 'units': Unit name string
            - 'format': 'binary'
            - 'description': Human-readable description

    Raises:
        ValueError: If stream doesn't contain 1 byte or unit code is invalid

    Example:
        >>> import io
        >>> data = struct.pack('<B', 3)  # Unit code 3 = millimeters
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x75_units_binary(stream)
        >>> result['unit_code']
        3
        >>> result['units']
        'mm'

    Notes:
        - Corresponds to WT_Units::materialize() with opcode 'u' in C++
        - Binary format is more compact than ASCII version
        - The ASCII version uses opcode 'U' (0x55)
        - Valid unit codes are 0-5; higher values may indicate extended units
    """
    data = stream.read(1)

    if len(data) != 1:
        raise ValueError(f"Expected 1 byte for opcode 0x75 (SET_UNITS_BINARY), got {len(data)} bytes")

    unit_code = struct.unpack('<B', data)[0]

    # Validate unit code and get unit name
    if unit_code in UNIT_CODE_TO_NAME:
        unit_name = UNIT_CODE_TO_NAME[unit_code]
    else:
        # Unknown unit code - could be extended units
        unit_name = f"unknown_unit_{unit_code}"

    return {
        'type': 'set_units',
        'unit_code': unit_code,
        'units': unit_name,
        'format': 'binary',
        'description': f'Drawing units set to {unit_name} (code={unit_code}, binary format)'
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x6F_origin_16r():
    """Test suite for opcode 0x6F (SET_ORIGIN_16R)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x6F 'o' (SET_ORIGIN_16R)")
    print("=" * 70)

    # Test 1: Positive coordinates
    print("\nTest 1: Positive origin coordinates (100, 200)")
    data = struct.pack('<hh', 100, 200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6F_origin_16r(stream)

    assert result['type'] == 'set_origin', f"Expected type='set_origin', got {result['type']}"
    assert result['x'] == 100, f"Expected x=100, got {result['x']}"
    assert result['y'] == 200, f"Expected y=200, got {result['y']}"
    assert result['coordinate_format'] == '16bit_relative'
    assert result['bytes_read'] == 4
    print(f"  PASS: {result}")

    # Test 2: Negative coordinates
    print("\nTest 2: Negative origin coordinates (-50, -30)")
    data = struct.pack('<hh', -50, -30)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6F_origin_16r(stream)

    assert result['x'] == -50, f"Expected x=-50, got {result['x']}"
    assert result['y'] == -30, f"Expected y=-30, got {result['y']}"
    print(f"  PASS: {result}")

    # Test 3: Zero origin (reset to origin)
    print("\nTest 3: Zero origin (0, 0)")
    data = struct.pack('<hh', 0, 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6F_origin_16r(stream)

    assert result['x'] == 0
    assert result['y'] == 0
    print(f"  PASS: {result}")

    # Test 4: Mixed positive/negative coordinates
    print("\nTest 4: Mixed coordinates (150, -75)")
    data = struct.pack('<hh', 150, -75)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6F_origin_16r(stream)

    assert result['x'] == 150
    assert result['y'] == -75
    print(f"  PASS: {result}")

    # Test 5: Maximum 16-bit values
    print("\nTest 5: Maximum 16-bit signed values")
    data = struct.pack('<hh', 32767, -32768)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6F_origin_16r(stream)

    assert result['x'] == 32767
    assert result['y'] == -32768
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02')  # Only 2 bytes instead of 4
    try:
        result = parse_opcode_0x6F_origin_16r(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x6F 'o' (SET_ORIGIN_16R): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x55_units_ascii():
    """Test suite for opcode 0x55 (SET_UNITS ASCII)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x55 'U' (SET_UNITS ASCII)")
    print("=" * 70)

    # Test 1: Millimeters
    print("\nTest 1: Units = millimeters (mm)")
    data = b'(mm)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x55_units_ascii(stream)

    assert result['type'] == 'set_units'
    assert result['units'] == 'mm', f"Expected units='mm', got {result['units']}"
    assert result['format'] == 'ascii'
    print(f"  PASS: {result}")

    # Test 2: Feet
    print("\nTest 2: Units = feet (ft)")
    data = b'(ft)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x55_units_ascii(stream)

    assert result['units'] == 'ft'
    print(f"  PASS: {result}")

    # Test 3: Inches
    print("\nTest 3: Units = inches (in)")
    data = b'(in)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x55_units_ascii(stream)

    assert result['units'] == 'in'
    print(f"  PASS: {result}")

    # Test 4: Meters
    print("\nTest 4: Units = meters (m)")
    data = b'(m)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x55_units_ascii(stream)

    assert result['units'] == 'm'
    print(f"  PASS: {result}")

    # Test 5: Centimeters
    print("\nTest 5: Units = centimeters (cm)")
    data = b'(cm)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x55_units_ascii(stream)

    assert result['units'] == 'cm'
    print(f"  PASS: {result}")

    # Test 6: None
    print("\nTest 6: Units = none")
    data = b'(none)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x55_units_ascii(stream)

    assert result['units'] == 'none'
    print(f"  PASS: {result}")

    # Test 7: Error handling - missing opening parenthesis
    print("\nTest 7: Error handling - missing parentheses")
    stream = io.BytesIO(b'mm)')
    try:
        result = parse_opcode_0x55_units_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 8: Error handling - empty unit string
    print("\nTest 8: Error handling - empty unit string")
    stream = io.BytesIO(b'()')
    try:
        result = parse_opcode_0x55_units_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x55 'U' (SET_UNITS ASCII): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x75_units_binary():
    """Test suite for opcode 0x75 (SET_UNITS_BINARY)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x75 'u' (SET_UNITS_BINARY)")
    print("=" * 70)

    # Test 1: None (code 0)
    print("\nTest 1: Units = none (code 0)")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['type'] == 'set_units'
    assert result['unit_code'] == 0
    assert result['units'] == 'none'
    assert result['format'] == 'binary'
    print(f"  PASS: {result}")

    # Test 2: Inches (code 1)
    print("\nTest 2: Units = inches (code 1)")
    data = struct.pack('<B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['unit_code'] == 1
    assert result['units'] == 'in'
    print(f"  PASS: {result}")

    # Test 3: Feet (code 2)
    print("\nTest 3: Units = feet (code 2)")
    data = struct.pack('<B', 2)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['unit_code'] == 2
    assert result['units'] == 'ft'
    print(f"  PASS: {result}")

    # Test 4: Millimeters (code 3)
    print("\nTest 4: Units = millimeters (code 3)")
    data = struct.pack('<B', 3)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['unit_code'] == 3
    assert result['units'] == 'mm'
    print(f"  PASS: {result}")

    # Test 5: Centimeters (code 4)
    print("\nTest 5: Units = centimeters (code 4)")
    data = struct.pack('<B', 4)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['unit_code'] == 4
    assert result['units'] == 'cm'
    print(f"  PASS: {result}")

    # Test 6: Meters (code 5)
    print("\nTest 6: Units = meters (code 5)")
    data = struct.pack('<B', 5)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['unit_code'] == 5
    assert result['units'] == 'm'
    print(f"  PASS: {result}")

    # Test 7: Unknown unit code (code 99)
    print("\nTest 7: Unknown unit code (99)")
    data = struct.pack('<B', 99)
    stream = io.BytesIO(data)
    result = parse_opcode_0x75_units_binary(stream)

    assert result['unit_code'] == 99
    assert 'unknown' in result['units']
    print(f"  PASS: {result}")

    # Test 8: Error handling - insufficient data
    print("\nTest 8: Error handling - insufficient data")
    stream = io.BytesIO(b'')  # Empty stream
    try:
        result = parse_opcode_0x75_units_binary(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x75 'u' (SET_UNITS_BINARY): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 34 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 34: COORDINATE TRANSFORM & UNITS TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x6F 'o': SET_ORIGIN_16R")
    print("  - 0x55 'U': SET_UNITS (ASCII)")
    print("  - 0x75 'u': SET_UNITS_BINARY")
    print("=" * 70)

    test_opcode_0x6F_origin_16r()
    test_opcode_0x55_units_ascii()
    test_opcode_0x75_units_binary()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x6F 'o' (SET_ORIGIN_16R): 6 tests passed")
    print("  - Opcode 0x55 'U' (SET_UNITS ASCII): 8 tests passed")
    print("  - Opcode 0x75 'u' (SET_UNITS_BINARY): 8 tests passed")
    print("  - Total: 22 tests passed")
    print("\nEdge Cases Handled:")
    print("  - Negative coordinates for origin")
    print("  - Zero values (origin reset)")
    print("  - Maximum 16-bit signed integer values")
    print("  - All standard unit codes (0-5)")
    print("  - Unknown unit codes (graceful handling)")
    print("  - Invalid ASCII format detection")
    print("  - Insufficient data detection")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
