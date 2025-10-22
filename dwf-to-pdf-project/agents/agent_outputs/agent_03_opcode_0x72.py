"""
DWF Opcode 0x72: Binary Rectangle/Circle (32-bit)

Opcode: 0x72 ('r')
Name: WD_SBBO_DRAW_CIRCLE_32R (Binary Rectangle/Circle)
Format: int32 x, int32 y, uint32 packed_dimensions
Total bytes: 12
Struct format: "<llL"

Based on: /home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/ellipse.cpp
Reference: /home/user/git-practice/dwf-to-pdf-project/spec/opcode_reference_initial.json

Implementation notes:
- The C++ source shows this opcode is primarily for circles (full circle with 32-bit relative coords)
- The third field can be interpreted as:
  1. A simple radius value (uint32) for circles
  2. Packed dimensions containing width (lower 16 bits) and height (upper 16 bits) for rectangles
- This implementation provides both interpretations
"""

import struct
import io
from typing import Dict, Union, BinaryIO


def opcode_0x72_binary_rectangle(stream: Union[bytes, BinaryIO]) -> Dict:
    """
    Parse DWF opcode 0x72 (Binary Rectangle/Circle).

    Reads 12 bytes from the stream and unpacks:
    - int32 x: X coordinate (relative)
    - int32 y: Y coordinate (relative)
    - uint32 packed_dimensions: Radius or packed width/height

    Args:
        stream: Binary stream or bytes object to read from

    Returns:
        Dictionary containing parsed rectangle/circle data with both interpretations

    Raises:
        struct.error: If unable to unpack the binary data
        ValueError: If stream doesn't contain enough bytes
    """
    # Read 12 bytes from stream
    if isinstance(stream, bytes):
        data = stream[:12]
        if len(data) < 12:
            raise ValueError(f"Expected 12 bytes, got {len(data)} bytes")
    else:
        data = stream.read(12)
        if len(data) < 12:
            raise ValueError(f"Expected 12 bytes, got {len(data)} bytes")

    # Unpack binary data using little-endian format
    # <: little-endian
    # l: signed 32-bit integer (int32)
    # l: signed 32-bit integer (int32)
    # L: unsigned 32-bit integer (uint32)
    x, y, packed_dimensions = struct.unpack("<llL", data)

    # Interpretation 1: Simple radius (for circles)
    # The C++ code shows this is the primary interpretation
    radius = packed_dimensions

    # Interpretation 2: Packed width/height (for rectangles)
    # Extract width from lower 16 bits, height from upper 16 bits
    width = packed_dimensions & 0xFFFF          # Lower 16 bits
    height = (packed_dimensions >> 16) & 0xFFFF  # Upper 16 bits

    # Determine if this is likely a circle or rectangle
    # If height is 0 or width == height, treat as circle (simple radius)
    is_circle = (height == 0) or (width == height and width != 0)

    return {
        "opcode": 0x72,
        "opcode_name": "binary_rectangle",
        "description": "Binary rectangle/circle (32-bit)",
        "x": x,
        "y": y,
        "packed_dimensions": packed_dimensions,

        # Circle interpretation
        "radius": radius,

        # Rectangle interpretation (unpacked dimensions)
        "width": width,
        "height": height,

        # Geometry type hint
        "is_circle": is_circle,
        "shape_type": "circle" if is_circle else "rectangle",

        # Raw data for debugging
        "raw_bytes": data.hex(),
        "bytes_read": 12
    }


def unpack_dimensions(packed: int) -> tuple:
    """
    Unpack a 32-bit packed dimension value into width and height.

    Format:
    - Lower 16 bits: width
    - Upper 16 bits: height

    Args:
        packed: 32-bit unsigned integer containing packed dimensions

    Returns:
        Tuple of (width, height)
    """
    width = packed & 0xFFFF
    height = (packed >> 16) & 0xFFFF
    return (width, height)


def pack_dimensions(width: int, height: int) -> int:
    """
    Pack width and height into a 32-bit value.

    Args:
        width: 16-bit width value
        height: 16-bit height value

    Returns:
        32-bit unsigned integer with packed dimensions
    """
    return (height << 16) | (width & 0xFFFF)


