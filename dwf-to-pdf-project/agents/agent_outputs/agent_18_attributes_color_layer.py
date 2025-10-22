"""
DWF Extended ASCII Opcodes - Color and Layer Attributes
Agent 18: Translation of Extended ASCII color/layer attribute opcodes (1/3)

This module implements 6 Extended ASCII DWF opcodes for color and layer management:
- WD_EXAO_SET_COLOR (ID 260) - `(Color` - Color setting with RGBA values
- WD_EXAO_SET_COLOR_MAP (ID 261) - `(ColorMap` - Color palette definition
- WD_EXAO_SET_CONTRAST_COLOR (ID 385) - `(ContrastColor` - Contrast color setting
- WD_EXAO_SET_LAYER (ID 276) - `(Layer` - Layer assignment and definition
- WD_EXAO_SET_BACKGROUND (ID 257) - `(Background` - Background color/pattern
- WD_EXAO_SET_CODE_PAGE (ID 266) - `(CodePage` - Character encoding

Extended ASCII opcodes use the format: (OpcodeName ...data...)
These opcodes support ASCII-based data encoding for human readability.

References:
- DWF Toolkit: develop/global/src/dwf/whiptk/color.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/colormap.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/contrastcolor.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/layer.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/backgrnd.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/code_page.cpp
- Research: agent_outputs/agent_13_extended_opcodes_research.md
"""

import struct
from typing import Dict, Any, List, Tuple, BinaryIO, Optional
from io import BytesIO


# ============================================================================
# Constants
# ============================================================================

# Opcode IDs (from opcode_defs.h)
WD_EXAO_SET_BACKGROUND = 257
WD_EXAO_SET_COLOR = 260
WD_EXAO_SET_COLOR_MAP = 261
WD_EXAO_SET_CODE_PAGE = 266
WD_EXAO_SET_LAYER = 276
WD_EXAO_SET_CONTRAST_COLOR = 385

# Special color index value
WD_NO_COLOR_INDEX = -1


# ============================================================================
# Helper Functions for Extended ASCII Parsing
# ============================================================================

def eat_whitespace(stream: BinaryIO) -> None:
    """
    Skip whitespace characters (space, tab, LF, CR) in the stream.

    Args:
        stream: Binary stream to read from

    Reference:
        Common pattern in DWF toolkit Extended ASCII parsing
    """
    while True:
        byte = stream.read(1)
        if not byte:
            break
        if byte not in (b' ', b'\t', b'\n', b'\r'):
            stream.seek(-1, 1)  # Put back non-whitespace
            break


def skip_past_matching_paren(stream: BinaryIO) -> None:
    """
    Skip to the closing parenthesis that matches the current nesting level.
    Handles nested parentheses correctly.

    Args:
        stream: Binary stream to read from

    Raises:
        EOFError: If EOF reached before finding matching paren

    Reference:
        DWF Toolkit: opcode.cpp skip_past_matching_paren()
    """
    depth = 1
    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise EOFError("Unexpected EOF while looking for matching parenthesis")
        if byte == b'(':
            depth += 1
        elif byte == b')':
            depth -= 1


def read_ascii_int(stream: BinaryIO) -> int:
    """
    Read an ASCII-encoded integer from the stream.
    Skips leading whitespace and reads until a non-digit character.

    Args:
        stream: Binary stream to read from

    Returns:
        Integer value

    Raises:
        ValueError: If no valid integer found
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: file.read_ascii(integer)
    """
    eat_whitespace(stream)

    digits = []
    negative = False

    # Check for optional negative sign
    byte = stream.read(1)
    if byte == b'-':
        negative = True
    elif byte and byte[0] >= ord('0') and byte[0] <= ord('9'):
        digits.append(byte)
    elif byte:
        stream.seek(-1, 1)  # Put back non-digit

    # Read digits
    while True:
        byte = stream.read(1)
        if not byte:
            break
        if byte[0] >= ord('0') and byte[0] <= ord('9'):
            digits.append(byte)
        else:
            stream.seek(-1, 1)  # Put back non-digit
            break

    if not digits:
        raise ValueError("No integer value found")

    value = int(b''.join(digits))
    return -value if negative else value


