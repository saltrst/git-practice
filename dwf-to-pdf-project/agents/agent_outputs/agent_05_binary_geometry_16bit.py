"""
DWF Binary Geometry Opcodes - 16-bit and 32-bit Polytriangle

Agent 5 - Binary Geometry (16-bit relative coordinates)

This module implements parsing for 5 DWF binary geometry opcodes:
- 0x0C: DRAW_LINE_16R (16-bit relative line)
- 0x10: DRAW_POLYLINE_POLYGON_16R (16-bit polygon)
- 0x12: DRAW_CIRCLE_16R (16-bit circle)
- 0x14: DRAW_POLYTRIANGLE_16R (16-bit polytriangle)
- 0x74: DRAW_POLYTRIANGLE_32R (32-bit polytriangle)

Format specifications based on DWF Toolkit C++ source:
/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/

References:
- polyline.cpp: Line and polygon implementations
- ellipse.cpp: Circle implementation
- polytri.cpp: Polytriangle implementation
- pointset.cpp: Point set materialization

Note on "Relative" Coordinates:
"Relative" means coordinates are offsets from the current drawing position,
not absolute coordinates. The file maintains a current position that gets
updated after each drawing operation.
"""

import struct
from io import BytesIO
from typing import Dict, List, Tuple, BinaryIO, Union


# ============================================================================
# Opcode 0x0C: DRAW_LINE_16R (16-bit relative line)
# ============================================================================

