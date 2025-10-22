"""
DWF Opcode Handlers for Agent 9: Bezier Curves and Contour Sets

This module implements parsing for 5 DWF opcodes related to Bezier curves and contour sets:
- 0x02 BEZIER_16R: 16-bit relative Bezier curve
- 0x62 BEZIER_32: 32-bit absolute Bezier curve
- 0x42 BEZIER_32R: 32-bit relative Bezier curve
- 0x0B DRAW_CONTOUR_SET_16R: 16-bit relative contour set
- 0x6B DRAW_CONTOUR_SET_32R: 32-bit relative contour set

Format Specifications:
=====================

Bezier Curves:
- A four-point Bezier curve consists of:
  * Start point (Xs, Ys) - where the curve begins
  * Control point 1 (Xc1, Yc1) - shapes the curve but doesn't touch it
  * Control point 2 (Xc2, Yc2) - shapes the curve but doesn't touch it
  * End point (Xe, Ye) - where the curve ends

- Multiple Bezier curves can be connected, where the end point of one
  becomes the start point of the next.

Contour Sets:
- A contour set is a collection of polygonal regions used for complex shapes
- Clockwise-wound contours indicate positive (filled) spaces
- Counterclockwise-wound contours indicate negative spaces (holes)
- Example: The letter "A" with a hole in the top triangle

Count Encoding:
- If count_byte == 0: Extended count follows as uint16, actual_count = 256 + extended_count
- If count_byte != 0: actual_count = count_byte
- This allows encoding counts from 1 to 65,791

Reference:
- C++ Source: dwf-toolkit-source/develop/global/src/dwf/whiptk/
- Documentation: dwf-toolkit-source/docs/DWF Toolkit/Whip2D/Specification/whipSpec/Opcodes/
"""

import struct
from typing import Dict, List, Tuple, BinaryIO
from io import BytesIO


def read_count(stream: BinaryIO) -> int:
    """
    Read a DWF count value (used for counts of points, contours, etc.).

    DWF uses a variable-length encoding for counts:
    - If the first byte is non-zero (1-255): that's the count
    - If the first byte is zero: read 2 more bytes as uint16, count = 256 + uint16

    This allows encoding counts from 1 to 65,791:
    - 1-255: encoded as 1 byte
    - 256-65,791: encoded as 3 bytes (0x00 + uint16)

    Args:
        stream: Binary stream to read from

    Returns:
        The decoded count value

    Raises:
        ValueError: If insufficient data is available

    Example:
        >>> stream = BytesIO(b'\\x05')  # count = 5
        >>> read_count(stream)
        5
        >>> stream = BytesIO(b'\\x00\\x0A\\x00')  # count = 256 + 10 = 266
        >>> read_count(stream)
        266
    """
    count_byte_data = stream.read(1)
    if len(count_byte_data) != 1:
        raise ValueError("Insufficient data: could not read count byte")

    count_byte = struct.unpack('<B', count_byte_data)[0]

    if count_byte != 0:
        return count_byte

    # Extended count mode
    extended_data = stream.read(2)
    if len(extended_data) != 2:
        raise ValueError("Insufficient data: could not read extended count")

    extended_count = struct.unpack('<H', extended_data)[0]
    return 256 + extended_count


# =============================================================================
# BEZIER CURVE OPCODES
# =============================================================================

