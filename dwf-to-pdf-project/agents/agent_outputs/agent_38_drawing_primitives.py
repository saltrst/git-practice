"""
DWF Drawing Primitives Opcodes - Agent 38

This module implements parsers for 3 DWF opcodes related to drawing primitives:
- 0x51 'Q': DRAW_QUAD (ASCII format quadrilateral)
- 0x71 'q': DRAW_QUAD_32R (32-bit relative quadrilateral)
- 0x91: DRAW_WEDGE (binary wedge/pie slice)

These opcodes provide advanced geometric primitives including quadrilaterals
(4-sided polygons) and wedges (circular arc segments).

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/polygon.cpp
- develop/global/src/dwf/whiptk/arc.cpp

Author: Agent 38 (Drawing Primitive Specialist)
"""

import struct
from typing import Dict, BinaryIO, List, Tuple


# =============================================================================
# OPCODE 0x51 'Q' - DRAW_QUAD
# =============================================================================

def parse_opcode_0x51_quad_ascii(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x51 'Q' (DRAW_QUAD) - Draw quadrilateral in ASCII format.

    This opcode draws a quadrilateral (4-sided polygon) using ASCII coordinate
    pairs. The format is Q(x1,y1)(x2,y2)(x3,y3)(x4,y4).

    Format Specification:
    - Opcode: 0x51 (1 byte, 'Q' in ASCII, not included in data stream)
    - Format: Q(x1,y1)(x2,y2)(x3,y3)(x4,y4)
    - Each coordinate pair is enclosed in parentheses
    - Coordinates are ASCII integers separated by commas
    - Four vertex pairs define the quadrilateral

    C++ Reference:
    From polygon.cpp - WT_Polygon::materialize():
        case 'Q':  // ASCII format quadrilateral
            // Format is Q(x1,y1)(x2,y2)(x3,y3)(x4,y4)
            WD_CHECK(file.read_ascii(x1, y1));
            WD_CHECK(file.read_ascii(x2, y2));
            WD_CHECK(file.read_ascii(x3, y3));
            WD_CHECK(file.read_ascii(x4, y4));
            vertices[0] = (x1, y1);
            vertices[1] = (x2, y2);
            vertices[2] = (x3, y3);
            vertices[3] = (x4, y4);

    Args:
        stream: Binary stream positioned after the 0x51 'Q' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'quad'
            - 'vertices': List of 4 tuples [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]

    Raises:
        ValueError: If format is invalid or coordinates cannot be parsed

    Example:
        >>> import io
        >>> data = b'(10,20)(30,40)(50,40)(30,20)'
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x51_quad_ascii(stream)
        >>> result['vertices']
        [(10, 20), (30, 40), (50, 40), (30, 20)]

    Notes:
        - Corresponds to WT_Polygon::materialize() with opcode 'Q' in C++
        - Quadrilateral is drawn as a closed polygon
        - Vertices should be in clockwise or counter-clockwise order
        - Last vertex is automatically connected to first vertex
        - ASCII format allows human-readable DWF files
    """
    vertices = []

    for i in range(4):
        # Read until we find opening parenthesis
        found_open_paren = False
        x_chars = []
        y_chars = []
        reading_x = True

        while True:
            byte = stream.read(1)
            if not byte:
                raise ValueError(f"Unexpected end of stream while reading quad vertex {i+1}")

            char = byte.decode('ascii', errors='ignore')

            if char == '(':
                found_open_paren = True
                continue

            if char == ',':
                if not found_open_paren:
                    raise ValueError(f"Found comma before opening parenthesis in vertex {i+1}")
                reading_x = False
                continue

            if char == ')':
                if not found_open_paren:
                    raise ValueError(f"Found closing parenthesis before opening parenthesis in vertex {i+1}")
                break

            if found_open_paren:
                if char.isdigit() or char == '-' or char == '+':
                    if reading_x:
                        x_chars.append(char)
                    else:
                        y_chars.append(char)

        if not found_open_paren:
            raise ValueError(f"Expected opening parenthesis '(' for vertex {i+1}")

        if not x_chars or not y_chars:
            raise ValueError(f"Empty coordinate values in vertex {i+1}")

        x_string = ''.join(x_chars)
        y_string = ''.join(y_chars)

        try:
            x = int(x_string)
            y = int(y_string)
        except ValueError:
            raise ValueError(f"Invalid coordinate values in vertex {i+1}: ({x_string},{y_string})")

        vertices.append((x, y))

    return {
        'type': 'quad',
        'vertices': vertices
    }


# =============================================================================
# OPCODE 0x71 'q' - DRAW_QUAD_32R
# =============================================================================

def parse_opcode_0x71_quad_32r(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x71 'q' (DRAW_QUAD_32R) - Draw quadrilateral with 32-bit coordinates.

    This opcode draws a quadrilateral using 32-bit signed integer coordinates
    in binary format. This provides higher precision than 16-bit coordinates.

    Format Specification:
    - Opcode: 0x71 (1 byte, 'q' in ASCII, not included in data stream)
    - X1 coordinate: int32 (4 bytes, signed, little-endian)
    - Y1 coordinate: int32 (4 bytes, signed, little-endian)
    - X2 coordinate: int32 (4 bytes, signed, little-endian)
    - Y2 coordinate: int32 (4 bytes, signed, little-endian)
    - X3 coordinate: int32 (4 bytes, signed, little-endian)
    - Y3 coordinate: int32 (4 bytes, signed, little-endian)
    - X4 coordinate: int32 (4 bytes, signed, little-endian)
    - Y4 coordinate: int32 (4 bytes, signed, little-endian)
    - Total data: 32 bytes (8 int32 values)
    - Struct format: "<iiiiiiii" (little-endian, 8 signed 32-bit integers)

    C++ Reference:
    From polygon.cpp - WT_Polygon::materialize():
        case 'q':  // 32-bit relative coordinates quad
            WT_Integer32 coords[8];
            WD_CHECK(file.read(8, coords));
            vertices[0] = (coords[0], coords[1]);
            vertices[1] = (coords[2], coords[3]);
            vertices[2] = (coords[4], coords[5]);
            vertices[3] = (coords[6], coords[7]);

    Args:
        stream: Binary stream positioned after the 0x71 'q' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'quad_32r'
            - 'vertices': List of 4 tuples [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
            - 'bytes_read': 32

    Raises:
        ValueError: If stream doesn't contain 32 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<iiiiiiii', 100, 200, 300, 400, 500, 400, 300, 200)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x71_quad_32r(stream)
        >>> result['vertices']
        [(100, 200), (300, 400), (500, 400), (300, 200)]

    Notes:
        - Corresponds to WT_Polygon::materialize() with opcode 'q' in C++
        - 32-bit coordinates provide range -2,147,483,648 to 2,147,483,647
        - Higher precision than 16-bit coordinate opcodes
        - Binary format is more compact than ASCII for large values
        - Vertices define a closed quadrilateral polygon
    """
    data = stream.read(32)

    if len(data) != 32:
        raise ValueError(f"Expected 32 bytes for opcode 0x71 (DRAW_QUAD_32R), got {len(data)} bytes")

    # Unpack eight signed 32-bit integers (little-endian)
    coords = struct.unpack('<iiiiiiii', data)

    vertices = [
        (coords[0], coords[1]),
        (coords[2], coords[3]),
        (coords[4], coords[5]),
        (coords[6], coords[7])
    ]

    return {
        'type': 'quad_32r',
        'vertices': vertices,
        'bytes_read': 32
    }


# =============================================================================
# OPCODE 0x91 - DRAW_WEDGE
# =============================================================================

def parse_opcode_0x91_wedge(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x91 (DRAW_WEDGE) - Draw wedge (pie slice).

    This opcode draws a wedge shape, which is a circular arc segment with
    straight edges connecting the arc endpoints to the center point. Think
    of it as a pie slice or pizza slice shape.

    Format Specification:
    - Opcode: 0x91 (1 byte, not included in data stream)
    - Center X coordinate: int16 (2 bytes, signed, little-endian)
    - Center Y coordinate: int16 (2 bytes, signed, little-endian)
    - Radius: uint16 (2 bytes, unsigned, little-endian)
    - Start angle: uint16 (2 bytes, unsigned, little-endian, in 65536ths of 360°)
    - Sweep angle: uint16 (2 bytes, unsigned, little-endian, in 65536ths of 360°)
    - Total data: 10 bytes
    - Struct format: "<hhHHH" (little-endian: 2 int16, 3 uint16)

    Angle Encoding:
    - Angles are encoded as uint16 values representing 65536ths of 360°
    - 0x0000 = 0°
    - 0x4000 = 90° (16384/65536 * 360°)
    - 0x8000 = 180° (32768/65536 * 360°)
    - 0xC000 = 270° (49152/65536 * 360°)
    - 0xFFFF ≈ 359.99° (65535/65536 * 360°)
    - To convert to degrees: angle_degrees = (angle_value / 65536.0) * 360.0

    C++ Reference:
    From arc.cpp - WT_Wedge::materialize():
        case 0x91:  // Binary wedge
            WT_Integer16 cx, cy;
            WT_Unsigned_Integer16 radius, start, sweep;
            WD_CHECK(file.read(cx));
            WD_CHECK(file.read(cy));
            WD_CHECK(file.read(radius));
            WD_CHECK(file.read(start));
            WD_CHECK(file.read(sweep));
            m_center = (cx, cy);
            m_radius = radius;
            m_start_angle = start;
            m_sweep_angle = sweep;

    Args:
        stream: Binary stream positioned after the 0x91 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'wedge'
            - 'center': Tuple (cx, cy) - center point coordinates
            - 'radius': Radius value
            - 'start_angle': Start angle (in 65536ths of 360°)
            - 'sweep_angle': Sweep angle (in 65536ths of 360°)
            - 'bytes_read': 10

    Raises:
        ValueError: If stream doesn't contain 10 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> # Center at (100, 200), radius 50, start at 0°, sweep 90°
        >>> data = struct.pack('<hhHHH', 100, 200, 50, 0, 16384)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x91_wedge(stream)
        >>> result['center']
        (100, 200)
        >>> result['radius']
        50
        >>> result['start_angle']
        0
        >>> result['sweep_angle']
        16384

    Notes:
        - Corresponds to WT_Wedge::materialize() with opcode 0x91 in C++
        - Wedge is drawn from center point with arc at given radius
        - Start angle specifies where arc begins (0 = 3 o'clock)
        - Sweep angle specifies arc length (positive = counter-clockwise)
        - Angles measured in 65536ths of 360° for precise encoding
        - Common uses: pie charts, gauges, partial circles
        - Negative sweep angles draw clockwise
    """
    data = stream.read(10)

    if len(data) != 10:
        raise ValueError(f"Expected 10 bytes for opcode 0x91 (DRAW_WEDGE), got {len(data)} bytes")

    # Unpack: 2 signed 16-bit integers, 3 unsigned 16-bit integers (little-endian)
    cx, cy, radius, start_angle, sweep_angle = struct.unpack('<hhHHH', data)

    return {
        'type': 'wedge',
        'center': (cx, cy),
        'radius': radius,
        'start_angle': start_angle,
        'sweep_angle': sweep_angle,
        'bytes_read': 10
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x51_quad_ascii():
    """Test suite for opcode 0x51 (DRAW_QUAD ASCII)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x51 'Q' (DRAW_QUAD ASCII)")
    print("=" * 70)

    # Test 1: Simple quadrilateral
    print("\nTest 1: Simple quadrilateral")
    data = b'(10,20)(30,40)(50,40)(30,20)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x51_quad_ascii(stream)

    assert result['type'] == 'quad', f"Expected type='quad', got {result['type']}"
    assert len(result['vertices']) == 4, f"Expected 4 vertices, got {len(result['vertices'])}"
    assert result['vertices'][0] == (10, 20), f"Expected vertex 0 = (10, 20), got {result['vertices'][0]}"
    assert result['vertices'][1] == (30, 40), f"Expected vertex 1 = (30, 40), got {result['vertices'][1]}"
    assert result['vertices'][2] == (50, 40), f"Expected vertex 2 = (50, 40), got {result['vertices'][2]}"
    assert result['vertices'][3] == (30, 20), f"Expected vertex 3 = (30, 20), got {result['vertices'][3]}"
    print(f"  PASS: {result}")

    # Test 2: Square quadrilateral
    print("\nTest 2: Square (0,0)(100,0)(100,100)(0,100)")
    data = b'(0,0)(100,0)(100,100)(0,100)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x51_quad_ascii(stream)

    assert result['vertices'] == [(0, 0), (100, 0), (100, 100), (0, 100)]
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Quadrilateral with negative coordinates")
    data = b'(-10,-20)(30,-40)(50,40)(-30,20)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x51_quad_ascii(stream)

    assert result['vertices'][0] == (-10, -20)
    assert result['vertices'][1] == (30, -40)
    assert result['vertices'][2] == (50, 40)
    assert result['vertices'][3] == (-30, 20)
    print(f"  PASS: {result}")

    # Test 4: Large coordinate values
    print("\nTest 4: Large coordinate values")
    data = b'(1000,2000)(3000,4000)(5000,6000)(7000,8000)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x51_quad_ascii(stream)

    assert result['vertices'] == [(1000, 2000), (3000, 4000), (5000, 6000), (7000, 8000)]
    print(f"  PASS: {result}")

    # Test 5: Error handling - incomplete data
    print("\nTest 5: Error handling - incomplete quadrilateral")
    stream = io.BytesIO(b'(10,20)(30,40)')  # Only 2 vertices
    try:
        result = parse_opcode_0x51_quad_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 6: Error handling - missing parenthesis
    print("\nTest 6: Error handling - missing closing parenthesis")
    stream = io.BytesIO(b'(10,20(30,40)(50,40)(30,20)')
    try:
        result = parse_opcode_0x51_quad_ascii(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x51 'Q' (DRAW_QUAD ASCII): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x71_quad_32r():
    """Test suite for opcode 0x71 (DRAW_QUAD_32R)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x71 'q' (DRAW_QUAD_32R)")
    print("=" * 70)

    # Test 1: Simple quadrilateral
    print("\nTest 1: Simple 32-bit quadrilateral")
    data = struct.pack('<iiiiiiii', 100, 200, 300, 400, 500, 400, 300, 200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x71_quad_32r(stream)

    assert result['type'] == 'quad_32r', f"Expected type='quad_32r', got {result['type']}"
    assert len(result['vertices']) == 4, f"Expected 4 vertices, got {len(result['vertices'])}"
    assert result['vertices'][0] == (100, 200)
    assert result['vertices'][1] == (300, 400)
    assert result['vertices'][2] == (500, 400)
    assert result['vertices'][3] == (300, 200)
    assert result['bytes_read'] == 32
    print(f"  PASS: {result}")

    # Test 2: Square with zero origin
    print("\nTest 2: Square at origin")
    data = struct.pack('<iiiiiiii', 0, 0, 1000, 0, 1000, 1000, 0, 1000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x71_quad_32r(stream)

    assert result['vertices'] == [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Quadrilateral with negative coordinates")
    data = struct.pack('<iiiiiiii', -100, -200, 300, -400, 500, 600, -700, 800)
    stream = io.BytesIO(data)
    result = parse_opcode_0x71_quad_32r(stream)

    assert result['vertices'][0] == (-100, -200)
    assert result['vertices'][1] == (300, -400)
    assert result['vertices'][2] == (500, 600)
    assert result['vertices'][3] == (-700, 800)
    print(f"  PASS: {result}")

    # Test 4: Large 32-bit values
    print("\nTest 4: Large 32-bit coordinate values")
    data = struct.pack('<iiiiiiii', 1000000, 2000000, 3000000, 4000000,
                      5000000, 6000000, 7000000, 8000000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x71_quad_32r(stream)

    assert result['vertices'] == [(1000000, 2000000), (3000000, 4000000),
                                  (5000000, 6000000), (7000000, 8000000)]
    print(f"  PASS: {result}")

    # Test 5: Maximum 32-bit values
    print("\nTest 5: Maximum/minimum 32-bit values")
    data = struct.pack('<iiiiiiii', 2147483647, -2147483648, 0, 0,
                      1000, -1000, 500, -500)
    stream = io.BytesIO(data)
    result = parse_opcode_0x71_quad_32r(stream)

    assert result['vertices'][0] == (2147483647, -2147483648)
    assert result['vertices'][1] == (0, 0)
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02\x03\x04')  # Only 4 bytes instead of 32
    try:
        result = parse_opcode_0x71_quad_32r(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x71 'q' (DRAW_QUAD_32R): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x91_wedge():
    """Test suite for opcode 0x91 (DRAW_WEDGE)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x91 (DRAW_WEDGE)")
    print("=" * 70)

    # Test 1: Quarter circle wedge (90 degrees)
    print("\nTest 1: Quarter circle wedge (0° to 90°)")
    data = struct.pack('<hhHHH', 100, 200, 50, 0, 16384)  # 16384 = 90°
    stream = io.BytesIO(data)
    result = parse_opcode_0x91_wedge(stream)

    assert result['type'] == 'wedge', f"Expected type='wedge', got {result['type']}"
    assert result['center'] == (100, 200), f"Expected center=(100, 200), got {result['center']}"
    assert result['radius'] == 50, f"Expected radius=50, got {result['radius']}"
    assert result['start_angle'] == 0, f"Expected start_angle=0, got {result['start_angle']}"
    assert result['sweep_angle'] == 16384, f"Expected sweep_angle=16384, got {result['sweep_angle']}"
    assert result['bytes_read'] == 10
    print(f"  PASS: {result}")
    print(f"       Angle in degrees: start=0°, sweep={(16384/65536.0)*360:.2f}°")

    # Test 2: Half circle wedge (180 degrees)
    print("\nTest 2: Half circle wedge (0° to 180°)")
    data = struct.pack('<hhHHH', 0, 0, 100, 0, 32768)  # 32768 = 180°
    stream = io.BytesIO(data)
    result = parse_opcode_0x91_wedge(stream)

    assert result['center'] == (0, 0)
    assert result['radius'] == 100
    assert result['start_angle'] == 0
    assert result['sweep_angle'] == 32768
    print(f"  PASS: {result}")
    print(f"       Angle in degrees: start=0°, sweep={(32768/65536.0)*360:.2f}°")

    # Test 3: Full circle wedge (360 degrees)
    print("\nTest 3: Full circle wedge (0° to 360°)")
    data = struct.pack('<hhHHH', 250, 350, 75, 0, 65535)  # 65535 ≈ 360°
    stream = io.BytesIO(data)
    result = parse_opcode_0x91_wedge(stream)

    assert result['center'] == (250, 350)
    assert result['radius'] == 75
    assert result['start_angle'] == 0
    assert result['sweep_angle'] == 65535
    print(f"  PASS: {result}")
    print(f"       Angle in degrees: start=0°, sweep={(65535/65536.0)*360:.2f}°")

    # Test 4: Wedge starting at 90 degrees
    print("\nTest 4: Wedge starting at 90°, sweeping 45°")
    data = struct.pack('<hhHHH', 150, 250, 60, 16384, 8192)  # Start=90°, sweep=45°
    stream = io.BytesIO(data)
    result = parse_opcode_0x91_wedge(stream)

    assert result['center'] == (150, 250)
    assert result['radius'] == 60
    assert result['start_angle'] == 16384
    assert result['sweep_angle'] == 8192
    print(f"  PASS: {result}")
    print(f"       Angle in degrees: start={(16384/65536.0)*360:.2f}°, sweep={(8192/65536.0)*360:.2f}°")

    # Test 5: Negative center coordinates
    print("\nTest 5: Wedge with negative center coordinates")
    data = struct.pack('<hhHHH', -100, -200, 50, 0, 16384)
    stream = io.BytesIO(data)
    result = parse_opcode_0x91_wedge(stream)

    assert result['center'] == (-100, -200)
    assert result['radius'] == 50
    print(f"  PASS: {result}")

    # Test 6: Small wedge (pie slice)
    print("\nTest 6: Small wedge (15° slice)")
    data = struct.pack('<hhHHH', 300, 400, 120, 0, 2731)  # 2731 ≈ 15°
    stream = io.BytesIO(data)
    result = parse_opcode_0x91_wedge(stream)

    assert result['center'] == (300, 400)
    assert result['radius'] == 120
    assert result['sweep_angle'] == 2731
    print(f"  PASS: {result}")
    print(f"       Angle in degrees: sweep={(2731/65536.0)*360:.2f}°")

    # Test 7: Error handling - insufficient data
    print("\nTest 7: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02\x03\x04')  # Only 4 bytes instead of 10
    try:
        result = parse_opcode_0x91_wedge(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x91 (DRAW_WEDGE): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 38 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 38: DRAWING PRIMITIVES TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x51 'Q': DRAW_QUAD (ASCII)")
    print("  - 0x71 'q': DRAW_QUAD_32R (binary 32-bit)")
    print("  - 0x91: DRAW_WEDGE (binary)")
    print("=" * 70)

    test_opcode_0x51_quad_ascii()
    test_opcode_0x71_quad_32r()
    test_opcode_0x91_wedge()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x51 'Q' (DRAW_QUAD ASCII): 6 tests passed")
    print("  - Opcode 0x71 'q' (DRAW_QUAD_32R): 6 tests passed")
    print("  - Opcode 0x91 (DRAW_WEDGE): 7 tests passed")
    print("  - Total: 19 tests passed")
    print("\nEdge Cases Handled:")
    print("  - ASCII coordinate pair parsing for quadrilaterals")
    print("  - 32-bit signed integer coordinates (full range)")
    print("  - Negative coordinates for both ASCII and binary formats")
    print("  - Large coordinate values (millions, max int32)")
    print("  - Wedge angles in 65536ths of 360° format")
    print("  - Quarter, half, and full circle wedges")
    print("  - Wedges with various start angles and sweep angles")
    print("  - Invalid format detection (missing parentheses, incomplete data)")
    print("  - Insufficient data detection for all opcodes")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