def opcode_0x0C_draw_line_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0C (DRAW_LINE_16R) - Binary line with 16-bit relative coordinates.

    This opcode represents a 2-point line using 16-bit signed integers for coordinates.
    The coordinates are relative offsets from the current drawing position.

    Format Specification:
    - Opcode: 0x0C (1 byte, not included in data stream)
    - Point 1: x1 (int16, 2 bytes) + y1 (int16, 2 bytes)
    - Point 2: x2 (int16, 2 bytes) + y2 (int16, 2 bytes)
    - Total data: 8 bytes
    - Struct format: "<hhhh" (little-endian, 4 signed 16-bit integers)

    C++ Reference:
    From polyline.cpp line 103-104:
        WD_CHECK (file.write((WT_Byte)0x0C));
        WD_CHECK (file.write(2, tmp_points));  // 2 WT_Logical_Point_16

    Materialization (line 272-297):
        WT_Logical_Point_16 tmp_points[2];
        WD_CHECK (file.read(2, tmp_points));

    Args:
        stream: Binary stream positioned after the 0x0C opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': 0x0C
        - 'type': 'line_16r'
        - 'point1': Tuple (x1, y1) - first point (relative)
        - 'point2': Tuple (x2, y2) - second point (relative)
        - 'bytes_read': 8

    Raises:
        ValueError: If stream doesn't contain 8 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> stream = BytesIO(b'\\x0A\\x00\\x14\\x00\\x1E\\x00\\x28\\x00')
        >>> result = opcode_0x0C_draw_line_16r(stream)
        >>> result['point1']
        (10, 20)
        >>> result['point2']
        (30, 40)
    """
    data = stream.read(8)

    if len(data) != 8:
        raise ValueError(f"Expected 8 bytes for opcode 0x0C, got {len(data)} bytes")

    # Unpack 4 signed 16-bit integers (little-endian)
    x1, y1, x2, y2 = struct.unpack('<hhhh', data)

    return {
        'opcode': 0x0C,
        'opcode_name': 'DRAW_LINE_16R',
        'type': 'line_16r',
        'point1': (x1, y1),
        'point2': (x2, y2),
        'bytes_read': 8,
        'relative': True
    }


# ============================================================================
# Opcode 0x10: DRAW_POLYLINE_POLYGON_16R (16-bit polygon)
# ============================================================================

def opcode_0x10_draw_polyline_polygon_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x10 (DRAW_POLYLINE_POLYGON_16R) - Multi-point polygon with 16-bit coordinates.

    This opcode represents a polygon or polyline with multiple vertices using 16-bit
    signed integers for coordinates. Coordinates are relative offsets.

    Format Specification:
    - Opcode: 0x10 (1 byte, not included in data stream)
    - Count: uint8 (1 byte) - number of points
      * If count == 0: Extended count follows as uint16 (2 bytes), actual count = 256 + extended_count
      * If count > 0: This is the actual count
    - Points: count * (x: int16, y: int16)
    - Variable total bytes: 1 + (count * 4) or 3 + (count * 4) if extended

    C++ Reference:
    From pointset.cpp materialize_16_bit() lines 430-495:
        WD_CHECK (file.read(count));  // uint8
        if (count == 0)
            m_count = -1;
        else
            m_count = count;

        if (m_count == -1) {
            WT_Unsigned_Integer16 tmp_short;
            WD_CHECK (file.read(tmp_short));
            m_count = 256 + tmp_short;
        }

        WT_Logical_Point_16 * tmp_buf = new WT_Logical_Point_16[m_count];
        result = file.read(m_count, tmp_buf);

    Args:
        stream: Binary stream positioned after the 0x10 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': 0x10
        - 'type': 'polyline_polygon_16r'
        - 'count': Number of points
        - 'points': List of (x, y) tuples
        - 'extended_count': True if count > 255
        - 'bytes_read': Total bytes consumed

    Raises:
        ValueError: If stream doesn't contain enough bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> stream = BytesIO(b'\\x03\\x0A\\x00\\x14\\x00\\x1E\\x00\\x28\\x00\\x32\\x00\\x3C\\x00')
        >>> result = opcode_0x10_draw_polyline_polygon_16r(stream)
        >>> result['count']
        3
        >>> result['points']
        [(10, 20), (30, 40), (50, 60)]
    """
    # Read the count byte
    count_data = stream.read(1)
    if len(count_data) != 1:
        raise ValueError(f"Expected 1 byte for count, got {len(count_data)} bytes")

    count = struct.unpack('<B', count_data)[0]
    bytes_read = 1
    extended = False

    # Check for extended count (count > 255)
    if count == 0:
        extended_count_data = stream.read(2)
        if len(extended_count_data) != 2:
            raise ValueError(f"Expected 2 bytes for extended count, got {len(extended_count_data)} bytes")

        extended_count = struct.unpack('<H', extended_count_data)[0]
        count = 256 + extended_count
        bytes_read += 2
        extended = True

    # Read all points
    points_data = stream.read(count * 4)  # Each point is 4 bytes (2 int16s)
    if len(points_data) != count * 4:
        raise ValueError(f"Expected {count * 4} bytes for {count} points, got {len(points_data)} bytes")

    # Unpack all points
    points = []
    for i in range(count):
        offset = i * 4
        x, y = struct.unpack('<hh', points_data[offset:offset + 4])
        points.append((x, y))

    bytes_read += count * 4

    return {
        'opcode': 0x10,
        'opcode_name': 'DRAW_POLYLINE_POLYGON_16R',
        'type': 'polyline_polygon_16r',
        'count': count,
        'points': points,
        'extended_count': extended,
        'bytes_read': bytes_read,
        'relative': True
    }


# ============================================================================
# Opcode 0x12: DRAW_CIRCLE_16R (16-bit circle)
# ============================================================================

