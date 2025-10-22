"""
DWF Opcode Parsers for Macros and Layers (Agent 11)

This module implements parsers for 5 DWF opcodes related to macros and layers:
- 0x47 'G': SET_MACRO_INDEX (ASCII macro index)
- 0x4D 'M': DRAW_MACRO_DRAW (ASCII macro draw)
- 0x6D 'm': DRAW_MACRO_DRAW_32R (binary macro draw 32-bit)
- 0x8D: DRAW_MACRO_DRAW_16R (binary macro draw 16-bit)
- 0xAC: SET_LAYER (binary layer)

Macros reference predefined symbol/marker definitions. Layers organize drawing content.

Based on DWF Toolkit C++ source code:
- develop/global/src/dwf/whiptk/macro_index.cpp
- develop/global/src/dwf/whiptk/macro_draw.cpp
- develop/global/src/dwf/whiptk/layer.cpp
"""

import struct
import io
from typing import Dict, BinaryIO, List, Tuple


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def read_dwf_count(stream: BinaryIO) -> int:
    """
    Read a DWF count value (variable-length encoding).

    DWF uses a variable-length encoding for counts:
    - If first byte < 255: count = first byte
    - If first byte == 255: read next 2 bytes as uint16 for extended count

    Max value: 256 + 65535 = 65791

    Args:
        stream: Binary stream to read from

    Returns:
        The count value

    Raises:
        ValueError: If insufficient data available
    """
    count_byte = stream.read(1)
    if len(count_byte) != 1:
        raise ValueError("Insufficient data: could not read count byte")

    count = struct.unpack('<B', count_byte)[0]

    if count == 255:
        # Extended count mode
        extended_bytes = stream.read(2)
        if len(extended_bytes) != 2:
            raise ValueError("Insufficient data: could not read extended count")
        count = struct.unpack('<H', extended_bytes)[0]

    return count


def read_ascii_integer(stream: BinaryIO) -> int:
    """
    Read an ASCII-encoded integer from the stream.

    Reads characters until a non-digit character is found (space, comma, etc.).
    Handles negative numbers with leading '-' sign.

    Args:
        stream: Binary stream to read from

    Returns:
        The parsed integer value

    Raises:
        ValueError: If no valid integer found
    """
    chars = []
    first_char = True

    while True:
        byte = stream.read(1)
        if len(byte) != 1:
            break

        char = byte.decode('ascii', errors='ignore')

        # Allow negative sign at the start
        if first_char and char == '-':
            chars.append(char)
            first_char = False
            continue

        # Read digits
        if char.isdigit():
            chars.append(char)
            first_char = False
        elif chars:
            # Non-digit found after reading some digits, we're done
            # Put the character back by seeking backwards
            stream.seek(-1, io.SEEK_CUR)
            break
        elif char in ' \t\n\r':
            # Skip leading whitespace
            continue
        else:
            # Invalid character
            break

    if not chars or chars == ['-']:
        raise ValueError("No valid ASCII integer found")

    return int(''.join(chars))


# ============================================================================
# OPCODE 0x47 'G': SET_MACRO_INDEX
# ============================================================================