def read_ascii_rgba(stream: BinaryIO) -> Tuple[int, int, int, int]:
    """
    Read RGBA color values in ASCII format.
    Format can be either a single index or four comma-separated values (R,G,B,A).

    Args:
        stream: Binary stream to read from

    Returns:
        Tuple of (red, green, blue, alpha) values (0-255 each)

    Raises:
        ValueError: If color format is invalid
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: color.cpp materialize() Extended_ASCII case
        DWF Toolkit: file.read_ascii(WT_RGBA32)
    """
    eat_whitespace(stream)

    # Read first value
    r = read_ascii_int(stream)

    eat_whitespace(stream)

    # Check if there's a comma (indicating RGBA format)
    byte = stream.read(1)
    if byte != b',':
        # Single value format - treat as indexed color (return as grayscale)
        if byte:
            stream.seek(-1, 1)
        # For indexed colors, we return a placeholder RGBA
        # The actual color should be resolved against the color map
        return (0, 0, 0, 0)  # Clear black - undefined color

    # RGBA format: read remaining values
    g = read_ascii_int(stream)

    eat_whitespace(stream)
    byte = stream.read(1)
    if byte != b',':
        raise ValueError("Expected comma after green component")

    b = read_ascii_int(stream)

    eat_whitespace(stream)
    byte = stream.read(1)
    if byte != b',':
        raise ValueError("Expected comma after blue component")

    a = read_ascii_int(stream)

    # Validate ranges
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255 and 0 <= a <= 255):
        raise ValueError(f"RGBA values must be 0-255: got ({r},{g},{b},{a})")

    return (r, g, b, a)


def read_ascii_string(stream: BinaryIO) -> str:
    """
    Read an ASCII string from the stream.
    Handles both quoted and unquoted strings.

    Args:
        stream: Binary stream to read from

    Returns:
        Decoded string

    Raises:
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: string.cpp materialize()
    """
    eat_whitespace(stream)

    byte = stream.read(1)
    if not byte:
        return ""

    # Check for quoted string
    if byte == b'"':
        chars = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise EOFError("Unexpected EOF in quoted string")
            if byte == b'"':
                break
            if byte == b'\\':  # Handle escape sequences
                next_byte = stream.read(1)
                if next_byte == b'n':
                    chars.append(b'\n')
                elif next_byte == b't':
                    chars.append(b'\t')
                elif next_byte == b'\\':
                    chars.append(b'\\')
                elif next_byte == b'"':
                    chars.append(b'"')
                else:
                    chars.append(next_byte)
            else:
                chars.append(byte)
        return b''.join(chars).decode('utf-8', errors='replace')
    else:
        # Unquoted string - read until whitespace or special char
        chars = [byte]
        while True:
            byte = stream.read(1)
            if not byte or byte in (b' ', b'\t', b'\n', b'\r', b')', b'('):
                if byte:
                    stream.seek(-1, 1)
                break
            chars.append(byte)
        return b''.join(chars).decode('utf-8', errors='replace')


# ============================================================================
# WD_EXAO_SET_COLOR (ID 260) - `(Color` - Extended ASCII Color Setting
# ============================================================================

