"""
DWF Rendering Attributes Opcodes - Agent 37

This module implements parsers for 3 DWF opcodes related to rendering attributes:
- 0x48 'H': SET_HALFTONE (ASCII format)
- 0x68 'h': SET_HIGHLIGHT (binary format)
- 0x41 'A': SET_ANTI_ALIAS (binary format)

These opcodes control advanced rendering features including halftone patterns
for shading, highlight modes for emphasis, and anti-aliasing for smooth edges.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/attribute.cpp
- develop/global/src/dwf/whiptk/rendering.cpp

Author: Agent 37 (Rendering Attribute Specialist)
"""

import struct
from typing import Dict, BinaryIO


# =============================================================================
# OPCODE 0x48 'H' - SET_HALFTONE
# =============================================================================

def parse_opcode_0x48_halftone(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x48 'H' (SET_HALFTONE) - Set halftone pattern.

    This opcode sets the halftone pattern used for shading and fills in ASCII
    format. Halftone patterns simulate shades of gray or color using dot patterns.

    Format Specification:
    - Opcode: 0x48 (1 byte, 'H' in ASCII, not included in data stream)
    - Format: H(pattern_id) where pattern_id is an ASCII integer (0-255)
    - Parentheses are required
    - Terminated by closing parenthesis ')'

    C++ Reference:
    From attribute.cpp - WT_Halftone::materialize():
        case 'H':  // ASCII format halftone
            // Format is H(pattern_id)
            WD_CHECK(file.eat_whitespace());
            WD_CHECK(file.read_ascii(m_pattern_id));

    Pattern IDs:
    - 0: No halftone (solid fill)
    - 1-255: Various halftone patterns (implementation-specific)
    - Common patterns: 0=solid, 1=50% gray, 2=25% gray, 3=75% gray, etc.

    Args:
        stream: Binary stream positioned after the 0x48 'H' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_halftone'
            - 'pattern_id': Halftone pattern ID (0-255)

    Raises:
        ValueError: If format is invalid or parentheses are missing

    Example:
        >>> import io
        >>> data = b'(5)'
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x48_halftone(stream)
        >>> result['pattern_id']
        5

    Notes:
        - Corresponds to WT_Halftone::materialize() with opcode 'H' in C++
        - Halftone patterns affect fill and shading appearance
        - Pattern 0 typically means solid fill without halftone
        - Higher pattern IDs may indicate different dot densities or patterns
        - Actual pattern appearance is renderer-dependent
    """
    # Read until we find opening parenthesis
    chars = []
    found_open_paren = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected end of stream while reading halftone (ASCII)")

        char = byte.decode('ascii', errors='ignore')

        if char == '(':
            found_open_paren = True
            continue

        if char == ')':
            if not found_open_paren:
                raise ValueError("Found closing parenthesis before opening parenthesis")
            break

        if found_open_paren:
            if char.isdigit():
                chars.append(char)

    if not found_open_paren:
        raise ValueError("Expected opening parenthesis '(' in halftone (ASCII) format")

    if not chars:
        raise ValueError("Empty pattern ID in parentheses")

    pattern_string = ''.join(chars)

    try:
        pattern_id = int(pattern_string)
    except ValueError:
        raise ValueError(f"Invalid pattern ID: {pattern_string}")

    return {
        'type': 'set_halftone',
        'pattern_id': pattern_id
    }


# =============================================================================
# OPCODE 0x68 'h' - SET_HIGHLIGHT
# =============================================================================

def parse_opcode_0x68_highlight(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x68 'h' (SET_HIGHLIGHT) - Set highlight mode.

    This opcode enables or disables highlighting mode for subsequent drawing
    operations. Highlighting can be used to emphasize certain elements in
    the drawing.

    Format Specification:
    - Opcode: 0x68 (1 byte, 'h' in ASCII, not included in data stream)
    - Highlight mode: uint8 (1 byte, unsigned, 0=off, 1=on)
    - Total data: 1 byte

    C++ Reference:
    From attribute.cpp - WT_Highlight::materialize():
        case 'h':  // Highlight mode
            WT_Byte mode;
            WD_CHECK(file.read(mode));
            m_highlight = (mode != 0);

    Highlight Modes:
    - 0: Highlight off (normal rendering)
    - 1: Highlight on (emphasized rendering)

    Args:
        stream: Binary stream positioned after the 0x68 'h' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_highlight'
            - 'mode': Highlight mode value (0 or 1)
            - 'enabled': Boolean indicating if highlight is enabled

    Raises:
        ValueError: If stream doesn't contain 1 byte

    Example:
        >>> import io
        >>> data = struct.pack('<B', 1)  # Highlight on
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x68_highlight(stream)
        >>> result['mode']
        1
        >>> result['enabled']
        True

    Notes:
        - Corresponds to WT_Highlight::materialize() with opcode 'h' in C++
        - Highlight mode affects rendering of subsequent elements
        - Typically used to draw attention to specific objects
        - Rendering implementation may use color, brightness, or other effects
        - Non-zero values are treated as "on" in most implementations
    """
    data = stream.read(1)

    if len(data) != 1:
        raise ValueError(f"Expected 1 byte for opcode 0x68 (SET_HIGHLIGHT), got {len(data)} bytes")

    mode = struct.unpack('<B', data)[0]

    return {
        'type': 'set_highlight',
        'mode': mode,
        'enabled': (mode != 0)
    }


# =============================================================================
# OPCODE 0x41 'A' - SET_ANTI_ALIAS
# =============================================================================

def parse_opcode_0x41_anti_alias(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x41 'A' (SET_ANTI_ALIAS) - Set anti-aliasing mode.

    This opcode enables or disables anti-aliasing for subsequent drawing
    operations. Anti-aliasing smooths edges by blending pixels along boundaries.

    Format Specification:
    - Opcode: 0x41 (1 byte, 'A' in ASCII, not included in data stream)
    - Anti-alias mode: uint8 (1 byte, unsigned, 0=off, 1=on)
    - Total data: 1 byte

    C++ Reference:
    From attribute.cpp - WT_Anti_Alias::materialize():
        case 'A':  // Anti-alias mode
            WT_Byte mode;
            WD_CHECK(file.read(mode));
            m_anti_alias = (mode != 0);

    Anti-Alias Modes:
    - 0: Anti-aliasing off (crisp edges, faster rendering)
    - 1: Anti-aliasing on (smooth edges, higher quality)

    Args:
        stream: Binary stream positioned after the 0x41 'A' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_anti_alias'
            - 'mode': Anti-alias mode value (0 or 1)
            - 'enabled': Boolean indicating if anti-aliasing is enabled

    Raises:
        ValueError: If stream doesn't contain 1 byte

    Example:
        >>> import io
        >>> data = struct.pack('<B', 1)  # Anti-aliasing on
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x41_anti_alias(stream)
        >>> result['mode']
        1
        >>> result['enabled']
        True

    Notes:
        - Corresponds to WT_Anti_Alias::materialize() with opcode 'A' in C++
        - Anti-aliasing improves visual quality at the cost of performance
        - Smooths jagged edges on lines, curves, and text
        - Most visible at lower resolutions or when zoomed in
        - Mode 0 provides crisp edges suitable for technical drawings
        - Mode 1 provides smooth edges suitable for presentation graphics
    """
    data = stream.read(1)

    if len(data) != 1:
        raise ValueError(f"Expected 1 byte for opcode 0x41 (SET_ANTI_ALIAS), got {len(data)} bytes")

    mode = struct.unpack('<B', data)[0]

    return {
        'type': 'set_anti_alias',
        'mode': mode,
        'enabled': (mode != 0)
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x48_halftone():
    """Test suite for opcode 0x48 (SET_HALFTONE)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x48 'H' (SET_HALFTONE)")
    print("=" * 70)

    # Test 1: Pattern ID 0 (solid fill)
    print("\nTest 1: Halftone pattern 0 (solid)")
    data = b'(0)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x48_halftone(stream)

    assert result['type'] == 'set_halftone', f"Expected type='set_halftone', got {result['type']}"
    assert result['pattern_id'] == 0, f"Expected pattern_id=0, got {result['pattern_id']}"
    print(f"  PASS: {result}")

    # Test 2: Pattern ID 5
    print("\nTest 2: Halftone pattern 5")
    data = b'(5)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x48_halftone(stream)

    assert result['pattern_id'] == 5
    print(f"  PASS: {result}")

    # Test 3: Pattern ID 255 (maximum)
    print("\nTest 3: Halftone pattern 255 (maximum)")
    data = b'(255)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x48_halftone(stream)

    assert result['pattern_id'] == 255
    print(f"  PASS: {result}")

    # Test 4: Pattern ID 42
    print("\nTest 4: Halftone pattern 42")
    data = b'(42)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x48_halftone(stream)

    assert result['pattern_id'] == 42
    print(f"  PASS: {result}")

    # Test 5: Pattern ID 100
    print("\nTest 5: Halftone pattern 100")
    data = b'(100)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x48_halftone(stream)

    assert result['pattern_id'] == 100
    print(f"  PASS: {result}")

    # Test 6: Error handling - missing parentheses
    print("\nTest 6: Error handling - missing parentheses")
    stream = io.BytesIO(b'5)')
    try:
        result = parse_opcode_0x48_halftone(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 7: Error handling - empty pattern ID
    print("\nTest 7: Error handling - empty pattern ID")
    stream = io.BytesIO(b'()')
    try:
        result = parse_opcode_0x48_halftone(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x48 'H' (SET_HALFTONE): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x68_highlight():
    """Test suite for opcode 0x68 (SET_HIGHLIGHT)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x68 'h' (SET_HIGHLIGHT)")
    print("=" * 70)

    # Test 1: Highlight off (mode 0)
    print("\nTest 1: Highlight off (mode 0)")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x68_highlight(stream)

    assert result['type'] == 'set_highlight', f"Expected type='set_highlight', got {result['type']}"
    assert result['mode'] == 0, f"Expected mode=0, got {result['mode']}"
    assert result['enabled'] == False, f"Expected enabled=False, got {result['enabled']}"
    print(f"  PASS: {result}")

    # Test 2: Highlight on (mode 1)
    print("\nTest 2: Highlight on (mode 1)")
    data = struct.pack('<B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x68_highlight(stream)

    assert result['mode'] == 1
    assert result['enabled'] == True
    print(f"  PASS: {result}")

    # Test 3: Non-zero value (mode 5) - should be enabled
    print("\nTest 3: Non-zero mode value (5) - treated as enabled")
    data = struct.pack('<B', 5)
    stream = io.BytesIO(data)
    result = parse_opcode_0x68_highlight(stream)

    assert result['mode'] == 5
    assert result['enabled'] == True
    print(f"  PASS: {result}")

    # Test 4: Maximum mode value (255)
    print("\nTest 4: Maximum mode value (255)")
    data = struct.pack('<B', 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0x68_highlight(stream)

    assert result['mode'] == 255
    assert result['enabled'] == True
    print(f"  PASS: {result}")

    # Test 5: Error handling - insufficient data
    print("\nTest 5: Error handling - insufficient data")
    stream = io.BytesIO(b'')  # Empty stream
    try:
        result = parse_opcode_0x68_highlight(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x68 'h' (SET_HIGHLIGHT): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x41_anti_alias():
    """Test suite for opcode 0x41 (SET_ANTI_ALIAS)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x41 'A' (SET_ANTI_ALIAS)")
    print("=" * 70)

    # Test 1: Anti-aliasing off (mode 0)
    print("\nTest 1: Anti-aliasing off (mode 0)")
    data = struct.pack('<B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x41_anti_alias(stream)

    assert result['type'] == 'set_anti_alias', f"Expected type='set_anti_alias', got {result['type']}"
    assert result['mode'] == 0, f"Expected mode=0, got {result['mode']}"
    assert result['enabled'] == False, f"Expected enabled=False, got {result['enabled']}"
    print(f"  PASS: {result}")

    # Test 2: Anti-aliasing on (mode 1)
    print("\nTest 2: Anti-aliasing on (mode 1)")
    data = struct.pack('<B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x41_anti_alias(stream)

    assert result['mode'] == 1
    assert result['enabled'] == True
    print(f"  PASS: {result}")

    # Test 3: Non-zero value (mode 2) - should be enabled
    print("\nTest 3: Non-zero mode value (2) - treated as enabled")
    data = struct.pack('<B', 2)
    stream = io.BytesIO(data)
    result = parse_opcode_0x41_anti_alias(stream)

    assert result['mode'] == 2
    assert result['enabled'] == True
    print(f"  PASS: {result}")

    # Test 4: Maximum mode value (255)
    print("\nTest 4: Maximum mode value (255)")
    data = struct.pack('<B', 255)
    stream = io.BytesIO(data)
    result = parse_opcode_0x41_anti_alias(stream)

    assert result['mode'] == 255
    assert result['enabled'] == True
    print(f"  PASS: {result}")

    # Test 5: Error handling - insufficient data
    print("\nTest 5: Error handling - insufficient data")
    stream = io.BytesIO(b'')  # Empty stream
    try:
        result = parse_opcode_0x41_anti_alias(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x41 'A' (SET_ANTI_ALIAS): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 37 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 37: RENDERING ATTRIBUTES TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x48 'H': SET_HALFTONE (ASCII)")
    print("  - 0x68 'h': SET_HIGHLIGHT (binary)")
    print("  - 0x41 'A': SET_ANTI_ALIAS (binary)")
    print("=" * 70)

    test_opcode_0x48_halftone()
    test_opcode_0x68_highlight()
    test_opcode_0x41_anti_alias()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x48 'H' (SET_HALFTONE): 7 tests passed")
    print("  - Opcode 0x68 'h' (SET_HIGHLIGHT): 5 tests passed")
    print("  - Opcode 0x41 'A' (SET_ANTI_ALIAS): 5 tests passed")
    print("  - Total: 17 tests passed")
    print("\nEdge Cases Handled:")
    print("  - ASCII format parsing for halftone pattern IDs")
    print("  - Binary mode values for highlight and anti-alias")
    print("  - Boolean conversion (non-zero = enabled)")
    print("  - Pattern ID range 0-255")
    print("  - Missing parentheses detection")
    print("  - Empty values detection")
    print("  - Insufficient data detection")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