def parse_opcode_0x47_set_macro_index(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x47 'G' (SET_MACRO_INDEX).

    Sets the current macro index to reference a predefined macro/symbol.
    Macros are symbol definitions that can be drawn at various positions.

    Format:
    - ASCII integer: macro index value

    Args:
        stream: Binary stream positioned after the 'G' opcode byte

    Returns:
        Dictionary containing:
            - 'macro_index': The macro index (integer)

    Example:
        >>> import io
        >>> # Set macro index to 42
        >>> data = b'42 '
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x47_set_macro_index(stream)
        >>> result['macro_index']
        42
    """
    try:
        macro_index = read_ascii_integer(stream)

        if macro_index < 0:
            raise ValueError(f"Macro index cannot be negative: {macro_index}")

        return {
            'macro_index': macro_index
        }
    except Exception as e:
        raise ValueError(f"Failed to parse SET_MACRO_INDEX: {e}")


# ============================================================================
# OPCODE 0x4D 'M': DRAW_MACRO_DRAW (ASCII)
# ============================================================================

def parse_opcode_0x4d_draw_macro_ascii(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x4D 'M' (DRAW_MACRO_DRAW - ASCII format).

    Draws macro instances at specified positions using ASCII coordinate encoding.
    Each position represents where to draw the currently selected macro.

    Format:
    - ASCII integer: point count
    - For each point: x,y as ASCII integers

    Args:
        stream: Binary stream positioned after the 'M' opcode byte

    Returns:
        Dictionary containing:
            - 'point_count': Number of macro positions
            - 'points': List of (x, y) tuples as integers

    Example:
        >>> import io
        >>> # Draw macro at 3 positions
        >>> data = b'3 100 200 300 400 500 600 '
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x4d_draw_macro_ascii(stream)
        >>> result['point_count']
        3
        >>> result['points']
        [(100, 200), (300, 400), (500, 600)]
    """
    try:
        # Read point count
        count = read_ascii_integer(stream)

        if count < 0:
            raise ValueError(f"Point count cannot be negative: {count}")

        # Read points
        points = []
        for i in range(count):
            x = read_ascii_integer(stream)
            y = read_ascii_integer(stream)
            points.append((x, y))

        return {
            'point_count': count,
            'points': points
        }
    except Exception as e:
        raise ValueError(f"Failed to parse DRAW_MACRO_DRAW (ASCII): {e}")


# ============================================================================
# OPCODE 0x6D 'm': DRAW_MACRO_DRAW_32R
# ============================================================================

def parse_opcode_0x6d_draw_macro_32r(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x6D 'm' (DRAW_MACRO_DRAW_32R).

    Draws macro instances at specified positions using 32-bit binary encoding.
    More compact than ASCII for large coordinate values.

    Format:
    - 1 byte (uint8): point count (or 255 for extended)
    - If count == 255: 2 bytes (uint16): extended count
    - For each point: x,y as int32 pairs (little-endian)

    Args:
        stream: Binary stream positioned after the 'm' opcode byte

    Returns:
        Dictionary containing:
            - 'point_count': Number of macro positions
            - 'points': List of (x, y) tuples as int32 coordinates

    Example:
        >>> import io
        >>> # Draw macro at 2 positions
        >>> data = struct.pack('<B', 2)  # count = 2
        >>> data += struct.pack('<llll', 1000, 2000, 3000, 4000)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x6d_draw_macro_32r(stream)
        >>> result['point_count']
        2
        >>> result['points']
        [(1000, 2000), (3000, 4000)]
    """
    try:
        # Read count using DWF variable-length encoding
        count = read_dwf_count(stream)

        # Read points (x, y pairs as int32)
        points = []
        for i in range(count):
            coord_bytes = stream.read(8)  # 4 bytes x + 4 bytes y
            if len(coord_bytes) != 8:
                raise ValueError(f"Insufficient data for point {i+1}/{count}")

            x, y = struct.unpack('<ll', coord_bytes)
            points.append((x, y))

        return {
            'point_count': count,
            'points': points
        }
    except Exception as e:
        raise ValueError(f"Failed to parse DRAW_MACRO_DRAW_32R: {e}")


# ============================================================================
# OPCODE 0x8D: DRAW_MACRO_DRAW_16R
# ============================================================================

def parse_opcode_0x8d_draw_macro_16r(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x8D (DRAW_MACRO_DRAW_16R).

    Draws macro instances at specified positions using 16-bit binary encoding.
    Most compact format, suitable for smaller coordinate values.

    Format:
    - 1 byte (uint8): point count (no extended mode for 16-bit)
    - For each point: x,y as int16 pairs (little-endian)

    Note: This opcode should have been 0x0D but is 0x8D for historical reasons.

    Args:
        stream: Binary stream positioned after the 0x8D opcode byte

    Returns:
        Dictionary containing:
            - 'point_count': Number of macro positions
            - 'points': List of (x, y) tuples as int16 coordinates

    Example:
        >>> import io
        >>> # Draw macro at 3 positions
        >>> data = struct.pack('<B', 3)  # count = 3
        >>> data += struct.pack('<hhhhhh', 100, 200, 300, 400, 500, 600)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x8d_draw_macro_16r(stream)
        >>> result['point_count']
        3
        >>> result['points']
        [(100, 200), (300, 400), (500, 600)]
    """
    try:
        # Read count (single byte only, no extended count for 16-bit)
        count_byte = stream.read(1)
        if len(count_byte) != 1:
            raise ValueError("Insufficient data: could not read count byte")

        count = struct.unpack('<B', count_byte)[0]

        # Read points (x, y pairs as int16)
        points = []
        for i in range(count):
            coord_bytes = stream.read(4)  # 2 bytes x + 2 bytes y
            if len(coord_bytes) != 4:
                raise ValueError(f"Insufficient data for point {i+1}/{count}")

            x, y = struct.unpack('<hh', coord_bytes)
            points.append((x, y))

        return {
            'point_count': count,
            'points': points
        }
    except Exception as e:
        raise ValueError(f"Failed to parse DRAW_MACRO_DRAW_16R: {e}")


# ============================================================================
# OPCODE 0xAC: SET_LAYER
# ============================================================================

def parse_opcode_0xac_set_layer(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0xAC (SET_LAYER).

    Sets the current layer by index. Layers organize drawing content into
    logical groups (similar to layers in CAD applications).

    Format:
    - 1 byte (uint8): layer index (or 255 for extended)
    - If index == 255: 2 bytes (uint16): extended layer index

    Args:
        stream: Binary stream positioned after the 0xAC opcode byte

    Returns:
        Dictionary containing:
            - 'layer_index': The layer index (0 to 65791)

    Example:
        >>> import io
        >>> # Set layer to index 5
        >>> data = struct.pack('<B', 5)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0xac_set_layer(stream)
        >>> result['layer_index']
        5
    """
    try:
        # Read layer index using DWF variable-length encoding
        layer_index = read_dwf_count(stream)

        return {
            'layer_index': layer_index
        }
    except Exception as e:
        raise ValueError(f"Failed to parse SET_LAYER: {e}")


# ============================================================================
# TEST SUITE
# ============================================================================

def test_opcode_0x47_set_macro_index():
    """Test suite for opcode 0x47 (SET_MACRO_INDEX)."""
    print("=" * 70)
    print("TESTING OPCODE 0x47 'G' (SET_MACRO_INDEX)")
    print("=" * 70)

    # Test 1: Simple macro index
    print("\nTest 1: Simple macro index (42)")
    data = b'42 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x47_set_macro_index(stream)
    assert result['macro_index'] == 42, f"Expected 42, got {result['macro_index']}"
    print(f"  PASS: {result}")

    # Test 2: Macro index 0
    print("\nTest 2: Macro index 0")
    data = b'0 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x47_set_macro_index(stream)
    assert result['macro_index'] == 0
    print(f"  PASS: {result}")

    # Test 3: Large macro index
    print("\nTest 3: Large macro index (65535)")
    data = b'65535 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x47_set_macro_index(stream)
    assert result['macro_index'] == 65535
    print(f"  PASS: {result}")

    # Test 4: Error handling - negative value
    print("\nTest 4: Error handling - negative value")
    data = b'-5 '
    stream = io.BytesIO(data)
    try:
        result = parse_opcode_0x47_set_macro_index(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x47 (SET_MACRO_INDEX): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x4d_draw_macro_ascii():
    """Test suite for opcode 0x4D (DRAW_MACRO_DRAW ASCII)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x4D 'M' (DRAW_MACRO_DRAW ASCII)")
    print("=" * 70)

    # Test 1: Single macro position
    print("\nTest 1: Single macro position")
    data = b'1 100 200 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x4d_draw_macro_ascii(stream)
    assert result['point_count'] == 1
    assert result['points'] == [(100, 200)]
    print(f"  PASS: {result}")

    # Test 2: Multiple macro positions
    print("\nTest 2: Three macro positions")
    data = b'3 100 200 300 400 500 600 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x4d_draw_macro_ascii(stream)
    assert result['point_count'] == 3
    assert result['points'] == [(100, 200), (300, 400), (500, 600)]
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Negative coordinates")
    data = b'2 -100 -200 100 200 '
    stream = io.BytesIO(data)
    result = parse_opcode_0x4d_draw_macro_ascii(stream)
    assert result['points'] == [(-100, -200), (100, 200)]
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("OPCODE 0x4D (DRAW_MACRO_DRAW ASCII): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x6d_draw_macro_32r():
    """Test suite for opcode 0x6D (DRAW_MACRO_DRAW_32R)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x6D 'm' (DRAW_MACRO_DRAW_32R)")
    print("=" * 70)

    # Test 1: Single macro position
    print("\nTest 1: Single macro position")
    data = struct.pack('<B', 1)
    data += struct.pack('<ll', 1000, 2000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6d_draw_macro_32r(stream)
    assert result['point_count'] == 1
    assert result['points'] == [(1000, 2000)]
    print(f"  PASS: {result}")

    # Test 2: Multiple positions
    print("\nTest 2: Four macro positions")
    data = struct.pack('<B', 4)
    data += struct.pack('<llllllll', 100, 200, 300, 400, 500, 600, 700, 800)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6d_draw_macro_32r(stream)
    assert result['point_count'] == 4
    assert len(result['points']) == 4
    assert result['points'][0] == (100, 200)
    assert result['points'][3] == (700, 800)
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Negative coordinates")
    data = struct.pack('<B', 2)
    data += struct.pack('<llll', -5000, -10000, 5000, 10000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6d_draw_macro_32r(stream)
    assert result['points'] == [(-5000, -10000), (5000, 10000)]
    print(f"  PASS: {result}")

    # Test 4: Extended count
    print("\nTest 4: Extended count (300 positions)")
    data = struct.pack('<B', 255)  # trigger extended mode
    data += struct.pack('<H', 300)  # extended count
    for i in range(300):
        data += struct.pack('<ll', i * 100, i * 200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6d_draw_macro_32r(stream)
    assert result['point_count'] == 300
    assert len(result['points']) == 300
    assert result['points'][0] == (0, 0)
    assert result['points'][299] == (29900, 59800)
    print(f"  PASS: Extended count with {result['point_count']} positions")

    # Test 5: Error handling - insufficient data
    print("\nTest 5: Error handling - insufficient data")
    data = struct.pack('<B', 3)
    data += struct.pack('<ll', 100, 200)  # only 1 point instead of 3
    stream = io.BytesIO(data)
    try:
        result = parse_opcode_0x6d_draw_macro_32r(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x6D (DRAW_MACRO_DRAW_32R): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x8d_draw_macro_16r():
    """Test suite for opcode 0x8D (DRAW_MACRO_DRAW_16R)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x8D (DRAW_MACRO_DRAW_16R)")
    print("=" * 70)

    # Test 1: Single macro position
    print("\nTest 1: Single macro position")
    data = struct.pack('<B', 1)
    data += struct.pack('<hh', 100, 200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8d_draw_macro_16r(stream)
    assert result['point_count'] == 1
    assert result['points'] == [(100, 200)]
    print(f"  PASS: {result}")

    # Test 2: Multiple positions
    print("\nTest 2: Five macro positions")
    data = struct.pack('<B', 5)
    data += struct.pack('<hhhhhhhhhh', 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8d_draw_macro_16r(stream)
    assert result['point_count'] == 5
    assert len(result['points']) == 5
    assert result['points'][0] == (10, 20)
    assert result['points'][4] == (90, 100)
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Negative coordinates (16-bit range)")
    data = struct.pack('<B', 2)
    data += struct.pack('<hhhh', -1000, -2000, 1000, 2000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8d_draw_macro_16r(stream)
    assert result['points'] == [(-1000, -2000), (1000, 2000)]
    print(f"  PASS: {result}")

    # Test 4: Maximum 16-bit values
    print("\nTest 4: Maximum 16-bit signed values")
    data = struct.pack('<B', 2)
    data += struct.pack('<hhhh', 32767, 32767, -32768, -32768)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8d_draw_macro_16r(stream)
    assert result['points'] == [(32767, 32767), (-32768, -32768)]
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("OPCODE 0x8D (DRAW_MACRO_DRAW_16R): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0xac_set_layer():
    """Test suite for opcode 0xAC (SET_LAYER)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0xAC (SET_LAYER)")
    print("=" * 70)

    # Test 1: Layer 0
    print("\nTest 1: Layer 0")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0xac_set_layer(stream)
    assert result['layer_index'] == 0
    print(f"  PASS: {result}")

    # Test 2: Layer 42
    print("\nTest 2: Layer 42")
    data = struct.pack('<B', 42)
    stream = io.BytesIO(data)
    result = parse_opcode_0xac_set_layer(stream)
    assert result['layer_index'] == 42
    print(f"  PASS: {result}")

    # Test 3: Layer 254 (max without extended)
    print("\nTest 3: Layer 254 (max without extended mode)")
    data = struct.pack('<B', 254)
    stream = io.BytesIO(data)
    result = parse_opcode_0xac_set_layer(stream)
    assert result['layer_index'] == 254
    print(f"  PASS: {result}")

    # Test 4: Extended layer index
    print("\nTest 4: Extended layer index (5000)")
    data = struct.pack('<B', 255)  # trigger extended
    data += struct.pack('<H', 5000)
    stream = io.BytesIO(data)
    result = parse_opcode_0xac_set_layer(stream)
    assert result['layer_index'] == 5000
    print(f"  PASS: {result}")

    # Test 5: Maximum extended layer
    print("\nTest 5: Maximum extended layer (65535)")
    data = struct.pack('<B', 255)
    data += struct.pack('<H', 65535)
    stream = io.BytesIO(data)
    result = parse_opcode_0xac_set_layer(stream)
    assert result['layer_index'] == 65535
    print(f"  PASS: {result}")

    print("\n" + "=" * 70)
    print("OPCODE 0xAC (SET_LAYER): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites."""
    print("\n" + "=" * 70)
    print("DWF MACRO & LAYER OPCODE PARSER TEST SUITE - AGENT 11")
    print("=" * 70)
    print("Testing 5 opcodes:")
    print("  - 0x47 'G': SET_MACRO_INDEX")
    print("  - 0x4D 'M': DRAW_MACRO_DRAW (ASCII)")
    print("  - 0x6D 'm': DRAW_MACRO_DRAW_32R")
    print("  - 0x8D: DRAW_MACRO_DRAW_16R")
    print("  - 0xAC: SET_LAYER")
    print("=" * 70)

    test_opcode_0x47_set_macro_index()
    test_opcode_0x4d_draw_macro_ascii()
    test_opcode_0x6d_draw_macro_32r()
    test_opcode_0x8d_draw_macro_16r()
    test_opcode_0xac_set_layer()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x47 (SET_MACRO_INDEX): 4 tests passed")
    print("  - Opcode 0x4D (DRAW_MACRO_DRAW ASCII): 3 tests passed")
    print("  - Opcode 0x6D (DRAW_MACRO_DRAW_32R): 5 tests passed")
    print("  - Opcode 0x8D (DRAW_MACRO_DRAW_16R): 4 tests passed")
    print("  - Opcode 0xAC (SET_LAYER): 5 tests passed")
    print("  - Total: 21 tests passed")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
