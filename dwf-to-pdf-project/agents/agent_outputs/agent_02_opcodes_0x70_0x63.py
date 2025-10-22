"""
DWF Opcode Parsers for 0x70 (Polygon) and 0x63 (Color)

This module implements binary parsers for two DWF drawing opcodes:
- 0x70: Binary polygon with 32-bit coordinates
- 0x63: Binary color using palette index

Based on opcode_reference_initial.json specifications.
"""

import struct
from typing import Dict, BinaryIO, Tuple, List


def parse_opcode_0x70_polygon(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x70 (binary_polygon_32r).

    Format:
    - 1 byte (uint8): vertex count
    - If count == 255: 2 bytes (uint16): extended count
    - For each vertex: x,y as int32 pairs (little-endian)

    Args:
        stream: Binary stream positioned after the 0x70 opcode byte

    Returns:
        Dictionary containing:
            - 'vertex_count': Number of vertices
            - 'vertices': List of (x, y) tuples as int32 coordinates

    Example:
        >>> import io
        >>> # 3 vertices: (100, 200), (300, 400), (500, 600)
        >>> data = struct.pack('<B', 3)  # count = 3
        >>> data += struct.pack('<llllll', 100, 200, 300, 400, 500, 600)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x70_polygon(stream)
        >>> result['vertex_count']
        3
        >>> result['vertices']
        [(100, 200), (300, 400), (500, 600)]
    """
    # Read vertex count (1 byte, uint8)
    count_bytes = stream.read(1)
    if len(count_bytes) != 1:
        raise ValueError("Insufficient data: could not read vertex count")

    count = struct.unpack('<B', count_bytes)[0]

    # Check for extended count
    if count == 255:
        extended_bytes = stream.read(2)
        if len(extended_bytes) != 2:
            raise ValueError("Insufficient data: could not read extended vertex count")
        count = struct.unpack('<H', extended_bytes)[0]

    # Read vertices (x, y pairs as int32)
    vertices = []
    for i in range(count):
        coord_bytes = stream.read(8)  # 4 bytes for x + 4 bytes for y
        if len(coord_bytes) != 8:
            raise ValueError(f"Insufficient data: could not read vertex {i+1}/{count}")

        x, y = struct.unpack('<ll', coord_bytes)
        vertices.append((x, y))

    return {
        'vertex_count': count,
        'vertices': vertices
    }


def parse_opcode_0x63_color(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x63 (binary_color_indexed).

    Format:
    - 1 byte (uint8): color palette index

    Args:
        stream: Binary stream positioned after the 0x63 opcode byte

    Returns:
        Dictionary containing:
            - 'color_index': The palette index (0-255)

    Example:
        >>> import io
        >>> data = struct.pack('<B', 42)  # color index 42
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x63_color(stream)
        >>> result['color_index']
        42
    """
    # Read color index (1 byte, uint8)
    index_bytes = stream.read(1)
    if len(index_bytes) != 1:
        raise ValueError("Insufficient data: could not read color index")

    color_index = struct.unpack('<B', index_bytes)[0]

    return {
        'color_index': color_index
    }


# ============================================================================
# TEST SUITE
# ============================================================================

def test_opcode_0x70_polygon():
    """Test suite for opcode 0x70 (Polygon)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x70 (POLYGON)")
    print("=" * 70)

    # Test 1: Simple triangle (3 vertices)
    print("\nTest 1: Simple triangle with 3 vertices")
    data = struct.pack('<B', 3)  # count = 3
    data += struct.pack('<llllll', 100, 200, 300, 400, 500, 600)
    stream = io.BytesIO(data)
    result = parse_opcode_0x70_polygon(stream)

    assert result['vertex_count'] == 3, f"Expected count 3, got {result['vertex_count']}"
    assert len(result['vertices']) == 3, f"Expected 3 vertices, got {len(result['vertices'])}"
    assert result['vertices'][0] == (100, 200), f"Vertex 0 mismatch: {result['vertices'][0]}"
    assert result['vertices'][1] == (300, 400), f"Vertex 1 mismatch: {result['vertices'][1]}"
    assert result['vertices'][2] == (500, 600), f"Vertex 2 mismatch: {result['vertices'][2]}"
    print(f"  PASS: {result}")

    # Test 2: Square (4 vertices)
    print("\nTest 2: Square with 4 vertices")
    data = struct.pack('<B', 4)  # count = 4
    data += struct.pack('<llllllll', 0, 0, 1000, 0, 1000, 1000, 0, 1000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x70_polygon(stream)

    assert result['vertex_count'] == 4
    assert len(result['vertices']) == 4
    assert result['vertices'] == [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    print(f"  PASS: {result}")

    # Test 3: Extended count (count == 255 triggers extended mode)
    print("\nTest 3: Extended count mode (255 vertices)")
    data = struct.pack('<B', 255)  # count = 255 (trigger)
    data += struct.pack('<H', 300)  # extended_count = 300
    # Add 300 vertices
    for i in range(300):
        data += struct.pack('<ll', i * 10, i * 20)
    stream = io.BytesIO(data)
    result = parse_opcode_0x70_polygon(stream)

    assert result['vertex_count'] == 300
    assert len(result['vertices']) == 300
    assert result['vertices'][0] == (0, 0)
    assert result['vertices'][299] == (2990, 5980)
    print(f"  PASS: Extended count with {result['vertex_count']} vertices")

    # Test 4: Negative coordinates
    print("\nTest 4: Polygon with negative coordinates")
    data = struct.pack('<B', 3)
    data += struct.pack('<llllll', -100, -200, 100, -200, 0, 100)
    stream = io.BytesIO(data)
    result = parse_opcode_0x70_polygon(stream)

    assert result['vertices'][0] == (-100, -200)
    assert result['vertices'][1] == (100, -200)
    assert result['vertices'][2] == (0, 100)
    print(f"  PASS: {result}")

    # Test 5: Single vertex (edge case)
    print("\nTest 5: Single vertex polygon")
    data = struct.pack('<B', 1)
    data += struct.pack('<ll', 500, 750)
    stream = io.BytesIO(data)
    result = parse_opcode_0x70_polygon(stream)

    assert result['vertex_count'] == 1
    assert result['vertices'] == [(500, 750)]
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    data = struct.pack('<B', 5)  # Claims 5 vertices
    data += struct.pack('<ll', 100, 200)  # Only 1 vertex
    stream = io.BytesIO(data)
    try:
        result = parse_opcode_0x70_polygon(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x70 (POLYGON): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x63_color():
    """Test suite for opcode 0x63 (Color)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x63 (COLOR)")
    print("=" * 70)

    # Test 1: Color index 0
    print("\nTest 1: Color index 0")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x63_color(stream)

    assert result['color_index'] == 0
    print(f"  PASS: {result}")

    # Test 2: Color index 42
    print("\nTest 2: Color index 42")
    data = struct.pack('<B', 42)
    stream = io.BytesIO(data)
    result = parse_opcode_0x63_color(stream)

    assert result['color_index'] == 42
    print(f"  PASS: {result}")

    # Test 3: Color index 255 (max value)
    print("\nTest 3: Color index 255 (maximum)")
    data = struct.pack('<B', 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0x63_color(stream)

    assert result['color_index'] == 255
    print(f"  PASS: {result}")

    # Test 4: Mid-range color index
    print("\nTest 4: Color index 128 (mid-range)")
    data = struct.pack('<B', 128)
    stream = io.BytesIO(data)
    result = parse_opcode_0x63_color(stream)

    assert result['color_index'] == 128
    print(f"  PASS: {result}")

    # Test 5: Error handling - no data
    print("\nTest 5: Error handling - no data")
    stream = io.BytesIO(b'')
    try:
        result = parse_opcode_0x63_color(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x63 (COLOR): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites."""
    print("\n" + "=" * 70)
    print("DWF OPCODE PARSER TEST SUITE")
    print("=" * 70)
    print(f"Testing opcodes: 0x70 (Polygon), 0x63 (Color)")
    print("=" * 70)

    test_opcode_0x70_polygon()
    test_opcode_0x63_color()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x70 (Polygon): 6 tests passed")
    print("  - Opcode 0x63 (Color): 5 tests passed")
    print("  - Total: 11 tests passed")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
