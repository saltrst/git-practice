"""
DWF Color Extensions Opcodes - Agent 36

This module implements parsers for 3 DWF opcodes related to extended color operations:
- 0x23: SET_COLOR_RGB_32 (32-bit RGBA color)
- 0x83: SET_COLOR_MAP_INDEX (indexed color reference)
- 0xA3: SET_BACKGROUND_COLOR (background RGBA color)

These opcodes provide extended color control including full RGBA color specification
with alpha channel support and indexed color mapping capabilities.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/color.cpp
- develop/global/src/dwf/whiptk/color_map.cpp

Author: Agent 36 (Color Extension Specialist)
"""

import struct
from typing import Dict, BinaryIO


# =============================================================================
# OPCODE 0x23 - SET_COLOR_RGB_32
# =============================================================================

def parse_opcode_0x23_color_rgb32(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x23 (SET_COLOR_RGB_32) - Set color with 32-bit RGBA values.

    This opcode sets the current drawing color using full 32-bit RGBA color
    specification with separate 8-bit channels for red, green, blue, and alpha.

    Format Specification:
    - Opcode: 0x23 (1 byte, not included in data stream)
    - Red component: uint8 (1 byte, unsigned, 0-255)
    - Green component: uint8 (1 byte, unsigned, 0-255)
    - Blue component: uint8 (1 byte, unsigned, 0-255)
    - Alpha component: uint8 (1 byte, unsigned, 0-255, 0=transparent, 255=opaque)
    - Total data: 4 bytes
    - Struct format: "<BBBB" (little-endian, 4 unsigned 8-bit integers)

    C++ Reference:
    From color.cpp - WT_Color::materialize():
        case 0x23:  // 32-bit RGBA color
            WT_Byte r, g, b, a;
            WD_CHECK(file.read(r));
            WD_CHECK(file.read(g));
            WD_CHECK(file.read(b));
            WD_CHECK(file.read(a));
            m_rgba = WT_RGBA32(r, g, b, a);

    Args:
        stream: Binary stream positioned after the 0x23 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_color_rgb32'
            - 'r': Red component (0-255)
            - 'g': Green component (0-255)
            - 'b': Blue component (0-255)
            - 'a': Alpha component (0-255)
            - 'bytes_read': 4

    Raises:
        ValueError: If stream doesn't contain 4 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<BBBB', 255, 128, 64, 255)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x23_color_rgb32(stream)
        >>> result['r']
        255
        >>> result['g']
        128
        >>> result['b']
        64
        >>> result['a']
        255

    Notes:
        - Corresponds to WT_Color::materialize() with opcode 0x23 in C++
        - Alpha channel: 0=fully transparent, 255=fully opaque
        - RGB values follow standard 8-bit color encoding
        - This provides full 32-bit RGBA color support
    """
    data = stream.read(4)

    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes for opcode 0x23 (SET_COLOR_RGB_32), got {len(data)} bytes")

    # Unpack four unsigned 8-bit integers (little-endian)
    r, g, b, a = struct.unpack('<BBBB', data)

    return {
        'type': 'set_color_rgb32',
        'r': r,
        'g': g,
        'b': b,
        'a': a,
        'bytes_read': 4
    }


# =============================================================================
# OPCODE 0x83 - SET_COLOR_MAP_INDEX
# =============================================================================

def parse_opcode_0x83_color_map_index(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x83 (SET_COLOR_MAP_INDEX) - Set color using color map index.

    This opcode sets the current drawing color by referencing an entry in the
    previously defined color map. This allows compact color specification when
    using a limited palette.

    Format Specification:
    - Opcode: 0x83 (1 byte, not included in data stream)
    - Color map index: uint16 (2 bytes, unsigned, little-endian)
    - Total data: 2 bytes
    - Struct format: "<H" (little-endian, unsigned 16-bit integer)

    C++ Reference:
    From color_map.cpp - WT_Color_Map::materialize():
        case 0x83:  // Color map index reference
            WT_Unsigned_Integer16 index;
            WD_CHECK(file.read(index));
            m_color_index = index;

    Args:
        stream: Binary stream positioned after the 0x83 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_color_map_index'
            - 'index': Color map index (0-65535)
            - 'bytes_read': 2

    Raises:
        ValueError: If stream doesn't contain 2 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<H', 42)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x83_color_map_index(stream)
        >>> result['index']
        42

    Notes:
        - Corresponds to WT_Color_Map::materialize() with opcode 0x83 in C++
        - Index refers to entry in previously defined color map
        - More compact than full RGBA specification for limited palettes
        - Valid indices depend on color map size defined earlier
        - Index 0 typically refers to first color map entry
    """
    data = stream.read(2)

    if len(data) != 2:
        raise ValueError(f"Expected 2 bytes for opcode 0x83 (SET_COLOR_MAP_INDEX), got {len(data)} bytes")

    # Unpack unsigned 16-bit integer (little-endian)
    index = struct.unpack('<H', data)[0]

    return {
        'type': 'set_color_map_index',
        'index': index,
        'bytes_read': 2
    }


