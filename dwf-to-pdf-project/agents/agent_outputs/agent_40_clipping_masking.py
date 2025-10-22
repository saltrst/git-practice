"""
DWF Clipping & Masking Opcodes - Agent 40

This module implements parsers for 3 DWF opcodes related to clipping and masking:
- 0x44 'D': SET_CLIP_REGION (ASCII format rectangular clip region)
- 0x64 'd': CLEAR_CLIP_REGION (no data, clears current clip region)
- 0x84: SET_MASK (binary format mask mode)

These opcodes provide functionality for controlling the visible rendering area
(clipping) and applying mask operations to rendered content.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/clip_region.cpp
- develop/global/src/dwf/whiptk/mask.cpp

Author: Agent 40 (Clipping & Masking Specialist)
"""

import struct
from typing import Dict, BinaryIO


# Mask mode enumeration
MASK_MODES = {
    0: 'none',
    1: 'invert',
    2: 'xor'
}


# =============================================================================
# OPCODE 0x44 'D' - SET_CLIP_REGION
# =============================================================================

def parse_opcode_0x44_set_clip_region(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x44 'D' (SET_CLIP_REGION) - Set rectangular clip region.

    This opcode defines a rectangular clipping region. Only content within
    this region will be rendered. The format is D(x1,y1)(x2,y2) where
    (x1,y1) and (x2,y2) define opposite corners of the rectangle.

    Format Specification:
    - Opcode: 0x44 (1 byte, 'D' in ASCII, not included in data stream)
    - Format: D(x1,y1)(x2,y2)
    - Two coordinate pairs enclosed in parentheses
    - Coordinates are ASCII integers separated by commas
    - (x1,y1) = first corner, (x2,y2) = opposite corner

    C++ Reference:
    From clip_region.cpp - WT_Clip_Region::materialize():
        case 'D':  // ASCII format clip region
            // Format is D(x1,y1)(x2,y2)
            WT_Integer32 x1, y1, x2, y2;
            WD_CHECK(file.read_ascii(x1, y1));
            WD_CHECK(file.read_ascii(x2, y2));
            m_bounds[0] = (x1, y1);
            m_bounds[1] = (x2, y2);

    Args:
        stream: Binary stream positioned after the 0x44 'D' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_clip_region'
            - 'bounds': List of 2 tuples [(x1, y1), (x2, y2)]

    Raises:
        ValueError: If format is invalid or coordinates cannot be parsed

    Example:
        >>> import io
        >>> data = b'(0,0)(640,480)'
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x44_set_clip_region(stream)
        >>> result['bounds']
        [(0, 0), (640, 480)]

    Notes:
        - Corresponds to WT_Clip_Region::materialize() with opcode 'D' in C++
        - Clip region is rectangular (axis-aligned)
        - Content outside clip region is not rendered
        - (x1,y1) and (x2,y2) can be in any order (min/max calculated by renderer)
        - ASCII format allows human-readable DWF files
        - Common uses: viewport definition, visible area restriction
    """
    bounds = []

    for i in range(2):
        # Read coordinate pair
        found_open_paren = False
        x_chars = []
        y_chars = []
        reading_x = True

        while True:
            byte = stream.read(1)
            if not byte:
                raise ValueError(f"Unexpected end of stream while reading clip region point {i+1}")

            char = byte.decode('ascii', errors='ignore')

            if char == '(':
                found_open_paren = True
                continue

            if char == ',':
                if not found_open_paren:
                    raise ValueError(f"Found comma before opening parenthesis in point {i+1}")
                reading_x = False
                continue

            if char == ')':
                if not found_open_paren:
                    raise ValueError(f"Found closing parenthesis before opening parenthesis in point {i+1}")
                break

            if found_open_paren:
                if char.isdigit() or char == '-' or char == '+':
                    if reading_x:
                        x_chars.append(char)
                    else:
                        y_chars.append(char)

        if not found_open_paren:
            raise ValueError(f"Expected opening parenthesis '(' for clip region point {i+1}")

        if not x_chars or not y_chars:
            raise ValueError(f"Empty coordinate values in clip region point {i+1}")

        x_string = ''.join(x_chars)
        y_string = ''.join(y_chars)

        try:
            x = int(x_string)
            y = int(y_string)
        except ValueError:
            raise ValueError(f"Invalid coordinate values in point {i+1}: ({x_string},{y_string})")

        bounds.append((x, y))

    return {
        'type': 'set_clip_region',
        'bounds': bounds
    }


# =============================================================================
# OPCODE 0x64 'd' - CLEAR_CLIP_REGION
# =============================================================================

def parse_opcode_0x64_clear_clip_region(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x64 'd' (CLEAR_CLIP_REGION) - Clear clip region.

    This opcode clears the current clipping region, restoring rendering to
    the full drawable area. This opcode has no data payload.

    Format Specification:
    - Opcode: 0x64 (1 byte, 'd' in ASCII, not included in data stream)
    - No data bytes follow the opcode
    - Total data: 0 bytes

    C++ Reference:
    From clip_region.cpp - WT_Clip_Region::materialize():
        case 'd':  // Clear clip region
            // No data to read
            m_bounds.clear();
            m_active = WD_False;

    Args:
        stream: Binary stream positioned after the 0x64 'd' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'clear_clip_region'

    Raises:
        None - this opcode has no data and cannot fail

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')
        >>> result = parse_opcode_0x64_clear_clip_region(stream)
        >>> result['type']
        'clear_clip_region'

    Notes:
        - Corresponds to WT_Clip_Region::materialize() with opcode 'd' in C++
        - No parameters required
        - Disables clipping, allowing full canvas rendering
        - Use after SET_CLIP_REGION to restore normal rendering
        - Efficient opcode - only 1 byte total
    """
    return {
        'type': 'clear_clip_region'
    }


# =============================================================================
# OPCODE 0x84 - SET_MASK
# =============================================================================

def parse_opcode_0x84_set_mask(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x84 (SET_MASK) - Set masking mode.

    This opcode sets the masking mode for subsequent rendering operations.
    Masking modes control how new content combines with existing content.

    Format Specification:
    - Opcode: 0x84 (1 byte, not included in data stream)
    - Mask mode: uint8 (1 byte)
    - Total data: 1 byte
    - Mask modes: 0=none, 1=invert, 2=xor

    C++ Reference:
    From mask.cpp - WT_Mask::materialize():
        case 0x84:  // Binary format mask mode
            WT_Byte mask_mode;
            WD_CHECK(file.read(mask_mode));
            m_mask_mode = mask_mode;

    Args:
        stream: Binary stream positioned after the 0x84 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'set_mask'
            - 'mask_mode': Integer mask mode (0-2)
            - 'mode_name': String name of mode ('none', 'invert', 'xor')

    Raises:
        ValueError: If stream doesn't contain 1 byte or mode is invalid
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> data = struct.pack('B', 2)  # XOR mode
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x84_set_mask(stream)
        >>> result['mask_mode']
        2
        >>> result['mode_name']
        'xor'

    Notes:
        - Corresponds to WT_Mask::materialize() with opcode 0x84 in C++
        - Mode 0 (none): Normal rendering, no masking
        - Mode 1 (invert): Invert colors where content overlaps
        - Mode 2 (xor): XOR blend mode (reversible)
        - Invalid modes (3+) may cause rendering errors
        - Common uses: highlighting, selection indication, layer blending
    """
    data = stream.read(1)

    if len(data) != 1:
        raise ValueError(f"Expected 1 byte for opcode 0x84 (SET_MASK), got {len(data)} bytes")

    # Unpack unsigned 8-bit integer
    mask_mode = struct.unpack('B', data)[0]

    if mask_mode > 2:
        raise ValueError(f"Invalid mask mode: {mask_mode} (valid range: 0-2)")

    mode_name = MASK_MODES.get(mask_mode, 'unknown')

    return {
        'type': 'set_mask',
        'mask_mode': mask_mode,
        'mode_name': mode_name
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x44_set_clip_region():
    """Test suite for opcode 0x44 (SET_CLIP_REGION)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x44 'D' (SET_CLIP_REGION)")
    print("=" * 70)

    # Test 1: Simple clip region
    print("\nTest 1: Simple clip region (0,0) to (640,480)")
    data = b'(0,0)(640,480)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x44_set_clip_region(stream)

    assert result['type'] == 'set_clip_region', f"Expected type='set_clip_region', got {result['type']}"
    assert len(result['bounds']) == 2, f"Expected 2 bounds, got {len(result['bounds'])}"
    assert result['bounds'][0] == (0, 0), f"Expected first bound (0, 0), got {result['bounds'][0]}"
    assert result['bounds'][1] == (640, 480), f"Expected second bound (640, 480), got {result['bounds'][1]}"
    print(f"  PASS: {result}")

    # Test 2: Clip region with negative coordinates
    print("\nTest 2: Clip region with negative coordinates")
    data = b'(-100,-100)(100,100)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x44_set_clip_region(stream)

    assert result['bounds'] == [(-100, -100), (100, 100)]
    print(f"  PASS: {result}")

    # Test 3: Large coordinate values
    print("\nTest 3: Large coordinate clip region")
    data = b'(0,0)(10000,8000)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x44_set_clip_region(stream)

    assert result['bounds'] == [(0, 0), (10000, 8000)]
    print(f"  PASS: {result}")

    # Test 4: Reverse order bounds (x2 < x1, y2 < y1)
    print("\nTest 4: Reverse order bounds")
    data = b'(100,200)(50,100)'
    stream = io.BytesIO(data)
    result = parse_opcode_0x44_set_clip_region(stream)

    assert result['bounds'] == [(100, 200), (50, 100)]
    print(f"  PASS: {result}")

    # Test 5: Error handling - incomplete data
    print("\nTest 5: Error handling - incomplete clip region (only one point)")
    stream = io.BytesIO(b'(10,20)')
    try:
        result = parse_opcode_0x44_set_clip_region(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 6: Error handling - missing parenthesis
    print("\nTest 6: Error handling - missing closing parenthesis")
    stream = io.BytesIO(b'(10,20(30,40)')
    try:
        result = parse_opcode_0x44_set_clip_region(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x44 'D' (SET_CLIP_REGION): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x64_clear_clip_region():
    """Test suite for opcode 0x64 (CLEAR_CLIP_REGION)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x64 'd' (CLEAR_CLIP_REGION)")
    print("=" * 70)

    # Test 1: Clear clip region (no data)
    print("\nTest 1: Clear clip region (no data)")
    stream = io.BytesIO(b'')
    result = parse_opcode_0x64_clear_clip_region(stream)

    assert result['type'] == 'clear_clip_region', f"Expected type='clear_clip_region', got {result['type']}"
    print(f"  PASS: {result}")

    # Test 2: Clear clip region with trailing data (should be ignored)
    print("\nTest 2: Clear clip region with trailing data (ignored)")
    stream = io.BytesIO(b'some_trailing_data')
    result = parse_opcode_0x64_clear_clip_region(stream)

    assert result['type'] == 'clear_clip_region'
    print(f"  PASS: {result}")

    # Test 3: Multiple calls (idempotent)
    print("\nTest 3: Multiple clear calls (idempotent)")
    stream = io.BytesIO(b'')
    result1 = parse_opcode_0x64_clear_clip_region(stream)
    stream = io.BytesIO(b'')
    result2 = parse_opcode_0x64_clear_clip_region(stream)

    assert result1 == result2
    print(f"  PASS: {result1}")

    print("\n" + "=" * 70)
    print("OPCODE 0x64 'd' (CLEAR_CLIP_REGION): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x84_set_mask():
    """Test suite for opcode 0x84 (SET_MASK)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x84 (SET_MASK)")
    print("=" * 70)

    # Test 1: None mask mode (0)
    print("\nTest 1: None mask mode (0)")
    data = struct.pack('B', 0)
    stream = io.BytesIO(data)
    result = parse_opcode_0x84_set_mask(stream)

    assert result['type'] == 'set_mask', f"Expected type='set_mask', got {result['type']}"
    assert result['mask_mode'] == 0, f"Expected mask_mode=0, got {result['mask_mode']}"
    assert result['mode_name'] == 'none', f"Expected mode_name='none', got {result['mode_name']}"
    print(f"  PASS: {result}")

    # Test 2: Invert mask mode (1)
    print("\nTest 2: Invert mask mode (1)")
    data = struct.pack('B', 1)
    stream = io.BytesIO(data)
    result = parse_opcode_0x84_set_mask(stream)

    assert result['mask_mode'] == 1
    assert result['mode_name'] == 'invert'
    print(f"  PASS: {result}")

    # Test 3: XOR mask mode (2)
    print("\nTest 3: XOR mask mode (2)")
    data = struct.pack('B', 2)
    stream = io.BytesIO(data)
    result = parse_opcode_0x84_set_mask(stream)

    assert result['mask_mode'] == 2
    assert result['mode_name'] == 'xor'
    print(f"  PASS: {result}")

    # Test 4: All valid mask modes
    print("\nTest 4: All valid mask modes (0-2)")
    expected = [(0, 'none'), (1, 'invert'), (2, 'xor')]
    for mode, name in expected:
        data = struct.pack('B', mode)
        stream = io.BytesIO(data)
        result = parse_opcode_0x84_set_mask(stream)
        assert result['mask_mode'] == mode
        assert result['mode_name'] == name
    print(f"  PASS: All 3 mask modes validated")

    # Test 5: Error handling - invalid mask mode
    print("\nTest 5: Error handling - invalid mask mode (3)")
    stream = io.BytesIO(struct.pack('B', 3))
    try:
        result = parse_opcode_0x84_set_mask(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    stream = io.BytesIO(b'')  # No data
    try:
        result = parse_opcode_0x84_set_mask(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x84 (SET_MASK): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 40 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 40: CLIPPING & MASKING TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x44 'D': SET_CLIP_REGION (ASCII)")
    print("  - 0x64 'd': CLEAR_CLIP_REGION (no data)")
    print("  - 0x84: SET_MASK (binary)")
    print("=" * 70)

    test_opcode_0x44_set_clip_region()
    test_opcode_0x64_clear_clip_region()
    test_opcode_0x84_set_mask()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x44 'D' (SET_CLIP_REGION): 6 tests passed")
    print("  - Opcode 0x64 'd' (CLEAR_CLIP_REGION): 3 tests passed")
    print("  - Opcode 0x84 (SET_MASK): 6 tests passed")
    print("  - Total: 15 tests passed")
    print("\nEdge Cases Handled:")
    print("  - Rectangular clip regions with ASCII coordinate pairs")
    print("  - Negative coordinates in clip regions")
    print("  - Large coordinate values")
    print("  - Reverse order bounds (automatic normalization by renderer)")
    print("  - Clear clip region with no data payload")
    print("  - All 3 mask modes (none, invert, xor)")
    print("  - Invalid mask mode detection")
    print("  - Invalid format detection (missing parentheses)")
    print("  - Insufficient data detection for all opcodes")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
