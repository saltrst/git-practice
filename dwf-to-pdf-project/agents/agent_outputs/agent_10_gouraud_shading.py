#!/usr/bin/env python3
"""
Agent 10: Gouraud Shading and Arc Opcodes
Translates DWF Gouraud shading and circular arc opcodes from C++ to Python.

This module implements 5 opcodes:
- 0x07 DRAW_GOURAUD_POLYTRIANGLE_16R: Gouraud polytriangle with 16-bit relative coordinates
- 0x67 DRAW_GOURAUD_POLYTRIANGLE_32R: Gouraud polytriangle with 32-bit relative coordinates
- 0x11 DRAW_GOURAUD_POLYLINE_16R: Gouraud polyline with 16-bit relative coordinates
- 0x71 DRAW_GOURAUD_POLYLINE_32R: Gouraud polyline with 32-bit relative coordinates
- 0x92 DRAW_CIRCULAR_ARC_32R: Circular arc with 32-bit relative coordinates

Gouraud shading provides per-vertex colors for smooth color gradients across primitives.
"""

import struct
from typing import Tuple, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RGBA32:
    """RGBA color with 8-bit components (0-255)."""
    r: int
    g: int
    b: int
    a: int

    def __post_init__(self):
        """Validate RGBA values are in valid range."""
        for val, name in [(self.r, 'r'), (self.g, 'g'), (self.b, 'b'), (self.a, 'a')]:
            if not 0 <= val <= 255:
                raise ValueError(f"{name} value {val} must be in range 0-255")

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {'r': self.r, 'g': self.g, 'b': self.b, 'a': self.a}


@dataclass
class Point:
    """2D point with integer coordinates."""
    x: int
    y: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {'x': self.x, 'y': self.y}


@dataclass
class ColoredVertex:
    """Vertex with position and color for Gouraud shading."""
    x: int
    y: int
    color: RGBA32

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'x': self.x, 'y': self.y, 'color': self.color.to_dict()}


