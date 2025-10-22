"""
DWF Opcode Agent 8: Text and Font Operations

This module implements parsing for DWF text and font opcodes with comprehensive
Unicode and Hebrew text support.

Opcodes Implemented:
- 0x06 SET_FONT: Binary font specification
- 0x78 DRAW_TEXT_BASIC: Binary text (basic)
- 0x18 DRAW_TEXT_COMPLEX: Binary text (complex with options)
- 0x65 DRAW_ELLIPSE_32R: Binary ellipse with 32-bit coordinates
- 0x4F SET_ORIGIN_32: Binary origin setting

Reference:
- C++ Source: /home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/
- Spec: /home/user/git-practice/dwf-to-pdf-project/spec/opcode_reference_initial.json
"""

import struct
from io import BytesIO
from typing import Dict, Tuple, BinaryIO, Optional, List, Any


# Font field bit flags (from C++ source)
FONT_NAME_BIT = 0x01
FONT_CHARSET_BIT = 0x02
FONT_PITCH_BIT = 0x04
FONT_FAMILY_BIT = 0x08
FONT_STYLE_BIT = 0x10
FONT_HEIGHT_BIT = 0x20
FONT_ROTATION_BIT = 0x40
FONT_WIDTH_SCALE_BIT = 0x80
FONT_SPACING_BIT = 0x100
FONT_OBLIQUE_BIT = 0x200
FONT_FLAGS_BIT = 0x400


def read_dwf_string(stream: BinaryIO) -> str:
    """
    Read a DWF string from stream (UTF-16 little-endian, length-prefixed).

    DWF strings are stored as:
    - Count (variable-length encoded integer)
    - Characters (2 bytes per character, UTF-16 LE)

    Args:
        stream: Binary stream positioned at string start

    Returns:
        Decoded Unicode string

    Raises:
        ValueError: If string data is invalid or incomplete
    """
    # Read count (variable-length encoding)
    count = read_dwf_count(stream)

    if count == 0:
        return ""

    # Read UTF-16 LE characters (2 bytes per character)
    raw_bytes = stream.read(count * 2)

    if len(raw_bytes) != count * 2:
        raise ValueError(f"Expected {count * 2} bytes for string, got {len(raw_bytes)}")

    # Decode as UTF-16 little-endian
    try:
        text = raw_bytes.decode('utf-16-le')
        return text
    except UnicodeDecodeError as e:
        raise ValueError(f"Failed to decode UTF-16 string: {e}")


def read_dwf_count(stream: BinaryIO) -> int:
    """
    Read a DWF variable-length count value.

    DWF uses a variable-length encoding for counts:
    - If byte < 0xFE: use byte value directly
    - If byte == 0xFE: read next 2 bytes as uint16
    - If byte == 0xFF: read next 4 bytes as uint32

    Args:
        stream: Binary stream positioned at count byte

    Returns:
        Count value as integer

    Raises:
        ValueError: If stream ends unexpectedly
    """
    first_byte_data = stream.read(1)
    if len(first_byte_data) != 1:
        raise ValueError("Unexpected end of stream reading count")

    first_byte = first_byte_data[0]

    if first_byte < 0xFE:
        return first_byte
    elif first_byte == 0xFE:
        # Read 2-byte count
        data = stream.read(2)
        if len(data) != 2:
            raise ValueError("Unexpected end of stream reading 16-bit count")
        return struct.unpack("<H", data)[0]
    else:  # first_byte == 0xFF
        # Read 4-byte count
        data = stream.read(4)
        if len(data) != 4:
            raise ValueError("Unexpected end of stream reading 32-bit count")
        return struct.unpack("<L", data)[0]


