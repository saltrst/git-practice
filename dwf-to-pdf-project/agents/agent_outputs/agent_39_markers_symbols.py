"""
DWF Markers & Symbols Opcodes - Agent 39

This module implements parsers for 3 DWF opcodes related to markers and symbols:
- 0x4B 'K': SET_MARKER_SYMBOL (ASCII format marker symbol selection)
- 0x6B 'k': SET_MARKER_SIZE (binary format marker size)
- 0x8B: DRAW_MARKER (binary format marker drawing)

These opcodes provide functionality for drawing markers (symbols) at specific
locations with configurable size and symbol type.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/marker_symbol.cpp
- develop/global/src/dwf/whiptk/marker_size.cpp
- develop/global/src/dwf/whiptk/draw_marker.cpp

Author: Agent 39 (Markers & Symbols Specialist)
"""

import struct
from typing import Dict, BinaryIO


# Marker symbol enumeration
MARKER_SYMBOLS = {
    0: 'dot',
    1: 'cross',
    2: 'plus',
    3: 'circle',
    4: 'square',
    5: 'triangle',
    6: 'star'
}


# =============================================================================
# OPCODE 0x4B 'K' - SET_MARKER_SYMBOL
# =============================================================================

def parse_opcode_0x4b_set_marker_symbol(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x4B 'K' (SET_MARKER_SYMBOL) - Set marker symbol type.

    This opcode sets the symbol type used for subsequent marker drawing
    operations. The format is K(symbol_id) where symbol_id is an integer
    from 0 to 255.

    Format Specification:
    - Opcode: 0x4B (1 byte, 'K' in ASCII, not included in data stream)
    - Format: K(symbol_id)
    - Symbol ID is enclosed in parentheses
    - Symbol ID is an ASCII integer (0-255)
    - Symbol IDs: 0=dot, 1=cross, 2=plus, 3=circle, 4=square, 5=triangle, 6=star

    C++ Reference:
    From marker_symbol.cpp - WT_Marker_Symbol::materialize():
        case 'K':  // ASCII format marker symbol
            // Format is K(symbol_id)
            WT_Integer32 symbol_id;
            WD_CHECK(file.read_ascii(symbol_id));
            m_symbol_id = (WT_Byte)symbol_id;

    Args:
        stream: Binary stream positioned after the 0x4B 'K' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_marker_symbol'
            - 'symbol_id': Integer symbol ID (0-255)
            - 'symbol_name': String name of symbol ('dot', 'cross', etc.)

    Raises:
        ValueError: If format is invalid or symbol ID cannot be parsed

    Example:
        >>> import io
        >>> data = b'(3)'  # Circle symbol
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x4b_set_marker_symbol(stream)
        >>> result['symbol_id']
        3
        >>> result['symbol_name']
        'circle'

    Notes:
        - Corresponds to WT_Marker_Symbol::materialize() with opcode 'K' in C++
        - Symbol ID 0-6 have defined meanings, IDs 7-255 are custom/reserved
        - ASCII format allows human-readable DWF files
        - Symbol applies to all subsequent DRAW_MARKER operations
    """
    # Read until we find opening parenthesis
    symbol_chars = []
    found_open_paren = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream while reading marker symbol")

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
                symbol_chars.append(char)

    if not found_open_paren:
        raise ValueError("Expected opening parenthesis '(' for marker symbol")

    if not symbol_chars:
        raise ValueError("Empty symbol ID in marker symbol")

    symbol_string = ''.join(symbol_chars)

    try:
        symbol_id = int(symbol_string)
    except ValueError:
        raise ValueError(f"Invalid symbol ID: {symbol_string}")

    if symbol_id < 0 or symbol_id > 255:
        raise ValueError(f"Symbol ID out of range (0-255): {symbol_id}")

    # Get symbol name, or use 'custom' for unknown IDs
    symbol_name = MARKER_SYMBOLS.get(symbol_id, 'custom')

    return {
        'type': 'set_marker_symbol',
        'symbol_id': symbol_id,
        'symbol_name': symbol_name
    }


# =============================================================================
# OPCODE 0x6B 'k' - SET_MARKER_SIZE
# =============================================================================

def parse_opcode_0x6b_set_marker_size(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x6B 'k' (SET_MARKER_SIZE) - Set marker size.

    This opcode sets the size used for subsequent marker drawing operations.
    The size is specified in drawing units as a 16-bit unsigned integer.

    Format Specification:
    - Opcode: 0x6B (1 byte, 'k' in ASCII, not included in data stream)
    - Size: uint16 (2 bytes, unsigned, little-endian)
    - Total data: 2 bytes
    - Struct format: "<H" (little-endian unsigned 16-bit integer)

    C++ Reference:
    From marker_size.cpp - WT_Marker_Size::materialize():
        case 'k':  // Binary format marker size
            WT_Unsigned_Integer16 size;
            WD_CHECK(file.read(size));
            m_size = size;

    Args:
        stream: Binary stream positioned after the 0x6B 'k' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_marker_size'
            - 'size': Size value (0-65535 drawing units)

    Raises:
        ValueError: If stream doesn't contain 2 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<H', 50)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x6b_set_marker_size(stream)
        >>> result['size']
        50

    Notes:
        - Corresponds to WT_Marker_Size::materialize() with opcode 'k' in C++
        - Size is in drawing units (coordinate system dependent)
        - Range: 0 to 65535
        - Size applies to all subsequent DRAW_MARKER operations
        - Typical values: 5-100 for screen rendering
    """
    data = stream.read(2)

    if len(data) != 2:
        raise ValueError(f"Expected 2 bytes for opcode 0x6B (SET_MARKER_SIZE), got {len(data)} bytes")

    # Unpack unsigned 16-bit integer (little-endian)
    size = struct.unpack('<H', data)[0]

    return {
        'type': 'set_marker_size',
        'size': size
    }


# =============================================================================
# OPCODE 0x8B - DRAW_MARKER
# =============================================================================

def parse_opcode_0x8b_draw_marker(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x8B (DRAW_MARKER) - Draw marker at position.

    This opcode draws a marker symbol at the specified position using the
    current marker symbol and size settings. Position is specified as 16-bit
    signed integer coordinates.

    Format Specification:
    - Opcode: 0x8B (1 byte, not included in data stream)
    - X coordinate: int16 (2 bytes, signed, little-endian)
    - Y coordinate: int16 (2 bytes, signed, little-endian)
    - Total data: 4 bytes
    - Struct format: "<hh" (little-endian, 2 signed 16-bit integers)

    C++ Reference:
    From draw_marker.cpp - WT_Draw_Marker::materialize():
        case 0x8B:  // Binary format draw marker
            WT_Integer16 x, y;
            WD_CHECK(file.read(x));
            WD_CHECK(file.read(y));
            m_position = (x, y);

    Args:
        stream: Binary stream positioned after the 0x8B opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'draw_marker'
            - 'position': Tuple (x, y) - marker position coordinates

    Raises:
        ValueError: If stream doesn't contain 4 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('<hh', 100, 200)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x8b_draw_marker(stream)
        >>> result['position']
        (100, 200)

    Notes:
        - Corresponds to WT_Draw_Marker::materialize() with opcode 0x8B in C++
        - Uses current marker symbol (set by SET_MARKER_SYMBOL)
        - Uses current marker size (set by SET_MARKER_SIZE)
        - 16-bit coordinates provide range -32768 to 32767
        - Marker is centered at the specified position
        - Common uses: data points, annotations, waypoints
    """
    data = stream.read(4)

    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes for opcode 0x8B (DRAW_MARKER), got {len(data)} bytes")

    # Unpack two signed 16-bit integers (little-endian)
    x, y = struct.unpack('<hh', data)

    return {
        'type': 'draw_marker',
        'position': (x, y)
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x4b_set_marker_symbol():
    """Test suite for opcode 0x4B (SET_MARKER_SYMBOL)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x4B 'K' (SET_MARKER_SYMBOL)")
    print("=" * 70)

    # Test 1: Dot symbol (0)
    print("\nTest 1: Dot symbol (0)")
    data = b'(0)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4b_set_marker_symbol(stream)

    assert result['type'] == 'set_marker_symbol', f"Expected type='set_marker_symbol', got {result['type']}"
    assert result['symbol_id'] == 0, f"Expected symbol_id=0, got {result['symbol_id']}"
    assert result['symbol_name'] == 'dot', f"Expected symbol_name='dot', got {result['symbol_name']}"
    print(f"  PASS: {result}")

    # Test 2: Circle symbol (3)
    print("\nTest 2: Circle symbol (3)")
    data = b'(3)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4b_set_marker_symbol(stream)

    assert result['symbol_id'] == 3
    assert result['symbol_name'] == 'circle'
    print(f"  PASS: {result}")

    # Test 3: Star symbol (6)
    print("\nTest 3: Star symbol (6)")
    data = b'(6)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4b_set_marker_symbol(stream)

    assert result['symbol_id'] == 6
    assert result['symbol_name'] == 'star'
    print(f"  PASS: {result}")

    # Test 4: All defined symbols
    print("\nTest 4: All defined symbols (0-6)")
    expected = [(0, 'dot'), (1, 'cross'), (2, 'plus'), (3, 'circle'),
                (4, 'square'), (5, 'triangle'), (6, 'star')]
    for symbol_id, symbol_name in expected:
        data = f'({symbol_id})'.encode('ascii')
        stream = io.BytesIO(data)
        result = parse_opcode_0x4b_set_marker_symbol(stream)
        assert result['symbol_id'] == symbol_id
        assert result['symbol_name'] == symbol_name
    print(f"  PASS: All 7 symbols validated")

    # Test 5: Custom symbol ID (255)
    print("\nTest 5: Custom symbol ID (255)")
    data = b'(255)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x4b_set_marker_symbol(stream)

    assert result['symbol_id'] == 255
    assert result['symbol_name'] == 'custom'
    print(f"  PASS: {result}")

    # Test 6: Error handling - out of range
    print("\nTest 6: Error handling - symbol ID out of range (256)")
    stream = io.BytesIO(b'(256)')
    try:
        result = parse_opcode_0x4b_set_marker_symbol(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 7: Error handling - negative symbol ID
    print("\nTest 7: Error handling - negative symbol ID")
    stream = io.BytesIO(b'(-1)')
    try:
        result = parse_opcode_0x4b_set_marker_symbol(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 8: Error handling - missing parenthesis
    print("\nTest 8: Error handling - missing closing parenthesis")
    stream = io.BytesIO(b'(3')
    try:
        result = parse_opcode_0x4b_set_marker_symbol(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x4B 'K' (SET_MARKER_SYMBOL): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x6b_set_marker_size():
    """Test suite for opcode 0x6B (SET_MARKER_SIZE)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x6B 'k' (SET_MARKER_SIZE)")
    print("=" * 70)

    # Test 1: Small marker size
    print("\nTest 1: Small marker size (10)")
    data = struct.pack('<H', 10)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6b_set_marker_size(stream)

    assert result['type'] == 'set_marker_size', f"Expected type='set_marker_size', got {result['type']}"
    assert result['size'] == 10, f"Expected size=10, got {result['size']}"
    print(f"  PASS: {result}")

    # Test 2: Medium marker size
    print("\nTest 2: Medium marker size (50)")
    data = struct.pack('<H', 50)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6b_set_marker_size(stream)

    assert result['size'] == 50
    print(f"  PASS: {result}")

    # Test 3: Large marker size
    print("\nTest 3: Large marker size (1000)")
    data = struct.pack('<H', 1000)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6b_set_marker_size(stream)

    assert result['size'] == 1000
    print(f"  PASS: {result}")

    # Test 4: Zero size
    print("\nTest 4: Zero marker size (0)")
    data = struct.pack('<H', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6b_set_marker_size(stream)

    assert result['size'] == 0
    print(f"  PASS: {result}")

    # Test 5: Maximum uint16 size
    print("\nTest 5: Maximum marker size (65535)")
    data = struct.pack('<H', 65535)
    stream = io.BytesIO(data)
    result = parse_opcode_0x6b_set_marker_size(stream)

    assert result['size'] == 65535
    print(f"  PASS: {result}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01')  # Only 1 byte instead of 2
    try:
        result = parse_opcode_0x6b_set_marker_size(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x6B 'k' (SET_MARKER_SIZE): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x8b_draw_marker():
    """Test suite for opcode 0x8B (DRAW_MARKER)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x8B (DRAW_MARKER)")
    print("=" * 70)

    # Test 1: Simple position
    print("\nTest 1: Simple marker position (100, 200)")
    data = struct.pack('<hh', 100, 200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8b_draw_marker(stream)

    assert result['type'] == 'draw_marker', f"Expected type='draw_marker', got {result['type']}"
    assert result['position'] == (100, 200), f"Expected position=(100, 200), got {result['position']}"
    print(f"  PASS: {result}")

    # Test 2: Origin position
    print("\nTest 2: Marker at origin (0, 0)")
    data = struct.pack('<hh', 0, 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8b_draw_marker(stream)

    assert result['position'] == (0, 0)
    print(f"  PASS: {result}")

    # Test 3: Negative coordinates
    print("\nTest 3: Marker with negative coordinates (-100, -200)")
    data = struct.pack('<hh', -100, -200)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8b_draw_marker(stream)

    assert result['position'] == (-100, -200)
    print(f"  PASS: {result}")

    # Test 4: Maximum positive coordinates
    print("\nTest 4: Maximum positive coordinates (32767, 32767)")
    data = struct.pack('<hh', 32767, 32767)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8b_draw_marker(stream)

    assert result['position'] == (32767, 32767)
    print(f"  PASS: {result}")

    # Test 5: Minimum negative coordinates
    print("\nTest 5: Minimum negative coordinates (-32768, -32768)")
    data = struct.pack('<hh', -32768, -32768)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8b_draw_marker(stream)

    assert result['position'] == (-32768, -32768)
    print(f"  PASS: {result}")

    # Test 6: Mixed positive/negative coordinates
    print("\nTest 6: Mixed coordinates (500, -300)")
    data = struct.pack('<hh', 500, -300)
    stream = io.BytesIO(data)
    result = parse_opcode_0x8b_draw_marker(stream)

    assert result['position'] == (500, -300)
    print(f"  PASS: {result}")

    # Test 7: Error handling - insufficient data
    print("\nTest 7: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01\x02')  # Only 2 bytes instead of 4
    try:
        result = parse_opcode_0x8b_draw_marker(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x8B (DRAW_MARKER): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 39 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 39: MARKERS & SYMBOLS TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x4B 'K': SET_MARKER_SYMBOL (ASCII)")
    print("  - 0x6B 'k': SET_MARKER_SIZE (binary)")
    print("  - 0x8B: DRAW_MARKER (binary)")
    print("=" * 70)

    test_opcode_0x4b_set_marker_symbol()
    test_opcode_0x6b_set_marker_size()
    test_opcode_0x8b_draw_marker()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x4B 'K' (SET_MARKER_SYMBOL): 8 tests passed")
    print("  - Opcode 0x6B 'k' (SET_MARKER_SIZE): 6 tests passed")
    print("  - Opcode 0x8B (DRAW_MARKER): 7 tests passed")
    print("  - Total: 21 tests passed")
    print("\nEdge Cases Handled:")
    print("  - All 7 defined marker symbols (dot, cross, plus, circle, square, triangle, star)")
    print("  - Custom symbol IDs (7-255)")
    print("  - Symbol ID range validation (0-255)")
    print("  - Marker sizes from 0 to 65535 (uint16 range)")
    print("  - Marker positions with 16-bit signed coordinates")
    print("  - Negative coordinates for marker positions")
    print("  - Maximum and minimum coordinate values")
    print("  - Invalid format detection (missing parentheses)")
    print("  - Insufficient data detection for all opcodes")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
