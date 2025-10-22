"""
DWF Opcode 0x6C: Binary Line (32-bit coordinates)

This module implements parsing for DWF opcode 0x6C which represents
a binary line with 32-bit coordinate values.

Format Specification:
- Opcode: 0x6C (1 byte, not included in data)
- x1: int32 (4 bytes, little-endian)
- y1: int32 (4 bytes, little-endian)
- x2: int32 (4 bytes, little-endian)
- y2: int32 (4 bytes, little-endian)
- Total: 16 bytes

Reference: /home/user/git-practice/dwf-to-pdf-project/spec/opcode_reference_initial.json
"""

import struct
from io import BytesIO
from typing import Dict, Tuple, BinaryIO


def opcode_0x6C_binary_line(stream: BinaryIO) -> Dict[str, any]:
    """
    Parse DWF Opcode 0x6C (Binary Line) from stream.

    Reads 16 bytes from the stream and unpacks them as 4 signed 32-bit
    integers representing line coordinates (x1, y1, x2, y2).

    Args:
        stream: Binary stream positioned at the start of the line data
                (immediately after the 0x6C opcode byte)

    Returns:
        Dictionary containing:
        - 'type': 'line'
        - 'start': Tuple (x1, y1) representing the line start point
        - 'end': Tuple (x2, y2) representing the line end point

    Format:
        Struct: "<llll" (little-endian, 4 signed 32-bit integers)
        Total: 16 bytes

    Example:
        >>> stream = BytesIO(b'\\x00\\x00\\x00\\x00\\x64\\x00\\x00\\x00\\xC8\\x00\\x00\\x00\\x2C\\x01\\x00\\x00')
        >>> result = opcode_0x6C_binary_line(stream)
        >>> result
        {'type': 'line', 'start': (0, 100), 'end': (200, 300)}
    """
    # Hi protocol verification: Reading 16 bytes for opcode 0x6C binary line
    data = stream.read(16)

    if len(data) != 16:
        raise ValueError(f"Expected 16 bytes for opcode 0x6C, got {len(data)} bytes")

    # Unpack 4 signed 32-bit integers (little-endian)
    x1, y1, x2, y2 = struct.unpack("<llll", data)

    return {
        'type': 'line',
        'start': (x1, y1),
        'end': (x2, y2)
    }


def test_opcode_0x6C():
    """
    Test function for opcode 0x6C binary line parser.

    Tests with provided hex bytes representing a line from (0, 100) to (200, 300).
    """
    # Test data: line from (0, 100) to (200, 300)
    test_hex = b'\x00\x00\x00\x00\x64\x00\x00\x00\xC8\x00\x00\x00\x2C\x01\x00\x00'

    # Expected result
    expected = {
        'type': 'line',
        'start': (0, 100),
        'end': (200, 300)
    }

    # Create stream from test data
    stream = BytesIO(test_hex)

    # Parse the line
    result = opcode_0x6C_binary_line(stream)

    # Verify results
    print("Test: DWF Opcode 0x6C Binary Line")
    print("-" * 50)
    print(f"Input hex: {test_hex.hex()}")
    print(f"Expected:  {expected}")
    print(f"Result:    {result}")
    print(f"Match:     {result == expected}")

    # Detailed verification
    assert result['type'] == expected['type'], "Type mismatch"
    assert result['start'] == expected['start'], f"Start point mismatch: {result['start']} != {expected['start']}"
    assert result['end'] == expected['end'], f"End point mismatch: {result['end']} != {expected['end']}"

    print("\n✓ All tests passed!")

    # Additional test with negative coordinates
    print("\n" + "=" * 50)
    print("Additional Test: Negative Coordinates")
    print("-" * 50)

    # Line from (-100, -50) to (150, -200)
    # -100 = 0xFFFFFF9C, -50 = 0xFFFFFFCE, 150 = 0x00000096, -200 = 0xFFFFFF38
    test_hex_neg = b'\x9C\xFF\xFF\xFF\xCE\xFF\xFF\xFF\x96\x00\x00\x00\x38\xFF\xFF\xFF'

    stream_neg = BytesIO(test_hex_neg)
    result_neg = opcode_0x6C_binary_line(stream_neg)

    print(f"Input hex: {test_hex_neg.hex()}")
    print(f"Result:    {result_neg}")

    assert result_neg['start'] == (-100, -50), "Negative start coordinates incorrect"
    assert result_neg['end'] == (150, -200), "Negative end coordinates incorrect"

    print("\n✓ Negative coordinate test passed!")

    return True


if __name__ == "__main__":
    test_opcode_0x6C()