def opcode_0x02_bezier_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x02: BEZIER_16R (16-bit relative Bezier curve).

    Format:
    - Count: variable-length count (1 or 3 bytes)
    - Start point (Xs, Ys): 2 x int16 (4 bytes total)
    - For each Bezier curve (repeated 'count' times):
      * Control point 1 (Xc1, Yc1): 2 x int16 (4 bytes)
      * Control point 2 (Xc2, Yc2): 2 x int16 (4 bytes)
      * End point (Xe, Ye): 2 x int16 (4 bytes)

    Total bytes: 1-3 (count) + 4 (start) + count * 12 (3 points per curve)

    Coordinates are relative to the last materialized point in the file.

    Args:
        stream: Binary stream positioned after the 0x02 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': '0x02'
        - 'name': 'BEZIER_16R'
        - 'count': Number of Bezier curves
        - 'start_point': Tuple (Xs, Ys)
        - 'curves': List of curve dictionaries, each with:
          * 'control_point_1': Tuple (Xc1, Yc1)
          * 'control_point_2': Tuple (Xc2, Yc2)
          * 'end_point': Tuple (Xe, Ye)

    Raises:
        ValueError: If insufficient data or invalid format

    Example:
        >>> # One Bezier curve: start (0,0), controls (10,20), (30,20), end (40,0)
        >>> data = struct.pack('<B', 1)  # count = 1
        >>> data += struct.pack('<hhhhhhhh', 0, 0, 10, 20, 30, 20, 40, 0)
        >>> stream = BytesIO(data)
        >>> result = opcode_0x02_bezier_16r(stream)
        >>> result['count']
        1
        >>> result['curves'][0]['end_point']
        (40, 0)
    """
    # Read count of Bezier curves
    count = read_count(stream)

    if count < 1:
        raise ValueError(f"Invalid Bezier curve count: {count} (must be >= 1)")

    # Read start point (2 x int16)
    start_data = stream.read(4)
    if len(start_data) != 4:
        raise ValueError("Insufficient data: could not read start point")

    xs, ys = struct.unpack('<hh', start_data)

    # Read each Bezier curve (3 points = 6 int16 values = 12 bytes each)
    curves = []
    for i in range(count):
        curve_data = stream.read(12)
        if len(curve_data) != 12:
            raise ValueError(f"Insufficient data: could not read Bezier curve {i+1}/{count}")

        xc1, yc1, xc2, yc2, xe, ye = struct.unpack('<hhhhhh', curve_data)

        curves.append({
            'control_point_1': (xc1, yc1),
            'control_point_2': (xc2, yc2),
            'end_point': (xe, ye)
        })

    return {
        'opcode': '0x02',
        'name': 'BEZIER_16R',
        'count': count,
        'start_point': (xs, ys),
        'curves': curves
    }


def opcode_0x62_bezier_32(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x62 'b': BEZIER_32 (32-bit absolute Bezier curve).

    Format:
    - Count: variable-length count (1 or 3 bytes)
    - Start point (Xs, Ys): 2 x int32 (8 bytes total)
    - For each Bezier curve (repeated 'count' times):
      * Control point 1 (Xc1, Yc1): 2 x int32 (8 bytes)
      * Control point 2 (Xc2, Yc2): 2 x int32 (8 bytes)
      * End point (Xe, Ye): 2 x int32 (8 bytes)

    Total bytes: 1-3 (count) + 8 (start) + count * 24 (3 points per curve)

    Coordinates are relative to the last materialized point in the file,
    but use 32-bit precision instead of 16-bit.

    Args:
        stream: Binary stream positioned after the 0x62 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': '0x62'
        - 'name': 'BEZIER_32'
        - 'count': Number of Bezier curves
        - 'start_point': Tuple (Xs, Ys)
        - 'curves': List of curve dictionaries, each with:
          * 'control_point_1': Tuple (Xc1, Yc1)
          * 'control_point_2': Tuple (Xc2, Yc2)
          * 'end_point': Tuple (Xe, Ye)

    Raises:
        ValueError: If insufficient data or invalid format

    Example:
        >>> # One Bezier curve with 32-bit coordinates
        >>> data = struct.pack('<B', 1)  # count = 1
        >>> data += struct.pack('<ll', 0, 0)  # start point
        >>> data += struct.pack('<llllll', 1000, 2000, 3000, 2000, 4000, 0)  # curve
        >>> stream = BytesIO(data)
        >>> result = opcode_0x62_bezier_32(stream)
        >>> result['start_point']
        (0, 0)
        >>> result['curves'][0]['control_point_1']
        (1000, 2000)
    """
    # Read count of Bezier curves
    count = read_count(stream)

    if count < 1:
        raise ValueError(f"Invalid Bezier curve count: {count} (must be >= 1)")

    # Read start point (2 x int32)
    start_data = stream.read(8)
    if len(start_data) != 8:
        raise ValueError("Insufficient data: could not read start point")

    xs, ys = struct.unpack('<ll', start_data)

    # Read each Bezier curve (3 points = 6 int32 values = 24 bytes each)
    curves = []
    for i in range(count):
        curve_data = stream.read(24)
        if len(curve_data) != 24:
            raise ValueError(f"Insufficient data: could not read Bezier curve {i+1}/{count}")

        xc1, yc1, xc2, yc2, xe, ye = struct.unpack('<llllll', curve_data)

        curves.append({
            'control_point_1': (xc1, yc1),
            'control_point_2': (xc2, yc2),
            'end_point': (xe, ye)
        })

    return {
        'opcode': '0x62',
        'name': 'BEZIER_32',
        'count': count,
        'start_point': (xs, ys),
        'curves': curves
    }