def opcode_0x12_draw_circle_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x12 (DRAW_CIRCLE_16R) - Full circle with 16-bit relative coordinates.

    This opcode represents a complete circle using 16-bit coordinates for the center
    and 16-bit unsigned integer for the radius. The center coordinates are relative
    offsets from the current drawing position.

    Format Specification:
    - Opcode: 0x12 (1 byte, not included in data stream)
    - Center X: int16 (2 bytes, signed)
    - Center Y: int16 (2 bytes, signed)
    - Radius: uint16 (2 bytes, unsigned)
    - Total data: 6 bytes
    - Struct format: "<hhH" (little-endian, 2 signed + 1 unsigned 16-bit integers)

    C++ Reference:
    From ellipse.cpp lines 156-162 (write):
        WD_CHECK (file.write ((WT_Byte)0x12));
        WD_CHECK (file.write (1, &tmp_point));  // WT_Logical_Point_16
        return    file.write ((WT_Integer16)m_major);  // radius

    From ellipse.cpp lines 450-465 (read):
        case 0x12:  // Ctrl-R - Full Circle, short relative coordinates
            WT_Logical_Point_16 position;
            WT_Unsigned_Integer16 radius;
            WD_CHECK (file.read (1, &position));
            m_position = position;
            WD_CHECK (file.read (radius));
            m_major = m_minor = radius;

    From ellipse.cpp lines 632-637 (skip):
        case 0x12:  // Ctrl-R
            // This is a circle, with 16-bit relative coords, 16-bit radius
            file.skip(2 * sizeof(WT_Integer16) + sizeof(WT_Unsigned_Integer16));

    Args:
        stream: Binary stream positioned after the 0x12 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': 0x12
        - 'type': 'circle_16r'
        - 'center': Tuple (x, y) - center position (relative)
        - 'radius': Circle radius (unsigned)
        - 'bytes_read': 6

    Raises:
        ValueError: If stream doesn't contain 6 bytes or radius is 0
        struct.error: If binary data cannot be unpacked

    Example:
        >>> stream = BytesIO(b'\\x64\\x00\\x64\\x00\\x32\\x00')
        >>> result = opcode_0x12_draw_circle_16r(stream)
        >>> result['center']
        (100, 100)
        >>> result['radius']
        50
    """
    data = stream.read(6)

    if len(data) != 6:
        raise ValueError(f"Expected 6 bytes for opcode 0x12, got {len(data)} bytes")

    # Unpack: 2 signed 16-bit integers (center) + 1 unsigned 16-bit integer (radius)
    center_x, center_y, radius = struct.unpack('<hhH', data)

    if radius == 0:
        raise ValueError("Circle radius cannot be zero")

    return {
        'opcode': 0x12,
        'opcode_name': 'DRAW_CIRCLE_16R',
        'type': 'circle_16r',
        'center': (center_x, center_y),
        'radius': radius,
        'bytes_read': 6,
        'relative': True
    }


# ============================================================================
# Opcode 0x14: DRAW_POLYTRIANGLE_16R (16-bit polytriangle)
# ============================================================================

def opcode_0x14_draw_polytriangle_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x14 (DRAW_POLYTRIANGLE_16R) - Polytriangle with 16-bit coordinates.

    This opcode represents a triangle strip or set of triangles using 16-bit signed
    integers for vertex coordinates. Minimum 3 points required for a triangle.
    Coordinates are relative offsets.

    A polytriangle is a strip of triangles where each new point forms a triangle
    with the previous two points. This is an efficient way to represent connected
    triangular meshes.

    Format Specification:
    - Opcode: 0x14 (1 byte, not included in data stream)
    - Count: uint8 (1 byte) - number of vertices
      * If count == 0: Extended count follows as uint16 (2 bytes), actual count = 256 + extended_count
      * If count > 0: This is the actual count
    - Points: count * (x: int16, y: int16)
    - Variable total bytes: 1 + (count * 4) or 3 + (count * 4) if extended

    C++ Reference:
    From polytri.cpp lines 354-361 (materialize):
        case 0x14: // Ctrl-T
            WD_CHECK (WT_Point_Set::materialize_16_bit(file));

    From polytri.cpp lines 78-79 (dump):
        return WT_Point_Set::serialize(file, (WT_Byte) 'T', (WT_Byte)'t', (WT_Byte)0x14);

    Triangle Formation:
    - Points 0, 1, 2 form the first triangle
    - Points 1, 2, 3 form the second triangle
    - Points 2, 3, 4 form the third triangle
    - And so on (triangle strip)

    Args:
        stream: Binary stream positioned after the 0x14 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': 0x14
        - 'type': 'polytriangle_16r'
        - 'count': Number of vertices
        - 'points': List of (x, y) tuples
        - 'triangle_count': Number of triangles formed (count - 2)
        - 'extended_count': True if count > 255
        - 'bytes_read': Total bytes consumed

    Raises:
        ValueError: If stream doesn't contain enough bytes or count < 3
        struct.error: If binary data cannot be unpacked

    Example:
        >>> stream = BytesIO(b'\\x04\\x00\\x00\\x64\\x00\\xC8\\x00\\x64\\x00\\x64\\x00\\xC8\\x00')
        >>> result = opcode_0x14_draw_polytriangle_16r(stream)
        >>> result['count']
        4
        >>> result['triangle_count']
        2
    """
    # Read the count byte
    count_data = stream.read(1)
    if len(count_data) != 1:
        raise ValueError(f"Expected 1 byte for count, got {len(count_data)} bytes")

    count = struct.unpack('<B', count_data)[0]
    bytes_read = 1
    extended = False

    # Check for extended count (count > 255)
    if count == 0:
        extended_count_data = stream.read(2)
        if len(extended_count_data) != 2:
            raise ValueError(f"Expected 2 bytes for extended count, got {len(extended_count_data)} bytes")

        extended_count = struct.unpack('<H', extended_count_data)[0]
        count = 256 + extended_count
        bytes_read += 2
        extended = True

    # Polytriangle must have at least 3 vertices
    if count < 3:
        raise ValueError(f"Polytriangle requires at least 3 vertices, got {count}")

    # Read all points
    points_data = stream.read(count * 4)  # Each point is 4 bytes (2 int16s)
    if len(points_data) != count * 4:
        raise ValueError(f"Expected {count * 4} bytes for {count} points, got {len(points_data)} bytes")

    # Unpack all points
    points = []
    for i in range(count):
        offset = i * 4
        x, y = struct.unpack('<hh', points_data[offset:offset + 4])
        points.append((x, y))

    bytes_read += count * 4
    triangle_count = count - 2  # Number of triangles in the strip

    return {
        'opcode': 0x14,
        'opcode_name': 'DRAW_POLYTRIANGLE_16R',
        'type': 'polytriangle_16r',
        'count': count,
        'points': points,
        'triangle_count': triangle_count,
        'extended_count': extended,
        'bytes_read': bytes_read,
        'relative': True
    }