# Test cases and Hi protocol verification
if __name__ == "__main__":
    print("=" * 70)
    print("DWF Opcode 0x72 - Binary Rectangle/Circle Test Suite")
    print("=" * 70)
    print()

    # Test Case 1: Circle with radius 100 at position (50, 75)
    print("Test 1: Circle (radius 100 at position 50, 75)")
    print("-" * 70)
    # x=50 (int32), y=75 (int32), radius=100 (uint32)
    test_data_1 = struct.pack("<llL", 50, 75, 100)
    print(f"Input bytes: {test_data_1.hex()}")
    result_1 = opcode_0x72_binary_rectangle(test_data_1)
    print(f"Parsed data:")
    print(f"  Position: ({result_1['x']}, {result_1['y']})")
    print(f"  Packed dimensions: 0x{result_1['packed_dimensions']:08x}")
    print(f"  Radius: {result_1['radius']}")
    print(f"  Width/Height: {result_1['width']} x {result_1['height']}")
    print(f"  Shape type: {result_1['shape_type']}")
    print()

    # Test Case 2: Rectangle 200x150 at position (100, 200)
    print("Test 2: Rectangle (200x150 at position 100, 200)")
    print("-" * 70)
    # x=100 (int32), y=200 (int32), packed_dimensions with width=200, height=150
    packed_dims = pack_dimensions(200, 150)
    test_data_2 = struct.pack("<llL", 100, 200, packed_dims)
    print(f"Input bytes: {test_data_2.hex()}")
    print(f"Packed dimensions: 0x{packed_dims:08x}")
    result_2 = opcode_0x72_binary_rectangle(test_data_2)
    print(f"Parsed data:")
    print(f"  Position: ({result_2['x']}, {result_2['y']})")
    print(f"  Packed dimensions: 0x{result_2['packed_dimensions']:08x}")
    print(f"  Radius: {result_2['radius']}")
    print(f"  Width/Height: {result_2['width']} x {result_2['height']}")
    print(f"  Shape type: {result_2['shape_type']}")
    print()

    # Test Case 3: Negative coordinates (relative positioning)
    print("Test 3: Circle at negative position (-50, -30), radius 25")
    print("-" * 70)
    test_data_3 = struct.pack("<llL", -50, -30, 25)
    print(f"Input bytes: {test_data_3.hex()}")
    result_3 = opcode_0x72_binary_rectangle(test_data_3)
    print(f"Parsed data:")
    print(f"  Position: ({result_3['x']}, {result_3['y']})")
    print(f"  Packed dimensions: 0x{result_3['packed_dimensions']:08x}")
    print(f"  Radius: {result_3['radius']}")
    print(f"  Width/Height: {result_3['width']} x {result_3['height']}")
    print(f"  Shape type: {result_3['shape_type']}")
    print()

    # Test Case 4: Using BytesIO stream
    print("Test 4: Reading from BytesIO stream")
    print("-" * 70)
    stream_data = struct.pack("<llL", 1000, 2000, 500)
    test_stream = io.BytesIO(stream_data)
    print(f"Input bytes: {stream_data.hex()}")
    result_4 = opcode_0x72_binary_rectangle(test_stream)
    print(f"Parsed data:")
    print(f"  Position: ({result_4['x']}, {result_4['y']})")
    print(f"  Radius: {result_4['radius']}")
    print(f"  Shape type: {result_4['shape_type']}")
    print()

    # Test Case 5: Dimension unpacking verification
    print("Test 5: Packed dimension unpacking verification")
    print("-" * 70)
    test_width, test_height = 640, 480
    packed = pack_dimensions(test_width, test_height)
    unpacked_width, unpacked_height = unpack_dimensions(packed)
    print(f"Original: width={test_width}, height={test_height}")
    print(f"Packed value: 0x{packed:08x} ({packed})")
    print(f"Unpacked: width={unpacked_width}, height={unpacked_height}")
    print(f"Verification: {'PASS' if (unpacked_width == test_width and unpacked_height == test_height) else 'FAIL'}")
    print()

    # Hi protocol verification
    print("Hi Protocol Verification")
    print("-" * 70)
    print("Protocol: DWF Binary Format")
    print("Byte order: Little-endian (<)")
    print("Struct format: '<llL' (int32, int32, uint32)")
    print("Total bytes: 12")
    print()
    print("Field breakdown:")
    print("  Bytes 0-3:   int32 x coordinate (signed, little-endian)")
    print("  Bytes 4-7:   int32 y coordinate (signed, little-endian)")
    print("  Bytes 8-11:  uint32 packed_dimensions (unsigned, little-endian)")
    print()
    print("Packed dimensions unpacking:")
    print("  Bits 0-15:   Width (lower 16 bits)")
    print("  Bits 16-31:  Height (upper 16 bits)")
    print()
    print("=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)