def opcode_0x42_bezier_32r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x42 'B': BEZIER_32R (32-bit relative Bezier curve).

    This opcode is essentially identical to 0x62 (BEZIER_32) in terms of
    binary format, but the semantic interpretation is that coordinates are
    relative to the last materialized point. The format is the same.

    Format:
    - Count: variable-length count (1 or 3 bytes)
    - Start point (Xs, Ys): 2 x int32 (8 bytes total)
    - For each Bezier curve (repeated 'count' times):
      * Control point 1 (Xc1, Yc1): 2 x int32 (8 bytes)
      * Control point 2 (Xc2, Yc2): 2 x int32 (8 bytes)
      * End point (Xe, Ye): 2 x int32 (8 bytes)

    Total bytes: 1-3 (count) + 8 (start) + count * 24 (3 points per curve)

    Args:
        stream: Binary stream positioned after the 0x42 opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': '0x42'
        - 'name': 'BEZIER_32R'
        - 'count': Number of Bezier curves
        - 'start_point': Tuple (Xs, Ys)
        - 'curves': List of curve dictionaries, each with:
          * 'control_point_1': Tuple (Xc1, Yc1)
          * 'control_point_2': Tuple (Xc2, Yc2)
          * 'end_point': Tuple (Xe, Ye)

    Raises:
        ValueError: If insufficient data or invalid format

    Example:
        >>> # One Bezier curve with relative 32-bit coordinates
        >>> data = struct.pack('<B', 1)  # count = 1
        >>> data += struct.pack('<ll', 100, 100)  # start point
        >>> data += struct.pack('<llllll', 50, 100, 150, 100, 200, 0)  # curve
        >>> stream = BytesIO(data)
        >>> result = opcode_0x42_bezier_32r(stream)
        >>> result['name']
        'BEZIER_32R'
    """
    # Read count of Bezier curves
    count = read_count(stream)

    if count < 1:
        raise ValueError(f"Invalid Bezier curve count: {count} (must be >= 1)")

    # Read start point (2 x int32)
    start_data = stream.read(8)
    if len(start_data) != 8:
        raise ValueError("Insufficient data: could not read start point")

    xs, ys = struct.unpack('<ll', start_data)

    # Read each Bezier curve (3 points = 6 int32 values = 24 bytes each)
    curves = []
    for i in range(count):
        curve_data = stream.read(24)
        if len(curve_data) != 24:
            raise ValueError(f"Insufficient data: could not read Bezier curve {i+1}/{count}")

        xc1, yc1, xc2, yc2, xe, ye = struct.unpack('<llllll', curve_data)

        curves.append({
            'control_point_1': (xc1, yc1),
            'control_point_2': (xc2, yc2),
            'end_point': (xe, ye)
        })

    return {
        'opcode': '0x42',
        'name': 'BEZIER_32R',
        'count': count,
        'start_point': (xs, ys),
        'curves': curves
    }


# =============================================================================
# CONTOUR SET OPCODES
# =============================================================================

def opcode_0x0B_draw_contour_set_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0B: DRAW_CONTOUR_SET_16R (16-bit relative contour set).

    A contour set is a collection of polygonal regions used for complex shapes
    with holes. For example, the letter "A" would have 2 contours: the outer
    triangle (clockwise) and the inner hole (counterclockwise).

    Format:
    - CS-count: variable-length count (number of contours)
    - For each contour:
      * P-count[i]: variable-length count (number of points in this contour)
    - All points for all contours:
      * For each point: (X, Y) as 2 x int16 (4 bytes)

    Coordinates are relative to the last materialized point in the file.

    Args:
        stream: Binary stream positioned after the 0x0B opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': '0x0B'
        - 'name': 'DRAW_CONTOUR_SET_16R'
        - 'contour_count': Number of contours
        - 'contours': List of contour dictionaries, each with:
          * 'point_count': Number of points in this contour
          * 'points': List of (X, Y) tuples

    Raises:
        ValueError: If insufficient data or invalid format

    Example:
        >>> # Two contours: triangle (3 points) and smaller triangle (3 points)
        >>> data = struct.pack('<B', 2)  # 2 contours
        >>> data += struct.pack('<BB', 3, 3)  # 3 points each
        >>> # First triangle points
        >>> data += struct.pack('<hhhhhh', 0, 0, 100, 0, 50, 100)
        >>> # Second triangle points (hole)
        >>> data += struct.pack('<hhhhhh', 25, 25, 75, 25, 50, 50)
        >>> stream = BytesIO(data)
        >>> result = opcode_0x0B_draw_contour_set_16r(stream)
        >>> result['contour_count']
        2
        >>> len(result['contours'][0]['points'])
        3
    """
    # Read contour count
    cs_count = read_count(stream)

    if cs_count < 1:
        raise ValueError(f"Invalid contour count: {cs_count} (must be >= 1)")

    # Read point count for each contour
    point_counts = []
    total_points = 0
    for i in range(cs_count):
        p_count = read_count(stream)
        if p_count < 2:
            raise ValueError(f"Invalid point count for contour {i+1}: {p_count} (must be >= 2)")
        point_counts.append(p_count)
        total_points += p_count

    # Read all points (2 x int16 per point)
    all_points = []
    for i in range(total_points):
        point_data = stream.read(4)
        if len(point_data) != 4:
            raise ValueError(f"Insufficient data: could not read point {i+1}/{total_points}")

        x, y = struct.unpack('<hh', point_data)
        all_points.append((x, y))

    # Organize points into contours
    contours = []
    point_index = 0
    for i, p_count in enumerate(point_counts):
        contour_points = all_points[point_index:point_index + p_count]
        contours.append({
            'point_count': p_count,
            'points': contour_points
        })
        point_index += p_count

    return {
        'opcode': '0x0B',
        'name': 'DRAW_CONTOUR_SET_16R',
        'contour_count': cs_count,
        'contours': contours
    }