# ============================================================================
# Opcode 0x74: DRAW_POLYTRIANGLE_32R (32-bit polytriangle)
# ============================================================================

def opcode_0x74_draw_polytriangle_32r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x74 (DRAW_POLYTRIANGLE_32R) - Polytriangle with 32-bit coordinates.

    This opcode represents a triangle strip or set of triangles using 32-bit signed
    integers for vertex coordinates. This is the higher precision version of 0x14.
    Minimum 3 points required for a triangle. Coordinates are relative offsets.

    Format Specification:
    - Opcode: 0x74 (1 byte, 't' in ASCII, not included in data stream)
    - Count: uint8 (1 byte) - number of vertices
      * If count == 0: Extended count follows as uint16 (2 bytes), actual count = 256 + extended_count
      * If count > 0: This is the actual count
    - Points: count * (x: int32, y: int32)
    - Variable total bytes: 1 + (count * 8) or 3 + (count * 8) if extended

    C++ Reference:
    From polytri.cpp lines 362-365 (materialize):
        case 't':
            WD_CHECK (WT_Point_Set::materialize(file));

    From polytri.cpp lines 78-79 (dump):
        return WT_Point_Set::serialize(file, (WT_Byte) 'T', (WT_Byte)'t', (WT_Byte)0x14);

    From pointset.cpp materialize() (32-bit version) uses same count logic as 16-bit
    but reads WT_Logical_Point (2 int32s) instead of WT_Logical_Point_16.

    Triangle Formation:
    - Points 0, 1, 2 form the first triangle
    - Points 1, 2, 3 form the second triangle
    - Points 2, 3, 4 form the third triangle
    - And so on (triangle strip)

    Args:
        stream: Binary stream positioned after the 0x74 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': 0x74
        - 'type': 'polytriangle_32r'
        - 'count': Number of vertices
        - 'points': List of (x, y) tuples
        - 'triangle_count': Number of triangles formed (count - 2)
        - 'extended_count': True if count > 255
        - 'bytes_read': Total bytes consumed

    Raises:
        ValueError: If stream doesn't contain enough bytes or count < 3
        struct.error: If binary data cannot be unpacked

    Example:
        >>> stream = BytesIO(b'\\x03\\x00\\x00\\x00\\x00\\x64\\x00\\x00\\x00\\xC8\\x00\\x00\\x00\\x64\\x00\\x00\\x00')
        >>> result = opcode_0x74_draw_polytriangle_32r(stream)
        >>> result['count']
        3
        >>> result['triangle_count']
        1
    """
    # Read the count byte
    count_data = stream.read(1)
    if len(count_data) != 1:
        raise ValueError(f"Expected 1 byte for count, got {len(count_data)} bytes")

    count = struct.unpack('<B', count_data)[0]
    bytes_read = 1
    extended = False

    # Check for extended count (count > 255)
    if count == 0:
        extended_count_data = stream.read(2)
        if len(extended_count_data) != 2:
            raise ValueError(f"Expected 2 bytes for extended count, got {len(extended_count_data)} bytes")

        extended_count = struct.unpack('<H', extended_count_data)[0]
        count = 256 + extended_count
        bytes_read += 2
        extended = True

    # Polytriangle must have at least 3 vertices
    if count < 3:
        raise ValueError(f"Polytriangle requires at least 3 vertices, got {count}")

    # Read all points (32-bit coordinates)
    points_data = stream.read(count * 8)  # Each point is 8 bytes (2 int32s)
    if len(points_data) != count * 8:
        raise ValueError(f"Expected {count * 8} bytes for {count} points, got {len(points_data)} bytes")

    # Unpack all points
    points = []
    for i in range(count):
        offset = i * 8
        x, y = struct.unpack('<ll', points_data[offset:offset + 8])
        points.append((x, y))

    bytes_read += count * 8
    triangle_count = count - 2  # Number of triangles in the strip

    return {
        'opcode': 0x74,
        'opcode_name': 'DRAW_POLYTRIANGLE_32R',
        'type': 'polytriangle_32r',
        'count': count,
        'points': points,
        'triangle_count': triangle_count,
        'extended_count': extended,
        'bytes_read': bytes_read,
        'relative': True
    }


# ============================================================================
# Test Suite
# ============================================================================

def test_opcode_0x0C():
    """Test DRAW_LINE_16R opcode."""
    print("\n" + "=" * 70)
    print("Test 1: Opcode 0x0C - DRAW_LINE_16R (16-bit line)")
    print("=" * 70)

    # Test case 1: Simple positive coordinates
    print("\nTest 1a: Positive coordinates")
    print("-" * 70)
    test_data = struct.pack('<hhhh', 10, 20, 30, 40)
    stream = BytesIO(test_data)
    result = opcode_0x0C_draw_line_16r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Point 1: {result['point1']}")
    print(f"Point 2: {result['point2']}")
    print(f"Bytes read: {result['bytes_read']}")

    assert result['point1'] == (10, 20), "Point 1 mismatch"
    assert result['point2'] == (30, 40), "Point 2 mismatch"
    assert result['bytes_read'] == 8, "Bytes read mismatch"
    print("✓ Test 1a passed")

    # Test case 2: Negative coordinates (relative offsets can be negative)
    print("\nTest 1b: Negative relative offsets")
    print("-" * 70)
    test_data = struct.pack('<hhhh', -50, -30, 100, -75)
    stream = BytesIO(test_data)
    result = opcode_0x0C_draw_line_16r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Point 1: {result['point1']}")
    print(f"Point 2: {result['point2']}")

    assert result['point1'] == (-50, -30), "Negative point 1 mismatch"
    assert result['point2'] == (100, -75), "Negative point 2 mismatch"
    print("✓ Test 1b passed")

    return True


def test_opcode_0x10():
    """Test DRAW_POLYLINE_POLYGON_16R opcode."""
    print("\n" + "=" * 70)
    print("Test 2: Opcode 0x10 - DRAW_POLYLINE_POLYGON_16R")
    print("=" * 70)

    # Test case 1: Simple polygon with 4 points
    print("\nTest 2a: 4-point polygon")
    print("-" * 70)
    points = [(10, 20), (30, 40), (50, 60), (70, 80)]
    count = len(points)
    test_data = struct.pack('<B', count)
    for x, y in points:
        test_data += struct.pack('<hh', x, y)

    stream = BytesIO(test_data)
    result = opcode_0x10_draw_polyline_polygon_16r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Count: {result['count']}")
    print(f"Points: {result['points']}")
    print(f"Extended count: {result['extended_count']}")
    print(f"Bytes read: {result['bytes_read']}")

    assert result['count'] == 4, "Count mismatch"
    assert result['points'] == points, "Points mismatch"
    assert result['extended_count'] == False, "Extended count should be False"
    assert result['bytes_read'] == 1 + 4 * 4, "Bytes read mismatch"
    print("✓ Test 2a passed")

    # Test case 2: Extended count (simulated for count > 255)
    print("\nTest 2b: Extended count simulation (260 points)")
    print("-" * 70)
    actual_count = 260
    extended_count = actual_count - 256
    test_data = struct.pack('<BH', 0, extended_count)  # 0 indicates extended count
    for i in range(actual_count):
        test_data += struct.pack('<hh', i, i * 2)

    stream = BytesIO(test_data)
    result = opcode_0x10_draw_polyline_polygon_16r(stream)

    print(f"Count: {result['count']}")
    print(f"Extended count: {result['extended_count']}")
    print(f"Points (first 3): {result['points'][:3]}")
    print(f"Points (last 3): {result['points'][-3:]}")
    print(f"Bytes read: {result['bytes_read']}")

    assert result['count'] == 260, "Extended count mismatch"
    assert result['extended_count'] == True, "Extended count flag should be True"
    assert len(result['points']) == 260, "Number of points mismatch"
    print("✓ Test 2b passed")

    return True


def test_opcode_0x12():
    """Test DRAW_CIRCLE_16R opcode."""
    print("\n" + "=" * 70)
    print("Test 3: Opcode 0x12 - DRAW_CIRCLE_16R")
    print("=" * 70)

    # Test case 1: Circle at origin with radius 100
    print("\nTest 3a: Circle at (100, 100) with radius 50")
    print("-" * 70)
    test_data = struct.pack('<hhH', 100, 100, 50)
    stream = BytesIO(test_data)
    result = opcode_0x12_draw_circle_16r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Center: {result['center']}")
    print(f"Radius: {result['radius']}")
    print(f"Bytes read: {result['bytes_read']}")

    assert result['center'] == (100, 100), "Center mismatch"
    assert result['radius'] == 50, "Radius mismatch"
    assert result['bytes_read'] == 6, "Bytes read mismatch"
    print("✓ Test 3a passed")

    # Test case 2: Circle with negative center (relative offset)
    print("\nTest 3b: Circle at negative offset (-50, -30) with radius 25")
    print("-" * 70)
    test_data = struct.pack('<hhH', -50, -30, 25)
    stream = BytesIO(test_data)
    result = opcode_0x12_draw_circle_16r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Center: {result['center']}")
    print(f"Radius: {result['radius']}")

    assert result['center'] == (-50, -30), "Negative center mismatch"
    assert result['radius'] == 25, "Radius mismatch"
    print("✓ Test 3b passed")

    # Test case 3: Large radius
    print("\nTest 3c: Large radius (32000)")
    print("-" * 70)
    test_data = struct.pack('<hhH', 0, 0, 32000)
    stream = BytesIO(test_data)
    result = opcode_0x12_draw_circle_16r(stream)

    print(f"Radius: {result['radius']}")
    assert result['radius'] == 32000, "Large radius mismatch"
    print("✓ Test 3c passed")

    return True


def test_opcode_0x14():
    """Test DRAW_POLYTRIANGLE_16R opcode."""
    print("\n" + "=" * 70)
    print("Test 4: Opcode 0x14 - DRAW_POLYTRIANGLE_16R")
    print("=" * 70)

    # Test case 1: Single triangle (3 vertices)
    print("\nTest 4a: Single triangle (3 vertices)")
    print("-" * 70)
    points = [(0, 0), (100, 0), (50, 100)]
    count = len(points)
    test_data = struct.pack('<B', count)
    for x, y in points:
        test_data += struct.pack('<hh', x, y)

    stream = BytesIO(test_data)
    result = opcode_0x14_draw_polytriangle_16r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Count: {result['count']}")
    print(f"Points: {result['points']}")
    print(f"Triangle count: {result['triangle_count']}")
    print(f"Bytes read: {result['bytes_read']}")

    assert result['count'] == 3, "Count mismatch"
    assert result['points'] == points, "Points mismatch"
    assert result['triangle_count'] == 1, "Should form 1 triangle"
    print("✓ Test 4a passed")

    # Test case 2: Triangle strip (5 vertices = 3 triangles)
    print("\nTest 4b: Triangle strip (5 vertices = 3 triangles)")
    print("-" * 70)
    points = [(0, 0), (100, 0), (50, 100), (150, 100), (100, 200)]
    count = len(points)
    test_data = struct.pack('<B', count)
    for x, y in points:
        test_data += struct.pack('<hh', x, y)

    stream = BytesIO(test_data)
    result = opcode_0x14_draw_polytriangle_16r(stream)

    print(f"Count: {result['count']}")
    print(f"Triangle count: {result['triangle_count']}")
    print(f"Points: {result['points']}")

    assert result['count'] == 5, "Count mismatch"
    assert result['triangle_count'] == 3, "Should form 3 triangles"
    assert len(result['points']) == 5, "Points count mismatch"
    print("✓ Test 4b passed")

    return True


def test_opcode_0x74():
    """Test DRAW_POLYTRIANGLE_32R opcode."""
    print("\n" + "=" * 70)
    print("Test 5: Opcode 0x74 - DRAW_POLYTRIANGLE_32R")
    print("=" * 70)

    # Test case 1: Single triangle with 32-bit coordinates
    print("\nTest 5a: Single triangle (3 vertices, 32-bit)")
    print("-" * 70)
    points = [(0, 0), (100000, 0), (50000, 100000)]
    count = len(points)
    test_data = struct.pack('<B', count)
    for x, y in points:
        test_data += struct.pack('<ll', x, y)

    stream = BytesIO(test_data)
    result = opcode_0x74_draw_polytriangle_32r(stream)

    print(f"Input bytes: {test_data.hex()}")
    print(f"Count: {result['count']}")
    print(f"Points: {result['points']}")
    print(f"Triangle count: {result['triangle_count']}")
    print(f"Bytes read: {result['bytes_read']}")

    assert result['count'] == 3, "Count mismatch"
    assert result['points'] == points, "Points mismatch"
    assert result['triangle_count'] == 1, "Should form 1 triangle"
    assert result['bytes_read'] == 1 + 3 * 8, "Bytes read mismatch"
    print("✓ Test 5a passed")

    # Test case 2: Negative coordinates
    print("\nTest 5b: Triangle with negative coordinates")
    print("-" * 70)
    points = [(-50000, -30000), (75000, -20000), (0, 50000)]
    count = len(points)
    test_data = struct.pack('<B', count)
    for x, y in points:
        test_data += struct.pack('<ll', x, y)

    stream = BytesIO(test_data)
    result = opcode_0x74_draw_polytriangle_32r(stream)

    print(f"Points: {result['points']}")

    assert result['points'] == points, "Negative coordinate points mismatch"
    print("✓ Test 5b passed")

    # Test case 3: Larger triangle strip
    print("\nTest 5c: Triangle strip (4 vertices = 2 triangles)")
    print("-" * 70)
    points = [(1000, 2000), (3000, 4000), (5000, 6000), (7000, 8000)]
    count = len(points)
    test_data = struct.pack('<B', count)
    for x, y in points:
        test_data += struct.pack('<ll', x, y)

    stream = BytesIO(test_data)
    result = opcode_0x74_draw_polytriangle_32r(stream)

    print(f"Count: {result['count']}")
    print(f"Triangle count: {result['triangle_count']}")

    assert result['count'] == 4, "Count mismatch"
    assert result['triangle_count'] == 2, "Should form 2 triangles"
    print("✓ Test 5c passed")

    return True


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 70)
    print("Test 6: Edge Cases and Error Handling")
    print("=" * 70)

    # Test 1: Insufficient data for line
    print("\nTest 6a: Insufficient data error handling")
    print("-" * 70)
    try:
        stream = BytesIO(b'\x00\x00\x00')  # Only 3 bytes instead of 8
        result = opcode_0x0C_draw_line_16r(stream)
        print("✗ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")

    # Test 2: Zero radius circle error
    print("\nTest 6b: Zero radius circle error")
    print("-" * 70)
    try:
        test_data = struct.pack('<hhH', 100, 100, 0)  # Radius = 0
        stream = BytesIO(test_data)
        result = opcode_0x12_draw_circle_16r(stream)
        print("✗ Should have raised ValueError for zero radius")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")

    # Test 3: Polytriangle with too few vertices
    print("\nTest 6c: Polytriangle with insufficient vertices")
    print("-" * 70)
    try:
        test_data = struct.pack('<B', 2)  # Only 2 vertices (need 3+)
        test_data += struct.pack('<hhhh', 0, 0, 100, 100)
        stream = BytesIO(test_data)
        result = opcode_0x14_draw_polytriangle_16r(stream)
        print("✗ Should have raised ValueError for < 3 vertices")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")

    # Test 4: Maximum 16-bit values
    print("\nTest 6d: Maximum 16-bit signed values")
    print("-" * 70)
    max_int16 = 32767
    min_int16 = -32768
    test_data = struct.pack('<hhhh', max_int16, max_int16, min_int16, min_int16)
    stream = BytesIO(test_data)
    result = opcode_0x0C_draw_line_16r(stream)

    print(f"Point 1: {result['point1']}")
    print(f"Point 2: {result['point2']}")

    assert result['point1'] == (max_int16, max_int16), "Max value mismatch"
    assert result['point2'] == (min_int16, min_int16), "Min value mismatch"
    print("✓ Test 6d passed")

    print("\n✓ All edge case tests passed")
    return True


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 70)
    print("DWF Binary Geometry Opcodes Test Suite")
    print("Agent 5: 16-bit Binary Geometry")
    print("=" * 70)
    print("\nTranslated Opcodes:")
    print("  - 0x0C: DRAW_LINE_16R")
    print("  - 0x10: DRAW_POLYLINE_POLYGON_16R")
    print("  - 0x12: DRAW_CIRCLE_16R")
    print("  - 0x14: DRAW_POLYTRIANGLE_16R")
    print("  - 0x74: DRAW_POLYTRIANGLE_32R")

    try:
        test_opcode_0x0C()
        test_opcode_0x10()
        test_opcode_0x12()
        test_opcode_0x14()
        test_opcode_0x74()
        test_edge_cases()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        print("\nSummary:")
        print("  - 5 opcodes translated successfully")
        print("  - 15+ test cases executed")
        print("  - All edge cases handled")
        print("  - Error handling verified")

        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