# =============================================================================
# OPCODE 0xA3 - SET_BACKGROUND_COLOR
# =============================================================================

def parse_opcode_0xA3_background_color(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0xA3 (SET_BACKGROUND_COLOR) - Set background color with RGBA.

    This opcode sets the background color of the drawing using full 32-bit RGBA
    color specification. The background color affects how the drawing is displayed
    and can be used for transparent overlays.

    Format Specification:
    - Opcode: 0xA3 (1 byte, not included in data stream)
    - Red component: uint8 (1 byte, unsigned, 0-255)
    - Green component: uint8 (1 byte, unsigned, 0-255)
    - Blue component: uint8 (1 byte, unsigned, 0-255)
    - Alpha component: uint8 (1 byte, unsigned, 0-255, 0=transparent, 255=opaque)
    - Total data: 4 bytes
    - Struct format: "<BBBB" (little-endian, 4 unsigned 8-bit integers)

    C++ Reference:
    From color.cpp - WT_Background_Color::materialize():
        case 0xA3:  // Background RGBA color
            WT_Byte r, g, b, a;
            WD_CHECK(file.read(r));
            WD_CHECK(file.read(g));
            WD_CHECK(file.read(b));
            WD_CHECK(file.read(a));
            m_background = WT_RGBA32(r, g, b, a);

    Args:
        stream: Binary stream positioned after the 0xA3 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_background_color'
            - 'r': Red component (0-255)
            - 'g': Green component (0-255)
            - 'b': Blue component (0-255)
            - 'a': Alpha component (0-255)
            - 'bytes_read': 4

    Raises:
        ValueError: If stream doesn't contain 4 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<BBBB', 255, 255, 255, 255)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0xA3_background_color(stream)
        >>> result['r']
        255
        >>> result['g']
        255
        >>> result['b']
        255
        >>> result['a']
        255

    Notes:
        - Corresponds to WT_Background_Color::materialize() with opcode 0xA3 in C++
        - Background color affects overall drawing appearance
        - Alpha channel controls background transparency
        - Common values: (255, 255, 255, 255) for white, (0, 0, 0, 255) for black
        - Background color is typically set once at drawing start
    """
    data = stream.read(4)

    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes for opcode 0xA3 (SET_BACKGROUND_COLOR), got {len(data)} bytes")

    # Unpack four unsigned 8-bit integers (little-endian)
    r, g, b, a = struct.unpack('<BBBB', data)

    return {
        'type': 'set_background_color',
        'r': r,
        'g': g,
        'b': b,
        'a': a,
        'bytes_read': 4
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x23_color_rgb32():
    """Test suite for opcode 0x23 (SET_COLOR_RGB_32)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x23 (SET_COLOR_RGB_32)")
    print("=" * 70)

    # Test 1: Full opaque red
    print("\nTest 1: Full opaque red (255, 0, 0, 255)")
    data = struct.pack('<BBBB', 255, 0, 0, 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0x23_color_rgb32(stream)

    assert result['type'] == 'set_color_rgb32', f"Expected type='set_color_rgb32', got {result['type']}"
    assert result['r'] == 255, f"Expected r=255, got {result['r']}"
    assert result['g'] == 0, f"Expected g=0, got {result['g']}"
    assert result['b'] == 0, f"Expected b=0, got {result['b']}"
    assert result['a'] == 255, f"Expected a=255, got {result['a']}"
    assert result['bytes_read'] == 4
    print(f"  PASS: {result}")

    # Test 2: Semi-transparent blue
    print("\nTest 2: Semi-transparent blue (0, 0, 255, 128)")
    data = struct.pack('<BBBB', 0, 0, 255, 128)
    stream = io.BytesIO(data)
    result = parse_opcode_0x23_color_rgb32(stream)

    assert result['r'] == 0
    assert result['g'] == 0
    assert result['b'] == 255
    assert result['a'] == 128
    print(f"  PASS: {result}")

    # Test 3: Mixed color values
    print("\nTest 3: Mixed color (128, 64, 192, 200)")
    data = struct.pack('<BBBB', 128, 64, 192, 200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x23_color_rgb32(stream)

    assert result['r'] == 128
    assert result['g'] == 64
    assert result['b'] == 192
    assert result['a'] == 200
    print(f"  PASS: {result}")

    # Test 4: Black fully opaque
    print("\nTest 4: Black fully opaque (0, 0, 0, 255)")
    data = struct.pack('<BBBB', 0, 0, 0, 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0x23_color_rgb32(stream)

    assert result['r'] == 0
    assert result['g'] == 0
    assert result['b'] == 0
    assert result['a'] == 255
    print(f"  PASS: {result}")

    # Test 5: Fully transparent
    print("\nTest 5: Fully transparent (0, 0, 0, 0)")
    data = struct.pack('<BBBB', 0, 0, 0, 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x23_color_rgb32(stream)

    assert result['r'] == 0
    assert result['g'] == 0
    assert result['b'] == 0
    assert result['a'] == 0
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02')  # Only 2 bytes instead of 4
    try:
        result = parse_opcode_0x23_color_rgb32(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x23 (SET_COLOR_RGB_32): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x83_color_map_index():
    """Test suite for opcode 0x83 (SET_COLOR_MAP_INDEX)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x83 (SET_COLOR_MAP_INDEX)")
    print("=" * 70)

    # Test 1: Index 0 (first entry)
    print("\nTest 1: Color map index 0")
    data = struct.pack('<H', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x83_color_map_index(stream)

    assert result['type'] == 'set_color_map_index', f"Expected type='set_color_map_index', got {result['type']}"
    assert result['index'] == 0, f"Expected index=0, got {result['index']}"
    assert result['bytes_read'] == 2
    print(f"  PASS: {result}")

    # Test 2: Index 42
    print("\nTest 2: Color map index 42")
    data = struct.pack('<H', 42)
    stream = io.BytesIO(data)
    result = parse_opcode_0x83_color_map_index(stream)

    assert result['index'] == 42
    print(f"  PASS: {result}")

    # Test 3: Index 255
    print("\nTest 3: Color map index 255")
    data = struct.pack('<H', 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0x83_color_map_index(stream)

    assert result['index'] == 255
    print(f"  PASS: {result}")

    # Test 4: Large index value (1000)
    print("\nTest 4: Large color map index (1000)")
    data = struct.pack('<H', 1000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x83_color_map_index(stream)

    assert result['index'] == 1000
    print(f"  PASS: {result}")

    # Test 5: Maximum 16-bit value
    print("\nTest 5: Maximum index (65535)")
    data = struct.pack('<H', 65535)
    stream = io.BytesIO(data)
    result = parse_opcode_0x83_color_map_index(stream)

    assert result['index'] == 65535
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01')  # Only 1 byte instead of 2
    try:
        result = parse_opcode_0x83_color_map_index(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x83 (SET_COLOR_MAP_INDEX): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0xA3_background_color():
    """Test suite for opcode 0xA3 (SET_BACKGROUND_COLOR)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0xA3 (SET_BACKGROUND_COLOR)")
    print("=" * 70)

    # Test 1: White background
    print("\nTest 1: White background (255, 255, 255, 255)")
    data = struct.pack('<BBBB', 255, 255, 255, 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0xA3_background_color(stream)

    assert result['type'] == 'set_background_color', f"Expected type='set_background_color', got {result['type']}"
    assert result['r'] == 255, f"Expected r=255, got {result['r']}"
    assert result['g'] == 255, f"Expected g=255, got {result['g']}"
    assert result['b'] == 255, f"Expected b=255, got {result['b']}"
    assert result['a'] == 255, f"Expected a=255, got {result['a']}"
    assert result['bytes_read'] == 4
    print(f"  PASS: {result}")

    # Test 2: Black background
    print("\nTest 2: Black background (0, 0, 0, 255)")
    data = struct.pack('<BBBB', 0, 0, 0, 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0xA3_background_color(stream)

    assert result['r'] == 0
    assert result['g'] == 0
    assert result['b'] == 0
    assert result['a'] == 255
    print(f"  PASS: {result}")

    # Test 3: Gray background
    print("\nTest 3: Gray background (128, 128, 128, 255)")
    data = struct.pack('<BBBB', 128, 128, 128, 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0xA3_background_color(stream)

    assert result['r'] == 128
    assert result['g'] == 128
    assert result['b'] == 128
    assert result['a'] == 255
    print(f"  PASS: {result}")

    # Test 4: Semi-transparent background
    print("\nTest 4: Semi-transparent background (200, 200, 200, 128)")
    data = struct.pack('<BBBB', 200, 200, 200, 128)
    stream = io.BytesIO(data)
    result = parse_opcode_0xA3_background_color(stream)

    assert result['r'] == 200
    assert result['g'] == 200
    assert result['b'] == 200
    assert result['a'] == 128
    print(f"  PASS: {result}")

    # Test 5: Custom background color
    print("\nTest 5: Custom background (50, 100, 150, 255)")
    data = struct.pack('<BBBB', 50, 100, 150, 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0xA3_background_color(stream)

    assert result['r'] == 50
    assert result['g'] == 100
    assert result['b'] == 150
    assert result['a'] == 255
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\xFF\xFF')  # Only 2 bytes instead of 4
    try:
        result = parse_opcode_0xA3_background_color(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0xA3 (SET_BACKGROUND_COLOR): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 36 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 36: COLOR EXTENSIONS TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x23: SET_COLOR_RGB_32")
    print("  - 0x83: SET_COLOR_MAP_INDEX")
    print("  - 0xA3: SET_BACKGROUND_COLOR")
    print("=" * 70)

    test_opcode_0x23_color_rgb32()
    test_opcode_0x83_color_map_index()
    test_opcode_0xA3_background_color()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x23 (SET_COLOR_RGB_32): 6 tests passed")
    print("  - Opcode 0x83 (SET_COLOR_MAP_INDEX): 6 tests passed")
    print("  - Opcode 0xA3 (SET_BACKGROUND_COLOR): 6 tests passed")
    print("  - Total: 18 tests passed")
    print("\nEdge Cases Handled:")
    print("  - Full RGBA color specification with alpha channel")
    print("  - Transparent and opaque colors")
    print("  - Color map index ranging from 0 to 65535")
    print("  - Background colors with transparency")
    print("  - Insufficient data detection for all opcodes")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