def opcode_0x6B_draw_contour_set_32r(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x6B 'k': DRAW_CONTOUR_SET_32R (32-bit relative contour set).

    This is identical to 0x0B but uses 32-bit coordinates instead of 16-bit.

    A contour set is a collection of polygonal regions used for complex shapes
    with holes. Clockwise-wound contours are positive (filled) regions, while
    counterclockwise-wound contours are negative (holes).

    Format:
    - CS-count: variable-length count (number of contours)
    - For each contour:
      * P-count[i]: variable-length count (number of points in this contour)
    - All points for all contours:
      * For each point: (X, Y) as 2 x int32 (8 bytes)

    Coordinates are relative to the last materialized point in the file.

    Args:
        stream: Binary stream positioned after the 0x6B opcode byte

    Returns:
        Dictionary containing:
        - 'opcode': '0x6B'
        - 'name': 'DRAW_CONTOUR_SET_32R'
        - 'contour_count': Number of contours
        - 'contours': List of contour dictionaries, each with:
          * 'point_count': Number of points in this contour
          * 'points': List of (X, Y) tuples

    Raises:
        ValueError: If insufficient data or invalid format

    Example:
        >>> # One contour: square with 4 points using 32-bit coords
        >>> data = struct.pack('<B', 1)  # 1 contour
        >>> data += struct.pack('<B', 4)  # 4 points
        >>> # Square points
        >>> data += struct.pack('<llllllll', 0, 0, 10000, 0, 10000, 10000, 0, 10000)
        >>> stream = BytesIO(data)
        >>> result = opcode_0x6B_draw_contour_set_32r(stream)
        >>> result['contour_count']
        1
        >>> result['contours'][0]['points'][1]
        (10000, 0)
    """
    # Read contour count
    cs_count = read_count(stream)

    if cs_count < 1:
        raise ValueError(f"Invalid contour count: {cs_count} (must be >= 1)")

    # Read point count for each contour
    point_counts = []
    total_points = 0
    for i in range(cs_count):
        p_count = read_count(stream)
        if p_count < 2:
            raise ValueError(f"Invalid point count for contour {i+1}: {p_count} (must be >= 2)")
        point_counts.append(p_count)
        total_points += p_count

    # Read all points (2 x int32 per point)
    all_points = []
    for i in range(total_points):
        point_data = stream.read(8)
        if len(point_data) != 8:
            raise ValueError(f"Insufficient data: could not read point {i+1}/{total_points}")

        x, y = struct.unpack('<ll', point_data)
        all_points.append((x, y))

    # Organize points into contours
    contours = []
    point_index = 0
    for i, p_count in enumerate(point_counts):
        contour_points = all_points[point_index:point_index + p_count]
        contours.append({
            'point_count': p_count,
            'points': contour_points
        })
        point_index += p_count

    return {
        'opcode': '0x6B',
        'name': 'DRAW_CONTOUR_SET_32R',
        'contour_count': cs_count,
        'contours': contours
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_read_count():
    """Test the read_count helper function."""
    print("=" * 70)
    print("TESTING read_count() helper function")
    print("=" * 70)

    # Test 1: Single byte count (value 5)
    print("\nTest 1: Single byte count = 5")
    stream = BytesIO(b'\x05')
    result = read_count(stream)
    assert result == 5, f"Expected 5, got {result}"
    print(f"  PASS: read_count(0x05) = {result}")

    # Test 2: Single byte count (value 255)
    print("\nTest 2: Single byte count = 255")
    stream = BytesIO(b'\xFF')
    result = read_count(stream)
    assert result == 255, f"Expected 255, got {result}"
    print(f"  PASS: read_count(0xFF) = {result}")

    # Test 3: Extended count (value 256)
    print("\nTest 3: Extended count = 256")
    stream = BytesIO(b'\x00\x00\x00')  # 0 + (256 + 0)
    result = read_count(stream)
    assert result == 256, f"Expected 256, got {result}"
    print(f"  PASS: read_count(0x00 0x00 0x00) = {result}")

    # Test 4: Extended count (value 1000)
    print("\nTest 4: Extended count = 1000")
    # 1000 = 256 + 744, so we encode 744 as uint16
    stream = BytesIO(struct.pack('<BH', 0, 744))
    result = read_count(stream)
    assert result == 1000, f"Expected 1000, got {result}"
    print(f"  PASS: read_count(0x00 + uint16(744)) = {result}")

    print("\n" + "=" * 70)
    print("ALL read_count() TESTS PASSED")
    print("=" * 70 + "\n")


def test_opcode_0x02_bezier_16r():
    """Test suite for opcode 0x02 (BEZIER_16R)."""
    print("=" * 70)
    print("TESTING OPCODE 0x02 (BEZIER_16R)")
    print("=" * 70)

    # Test 1: Single Bezier curve
    print("\nTest 1: Single Bezier curve with 16-bit coordinates")
    data = struct.pack('<B', 1)  # count = 1
    data += struct.pack('<hh', 0, 0)  # start point (0, 0)
    data += struct.pack('<hhhhhh', 10, 20, 30, 20, 40, 0)  # curve
    stream = BytesIO(data)
    result = opcode_0x02_bezier_16r(stream)

    assert result['opcode'] == '0x02'
    assert result['name'] == 'BEZIER_16R'
    assert result['count'] == 1
    assert result['start_point'] == (0, 0)
    assert len(result['curves']) == 1
    assert result['curves'][0]['control_point_1'] == (10, 20)
    assert result['curves'][0]['control_point_2'] == (30, 20)
    assert result['curves'][0]['end_point'] == (40, 0)
    print(f"  PASS: {result}")

    # Test 2: Multiple connected Bezier curves
    print("\nTest 2: Two connected Bezier curves")
    data = struct.pack('<B', 2)  # count = 2
    data += struct.pack('<hh', 100, 100)  # start point
    # First curve
    data += struct.pack('<hhhhhh', 110, 150, 130, 150, 140, 100)
    # Second curve (starts from previous end point)
    data += struct.pack('<hhhhhh', 150, 50, 170, 50, 180, 100)
    stream = BytesIO(data)
    result = opcode_0x02_bezier_16r(stream)

    assert result['count'] == 2
    assert result['start_point'] == (100, 100)
    assert len(result['curves']) == 2
    assert result['curves'][0]['end_point'] == (140, 100)
    assert result['curves'][1]['end_point'] == (180, 100)
    print(f"  PASS: {result['count']} curves parsed")

    print("\n" + "=" * 70)
    print("ALL OPCODE 0x02 TESTS PASSED")
    print("=" * 70 + "\n")


def test_opcode_0x62_bezier_32():
    """Test suite for opcode 0x62 (BEZIER_32)."""
    print("=" * 70)
    print("TESTING OPCODE 0x62 (BEZIER_32)")
    print("=" * 70)

    # Test 1: Single Bezier curve with 32-bit coordinates
    print("\nTest 1: Single Bezier curve with 32-bit coordinates")
    data = struct.pack('<B', 1)  # count = 1
    data += struct.pack('<ll', 0, 0)  # start point
    data += struct.pack('<llllll', 1000, 2000, 3000, 2000, 4000, 0)  # curve
    stream = BytesIO(data)
    result = opcode_0x62_bezier_32(stream)

    assert result['opcode'] == '0x62'
    assert result['name'] == 'BEZIER_32'
    assert result['count'] == 1
    assert result['start_point'] == (0, 0)
    assert result['curves'][0]['control_point_1'] == (1000, 2000)
    assert result['curves'][0]['control_point_2'] == (3000, 2000)
    assert result['curves'][0]['end_point'] == (4000, 0)
    print(f"  PASS: {result}")

    # Test 2: Large coordinate values (testing 32-bit range)
    print("\nTest 2: Large coordinate values")
    data = struct.pack('<B', 1)  # count = 1
    data += struct.pack('<ll', -1000000, 1000000)  # start point
    data += struct.pack('<llllll', -500000, 1500000, 500000, 1500000, 1000000, 1000000)
    stream = BytesIO(data)
    result = opcode_0x62_bezier_32(stream)

    assert result['start_point'] == (-1000000, 1000000)
    assert result['curves'][0]['control_point_1'] == (-500000, 1500000)
    print(f"  PASS: Large coordinates handled correctly")

    print("\n" + "=" * 70)
    print("ALL OPCODE 0x62 TESTS PASSED")
    print("=" * 70 + "\n")


def test_opcode_0x42_bezier_32r():
    """Test suite for opcode 0x42 (BEZIER_32R)."""
    print("=" * 70)
    print("TESTING OPCODE 0x42 (BEZIER_32R)")
    print("=" * 70)

    # Test 1: Single relative Bezier curve
    print("\nTest 1: Single relative Bezier curve")
    data = struct.pack('<B', 1)  # count = 1
    data += struct.pack('<ll', 100, 100)  # relative start point
    data += struct.pack('<llllll', 50, 100, 150, 100, 200, 0)  # relative curve
    stream = BytesIO(data)
    result = opcode_0x42_bezier_32r(stream)

    assert result['opcode'] == '0x42'
    assert result['name'] == 'BEZIER_32R'
    assert result['count'] == 1
    assert result['start_point'] == (100, 100)
    assert result['curves'][0]['end_point'] == (200, 0)
    print(f"  PASS: {result}")

    # Test 2: Negative relative coordinates
    print("\nTest 2: Negative relative coordinates")
    data = struct.pack('<B', 1)  # count = 1
    data += struct.pack('<ll', 0, 0)  # start at origin
    data += struct.pack('<llllll', -50, 100, 50, 100, 0, 0)  # curve with negatives
    stream = BytesIO(data)
    result = opcode_0x42_bezier_32r(stream)

    assert result['curves'][0]['control_point_1'] == (-50, 100)
    assert result['curves'][0]['end_point'] == (0, 0)
    print(f"  PASS: Negative coordinates handled correctly")

    print("\n" + "=" * 70)
    print("ALL OPCODE 0x42 TESTS PASSED")
    print("=" * 70 + "\n")


def test_opcode_0x0B_draw_contour_set_16r():
    """Test suite for opcode 0x0B (DRAW_CONTOUR_SET_16R)."""
    print("=" * 70)
    print("TESTING OPCODE 0x0B (DRAW_CONTOUR_SET_16R)")
    print("=" * 70)

    # Test 1: Simple contour set - one triangle
    print("\nTest 1: Single contour (triangle)")
    data = struct.pack('<B', 1)  # 1 contour
    data += struct.pack('<B', 3)  # 3 points
    data += struct.pack('<hhhhhh', 0, 0, 100, 0, 50, 100)  # triangle points
    stream = BytesIO(data)
    result = opcode_0x0B_draw_contour_set_16r(stream)

    assert result['opcode'] == '0x0B'
    assert result['name'] == 'DRAW_CONTOUR_SET_16R'
    assert result['contour_count'] == 1
    assert result['contours'][0]['point_count'] == 3
    assert result['contours'][0]['points'] == [(0, 0), (100, 0), (50, 100)]
    print(f"  PASS: {result}")

    # Test 2: Complex contour set - letter "A" shape (outer + hole)
    print("\nTest 2: Two contours (letter 'A' with hole)")
    data = struct.pack('<B', 2)  # 2 contours
    data += struct.pack('<BB', 3, 3)  # 3 points each
    # Outer triangle (clockwise - positive space)
    data += struct.pack('<hhhhhh', 0, 0, 100, 0, 50, 100)
    # Inner triangle (counterclockwise - negative space/hole)
    data += struct.pack('<hhhhhh', 50, 50, 25, 25, 75, 25)
    stream = BytesIO(data)
    result = opcode_0x0B_draw_contour_set_16r(stream)

    assert result['contour_count'] == 2
    assert len(result['contours']) == 2
    assert result['contours'][0]['point_count'] == 3
    assert result['contours'][1]['point_count'] == 3
    print(f"  PASS: 2 contours with 3 points each")

    # Test 3: Extended count for contour with many points
    print("\nTest 3: Contour with extended point count (256 points)")
    data = struct.pack('<B', 1)  # 1 contour
    data += struct.pack('<BH', 0, 0)  # extended count: 256 + 0 = 256
    # Generate 256 points in a circle-like pattern
    for i in range(256):
        data += struct.pack('<hh', i * 10, i * 10)
    stream = BytesIO(data)
    result = opcode_0x0B_draw_contour_set_16r(stream)

    assert result['contour_count'] == 1
    assert result['contours'][0]['point_count'] == 256
    assert len(result['contours'][0]['points']) == 256
    print(f"  PASS: Extended count handled (256 points)")

    print("\n" + "=" * 70)
    print("ALL OPCODE 0x0B TESTS PASSED")
    print("=" * 70 + "\n")


def test_opcode_0x6B_draw_contour_set_32r():
    """Test suite for opcode 0x6B (DRAW_CONTOUR_SET_32R)."""
    print("=" * 70)
    print("TESTING OPCODE 0x6B (DRAW_CONTOUR_SET_32R)")
    print("=" * 70)

    # Test 1: Simple square with 32-bit coordinates
    print("\nTest 1: Single contour (square) with 32-bit coordinates")
    data = struct.pack('<B', 1)  # 1 contour
    data += struct.pack('<B', 4)  # 4 points
    data += struct.pack('<llllllll', 0, 0, 10000, 0, 10000, 10000, 0, 10000)
    stream = BytesIO(data)
    result = opcode_0x6B_draw_contour_set_32r(stream)

    assert result['opcode'] == '0x6B'
    assert result['name'] == 'DRAW_CONTOUR_SET_32R'
    assert result['contour_count'] == 1
    assert result['contours'][0]['point_count'] == 4
    assert result['contours'][0]['points'][0] == (0, 0)
    assert result['contours'][0]['points'][1] == (10000, 0)
    assert result['contours'][0]['points'][2] == (10000, 10000)
    assert result['contours'][0]['points'][3] == (0, 10000)
    print(f"  PASS: {result}")

    # Test 2: Multiple contours with large coordinates
    print("\nTest 2: Two contours with large coordinates")
    data = struct.pack('<B', 2)  # 2 contours
    data += struct.pack('<BB', 3, 3)  # 3 points each
    # First contour
    data += struct.pack('<llllll', -1000000, -1000000, 1000000, -1000000, 0, 1000000)
    # Second contour
    data += struct.pack('<llllll', -100000, -100000, 100000, -100000, 0, 100000)
    stream = BytesIO(data)
    result = opcode_0x6B_draw_contour_set_32r(stream)

    assert result['contour_count'] == 2
    assert result['contours'][0]['points'][0] == (-1000000, -1000000)
    assert result['contours'][1]['points'][0] == (-100000, -100000)
    print(f"  PASS: Large coordinates handled correctly")

    print("\n" + "=" * 70)
    print("ALL OPCODE 0x6B TESTS PASSED")
    print("=" * 70 + "\n")


def run_all_tests():
    """Run all test suites."""
    print("\n" + "=" * 70)
    print("AGENT 9: BEZIER CURVES AND CONTOUR SETS - FULL TEST SUITE")
    print("=" * 70 + "\n")

    test_read_count()
    test_opcode_0x02_bezier_16r()
    test_opcode_0x62_bezier_32()
    test_opcode_0x42_bezier_32r()
    test_opcode_0x0B_draw_contour_set_16r()
    test_opcode_0x6B_draw_contour_set_32r()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - 5 opcodes implemented")
    print("  - 3 Bezier curve opcodes (0x02, 0x62, 0x42)")
    print("  - 2 Contour set opcodes (0x0B, 0x6B)")
    print("  - All test cases passed")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