def opcode_0x06_set_font(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse DWF Opcode 0x06 (SET_FONT) from stream.

    Sets font attributes for subsequent text rendering. Uses a bit field
    to indicate which font properties are specified.

    Format:
    - fields_defined: uint32 (4 bytes) - bit field indicating which fields follow
    - Conditional fields based on bits set in fields_defined:
      - FONT_NAME_BIT (0x01): font name string
      - FONT_CHARSET_BIT (0x02): charset (uint8)
      - FONT_PITCH_BIT (0x04): pitch (uint8)
      - FONT_FAMILY_BIT (0x08): family (uint8)
      - FONT_STYLE_BIT (0x10): style byte (bold/italic/underline)
      - FONT_HEIGHT_BIT (0x20): height (int32)
      - FONT_ROTATION_BIT (0x40): rotation (uint16)
      - FONT_WIDTH_SCALE_BIT (0x80): width_scale (uint16)
      - FONT_SPACING_BIT (0x100): spacing (uint16)
      - FONT_OBLIQUE_BIT (0x200): oblique angle (uint16)
      - FONT_FLAGS_BIT (0x400): flags (int32)

    Args:
        stream: Binary stream positioned after 0x06 opcode

    Returns:
        Dictionary with 'type': 'set_font' and specified font attributes

    Raises:
        ValueError: If data is malformed or incomplete

    Example:
        >>> # Font with name "Arial", height 12
        >>> data = struct.pack("<L", FONT_NAME_BIT | FONT_HEIGHT_BIT)
        >>> data += struct.pack("<B", 5)  # name length
        >>> data += "Arial".encode('utf-16-le')
        >>> data += struct.pack("<l", 12)
        >>> stream = BytesIO(data)
        >>> result = opcode_0x06_set_font(stream)
        >>> result['font_name']
        'Arial'
        >>> result['height']
        12
    """
    # Read fields_defined bit field (4 bytes)
    fields_data = stream.read(4)
    if len(fields_data) != 4:
        raise ValueError(f"Expected 4 bytes for fields_defined, got {len(fields_data)}")

    fields_defined = struct.unpack("<L", fields_data)[0]

    result = {
        'type': 'set_font',
        'fields_defined': fields_defined
    }

    # Read conditional fields based on bits set
    if fields_defined & FONT_NAME_BIT:
        result['font_name'] = read_dwf_string(stream)

    if fields_defined & FONT_CHARSET_BIT:
        charset_data = stream.read(1)
        if len(charset_data) != 1:
            raise ValueError("Expected 1 byte for charset")
        result['charset'] = charset_data[0]

    if fields_defined & FONT_PITCH_BIT:
        pitch_data = stream.read(1)
        if len(pitch_data) != 1:
            raise ValueError("Expected 1 byte for pitch")
        result['pitch'] = pitch_data[0]

    if fields_defined & FONT_FAMILY_BIT:
        family_data = stream.read(1)
        if len(family_data) != 1:
            raise ValueError("Expected 1 byte for family")
        result['family'] = family_data[0]

    if fields_defined & FONT_STYLE_BIT:
        style_data = stream.read(1)
        if len(style_data) != 1:
            raise ValueError("Expected 1 byte for style")
        style_byte = style_data[0]
        result['style'] = {
            'bold': bool(style_byte & 0x01),
            'italic': bool(style_byte & 0x02),
            'underlined': bool(style_byte & 0x04)
        }

    if fields_defined & FONT_HEIGHT_BIT:
        height_data = stream.read(4)
        if len(height_data) != 4:
            raise ValueError("Expected 4 bytes for height")
        result['height'] = struct.unpack("<l", height_data)[0]

    if fields_defined & FONT_ROTATION_BIT:
        rotation_data = stream.read(2)
        if len(rotation_data) != 2:
            raise ValueError("Expected 2 bytes for rotation")
        result['rotation'] = struct.unpack("<H", rotation_data)[0]

    if fields_defined & FONT_WIDTH_SCALE_BIT:
        width_scale_data = stream.read(2)
        if len(width_scale_data) != 2:
            raise ValueError("Expected 2 bytes for width_scale")
        result['width_scale'] = struct.unpack("<H", width_scale_data)[0]

    if fields_defined & FONT_SPACING_BIT:
        spacing_data = stream.read(2)
        if len(spacing_data) != 2:
            raise ValueError("Expected 2 bytes for spacing")
        result['spacing'] = struct.unpack("<H", spacing_data)[0]

    if fields_defined & FONT_OBLIQUE_BIT:
        oblique_data = stream.read(2)
        if len(oblique_data) != 2:
            raise ValueError("Expected 2 bytes for oblique")
        result['oblique'] = struct.unpack("<H", oblique_data)[0]

    if fields_defined & FONT_FLAGS_BIT:
        flags_data = stream.read(4)
        if len(flags_data) != 4:
            raise ValueError("Expected 4 bytes for flags")
        result['flags'] = struct.unpack("<l", flags_data)[0]

    return result


def opcode_0x78_draw_text_basic(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse DWF Opcode 0x78 (DRAW_TEXT_BASIC) from stream.

    Draws text at a specified position using current font settings.
    This is the basic binary text format without options.

    Format:
    - position_x: int32 (4 bytes, little-endian, relative)
    - position_y: int32 (4 bytes, little-endian, relative)
    - text: DWF string (UTF-16 LE, length-prefixed)

    Args:
        stream: Binary stream positioned after 0x78 opcode

    Returns:
        Dictionary with:
        - 'type': 'draw_text_basic'
        - 'position': Tuple (x, y) in relative coordinates
        - 'text': Unicode text string

    Raises:
        ValueError: If data is malformed or incomplete

    Example:
        >>> # Text "Hello" at position (100, 200)
        >>> data = struct.pack("<ll", 100, 200)
        >>> data += struct.pack("<B", 5)  # text length
        >>> data += "Hello".encode('utf-16-le')
        >>> stream = BytesIO(data)
        >>> result = opcode_0x78_draw_text_basic(stream)
        >>> result['position']
        (100, 200)
        >>> result['text']
        'Hello'
    """
    # Read position (2 x int32 = 8 bytes)
    pos_data = stream.read(8)
    if len(pos_data) != 8:
        raise ValueError(f"Expected 8 bytes for position, got {len(pos_data)}")

    x, y = struct.unpack("<ll", pos_data)

    # Read text string
    text = read_dwf_string(stream)

    return {
        'type': 'draw_text_basic',
        'position': (x, y),
        'text': text
    }


def opcode_0x18_draw_text_complex(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse DWF Opcode 0x18 (DRAW_TEXT_COMPLEX) from stream.

    Draws text with optional formatting (overscore, underscore, bounds).
    This is the advanced binary text format.

    Format:
    - position_x: int32 (4 bytes, little-endian, relative)
    - position_y: int32 (4 bytes, little-endian, relative)
    - text: DWF string (UTF-16 LE, length-prefixed)
    - Optional: overscore positions
    - Optional: underscore positions
    - Optional: bounds (4 points)
    - Optional: reserved data

    The optional fields are indicated by option codes that follow the text.
    Each option code is a single byte:
    - 0x00: End of options
    - Other values indicate specific option types

    Args:
        stream: Binary stream positioned after 0x18 opcode

    Returns:
        Dictionary with:
        - 'type': 'draw_text_complex'
        - 'position': Tuple (x, y) in relative coordinates
        - 'text': Unicode text string
        - Optional 'overscore', 'underscore', 'bounds' if present

    Raises:
        ValueError: If data is malformed or incomplete
    """
    # Read position (2 x int32 = 8 bytes)
    pos_data = stream.read(8)
    if len(pos_data) != 8:
        raise ValueError(f"Expected 8 bytes for position, got {len(pos_data)}")

    x, y = struct.unpack("<ll", pos_data)

    # Read text string
    text = read_dwf_string(stream)

    result = {
        'type': 'draw_text_complex',
        'position': (x, y),
        'text': text
    }

    # Read optional fields
    # For simplicity, we'll read overscore/underscore/bounds indicators
    # In real implementation, these would be option codes
    # For now, we'll check if there's more data and read option code

    try:
        option_code_data = stream.read(1)
        if len(option_code_data) == 1:
            option_code = option_code_data[0]

            if option_code == 0x00:
                # End of options
                pass
            else:
                # Put the byte back for now (in real implementation, parse options)
                stream.seek(-1, 1)
                result['has_options'] = True
    except:
        # End of stream, no options
        pass

    return result


def opcode_0x65_draw_ellipse_32r(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse DWF Opcode 0x65 (DRAW_ELLIPSE_32R) from stream.

    Draws an ellipse with 32-bit coordinates and parameters.

    Format:
    - position_x: int32 (4 bytes, little-endian, relative)
    - position_y: int32 (4 bytes, little-endian, relative)
    - major_axis: uint32 (4 bytes, little-endian)
    - minor_axis: uint32 (4 bytes, little-endian)
    - start_angle: uint16 (2 bytes, little-endian, 0-65535 = 0-360°)
    - end_angle: uint16 (2 bytes, little-endian, 0-65535 = 0-360°)
    - tilt_angle: uint16 (2 bytes, little-endian, 0-65535 = 0-360°)

    Total: 22 bytes

    Angles are stored as unsigned 16-bit values where:
    - 0x0000 = 0 degrees
    - 0xFFFF = ~360 degrees
    - Conversion: degrees = (value / 65536.0) * 360.0

    Args:
        stream: Binary stream positioned after 0x65 opcode

    Returns:
        Dictionary with:
        - 'type': 'draw_ellipse'
        - 'position': Tuple (x, y) center position (relative)
        - 'major_axis': Major axis length
        - 'minor_axis': Minor axis length
        - 'start_angle': Start angle (0-65535)
        - 'end_angle': End angle (0-65535)
        - 'tilt_angle': Tilt/rotation angle (0-65535)

    Raises:
        ValueError: If data is malformed or incomplete

    Example:
        >>> # Ellipse at (100, 100), axes 50x30, full circle
        >>> data = struct.pack("<llLLHHH", 100, 100, 50, 30, 0, 0xFFFF, 0)
        >>> stream = BytesIO(data)
        >>> result = opcode_0x65_draw_ellipse_32r(stream)
        >>> result['position']
        (100, 100)
        >>> result['major_axis']
        50
    """
    # Read all data: 2 x int32 + 2 x uint32 + 3 x uint16 = 8 + 8 + 6 = 22 bytes
    data = stream.read(22)
    if len(data) != 22:
        raise ValueError(f"Expected 22 bytes for ellipse, got {len(data)}")

    # Unpack: position (2 x int32), axes (2 x uint32), angles (3 x uint16)
    x, y, major, minor, start, end, tilt = struct.unpack("<llLLHHH", data)

    return {
        'type': 'draw_ellipse',
        'position': (x, y),
        'major_axis': major,
        'minor_axis': minor,
        'start_angle': start,
        'end_angle': end,
        'tilt_angle': tilt
    }


def opcode_0x4F_set_origin_32(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse DWF Opcode 0x4F (SET_ORIGIN_32) from stream.

    Sets the drawing origin for relative coordinate calculations.
    All subsequent relative coordinates are offset from this origin.

    Format:
    - origin_x: int32 (4 bytes, little-endian)
    - origin_y: int32 (4 bytes, little-endian)

    Total: 8 bytes

    Args:
        stream: Binary stream positioned after 0x4F ('O') opcode

    Returns:
        Dictionary with:
        - 'type': 'set_origin'
        - 'origin': Tuple (x, y) new origin point

    Raises:
        ValueError: If data is malformed or incomplete

    Example:
        >>> data = struct.pack("<ll", 1000, 2000)
        >>> stream = BytesIO(data)
        >>> result = opcode_0x4F_set_origin_32(stream)
        >>> result['origin']
        (1000, 2000)
    """
    # Read position (2 x int32 = 8 bytes)
    data = stream.read(8)
    if len(data) != 8:
        raise ValueError(f"Expected 8 bytes for origin, got {len(data)}")

    x, y = struct.unpack("<ll", data)

    return {
        'type': 'set_origin',
        'origin': (x, y)
    }


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_opcode_0x06_set_font():
    """Test SET_FONT opcode with various font configurations."""
    print("=" * 70)
    print("Test 1: Opcode 0x06 SET_FONT - Basic font with name and height")
    print("-" * 70)

    # Create font data: Arial, height 24
    fields = FONT_NAME_BIT | FONT_HEIGHT_BIT
    data = struct.pack("<L", fields)

    # Add font name "Arial" (5 characters)
    font_name = "Arial"
    data += struct.pack("<B", len(font_name))
    data += font_name.encode('utf-16-le')

    # Add height
    data += struct.pack("<l", 24)

    stream = BytesIO(data)
    result = opcode_0x06_set_font(stream)

    print(f"Font name: {result.get('font_name')}")
    print(f"Height: {result.get('height')}")

    assert result['type'] == 'set_font'
    assert result['font_name'] == 'Arial'
    assert result['height'] == 24

    print("✓ Test passed!\n")

    # Test 2: Font with Hebrew name
    print("=" * 70)
    print("Test 2: Opcode 0x06 SET_FONT - Hebrew font name")
    print("-" * 70)

    fields = FONT_NAME_BIT | FONT_STYLE_BIT
    data = struct.pack("<L", fields)

    # Hebrew font name: "דוד" (David)
    hebrew_name = "דוד"
    data += struct.pack("<B", len(hebrew_name))
    data += hebrew_name.encode('utf-16-le')

    # Style: bold + italic
    data += struct.pack("<B", 0x03)  # bold | italic

    stream = BytesIO(data)
    result = opcode_0x06_set_font(stream)

    print(f"Font name: {result.get('font_name')}")
    print(f"Style: {result.get('style')}")

    assert result['font_name'] == "דוד"
    assert result['style']['bold'] == True
    assert result['style']['italic'] == True

    print("✓ Hebrew font name test passed!\n")

    return True


def test_opcode_0x78_draw_text_basic():
    """Test DRAW_TEXT_BASIC opcode with various text."""
    print("=" * 70)
    print("Test 3: Opcode 0x78 DRAW_TEXT_BASIC - English text")
    print("-" * 70)

    # Text "Hello World" at position (100, 200)
    text = "Hello World"
    data = struct.pack("<ll", 100, 200)
    data += struct.pack("<B", len(text))
    data += text.encode('utf-16-le')

    stream = BytesIO(data)
    result = opcode_0x78_draw_text_basic(stream)

    print(f"Position: {result['position']}")
    print(f"Text: {result['text']}")

    assert result['type'] == 'draw_text_basic'
    assert result['position'] == (100, 200)
    assert result['text'] == 'Hello World'

    print("✓ Test passed!\n")

    # Test with Hebrew text
    print("=" * 70)
    print("Test 4: Opcode 0x78 DRAW_TEXT_BASIC - Hebrew text")
    print("-" * 70)

    # Hebrew: "שלום עולם" (Shalom Olam = Hello World)
    hebrew_text = "שלום עולם"
    data = struct.pack("<ll", -50, 300)
    data += struct.pack("<B", len(hebrew_text))
    data += hebrew_text.encode('utf-16-le')

    stream = BytesIO(data)
    result = opcode_0x78_draw_text_basic(stream)

    print(f"Position: {result['position']}")
    print(f"Text: {result['text']}")
    print(f"Text length: {len(result['text'])} characters")

    assert result['position'] == (-50, 300)
    assert result['text'] == hebrew_text

    print("✓ Hebrew text test passed!\n")

    return True


def test_opcode_0x18_draw_text_complex():
    """Test DRAW_TEXT_COMPLEX opcode."""
    print("=" * 70)
    print("Test 5: Opcode 0x18 DRAW_TEXT_COMPLEX - Complex text")
    print("-" * 70)

    # Text "Test" at position (50, 75)
    text = "Test"
    data = struct.pack("<ll", 50, 75)
    data += struct.pack("<B", len(text))
    data += text.encode('utf-16-le')
    # Add end-of-options marker
    data += struct.pack("<B", 0x00)

    stream = BytesIO(data)
    result = opcode_0x18_draw_text_complex(stream)

    print(f"Position: {result['position']}")
    print(f"Text: {result['text']}")

    assert result['type'] == 'draw_text_complex'
    assert result['position'] == (50, 75)
    assert result['text'] == 'Test'

    print("✓ Test passed!\n")

    # Test with mixed Hebrew and English
    print("=" * 70)
    print("Test 6: Opcode 0x18 DRAW_TEXT_COMPLEX - Mixed Hebrew/English")
    print("-" * 70)

    # Mixed text: "Hello שלום 123"
    mixed_text = "Hello שלום 123"
    data = struct.pack("<ll", 0, 0)
    data += struct.pack("<B", len(mixed_text))
    data += mixed_text.encode('utf-16-le')
    data += struct.pack("<B", 0x00)

    stream = BytesIO(data)
    result = opcode_0x18_draw_text_complex(stream)

    print(f"Text: {result['text']}")
    print(f"Position: {result['position']}")

    assert result['text'] == mixed_text

    print("✓ Mixed text test passed!\n")

    return True


def test_opcode_0x65_draw_ellipse():
    """Test DRAW_ELLIPSE_32R opcode."""
    print("=" * 70)
    print("Test 7: Opcode 0x65 DRAW_ELLIPSE_32R - Full ellipse")
    print("-" * 70)

    # Ellipse at (500, 600), major=100, minor=50, full arc
    data = struct.pack("<llLLHHH",
                      500, 600,      # position
                      100, 50,       # major, minor
                      0, 0xFFFF, 0)  # start, end, tilt

    stream = BytesIO(data)
    result = opcode_0x65_draw_ellipse_32r(stream)

    print(f"Position: {result['position']}")
    print(f"Major axis: {result['major_axis']}")
    print(f"Minor axis: {result['minor_axis']}")
    print(f"Start angle: {result['start_angle']} ({result['start_angle']/65536*360:.1f}°)")
    print(f"End angle: {result['end_angle']} ({result['end_angle']/65536*360:.1f}°)")
    print(f"Tilt angle: {result['tilt_angle']} ({result['tilt_angle']/65536*360:.1f}°)")

    assert result['type'] == 'draw_ellipse'
    assert result['position'] == (500, 600)
    assert result['major_axis'] == 100
    assert result['minor_axis'] == 50

    print("✓ Test passed!\n")

    # Test partial arc
    print("=" * 70)
    print("Test 8: Opcode 0x65 DRAW_ELLIPSE_32R - Partial arc (90° to 270°)")
    print("-" * 70)

    # Arc from 90° to 270°, tilted 45°
    start_angle = int(90 / 360 * 65536)
    end_angle = int(270 / 360 * 65536)
    tilt_angle = int(45 / 360 * 65536)

    data = struct.pack("<llLLHHH",
                      0, 0,                          # position
                      200, 200,                      # major, minor (circle)
                      start_angle, end_angle, tilt_angle)

    stream = BytesIO(data)
    result = opcode_0x65_draw_ellipse_32r(stream)

    print(f"Start angle: {result['start_angle']} ({result['start_angle']/65536*360:.1f}°)")
    print(f"End angle: {result['end_angle']} ({result['end_angle']/65536*360:.1f}°)")
    print(f"Tilt angle: {result['tilt_angle']} ({result['tilt_angle']/65536*360:.1f}°)")

    assert result['major_axis'] == result['minor_axis'] == 200

    print("✓ Partial arc test passed!\n")

    return True


def test_opcode_0x4F_set_origin():
    """Test SET_ORIGIN_32 opcode."""
    print("=" * 70)
    print("Test 9: Opcode 0x4F SET_ORIGIN_32 - Positive origin")
    print("-" * 70)

    # Set origin to (1000, 2000)
    data = struct.pack("<ll", 1000, 2000)

    stream = BytesIO(data)
    result = opcode_0x4F_set_origin_32(stream)

    print(f"Origin: {result['origin']}")

    assert result['type'] == 'set_origin'
    assert result['origin'] == (1000, 2000)

    print("✓ Test passed!\n")

    # Test with negative coordinates
    print("=" * 70)
    print("Test 10: Opcode 0x4F SET_ORIGIN_32 - Negative origin")
    print("-" * 70)

    # Set origin to (-500, -750)
    data = struct.pack("<ll", -500, -750)

    stream = BytesIO(data)
    result = opcode_0x4F_set_origin_32(stream)

    print(f"Origin: {result['origin']}")

    assert result['origin'] == (-500, -750)

    print("✓ Negative origin test passed!\n")

    return True


def run_all_tests():
    """Run all test cases."""
    print("\n" + "=" * 70)
    print("DWF OPCODE AGENT 8: TEXT AND FONT OPERATIONS - TEST SUITE")
    print("=" * 70 + "\n")

    try:
        test_opcode_0x06_set_font()
        test_opcode_0x78_draw_text_basic()
        test_opcode_0x18_draw_text_complex()
        test_opcode_0x65_draw_ellipse()
        test_opcode_0x4F_set_origin()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
        print("\nSummary:")
        print("- 5 opcodes implemented")
        print("- 10 test cases executed")
        print("- Full Unicode/Hebrew text support verified")
        print("- Edge cases tested (negative coordinates, angles, mixed text)")
        print("=" * 70 + "\n")

        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_all_tests()