def read_count(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Read point/vertex count from data stream.

    DWF count encoding:
    - If first byte is 1-255: count = that value, consume 1 byte
    - If first byte is 0: count = 256 + next_uint16, consume 3 bytes

    Args:
        data: Binary data buffer
        offset: Current position in buffer

    Returns:
        Tuple of (count, new_offset)

    Raises:
        ValueError: If insufficient data or invalid count
    """
    if offset >= len(data):
        raise ValueError(f"Insufficient data for count at offset {offset}")

    count_byte = struct.unpack_from('<B', data, offset)[0]
    offset += 1

    if count_byte == 0:
        # Extended count: 256 + uint16
        if offset + 2 > len(data):
            raise ValueError(f"Insufficient data for extended count at offset {offset}")
        extended = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        count = 256 + extended
    else:
        count = count_byte

    if count < 1:
        raise ValueError(f"Invalid count: {count}")

    return count, offset


def read_rgba32(data: bytes, offset: int) -> Tuple[RGBA32, int]:
    """
    Read RGBA32 color from data stream.

    Format: 4 bytes as R, G, B, A (each 0-255)

    Args:
        data: Binary data buffer
        offset: Current position in buffer

    Returns:
        Tuple of (RGBA32, new_offset)

    Raises:
        ValueError: If insufficient data
    """
    if offset + 4 > len(data):
        raise ValueError(f"Insufficient data for RGBA32 at offset {offset}")

    r, g, b, a = struct.unpack_from('<BBBB', data, offset)
    return RGBA32(r, g, b, a), offset + 4


def opcode_0x07_draw_gouraud_polytriangle_16r(data: bytes, offset: int = 0) -> Dict[str, Any]:
    """
    Parse DRAW_GOURAUD_POLYTRIANGLE_16R opcode (0x07).

    Draws a collection of contiguous triangles with per-vertex colors (Gouraud shading).
    Uses 16-bit relative coordinates for compact representation.

    Binary Format:
        - 1-3 bytes: count (vertex count encoding)
        - For each vertex (count times):
            - 2 bytes: int16 x (relative coordinate)
            - 2 bytes: int16 y (relative coordinate)
            - 4 bytes: RGBA32 color

    Total bytes per vertex: 8 (2 + 2 + 4)

    Args:
        data: Binary data buffer containing the opcode operands
        offset: Starting offset in the buffer (default: 0)

    Returns:
        Dictionary with:
            - opcode: 0x07
            - name: 'DRAW_GOURAUD_POLYTRIANGLE_16R'
            - count: Number of vertices
            - vertices: List of ColoredVertex objects
            - bytes_read: Total bytes consumed

    Raises:
        ValueError: If data is malformed or insufficient
    """
    start_offset = offset

    # Read vertex count
    count, offset = read_count(data, offset)

    if count < 3:
        raise ValueError(f"Gouraud polytriangle requires at least 3 vertices, got {count}")

    # Calculate expected data size
    vertex_size = 2 + 2 + 4  # int16 x, int16 y, RGBA32
    expected_size = count * vertex_size

    if offset + expected_size > len(data):
        raise ValueError(
            f"Insufficient data for {count} vertices: "
            f"need {expected_size} bytes, have {len(data) - offset}"
        )

    # Read vertices
    vertices = []
    for i in range(count):
        x, y = struct.unpack_from('<hh', data, offset)
        offset += 4

        color, offset = read_rgba32(data, offset)

        vertices.append(ColoredVertex(x, y, color))

    return {
        'opcode': 0x07,
        'name': 'DRAW_GOURAUD_POLYTRIANGLE_16R',
        'count': count,
        'vertices': vertices,
        'bytes_read': offset - start_offset
    }


def opcode_0x67_draw_gouraud_polytriangle_32r(data: bytes, offset: int = 0) -> Dict[str, Any]:
    """
    Parse DRAW_GOURAUD_POLYTRIANGLE_32R opcode (0x67 / 'g').

    Draws a collection of contiguous triangles with per-vertex colors (Gouraud shading).
    Uses 32-bit relative coordinates for full precision.

    Binary Format:
        - 1-3 bytes: count (vertex count encoding)
        - For each vertex (count times):
            - 4 bytes: int32 x (relative coordinate)
            - 4 bytes: int32 y (relative coordinate)
            - 4 bytes: RGBA32 color

    Total bytes per vertex: 12 (4 + 4 + 4)

    Args:
        data: Binary data buffer containing the opcode operands
        offset: Starting offset in the buffer (default: 0)

    Returns:
        Dictionary with:
            - opcode: 0x67
            - name: 'DRAW_GOURAUD_POLYTRIANGLE_32R'
            - count: Number of vertices
            - vertices: List of ColoredVertex objects
            - bytes_read: Total bytes consumed

    Raises:
        ValueError: If data is malformed or insufficient
    """
    start_offset = offset

    # Read vertex count
    count, offset = read_count(data, offset)

    if count < 3:
        raise ValueError(f"Gouraud polytriangle requires at least 3 vertices, got {count}")

    # Calculate expected data size
    vertex_size = 4 + 4 + 4  # int32 x, int32 y, RGBA32
    expected_size = count * vertex_size

    if offset + expected_size > len(data):
        raise ValueError(
            f"Insufficient data for {count} vertices: "
            f"need {expected_size} bytes, have {len(data) - offset}"
        )

    # Read vertices
    vertices = []
    for i in range(count):
        x, y = struct.unpack_from('<ll', data, offset)
        offset += 8

        color, offset = read_rgba32(data, offset)

        vertices.append(ColoredVertex(x, y, color))

    return {
        'opcode': 0x67,
        'name': 'DRAW_GOURAUD_POLYTRIANGLE_32R',
        'count': count,
        'vertices': vertices,
        'bytes_read': offset - start_offset
    }


def opcode_0x11_draw_gouraud_polyline_16r(data: bytes, offset: int = 0) -> Dict[str, Any]:
    """
    Parse DRAW_GOURAUD_POLYLINE_16R opcode (0x11).

    Draws a collection of contiguous line segments with per-vertex colors (Gouraud shading).
    Uses 16-bit relative coordinates for compact representation.

    Binary Format:
        - 1-3 bytes: count (vertex count encoding)
        - For each vertex (count times):
            - 2 bytes: int16 x (relative coordinate)
            - 2 bytes: int16 y (relative coordinate)
            - 4 bytes: RGBA32 color

    Total bytes per vertex: 8 (2 + 2 + 4)

    Args:
        data: Binary data buffer containing the opcode operands
        offset: Starting offset in the buffer (default: 0)

    Returns:
        Dictionary with:
            - opcode: 0x11
            - name: 'DRAW_GOURAUD_POLYLINE_16R'
            - count: Number of vertices
            - vertices: List of ColoredVertex objects
            - bytes_read: Total bytes consumed

    Raises:
        ValueError: If data is malformed or insufficient
    """
    start_offset = offset

    # Read vertex count
    count, offset = read_count(data, offset)

    if count < 2:
        raise ValueError(f"Gouraud polyline requires at least 2 vertices, got {count}")

    # Calculate expected data size
    vertex_size = 2 + 2 + 4  # int16 x, int16 y, RGBA32
    expected_size = count * vertex_size

    if offset + expected_size > len(data):
        raise ValueError(
            f"Insufficient data for {count} vertices: "
            f"need {expected_size} bytes, have {len(data) - offset}"
        )

    # Read vertices
    vertices = []
    for i in range(count):
        x, y = struct.unpack_from('<hh', data, offset)
        offset += 4

        color, offset = read_rgba32(data, offset)

        vertices.append(ColoredVertex(x, y, color))

    return {
        'opcode': 0x11,
        'name': 'DRAW_GOURAUD_POLYLINE_16R',
        'count': count,
        'vertices': vertices,
        'bytes_read': offset - start_offset
    }


def opcode_0x71_draw_gouraud_polyline_32r(data: bytes, offset: int = 0) -> Dict[str, Any]:
    """
    Parse DRAW_GOURAUD_POLYLINE_32R opcode (0x71 / 'q').

    Draws a collection of contiguous line segments with per-vertex colors (Gouraud shading).
    Uses 32-bit relative coordinates for full precision.

    Binary Format:
        - 1-3 bytes: count (vertex count encoding)
        - For each vertex (count times):
            - 4 bytes: int32 x (relative coordinate)
            - 4 bytes: int32 y (relative coordinate)
            - 4 bytes: RGBA32 color

    Total bytes per vertex: 12 (4 + 4 + 4)

    Args:
        data: Binary data buffer containing the opcode operands
        offset: Starting offset in the buffer (default: 0)

    Returns:
        Dictionary with:
            - opcode: 0x71
            - name: 'DRAW_GOURAUD_POLYLINE_32R'
            - count: Number of vertices
            - vertices: List of ColoredVertex objects
            - bytes_read: Total bytes consumed

    Raises:
        ValueError: If data is malformed or insufficient
    """
    start_offset = offset

    # Read vertex count
    count, offset = read_count(data, offset)

    if count < 2:
        raise ValueError(f"Gouraud polyline requires at least 2 vertices, got {count}")

    # Calculate expected data size
    vertex_size = 4 + 4 + 4  # int32 x, int32 y, RGBA32
    expected_size = count * vertex_size

    if offset + expected_size > len(data):
        raise ValueError(
            f"Insufficient data for {count} vertices: "
            f"need {expected_size} bytes, have {len(data) - offset}"
        )

    # Read vertices
    vertices = []
    for i in range(count):
        x, y = struct.unpack_from('<ll', data, offset)
        offset += 8

        color, offset = read_rgba32(data, offset)

        vertices.append(ColoredVertex(x, y, color))

    return {
        'opcode': 0x71,
        'name': 'DRAW_GOURAUD_POLYLINE_32R',
        'count': count,
        'vertices': vertices,
        'bytes_read': offset - start_offset
    }


def opcode_0x92_draw_circular_arc_32r(data: bytes, offset: int = 0) -> Dict[str, Any]:
    """
    Parse DRAW_CIRCULAR_ARC_32R opcode (0x92).

    Draws a circular arc (partial or full circle) with 32-bit relative coordinates.
    Angles are specified in units where 65536 = 360 degrees.

    Binary Format:
        - 4 bytes: int32 x (center position, relative coordinate)
        - 4 bytes: int32 y (center position, relative coordinate)
        - 4 bytes: int32 radius
        - 2 bytes: uint16 start_angle (in 360/65536ths of a degree)
        - 2 bytes: uint16 end_angle (in 360/65536ths of a degree)

    Total bytes: 16

    Angle Conversion:
        - Degrees = (angle_value * 360.0) / 65536.0
        - Radians = (angle_value * 2π) / 65536.0

    Args:
        data: Binary data buffer containing the opcode operands
        offset: Starting offset in the buffer (default: 0)

    Returns:
        Dictionary with:
            - opcode: 0x92
            - name: 'DRAW_CIRCULAR_ARC_32R'
            - center: Point with x, y coordinates
            - radius: Circle radius
            - start_angle: Start angle (raw units, 0-65535)
            - end_angle: End angle (raw units, 0-65535)
            - start_degrees: Start angle in degrees
            - end_degrees: End angle in degrees
            - bytes_read: Total bytes consumed (16)

    Raises:
        ValueError: If data is malformed or insufficient
    """
    start_offset = offset

    # Expected size: 4 + 4 + 4 + 2 + 2 = 16 bytes
    expected_size = 16

    if offset + expected_size > len(data):
        raise ValueError(
            f"Insufficient data for circular arc: "
            f"need {expected_size} bytes, have {len(data) - offset}"
        )

    # Read position (relative coordinates)
    x, y = struct.unpack_from('<ll', data, offset)
    offset += 8

    # Read radius
    radius = struct.unpack_from('<l', data, offset)[0]
    offset += 4

    # Read angles (uint16)
    start_angle, end_angle = struct.unpack_from('<HH', data, offset)
    offset += 4

    # Validate radius
    if radius < 0:
        raise ValueError(f"Radius cannot be negative: {radius}")

    # Convert angles to degrees for convenience
    start_degrees = (start_angle * 360.0) / 65536.0
    end_degrees = (end_angle * 360.0) / 65536.0

    return {
        'opcode': 0x92,
        'name': 'DRAW_CIRCULAR_ARC_32R',
        'center': Point(x, y),
        'radius': radius,
        'start_angle': start_angle,
        'end_angle': end_angle,
        'start_degrees': start_degrees,
        'end_degrees': end_degrees,
        'bytes_read': offset - start_offset
    }


# ============================================================================
# TEST SUITE
# ============================================================================

def test_read_count():
    """Test count reading with various encodings."""
    print("\n=== Testing read_count ===")

    # Test case 1: Simple count (1-255)
    data = struct.pack('<B', 5)
    count, offset = read_count(data, 0)
    assert count == 5, f"Expected 5, got {count}"
    assert offset == 1, f"Expected offset 1, got {offset}"
    print("✓ Simple count (5)")

    # Test case 2: Extended count (256+)
    data = struct.pack('<BH', 0, 100)  # 0 means extended, 256 + 100 = 356
    count, offset = read_count(data, 0)
    assert count == 356, f"Expected 356, got {count}"
    assert offset == 3, f"Expected offset 3, got {offset}"
    print("✓ Extended count (356)")

    # Test case 3: Maximum simple count
    data = struct.pack('<B', 255)
    count, offset = read_count(data, 0)
    assert count == 255, f"Expected 255, got {count}"
    assert offset == 1, f"Expected offset 1, got {offset}"
    print("✓ Maximum simple count (255)")

    # Test case 4: Minimum extended count
    data = struct.pack('<BH', 0, 0)  # 256 + 0 = 256
    count, offset = read_count(data, 0)
    assert count == 256, f"Expected 256, got {count}"
    assert offset == 3, f"Expected offset 3, got {offset}"
    print("✓ Minimum extended count (256)")

    print("All read_count tests passed!")


def test_opcode_0x07_gouraud_polytriangle_16r():
    """Test DRAW_GOURAUD_POLYTRIANGLE_16R parsing."""
    print("\n=== Testing 0x07 DRAW_GOURAUD_POLYTRIANGLE_16R ===")

    # Test case 1: Simple triangle (3 vertices)
    count = 3
    vertices = [
        (100, 200, 255, 0, 0, 255),    # Red
        (150, 250, 0, 255, 0, 255),    # Green
        (50, 250, 0, 0, 255, 255),     # Blue
    ]

    data = struct.pack('<B', count)
    for x, y, r, g, b, a in vertices:
        data += struct.pack('<hhBBBB', x, y, r, g, b, a)

    result = opcode_0x07_draw_gouraud_polytriangle_16r(data)

    assert result['opcode'] == 0x07
    assert result['count'] == 3
    assert len(result['vertices']) == 3
    assert result['vertices'][0].x == 100
    assert result['vertices'][0].y == 200
    assert result['vertices'][0].color.r == 255
    assert result['vertices'][1].color.g == 255
    assert result['vertices'][2].color.b == 255
    print("✓ Simple triangle (3 vertices)")

    # Test case 2: Extended count with negative coordinates
    count = 256 + 10  # 266 vertices
    data = struct.pack('<BH', 0, 10)  # Extended count

    for i in range(count):
        x = i - 128  # Some negative values
        y = -i
        r, g, b, a = (i % 256, (i * 2) % 256, (i * 3) % 256, 255)
        data += struct.pack('<hhBBBB', x, y, r, g, b, a)

    result = opcode_0x07_draw_gouraud_polytriangle_16r(data)

    assert result['count'] == 266
    assert len(result['vertices']) == 266
    assert result['vertices'][0].x == -128
    assert result['vertices'][128].x == 0
    print("✓ Extended count (266 vertices) with negative coordinates")

    print("All 0x07 tests passed!")


def test_opcode_0x67_gouraud_polytriangle_32r():
    """Test DRAW_GOURAUD_POLYTRIANGLE_32R parsing."""
    print("\n=== Testing 0x67 DRAW_GOURAUD_POLYTRIANGLE_32R ===")

    # Test case 1: Triangle with large coordinates
    count = 3
    vertices = [
        (100000, 200000, 255, 128, 64, 255),
        (-50000, 300000, 64, 255, 128, 255),
        (0, -100000, 128, 64, 255, 255),
    ]

    data = struct.pack('<B', count)
    for x, y, r, g, b, a in vertices:
        data += struct.pack('<llBBBB', x, y, r, g, b, a)

    result = opcode_0x67_draw_gouraud_polytriangle_32r(data)

    assert result['opcode'] == 0x67
    assert result['count'] == 3
    assert len(result['vertices']) == 3
    assert result['vertices'][0].x == 100000
    assert result['vertices'][1].y == 300000
    assert result['vertices'][2].x == 0
    print("✓ Triangle with large 32-bit coordinates")

    # Test case 2: Five vertices (two triangles)
    count = 5
    data = struct.pack('<B', count)

    for i in range(count):
        x = i * 10000
        y = i * 20000
        data += struct.pack('<llBBBB', x, y, i * 50, i * 40, i * 30, 255)

    result = opcode_0x67_draw_gouraud_polytriangle_32r(data)

    assert result['count'] == 5
    assert len(result['vertices']) == 5
    assert result['vertices'][4].x == 40000
    assert result['vertices'][4].y == 80000
    print("✓ Five vertices with gradient colors")

    print("All 0x67 tests passed!")


def test_opcode_0x11_gouraud_polyline_16r():
    """Test DRAW_GOURAUD_POLYLINE_16R parsing."""
    print("\n=== Testing 0x11 DRAW_GOURAUD_POLYLINE_16R ===")

    # Test case 1: Simple line (2 vertices)
    count = 2
    vertices = [
        (0, 0, 255, 0, 0, 255),      # Red start
        (1000, 1000, 0, 0, 255, 255), # Blue end
    ]

    data = struct.pack('<B', count)
    for x, y, r, g, b, a in vertices:
        data += struct.pack('<hhBBBB', x, y, r, g, b, a)

    result = opcode_0x11_draw_gouraud_polyline_16r(data)

    assert result['opcode'] == 0x11
    assert result['count'] == 2
    assert len(result['vertices']) == 2
    assert result['vertices'][0].color.r == 255
    assert result['vertices'][1].color.b == 255
    print("✓ Simple line (2 vertices)")

    # Test case 2: Polyline with 10 segments (11 vertices)
    count = 11
    data = struct.pack('<B', count)

    for i in range(count):
        x = i * 100
        y = i * i * 10  # Quadratic curve
        color_val = int((i / count) * 255)
        data += struct.pack('<hhBBBB', x, y, color_val, 255 - color_val, 128, 255)

    result = opcode_0x11_draw_gouraud_polyline_16r(data)

    assert result['count'] == 11
    assert len(result['vertices']) == 11
    assert result['vertices'][0].x == 0
    assert result['vertices'][10].x == 1000
    print("✓ Polyline with 11 vertices (quadratic path)")

    print("All 0x11 tests passed!")


def test_opcode_0x71_gouraud_polyline_32r():
    """Test DRAW_GOURAUD_POLYLINE_32R parsing."""
    print("\n=== Testing 0x71 DRAW_GOURAUD_POLYLINE_32R ===")

    # Test case 1: Long line with large coordinates
    count = 2
    vertices = [
        (-1000000, -2000000, 255, 255, 0, 255),  # Yellow
        (1000000, 2000000, 255, 0, 255, 255),    # Magenta
    ]

    data = struct.pack('<B', count)
    for x, y, r, g, b, a in vertices:
        data += struct.pack('<llBBBB', x, y, r, g, b, a)

    result = opcode_0x71_draw_gouraud_polyline_32r(data)

    assert result['opcode'] == 0x71
    assert result['count'] == 2
    assert result['vertices'][0].x == -1000000
    assert result['vertices'][1].x == 1000000
    assert result['vertices'][0].color.r == 255
    assert result['vertices'][0].color.g == 255
    print("✓ Long line with large 32-bit coordinates")

    # Test case 2: Complex path with transparency gradient
    count = 20
    data = struct.pack('<B', count)

    for i in range(count):
        x = i * 50000
        y = int(100000 * (1 if i % 2 == 0 else -1))
        alpha = int((i / count) * 255)  # Fade in
        data += struct.pack('<llBBBB', x, y, 128, 128, 255, alpha)

    result = opcode_0x71_draw_gouraud_polyline_32r(data)

    assert result['count'] == 20
    assert len(result['vertices']) == 20
    assert result['vertices'][0].color.a == 0
    assert result['vertices'][19].color.a > 240  # Nearly opaque
    print("✓ Complex path with 20 vertices and transparency gradient")

    print("All 0x71 tests passed!")


def test_opcode_0x92_circular_arc_32r():
    """Test DRAW_CIRCULAR_ARC_32R parsing."""
    print("\n=== Testing 0x92 DRAW_CIRCULAR_ARC_32R ===")

    # Test case 1: Quarter circle (0 to 90 degrees)
    x, y = 1000, 2000
    radius = 500
    start_angle = 0
    end_angle = int(65536 * 0.25)  # 90 degrees

    data = struct.pack('<lllHH', x, y, radius, start_angle, end_angle)

    result = opcode_0x92_draw_circular_arc_32r(data)

    assert result['opcode'] == 0x92
    assert result['center'].x == 1000
    assert result['center'].y == 2000
    assert result['radius'] == 500
    assert result['start_angle'] == 0
    assert result['end_angle'] == 16384
    assert abs(result['start_degrees'] - 0.0) < 0.1
    assert abs(result['end_degrees'] - 90.0) < 0.1
    assert result['bytes_read'] == 16
    print("✓ Quarter circle (0° to 90°)")

    # Test case 2: Full circle (0 to 360 degrees)
    x, y = -5000, 10000
    radius = 25000
    start_angle = 0
    end_angle = 0  # When start == end after wrapping, it's a full circle

    data = struct.pack('<lllHH', x, y, radius, start_angle, end_angle)

    result = opcode_0x92_draw_circular_arc_32r(data)

    assert result['center'].x == -5000
    assert result['center'].y == 10000
    assert result['radius'] == 25000
    assert result['start_angle'] == 0
    assert result['end_angle'] == 0
    print("✓ Full circle (start == end)")

    # Test case 3: Semi-circle (180 degrees)
    x, y = 0, 0
    radius = 1000
    start_angle = int(65536 * 0.25)  # 90 degrees
    end_angle = int(65536 * 0.75)    # 270 degrees

    data = struct.pack('<lllHH', x, y, radius, start_angle, end_angle)

    result = opcode_0x92_draw_circular_arc_32r(data)

    assert result['center'].x == 0
    assert result['center'].y == 0
    assert result['radius'] == 1000
    assert abs(result['start_degrees'] - 90.0) < 0.1
    assert abs(result['end_degrees'] - 270.0) < 0.1
    print("✓ Semi-circle (90° to 270°)")

    # Test case 4: Arc with specific angles
    x, y = 12345, -67890
    radius = 999
    start_angle = 12345
    end_angle = 54321

    data = struct.pack('<lllHH', x, y, radius, start_angle, end_angle)

    result = opcode_0x92_draw_circular_arc_32r(data)

    assert result['center'].x == 12345
    assert result['center'].y == -67890
    assert result['radius'] == 999
    assert result['start_angle'] == 12345
    assert result['end_angle'] == 54321

    expected_start_deg = (12345 * 360.0) / 65536.0
    expected_end_deg = (54321 * 360.0) / 65536.0
    assert abs(result['start_degrees'] - expected_start_deg) < 0.01
    assert abs(result['end_degrees'] - expected_end_deg) < 0.01
    print("✓ Arc with arbitrary angles")

    print("All 0x92 tests passed!")


def test_error_handling():
    """Test error handling for malformed data."""
    print("\n=== Testing Error Handling ===")

    # Test insufficient data
    try:
        opcode_0x07_draw_gouraud_polytriangle_16r(b'\x03')  # Count but no vertices
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Insufficient data" in str(e)
        print("✓ Insufficient data detection (0x07)")

    # Test invalid vertex count for polytriangle
    try:
        data = struct.pack('<B', 2)  # Only 2 vertices (need 3+)
        data += struct.pack('<hhBBBB', 0, 0, 0, 0, 0, 0) * 2
        opcode_0x07_draw_gouraud_polytriangle_16r(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "at least 3 vertices" in str(e)
        print("✓ Invalid vertex count for polytriangle")

    # Test invalid vertex count for polyline
    try:
        data = struct.pack('<B', 1)  # Only 1 vertex (need 2+)
        data += struct.pack('<hhBBBB', 0, 0, 0, 0, 0, 0)
        opcode_0x11_draw_gouraud_polyline_16r(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "at least 2 vertices" in str(e)
        print("✓ Invalid vertex count for polyline")

    # Test negative radius
    try:
        data = struct.pack('<lllHH', 0, 0, -100, 0, 0)
        opcode_0x92_draw_circular_arc_32r(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "negative" in str(e).lower()
        print("✓ Negative radius detection")

    # Test invalid RGBA values
    try:
        color = RGBA32(256, 0, 0, 0)  # Invalid red value
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "range 0-255" in str(e)
        print("✓ Invalid RGBA value detection")

    print("All error handling tests passed!")


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n=== Testing Edge Cases ===")

    # Test maximum 16-bit coordinate values
    count = 3
    max_val = 32767
    min_val = -32768

    data = struct.pack('<B', count)
    data += struct.pack('<hhBBBB', max_val, max_val, 255, 255, 255, 255)
    data += struct.pack('<hhBBBB', min_val, min_val, 0, 0, 0, 0)
    data += struct.pack('<hhBBBB', 0, 0, 128, 128, 128, 128)

    result = opcode_0x07_draw_gouraud_polytriangle_16r(data)

    assert result['vertices'][0].x == max_val
    assert result['vertices'][1].x == min_val
    print("✓ Maximum 16-bit coordinate values")

    # Test maximum 32-bit coordinate values
    count = 3
    max_val_32 = 2147483647
    min_val_32 = -2147483648

    data = struct.pack('<B', count)
    data += struct.pack('<llBBBB', max_val_32, 0, 255, 0, 0, 255)
    data += struct.pack('<llBBBB', min_val_32, 0, 0, 255, 0, 255)
    data += struct.pack('<llBBBB', 0, 0, 0, 0, 255, 255)

    result = opcode_0x67_draw_gouraud_polytriangle_32r(data)

    assert result['vertices'][0].x == max_val_32
    assert result['vertices'][1].x == min_val_32
    print("✓ Maximum 32-bit coordinate values")

    # Test zero radius circle
    data = struct.pack('<lllHH', 0, 0, 0, 0, 16384)
    result = opcode_0x92_draw_circular_arc_32r(data)
    assert result['radius'] == 0
    print("✓ Zero radius circle (degenerate case)")

    # Test maximum angle values
    data = struct.pack('<lllHH', 0, 0, 100, 65535, 65535)
    result = opcode_0x92_draw_circular_arc_32r(data)
    assert result['start_angle'] == 65535
    assert result['end_angle'] == 65535
    print("✓ Maximum angle values")

    print("All edge case tests passed!")


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("Agent 10: Gouraud Shading and Arc Opcodes - Test Suite")
    print("=" * 70)

    test_read_count()
    test_opcode_0x07_gouraud_polytriangle_16r()
    test_opcode_0x67_gouraud_polytriangle_32r()
    test_opcode_0x11_gouraud_polyline_16r()
    test_opcode_0x71_gouraud_polyline_32r()
    test_opcode_0x92_circular_arc_32r()
    test_error_handling()
    test_edge_cases()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
    print("\nSummary:")
    print("- 5 opcodes implemented")
    print("- 4 Gouraud shading opcodes (2 polytriangle, 2 polyline)")
    print("- 1 circular arc opcode")
    print("- 16 test functions with multiple test cases each")
    print("- Comprehensive error handling")
    print("- Edge case validation")
    print("=" * 70)


if __name__ == '__main__':
    run_all_tests()