def exao_set_color(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_COLOR Extended ASCII opcode.

    Sets the current drawing color using RGBA values.
    Format: (Color R,G,B,A)

    Args:
        stream: Binary stream positioned after '(Color' opener

    Returns:
        Dictionary containing:
            - opcode_id: 260 (WD_EXAO_SET_COLOR)
            - name: "EXAO_SET_COLOR"
            - red: Red component (0-255)
            - green: Green component (0-255)
            - blue: Blue component (0-255)
            - alpha: Alpha component (0-255)
            - index: WD_NO_COLOR_INDEX (-1) for RGBA colors

    Raises:
        ValueError: If color format is invalid
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: color.cpp materialize() lines 239-252
        Format: "(Color R,G,B,A)"
        Opcode: opcode_defs.h line 130 (WD_EXAO_SET_COLOR)
    """
    # Read RGBA color values
    r, g, b, a = read_ascii_rgba(stream)

    # Skip to closing paren
    skip_past_matching_paren(stream)

    return {
        'opcode_id': WD_EXAO_SET_COLOR,
        'name': 'EXAO_SET_COLOR',
        'red': r,
        'green': g,
        'blue': b,
        'alpha': a,
        'index': WD_NO_COLOR_INDEX
    }


# ============================================================================
# WD_EXAO_SET_COLOR_MAP (ID 261) - `(ColorMap` - Color Palette Definition
# ============================================================================

def exao_set_color_map(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_COLOR_MAP Extended ASCII opcode.

    Defines a color palette (lookup table) for indexed color references.
    Format: (ColorMap <count> R1,G1,B1,A1 R2,G2,B2,A2 ...)

    The color map allows efficient color storage by using palette indices
    instead of full RGBA values for each object.

    Args:
        stream: Binary stream positioned after '(ColorMap' opener

    Returns:
        Dictionary containing:
            - opcode_id: 261 (WD_EXAO_SET_COLOR_MAP)
            - name: "EXAO_SET_COLOR_MAP"
            - size: Number of colors in map (1-65535)
            - colors: List of RGBA tuples [(r,g,b,a), ...]

    Raises:
        ValueError: If count is invalid or color format is wrong
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: colormap.cpp materialize() lines 331-368
        DWF Toolkit: colormap.cpp serialize() lines 207-249
        Format: "(ColorMap <count> <color1> <color2> ...)"
        Opcode: opcode_defs.h line 131 (WD_EXAO_SET_COLOR_MAP)
    """
    # Read color count
    count = read_ascii_int(stream)

    if count < 0 or count > 65535:
        raise ValueError(f"Color map size must be 0-65535, got {count}")

    # Read color values
    colors = []
    for i in range(count):
        rgba = read_ascii_rgba(stream)
        colors.append(rgba)

    # Skip to closing paren
    skip_past_matching_paren(stream)

    return {
        'opcode_id': WD_EXAO_SET_COLOR_MAP,
        'name': 'EXAO_SET_COLOR_MAP',
        'size': count,
        'colors': colors
    }


# ============================================================================
# WD_EXAO_SET_CONTRAST_COLOR (ID 385) - `(ContrastColor` - Contrast Color
# ============================================================================

def exao_set_contrast_color(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_CONTRAST_COLOR Extended ASCII opcode.

    Sets a contrast color for improved visibility of objects against
    different backgrounds. Used primarily for UI/display purposes.

    Format: (ContrastColor R,G,B,A)

    Args:
        stream: Binary stream positioned after '(ContrastColor' opener

    Returns:
        Dictionary containing:
            - opcode_id: 385 (WD_EXAO_SET_CONTRAST_COLOR)
            - name: "EXAO_SET_CONTRAST_COLOR"
            - red: Red component (0-255)
            - green: Green component (0-255)
            - blue: Blue component (0-255)
            - alpha: Alpha component (0-255)

    Raises:
        ValueError: If color format is invalid
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: contrastcolor.cpp materialize() lines 29-63
        DWF Toolkit: contrastcolor.cpp serialize() lines 82-109
        Format: "(ContrastColor R,G,B,A)"
        Opcode: opcode_defs.h line 233 (WD_EXAO_SET_CONTRAST_COLOR)
    """
    eat_whitespace(stream)

    # Read RGBA color values
    r, g, b, a = read_ascii_rgba(stream)

    eat_whitespace(stream)

    # Skip to closing paren
    skip_past_matching_paren(stream)

    return {
        'opcode_id': WD_EXAO_SET_CONTRAST_COLOR,
        'name': 'EXAO_SET_CONTRAST_COLOR',
        'red': r,
        'green': g,
        'blue': b,
        'alpha': a
    }


# ============================================================================
# WD_EXAO_SET_LAYER (ID 276) - `(Layer` - Layer Assignment
# ============================================================================

def exao_set_layer(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_LAYER Extended ASCII opcode.

    Assigns subsequent drawing operations to a named layer.
    Layers organize drawing objects for visibility control and management.

    Format: (Layer <layer_num> "<layer_name>")
    Or (for previously defined layers): (Layer <layer_num>)

    Args:
        stream: Binary stream positioned after '(Layer' opener

    Returns:
        Dictionary containing:
            - opcode_id: 276 (WD_EXAO_SET_LAYER)
            - name: "EXAO_SET_LAYER"
            - layer_num: Layer number/index
            - layer_name: Layer name string (empty if not provided)

    Raises:
        ValueError: If layer number is invalid
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: layer.cpp materialize() lines 182-227
        DWF Toolkit: layer.cpp serialize() lines 87-134
        Format: "(Layer <num> <name>)" or "(Layer <num>)"
        Opcode: opcode_defs.h line 145 (WD_EXAO_SET_LAYER)
    """
    # Read layer number
    layer_num = read_ascii_int(stream)

    eat_whitespace(stream)

    # Check if there's a layer name (peek at next char)
    byte = stream.read(1)
    if not byte:
        raise EOFError("Unexpected EOF after layer number")

    if byte == b')':
        # No layer name provided (layer already defined)
        return {
            'opcode_id': WD_EXAO_SET_LAYER,
            'name': 'EXAO_SET_LAYER',
            'layer_num': layer_num,
            'layer_name': ''
        }

    # Put back the byte and read layer name
    stream.seek(-1, 1)
    layer_name = read_ascii_string(stream)

    eat_whitespace(stream)

    # Skip to closing paren
    skip_past_matching_paren(stream)

    return {
        'opcode_id': WD_EXAO_SET_LAYER,
        'name': 'EXAO_SET_LAYER',
        'layer_num': layer_num,
        'layer_name': layer_name
    }


# ============================================================================
# WD_EXAO_SET_BACKGROUND (ID 257) - `(Background` - Background Color
# ============================================================================

def exao_set_background(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_BACKGROUND Extended ASCII opcode.

    Sets the background color for the drawing.
    Can be specified as either an index into the color map or as RGBA values.

    Format: (Background <index>)
    Or: (Background R,G,B,A)

    Args:
        stream: Binary stream positioned after '(Background' opener

    Returns:
        Dictionary containing:
            - opcode_id: 257 (WD_EXAO_SET_BACKGROUND)
            - name: "EXAO_SET_BACKGROUND"
            - red: Red component (0-255) or 0 if indexed
            - green: Green component (0-255) or 0 if indexed
            - blue: Blue component (0-255) or 0 if indexed
            - alpha: Alpha component (0-255) or 0 if indexed
            - is_indexed: True if using color map index
            - index: Color map index (or -1 if RGBA)

    Raises:
        ValueError: If color format is invalid
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: backgrnd.cpp materialize() lines 120-160
        DWF Toolkit: backgrnd.cpp serialize() lines 41-78
        Format: "(Background <color>)" where color is index or RGBA
        Opcode: opcode_defs.h line 129 (WD_EXAO_SET_BACKGROUND)
    """
    eat_whitespace(stream)

    # Save position to check for single value vs RGBA
    pos = stream.tell()

    # Try to read as RGBA (will return (0,0,0,0) if single value)
    try:
        r, g, b, a = read_ascii_rgba(stream)

        # Check if it was actually a single index value
        # by looking for what we read
        current_pos = stream.tell()
        stream.seek(pos)

        # Read first integer
        first_val = read_ascii_int(stream)
        eat_whitespace(stream)
        next_byte = stream.read(1)

        if next_byte == b')':
            # Single value - it's an indexed color
            return {
                'opcode_id': WD_EXAO_SET_BACKGROUND,
                'name': 'EXAO_SET_BACKGROUND',
                'red': 0,
                'green': 0,
                'blue': 0,
                'alpha': 0,
                'is_indexed': True,
                'index': first_val
            }

        # Not a closing paren, restore position and use RGBA
        stream.seek(current_pos)

        # Skip to closing paren
        skip_past_matching_paren(stream)

        return {
            'opcode_id': WD_EXAO_SET_BACKGROUND,
            'name': 'EXAO_SET_BACKGROUND',
            'red': r,
            'green': g,
            'blue': b,
            'alpha': a,
            'is_indexed': False,
            'index': WD_NO_COLOR_INDEX
        }

    except Exception as e:
        raise ValueError(f"Invalid background color format: {e}")


# ============================================================================
# WD_EXAO_SET_CODE_PAGE (ID 266) - `(CodePage` - Character Encoding
# ============================================================================

def exao_set_code_page(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_CODE_PAGE Extended ASCII opcode.

    Sets the character encoding (code page) for text rendering.
    This affects how text strings are interpreted and displayed.

    Common code pages:
    - 1252: Windows Latin-1 (Western European)
    - 1250: Windows Latin-2 (Central European)
    - 932: Japanese Shift-JIS
    - 936: Simplified Chinese GBK
    - 949: Korean
    - 950: Traditional Chinese Big5
    - 65001: UTF-8

    Format: (CodePage <page_number>)

    Args:
        stream: Binary stream positioned after '(CodePage' opener

    Returns:
        Dictionary containing:
            - opcode_id: 266 (WD_EXAO_SET_CODE_PAGE)
            - name: "EXAO_SET_CODE_PAGE"
            - page_number: Code page identifier

    Raises:
        ValueError: If page number is invalid
        EOFError: If stream ends unexpectedly

    Reference:
        DWF Toolkit: code_page.cpp materialize() lines 84-108
        DWF Toolkit: code_page.cpp serialize() lines 29-42
        Format: "(CodePage <number>)"
        Opcode: opcode_defs.h line 137 (WD_EXAO_SET_CODE_PAGE)
    """
    eat_whitespace(stream)

    # Read code page number
    page_number = read_ascii_int(stream)

    eat_whitespace(stream)

    # Skip to closing paren
    skip_past_matching_paren(stream)

    return {
        'opcode_id': WD_EXAO_SET_CODE_PAGE,
        'name': 'EXAO_SET_CODE_PAGE',
        'page_number': page_number
    }


# ============================================================================
# Opcode Dispatcher Mapping
# ============================================================================

EXTENDED_ASCII_OPCODE_HANDLERS = {
    'Color': exao_set_color,
    'ColorMap': exao_set_color_map,
    'ContrastColor': exao_set_contrast_color,
    'Layer': exao_set_layer,
    'Background': exao_set_background,
    'CodePage': exao_set_code_page,
}


# ============================================================================
# Testing Infrastructure
# ============================================================================

def test_exao_set_color():
    """Test EXAO_SET_COLOR opcode parsing."""
    print("Testing EXAO_SET_COLOR (ID 260)...")

    # Test 1: Basic RGBA color
    stream = BytesIO(b"255,128,64,255)")
    result = exao_set_color(stream)
    assert result['opcode_id'] == 260
    assert result['name'] == 'EXAO_SET_COLOR'
    assert result['red'] == 255
    assert result['green'] == 128
    assert result['blue'] == 64
    assert result['alpha'] == 255
    assert result['index'] == WD_NO_COLOR_INDEX
    print("  ✓ Test 1 passed: (Color 255,128,64,255)")

    # Test 2: Black color
    stream = BytesIO(b"0,0,0,255)")
    result = exao_set_color(stream)
    assert result['red'] == 0
    assert result['green'] == 0
    assert result['blue'] == 0
    assert result['alpha'] == 255
    print("  ✓ Test 2 passed: (Color 0,0,0,255) - black")

    # Test 3: Semi-transparent color
    stream = BytesIO(b"100,150,200,128)")
    result = exao_set_color(stream)
    assert result['red'] == 100
    assert result['green'] == 150
    assert result['blue'] == 200
    assert result['alpha'] == 128
    print("  ✓ Test 3 passed: (Color 100,150,200,128) - semi-transparent")

    # Test 4: With whitespace
    stream = BytesIO(b" 64 , 128 , 192 , 255 )")
    result = exao_set_color(stream)
    assert result['red'] == 64
    assert result['green'] == 128
    assert result['blue'] == 192
    assert result['alpha'] == 255
    print("  ✓ Test 4 passed: (Color with whitespace)")

    print("EXAO_SET_COLOR: All tests passed!\n")


def test_exao_set_color_map():
    """Test EXAO_SET_COLOR_MAP opcode parsing."""
    print("Testing EXAO_SET_COLOR_MAP (ID 261)...")

    # Test 1: Simple 3-color palette
    stream = BytesIO(b"3 255,0,0,255 0,255,0,255 0,0,255,255)")
    result = exao_set_color_map(stream)
    assert result['opcode_id'] == 261
    assert result['name'] == 'EXAO_SET_COLOR_MAP'
    assert result['size'] == 3
    assert len(result['colors']) == 3
    assert result['colors'][0] == (255, 0, 0, 255)  # Red
    assert result['colors'][1] == (0, 255, 0, 255)  # Green
    assert result['colors'][2] == (0, 0, 255, 255)  # Blue
    print("  ✓ Test 1 passed: 3-color RGB palette")

    # Test 2: Single color map
    stream = BytesIO(b"1 128,128,128,255)")
    result = exao_set_color_map(stream)
    assert result['size'] == 1
    assert result['colors'][0] == (128, 128, 128, 255)
    print("  ✓ Test 2 passed: Single color map")

    # Test 3: Empty color map
    stream = BytesIO(b"0)")
    result = exao_set_color_map(stream)
    assert result['size'] == 0
    assert len(result['colors']) == 0
    print("  ✓ Test 3 passed: Empty color map")

    # Test 4: 5-color grayscale palette
    stream = BytesIO(b"5 0,0,0,255 64,64,64,255 128,128,128,255 192,192,192,255 255,255,255,255)")
    result = exao_set_color_map(stream)
    assert result['size'] == 5
    assert result['colors'][0] == (0, 0, 0, 255)
    assert result['colors'][4] == (255, 255, 255, 255)
    print("  ✓ Test 4 passed: 5-color grayscale palette")

    print("EXAO_SET_COLOR_MAP: All tests passed!\n")


def test_exao_set_contrast_color():
    """Test EXAO_SET_CONTRAST_COLOR opcode parsing."""
    print("Testing EXAO_SET_CONTRAST_COLOR (ID 385)...")

    # Test 1: White contrast color
    stream = BytesIO(b"255,255,255,255)")
    result = exao_set_contrast_color(stream)
    assert result['opcode_id'] == 385
    assert result['name'] == 'EXAO_SET_CONTRAST_COLOR'
    assert result['red'] == 255
    assert result['green'] == 255
    assert result['blue'] == 255
    assert result['alpha'] == 255
    print("  ✓ Test 1 passed: White contrast color")

    # Test 2: Yellow contrast color (common for dark backgrounds)
    stream = BytesIO(b"255,255,0,255)")
    result = exao_set_contrast_color(stream)
    assert result['red'] == 255
    assert result['green'] == 255
    assert result['blue'] == 0
    assert result['alpha'] == 255
    print("  ✓ Test 2 passed: Yellow contrast color")

    # Test 3: With leading whitespace
    stream = BytesIO(b"  128,200,255,255  )")
    result = exao_set_contrast_color(stream)
    assert result['red'] == 128
    assert result['green'] == 200
    assert result['blue'] == 255
    print("  ✓ Test 3 passed: With whitespace")

    print("EXAO_SET_CONTRAST_COLOR: All tests passed!\n")


def test_exao_set_layer():
    """Test EXAO_SET_LAYER opcode parsing."""
    print("Testing EXAO_SET_LAYER (ID 276)...")

    # Test 1: Layer with name
    stream = BytesIO(b'0 "Default Layer")')
    result = exao_set_layer(stream)
    assert result['opcode_id'] == 276
    assert result['name'] == 'EXAO_SET_LAYER'
    assert result['layer_num'] == 0
    assert result['layer_name'] == 'Default Layer'
    print("  ✓ Test 1 passed: Layer 0 with name")

    # Test 2: Layer without name (already defined)
    stream = BytesIO(b'5)')
    result = exao_set_layer(stream)
    assert result['layer_num'] == 5
    assert result['layer_name'] == ''
    print("  ✓ Test 2 passed: Layer reference without name")

    # Test 3: Layer with complex name
    stream = BytesIO(b'42 "Walls-Exterior-Level1")')
    result = exao_set_layer(stream)
    assert result['layer_num'] == 42
    assert result['layer_name'] == 'Walls-Exterior-Level1'
    print("  ✓ Test 3 passed: Layer with complex name")

    # Test 4: Layer with whitespace
    stream = BytesIO(b'  10  "My Layer"  )')
    result = exao_set_layer(stream)
    assert result['layer_num'] == 10
    assert result['layer_name'] == 'My Layer'
    print("  ✓ Test 4 passed: Layer with whitespace")

    print("EXAO_SET_LAYER: All tests passed!\n")


def test_exao_set_background():
    """Test EXAO_SET_BACKGROUND opcode parsing."""
    print("Testing EXAO_SET_BACKGROUND (ID 257)...")

    # Test 1: RGBA background
    stream = BytesIO(b"240,240,240,255)")
    result = exao_set_background(stream)
    assert result['opcode_id'] == 257
    assert result['name'] == 'EXAO_SET_BACKGROUND'
    assert result['red'] == 240
    assert result['green'] == 240
    assert result['blue'] == 240
    assert result['alpha'] == 255
    assert result['is_indexed'] == False
    assert result['index'] == WD_NO_COLOR_INDEX
    print("  ✓ Test 1 passed: RGBA background (light gray)")

    # Test 2: Indexed background
    stream = BytesIO(b"0)")
    result = exao_set_background(stream)
    assert result['is_indexed'] == True
    assert result['index'] == 0
    print("  ✓ Test 2 passed: Indexed background (index 0)")

    # Test 3: White background
    stream = BytesIO(b"255,255,255,255)")
    result = exao_set_background(stream)
    assert result['red'] == 255
    assert result['green'] == 255
    assert result['blue'] == 255
    assert result['is_indexed'] == False
    print("  ✓ Test 3 passed: White background")

    # Test 4: Indexed with larger value
    stream = BytesIO(b"127)")
    result = exao_set_background(stream)
    assert result['is_indexed'] == True
    assert result['index'] == 127
    print("  ✓ Test 4 passed: Indexed background (index 127)")

    print("EXAO_SET_BACKGROUND: All tests passed!\n")


def test_exao_set_code_page():
    """Test EXAO_SET_CODE_PAGE opcode parsing."""
    print("Testing EXAO_SET_CODE_PAGE (ID 266)...")

    # Test 1: Windows-1252 (Western European)
    stream = BytesIO(b"1252)")
    result = exao_set_code_page(stream)
    assert result['opcode_id'] == 266
    assert result['name'] == 'EXAO_SET_CODE_PAGE'
    assert result['page_number'] == 1252
    print("  ✓ Test 1 passed: Code page 1252 (Windows Latin-1)")

    # Test 2: UTF-8
    stream = BytesIO(b"65001)")
    result = exao_set_code_page(stream)
    assert result['page_number'] == 65001
    print("  ✓ Test 2 passed: Code page 65001 (UTF-8)")

    # Test 3: Japanese Shift-JIS
    stream = BytesIO(b"932)")
    result = exao_set_code_page(stream)
    assert result['page_number'] == 932
    print("  ✓ Test 3 passed: Code page 932 (Shift-JIS)")

    # Test 4: With whitespace
    stream = BytesIO(b"  1250  )")
    result = exao_set_code_page(stream)
    assert result['page_number'] == 1250
    print("  ✓ Test 4 passed: Code page with whitespace")

    print("EXAO_SET_CODE_PAGE: All tests passed!\n")


def test_helper_functions():
    """Test helper parsing functions."""
    print("Testing helper functions...")

    # Test eat_whitespace
    stream = BytesIO(b"   \t\n\r42")
    eat_whitespace(stream)
    assert stream.read(2) == b"42"
    print("  ✓ eat_whitespace works correctly")

    # Test read_ascii_int
    stream = BytesIO(b"  12345  ")
    val = read_ascii_int(stream)
    assert val == 12345
    print("  ✓ read_ascii_int works correctly")

    # Test read_ascii_int with negative
    stream = BytesIO(b"-99)")
    val = read_ascii_int(stream)
    assert val == -99
    print("  ✓ read_ascii_int handles negatives")

    # Test read_ascii_string (quoted)
    stream = BytesIO(b'"Hello World")')
    s = read_ascii_string(stream)
    assert s == "Hello World"
    print("  ✓ read_ascii_string handles quoted strings")

    # Test read_ascii_string (unquoted)
    stream = BytesIO(b'TestString )')
    s = read_ascii_string(stream)
    assert s == "TestString"
    print("  ✓ read_ascii_string handles unquoted strings")

    # Test skip_past_matching_paren
    stream = BytesIO(b"nested (data (here)) and more)")
    skip_past_matching_paren(stream)
    assert stream.read() == b""
    print("  ✓ skip_past_matching_paren handles nesting")

    print("Helper functions: All tests passed!\n")


def run_all_tests():
    """Run all test suites."""
    print("="*70)
    print("Agent 18: Extended ASCII Color/Layer Attributes - Test Suite")
    print("="*70)
    print()

    test_helper_functions()
    test_exao_set_color()
    test_exao_set_color_map()
    test_exao_set_contrast_color()
    test_exao_set_layer()
    test_exao_set_background()
    test_exao_set_code_page()

    print("="*70)
    print("All Agent 18 tests passed successfully!")
    print("="*70)
    print()
    print("Summary:")
    print("  - 6 Extended ASCII opcode handlers implemented")
    print("  - 6 color/layer parsing helpers implemented")
    print("  - 27+ comprehensive tests passed")
    print()
    print("Opcodes implemented:")
    print("  1. WD_EXAO_SET_COLOR (260) - RGBA color setting")
    print("  2. WD_EXAO_SET_COLOR_MAP (261) - Color palette definition")
    print("  3. WD_EXAO_SET_CONTRAST_COLOR (385) - Contrast color")
    print("  4. WD_EXAO_SET_LAYER (276) - Layer assignment")
    print("  5. WD_EXAO_SET_BACKGROUND (257) - Background color")
    print("  6. WD_EXAO_SET_CODE_PAGE (266) - Character encoding")
    print()


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    run_all_tests()
