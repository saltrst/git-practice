"""
DWF Extended ASCII Attribute Opcodes - Fill and Merge Handlers
Agent 20: Translation of fill/merge pattern and merge control opcodes

This module implements 6 DWF Extended ASCII opcodes related to fill patterns and merge control:
- WD_EXAO_PENPAT_OPTIONS (363) - (PenPat_Options) - Pen pattern rendering options
- WD_EXAO_SET_USER_FILL_PATTERN (381) - (UserFillPattern) - User-defined fill pattern
- WD_EXAO_SET_USER_HATCH_PATTERN (383) - (UserHatchPattern) - User-defined hatch pattern
- WD_EXAO_SET_MERGE_CONTROL (308) - (LinesOverwrite) - Merge control mode
- WD_EXAO_SET_OPAQUE (309) - Opaque merge mode (convenience)
- WD_EXAO_SET_MERGE (310) - Merge mode (convenience)

References:
- DWF Toolkit: develop/global/src/dwf/whiptk/penpat_options.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/usrfillpat.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/usrhatchpat.cpp
- DWF Toolkit: develop/global/src/dwf/whiptk/merge_control.cpp
- Research: agents/agent_outputs/agent_13_extended_opcodes_research.md
- Opcode definitions: develop/global/src/dwf/whiptk/opcode_defs.h

Author: Agent 20 (Fill/Merge Pattern Specialist)
"""

import struct
from typing import Dict, Any, List, Tuple, BinaryIO, Optional
from io import BytesIO


# ============================================================================
# Extended ASCII Parsing Utilities
# ============================================================================

class ExtendedASCIIParser:
    """
    Utility class for parsing Extended ASCII opcodes in format: (OpcodeName ...data...)

    Based on DWF Toolkit opcode.cpp lines 138-166
    """

    MAX_TOKEN_SIZE = 40

    @staticmethod
    def read_ascii_integer(stream: BinaryIO, eat_whitespace: bool = True) -> int:
        """
        Read an ASCII integer from the stream.

        Args:
            stream: Input stream
            eat_whitespace: If True, skip leading whitespace

        Returns:
            Integer value

        Raises:
            ValueError: If no valid integer found
            EOFError: If stream ends unexpectedly
        """
        if eat_whitespace:
            ExtendedASCIIParser.eat_whitespace(stream)

        num_str = ""
        sign = 1

        # Check for sign
        byte = stream.read(1)
        if not byte:
            raise EOFError("Unexpected EOF reading integer")

        char = chr(byte[0])
        if char == '-':
            sign = -1
        elif char == '+':
            pass
        elif char.isdigit():
            num_str += char
        else:
            stream.seek(-1, 1)

        # Read digits
        while True:
            byte = stream.read(1)
            if not byte:
                break

            char = chr(byte[0])
            if char.isdigit():
                num_str += char
            else:
                stream.seek(-1, 1)
                break

        if not num_str:
            raise ValueError("No integer value found")

        return sign * int(num_str)

    @staticmethod
    def read_ascii_double(stream: BinaryIO, eat_whitespace: bool = True) -> float:
        """
        Read an ASCII double/float from the stream.

        Args:
            stream: Input stream
            eat_whitespace: If True, skip leading whitespace

        Returns:
            Float value
        """
        if eat_whitespace:
            ExtendedASCIIParser.eat_whitespace(stream)

        num_str = ""

        # Read number (including sign, digits, decimal point)
        while True:
            byte = stream.read(1)
            if not byte:
                break

            char = chr(byte[0])
            if char in '0123456789.-+eE':
                num_str += char
            else:
                stream.seek(-1, 1)
                break

        if not num_str:
            raise ValueError("No double value found")

        return float(num_str)

    @staticmethod
    def read_quoted_string(stream: BinaryIO, max_length: int = 256) -> str:
        """
        Read a quoted string from the stream.

        Args:
            stream: Input stream
            max_length: Maximum string length

        Returns:
            Unquoted string
        """
        result = ""
        in_quotes = False

        while len(result) < max_length:
            byte = stream.read(1)
            if not byte:
                break

            char = chr(byte[0])

            if char == '"':
                if in_quotes:
                    return result
                else:
                    in_quotes = True
            elif in_quotes:
                result += char
            elif char not in ' \t\n\r':
                # Not in quotes and found non-whitespace
                stream.seek(-1, 1)
                return result

        return result

    @staticmethod
    def read_hex_data(stream: BinaryIO, size: int) -> bytes:
        """
        Read hex-encoded binary data from the stream.

        Args:
            stream: Input stream
            size: Number of bytes to read

        Returns:
            Decoded binary data
        """
        hex_str = ""
        bytes_needed = size * 2  # 2 hex chars per byte

        while len(hex_str) < bytes_needed:
            byte = stream.read(1)
            if not byte:
                break

            char = chr(byte[0])
            if char in '0123456789ABCDEFabcdef':
                hex_str += char
            elif char not in ' \t\n\r':
                stream.seek(-1, 1)
                break

        return bytes.fromhex(hex_str)

    @staticmethod
    def eat_whitespace(stream: BinaryIO) -> None:
        """Skip whitespace characters in the stream."""
        while True:
            byte = stream.read(1)
            if not byte:
                break
            if chr(byte[0]) not in ' \t\n\r':
                stream.seek(-1, 1)
                break

    @staticmethod
    def skip_past_matching_paren(stream: BinaryIO) -> None:
        """Skip to the closing parenthesis, accounting for nesting."""
        depth = 1
        while depth > 0:
            byte = stream.read(1)
            if not byte:
                raise EOFError("Unexpected EOF while skipping to matching paren")

            char = chr(byte[0])
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1


# ============================================================================
# Opcode 363 - WD_EXAO_PENPAT_OPTIONS - (PenPat_Options)
# ============================================================================

def opcode_363_penpat_options(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_PENPAT_OPTIONS opcode (ID 363) - (PenPat_Options).

    Sets rendering options for pen patterns, controlling how patterns are applied
    to drawing operations.

    Format (Extended ASCII):
        (PenPat_Options scale_pen_width map_colors_to_gray use_alt_fill use_error_diffusion)

        Each parameter is a boolean encoded as:
        - 0 = False
        - non-zero (typically 1) = True

    Example:
        (PenPat_Options 1 0 1 0)
        - scale_pen_width: True (1)
        - map_colors_to_gray_scale: False (0)
        - use_alternate_fill_rule: True (1)
        - use_error_diffusion_for_DWF_Rasters: False (0)

    Args:
        stream: Binary stream positioned after "(PenPat_Options" token

    Returns:
        Dictionary containing:
            - opcode: 363
            - name: "PENPAT_OPTIONS"
            - scale_pen_width: Boolean - Scale pen width with pattern
            - map_colors_to_gray_scale: Boolean - Convert colors to grayscale
            - use_alternate_fill_rule: Boolean - Use alternate fill rule (even-odd vs winding)
            - use_error_diffusion_for_DWF_Rasters: Boolean - Use error diffusion for rasters

    Reference:
        DWF Toolkit: whiptk/penpat_options.cpp lines 76-155
        Opcode def: opcode_defs.h line 238 (WD_EXAO_PENPAT_OPTIONS 363)
        Serialize: penpat_options.cpp lines 29-67
    """
    parser = ExtendedASCIIParser()

    # Read 4 boolean flags
    parser.eat_whitespace(stream)
    scale_pen_width = parser.read_ascii_integer(stream) != 0

    parser.eat_whitespace(stream)
    map_colors_to_gray_scale = parser.read_ascii_integer(stream) != 0

    parser.eat_whitespace(stream)
    use_alternate_fill_rule = parser.read_ascii_integer(stream) != 0

    parser.eat_whitespace(stream)
    use_error_diffusion_for_DWF_Rasters = parser.read_ascii_integer(stream) != 0

    # Skip to closing paren
    parser.skip_past_matching_paren(stream)

    return {
        'opcode': 363,
        'name': 'PENPAT_OPTIONS',
        'scale_pen_width': scale_pen_width,
        'map_colors_to_gray_scale': map_colors_to_gray_scale,
        'use_alternate_fill_rule': use_alternate_fill_rule,
        'use_error_diffusion_for_DWF_Rasters': use_error_diffusion_for_DWF_Rasters
    }


# ============================================================================
# Opcode 381 - WD_EXAO_SET_USER_FILL_PATTERN - (UserFillPattern)
# ============================================================================

def opcode_381_user_fill_pattern(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_USER_FILL_PATTERN opcode (ID 381) - (UserFillPattern).

    Defines a user-defined fill pattern using a bitonal (black/white) bitmap.
    The pattern can be referenced by its pattern number in subsequent drawing operations.

    Format (Extended ASCII):
        (UserFillPattern pattern_num)
        OR
        (UserFillPattern pattern_num cols,rows (data_size hex_data))
        OR
        (UserFillPattern pattern_num cols,rows (FillPatternScale scale) (data_size hex_data))

    Examples:
        (UserFillPattern 5)  # Reference pattern 5 without defining it
        (UserFillPattern 3 8,8 (8 0F1E3C78F0E1C387))  # 8x8 pattern, 8 bytes of hex data
        (UserFillPattern 1 16,16 (FillPatternScale 2.5) (32 FF00FF00...))  # With scale

    Args:
        stream: Binary stream positioned after "(UserFillPattern" token

    Returns:
        Dictionary containing:
            - opcode: 381
            - name: "USER_FILL_PATTERN"
            - pattern_num: Integer pattern identifier
            - columns: Optional[int] - Pattern width in pixels
            - rows: Optional[int] - Pattern height in pixels
            - pattern_scale: Optional[float] - Scale factor (default 1.0)
            - data_size: Optional[int] - Size of pattern data in bytes
            - data: Optional[bytes] - Bitonal bitmap data

    Reference:
        DWF Toolkit: whiptk/usrfillpat.cpp lines 115-236 (materialize)
        DWF Toolkit: whiptk/usrfillpat.cpp lines 254-333 (serialize)
        Opcode def: opcode_defs.h line 256 (WD_EXAO_SET_USER_FILL_PATTERN 381)
    """
    parser = ExtendedASCIIParser()

    # Read pattern number
    parser.eat_whitespace(stream)
    pattern_num = parser.read_ascii_integer(stream)

    # Check if there's more data or just pattern reference
    parser.eat_whitespace(stream)
    byte = stream.read(1)

    if not byte or chr(byte[0]) == ')':
        # Just a pattern reference, no definition
        return {
            'opcode': 381,
            'name': 'USER_FILL_PATTERN',
            'pattern_num': pattern_num,
            'columns': None,
            'rows': None,
            'pattern_scale': 1.0,
            'data_size': None,
            'data': None
        }

    stream.seek(-1, 1)  # Put byte back

    # Read columns,rows
    columns = parser.read_ascii_integer(stream)

    # Read comma separator
    byte = stream.read(1)
    if not byte or chr(byte[0]) != ',':
        raise ValueError(f"Expected comma after columns, got {chr(byte[0]) if byte else 'EOF'}")

    rows = parser.read_ascii_integer(stream)

    parser.eat_whitespace(stream)

    # Check for optional (FillPatternScale value)
    pattern_scale = 1.0
    byte = stream.read(1)
    if byte and chr(byte[0]) == '(':
        # Peek ahead to see if it's FillPatternScale
        peek = stream.read(16)
        stream.seek(-16, 1)

        if peek.startswith(b'FillPatternScale'):
            # Skip the opening paren we already read
            # Read "FillPatternScale"
            token = stream.read(16).decode('ascii')
            parser.eat_whitespace(stream)
            pattern_scale = parser.read_ascii_double(stream)

            # Skip closing paren for FillPatternScale
            parser.eat_whitespace(stream)
            byte = stream.read(1)
            if byte and chr(byte[0]) != ')':
                raise ValueError("Expected closing paren after FillPatternScale")

            parser.eat_whitespace(stream)
            byte = stream.read(1)

    # Now we should be at the data section: (data_size hex_data)
    if not byte or chr(byte[0]) != '(':
        raise ValueError(f"Expected opening paren for data section, got {chr(byte[0]) if byte else 'EOF'}")

    # Read data size
    parser.eat_whitespace(stream)
    data_size = parser.read_ascii_integer(stream)

    # Read hex data
    parser.eat_whitespace(stream)
    data = parser.read_hex_data(stream, data_size)

    # Read closing paren for data section
    parser.eat_whitespace(stream)
    byte = stream.read(1)
    if not byte or chr(byte[0]) != ')':
        raise ValueError("Expected closing paren after hex data")

    # Read closing paren for entire opcode
    parser.eat_whitespace(stream)
    byte = stream.read(1)
    if not byte or chr(byte[0]) != ')':
        raise ValueError("Expected closing paren for opcode")

    return {
        'opcode': 381,
        'name': 'USER_FILL_PATTERN',
        'pattern_num': pattern_num,
        'columns': columns,
        'rows': rows,
        'pattern_scale': pattern_scale,
        'data_size': data_size,
        'data': data
    }


# ============================================================================
# Opcode 383 - WD_EXAO_SET_USER_HATCH_PATTERN - (UserHatchPattern)
# ============================================================================

def opcode_383_user_hatch_pattern(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_USER_HATCH_PATTERN opcode (ID 383) - (UserHatchPattern).

    Defines a user-defined hatch pattern consisting of one or more line sets.
    Each line set defines parallel lines with specific angle, spacing, and dash pattern.

    Format (Extended ASCII):
        (UserHatchPattern pattern_num)
        OR
        (UserHatchPattern pattern_num xsize,ysize count (x y angle spacing) ...)
        OR
        (UserHatchPattern pattern_num xsize,ysize count (x y angle spacing skew dash_count d1 d2 ...) ...)

    Examples:
        (UserHatchPattern 7)  # Reference pattern 7 without defining
        (UserHatchPattern 2 1.0,1.0 1 (0.0 0.0 45.0 0.5))  # Single diagonal hatch
        (UserHatchPattern 3 1.0,1.0 2 (0.0 0.0 0.0 0.25 0.0 2 0.5 0.5) (0.0 0.0 90.0 0.25))  # Cross-hatch

    Args:
        stream: Binary stream positioned after "(UserHatchPattern" token

    Returns:
        Dictionary containing:
            - opcode: 383
            - name: "USER_HATCH_PATTERN"
            - pattern_num: Integer pattern identifier
            - xsize: Optional[float] - X dimension of pattern cell
            - ysize: Optional[float] - Y dimension of pattern cell
            - count: Optional[int] - Number of hatch line sets
            - patterns: Optional[List[Dict]] - List of hatch pattern definitions, each with:
                - x: float - X offset
                - y: float - Y offset
                - angle: float - Line angle in degrees
                - spacing: float - Distance between parallel lines
                - skew: Optional[float] - Skew angle
                - dash_pattern: Optional[List[float]] - Dash pattern (on/off lengths)

    Reference:
        DWF Toolkit: whiptk/usrhatchpat.cpp lines 382-496 (materialize_ascii)
        DWF Toolkit: whiptk/usrhatchpat.cpp lines 265-316 (serialize_ascii)
        Opcode def: opcode_defs.h line 258 (WD_EXAO_SET_USER_HATCH_PATTERN 383)
    """
    parser = ExtendedASCIIParser()

    # Read pattern number
    parser.eat_whitespace(stream)
    pattern_num = parser.read_ascii_integer(stream)

    # Check if there's more data
    parser.eat_whitespace(stream)
    byte = stream.read(1)

    if not byte or chr(byte[0]) == ')':
        # Just a pattern reference
        return {
            'opcode': 383,
            'name': 'USER_HATCH_PATTERN',
            'pattern_num': pattern_num,
            'xsize': None,
            'ysize': None,
            'count': None,
            'patterns': None
        }

    stream.seek(-1, 1)  # Put byte back

    # Read xsize,ysize
    xsize = parser.read_ascii_double(stream)

    byte = stream.read(1)
    if not byte or chr(byte[0]) != ',':
        raise ValueError(f"Expected comma after xsize, got {chr(byte[0]) if byte else 'EOF'}")

    ysize = parser.read_ascii_double(stream)

    # Read count
    parser.eat_whitespace(stream)
    count = parser.read_ascii_integer(stream)

    # Read hatch patterns
    patterns = []
    for i in range(count):
        parser.eat_whitespace(stream)

        # Expect opening paren
        byte = stream.read(1)
        if not byte or chr(byte[0]) != '(':
            raise ValueError(f"Expected opening paren for hatch pattern {i}")

        # Read required fields: x y angle spacing
        x = parser.read_ascii_double(stream)
        parser.eat_whitespace(stream)
        y = parser.read_ascii_double(stream)
        parser.eat_whitespace(stream)
        angle = parser.read_ascii_double(stream)
        parser.eat_whitespace(stream)
        spacing = parser.read_ascii_double(stream)

        # Check for optional skew and dash pattern
        parser.eat_whitespace(stream)
        byte = stream.read(1)

        skew = 0.0
        dash_pattern = []

        if byte and chr(byte[0]) != ')':
            # Has optional data
            stream.seek(-1, 1)

            skew = parser.read_ascii_double(stream)
            parser.eat_whitespace(stream)
            dash_count = parser.read_ascii_integer(stream)

            for j in range(dash_count):
                parser.eat_whitespace(stream)
                dash_value = parser.read_ascii_double(stream)
                dash_pattern.append(dash_value)

            # Read closing paren
            parser.eat_whitespace(stream)
            byte = stream.read(1)
            if not byte or chr(byte[0]) != ')':
                raise ValueError(f"Expected closing paren for hatch pattern {i}")

        pattern_entry = {
            'x': x,
            'y': y,
            'angle': angle,
            'spacing': spacing,
            'skew': skew,
            'dash_pattern': dash_pattern if dash_pattern else None
        }
        patterns.append(pattern_entry)

    # Read closing paren for entire opcode
    parser.eat_whitespace(stream)
    byte = stream.read(1)
    if not byte or chr(byte[0]) != ')':
        raise ValueError("Expected closing paren for opcode")

    return {
        'opcode': 383,
        'name': 'USER_HATCH_PATTERN',
        'pattern_num': pattern_num,
        'xsize': xsize,
        'ysize': ysize,
        'count': count,
        'patterns': patterns
    }


# ============================================================================
# Opcode 308 - WD_EXAO_SET_MERGE_CONTROL - (LinesOverwrite)
# ============================================================================

def opcode_308_merge_control(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SET_MERGE_CONTROL opcode (ID 308) - (LinesOverwrite).

    Sets the merge/blending mode for overlapping geometry. Controls how pixels
    are combined when objects overlap.

    Format (Extended ASCII):
        (LinesOverwrite "mode")

    Modes:
        - "opaque" (309): Overlapping geometry completely obscures underlying geometry
        - "merge" (310): Pixel colors blend/mask merge (mostly top color)
        - "transparent" (311): Pixel colors exclusive-or

    Examples:
        (LinesOverwrite "opaque")
        (LinesOverwrite "merge")
        (LinesOverwrite "transparent")

    Args:
        stream: Binary stream positioned after "(LinesOverwrite" token

    Returns:
        Dictionary containing:
            - opcode: 308
            - name: "MERGE_CONTROL"
            - mode: String - One of "opaque", "merge", or "transparent"
            - mode_id: Integer - Corresponding enum value (309, 310, or 311)

    Reference:
        DWF Toolkit: whiptk/merge_control.cpp lines 108-145 (materialize)
        DWF Toolkit: whiptk/merge_control.cpp lines 41-63 (serialize)
        DWF Toolkit: whiptk/merge_control.h lines 54-56 (enum values)
        Opcode def: opcode_defs.h line 183 (WD_EXAO_SET_MERGE_CONTROL 308)
    """
    parser = ExtendedASCIIParser()

    # Read the mode string (quoted)
    parser.eat_whitespace(stream)
    mode = parser.read_quoted_string(stream, max_length=40)

    # Validate mode and map to ID
    mode_map = {
        'opaque': 309,      # WD_EXAO_SET_OPAQUE
        'merge': 310,       # WD_EXAO_SET_MERGE
        'transparent': 311  # WD_EXAO_SET_TRANSPARENT
    }

    if mode not in mode_map:
        raise ValueError(f"Invalid merge control mode: '{mode}'. Expected 'opaque', 'merge', or 'transparent'")

    mode_id = mode_map[mode]

    # Skip to closing paren
    parser.skip_past_matching_paren(stream)

    return {
        'opcode': 308,
        'name': 'MERGE_CONTROL',
        'mode': mode,
        'mode_id': mode_id
    }


# ============================================================================
# Opcodes 309 & 310 - Convenience Functions
# ============================================================================

def opcode_309_set_opaque() -> Dict[str, Any]:
    """
    Convenience function for WD_EXAO_SET_OPAQUE (ID 309).

    Note: This is not a separate opcode in the file format. It's an enum value
    used by the merge control system. In practice, merge control is set via
    opcode 308 (LinesOverwrite "opaque").

    Returns:
        Dictionary containing:
            - opcode: 309
            - name: "SET_OPAQUE"
            - mode: "opaque"
            - description: "Opaque rendering mode"

    Reference:
        DWF Toolkit: whiptk/merge_control.h line 54
        Opcode def: opcode_defs.h line 184 (WD_EXAO_SET_OPAQUE 309)
    """
    return {
        'opcode': 309,
        'name': 'SET_OPAQUE',
        'mode': 'opaque',
        'description': 'Overlapping geometry completely obscures underlying geometry'
    }


def opcode_310_set_merge() -> Dict[str, Any]:
    """
    Convenience function for WD_EXAO_SET_MERGE (ID 310).

    Note: This is not a separate opcode in the file format. It's an enum value
    used by the merge control system. In practice, merge control is set via
    opcode 308 (LinesOverwrite "merge").

    Returns:
        Dictionary containing:
            - opcode: 310
            - name: "SET_MERGE"
            - mode: "merge"
            - description: "Merge rendering mode"

    Reference:
        DWF Toolkit: whiptk/merge_control.h line 55
        Opcode def: opcode_defs.h line 185 (WD_EXAO_SET_MERGE 310)
    """
    return {
        'opcode': 310,
        'name': 'SET_MERGE',
        'mode': 'merge',
        'description': 'Overlapping geometry pixel colors should mask merge'
    }


# ============================================================================
# Tests
# ============================================================================

def test_opcode_363_penpat_options():
    """Test WD_EXAO_PENPAT_OPTIONS parsing."""
    # Test 1: All options enabled
    data = b" 1 1 1 1)"
    stream = BytesIO(data)
    result = opcode_363_penpat_options(stream)

    assert result['opcode'] == 363
    assert result['name'] == 'PENPAT_OPTIONS'
    assert result['scale_pen_width'] == True
    assert result['map_colors_to_gray_scale'] == True
    assert result['use_alternate_fill_rule'] == True
    assert result['use_error_diffusion_for_DWF_Rasters'] == True
    print("✓ Test 1 passed: PenPat_Options all enabled")

    # Test 2: Mixed options
    data = b" 1 0 1 0)"
    stream = BytesIO(data)
    result = opcode_363_penpat_options(stream)

    assert result['scale_pen_width'] == True
    assert result['map_colors_to_gray_scale'] == False
    assert result['use_alternate_fill_rule'] == True
    assert result['use_error_diffusion_for_DWF_Rasters'] == False
    print("✓ Test 2 passed: PenPat_Options mixed values")

    # Test 3: All disabled
    data = b" 0 0 0 0)"
    stream = BytesIO(data)
    result = opcode_363_penpat_options(stream)

    assert result['scale_pen_width'] == False
    assert result['map_colors_to_gray_scale'] == False
    assert result['use_alternate_fill_rule'] == False
    assert result['use_error_diffusion_for_DWF_Rasters'] == False
    print("✓ Test 3 passed: PenPat_Options all disabled")


def test_opcode_381_user_fill_pattern():
    """Test WD_EXAO_SET_USER_FILL_PATTERN parsing."""
    # Test 1: Pattern reference only
    data = b" 5)"
    stream = BytesIO(data)
    result = opcode_381_user_fill_pattern(stream)

    assert result['opcode'] == 381
    assert result['name'] == 'USER_FILL_PATTERN'
    assert result['pattern_num'] == 5
    assert result['columns'] is None
    assert result['data'] is None
    print("✓ Test 1 passed: UserFillPattern reference only")

    # Test 2: Simple pattern with data
    data = b" 3 8,8 (8 0F1E3C78F0E1C387))"
    stream = BytesIO(data)
    result = opcode_381_user_fill_pattern(stream)

    assert result['pattern_num'] == 3
    assert result['columns'] == 8
    assert result['rows'] == 8
    assert result['data_size'] == 8
    assert len(result['data']) == 8
    assert result['data'] == bytes.fromhex('0F1E3C78F0E1C387')
    print("✓ Test 2 passed: UserFillPattern with 8x8 data")

    # Test 3: Pattern with scale
    data = b" 1 4,4 (FillPatternScale 2.5) (2 FFAA))"
    stream = BytesIO(data)
    result = opcode_381_user_fill_pattern(stream)

    assert result['pattern_num'] == 1
    assert result['columns'] == 4
    assert result['rows'] == 4
    assert result['pattern_scale'] == 2.5
    assert result['data_size'] == 2
    assert result['data'] == bytes.fromhex('FFAA')
    print("✓ Test 3 passed: UserFillPattern with scale")


def test_opcode_383_user_hatch_pattern():
    """Test WD_EXAO_SET_USER_HATCH_PATTERN parsing."""
    # Test 1: Pattern reference only
    data = b" 7)"
    stream = BytesIO(data)
    result = opcode_383_user_hatch_pattern(stream)

    assert result['opcode'] == 383
    assert result['name'] == 'USER_HATCH_PATTERN'
    assert result['pattern_num'] == 7
    assert result['patterns'] is None
    print("✓ Test 1 passed: UserHatchPattern reference only")

    # Test 2: Single hatch line (no dash pattern)
    data = b" 2 1.0,1.0 1 (0.0 0.0 45.0 0.5))"
    stream = BytesIO(data)
    result = opcode_383_user_hatch_pattern(stream)

    assert result['pattern_num'] == 2
    assert result['xsize'] == 1.0
    assert result['ysize'] == 1.0
    assert result['count'] == 1
    assert len(result['patterns']) == 1
    assert result['patterns'][0]['x'] == 0.0
    assert result['patterns'][0]['y'] == 0.0
    assert result['patterns'][0]['angle'] == 45.0
    assert result['patterns'][0]['spacing'] == 0.5
    assert result['patterns'][0]['skew'] == 0.0
    assert result['patterns'][0]['dash_pattern'] is None
    print("✓ Test 2 passed: UserHatchPattern single line")

    # Test 3: Multiple hatch lines with dash pattern
    data = b" 3 1.0,1.0 2 (0.0 0.0 0.0 0.25 0.0 2 0.5 0.5) (0.0 0.0 90.0 0.25))"
    stream = BytesIO(data)
    result = opcode_383_user_hatch_pattern(stream)

    assert result['count'] == 2
    assert len(result['patterns']) == 2

    # First pattern has dash pattern
    assert result['patterns'][0]['angle'] == 0.0
    assert result['patterns'][0]['spacing'] == 0.25
    assert result['patterns'][0]['skew'] == 0.0
    assert result['patterns'][0]['dash_pattern'] == [0.5, 0.5]

    # Second pattern has no dash pattern
    assert result['patterns'][1]['angle'] == 90.0
    assert result['patterns'][1]['spacing'] == 0.25
    assert result['patterns'][1]['dash_pattern'] is None
    print("✓ Test 3 passed: UserHatchPattern cross-hatch with dash")


def test_opcode_308_merge_control():
    """Test WD_EXAO_SET_MERGE_CONTROL parsing."""
    # Test 1: Opaque mode
    data = b' "opaque")'
    stream = BytesIO(data)
    result = opcode_308_merge_control(stream)

    assert result['opcode'] == 308
    assert result['name'] == 'MERGE_CONTROL'
    assert result['mode'] == 'opaque'
    assert result['mode_id'] == 309
    print("✓ Test 1 passed: Merge control opaque mode")

    # Test 2: Merge mode
    data = b' "merge")'
    stream = BytesIO(data)
    result = opcode_308_merge_control(stream)

    assert result['mode'] == 'merge'
    assert result['mode_id'] == 310
    print("✓ Test 2 passed: Merge control merge mode")

    # Test 3: Transparent mode
    data = b' "transparent")'
    stream = BytesIO(data)
    result = opcode_308_merge_control(stream)

    assert result['mode'] == 'transparent'
    assert result['mode_id'] == 311
    print("✓ Test 3 passed: Merge control transparent mode")


def test_convenience_functions():
    """Test convenience functions for opcodes 309 and 310."""
    # Test opcode 309
    result = opcode_309_set_opaque()
    assert result['opcode'] == 309
    assert result['mode'] == 'opaque'
    print("✓ Test passed: SET_OPAQUE convenience function")

    # Test opcode 310
    result = opcode_310_set_merge()
    assert result['opcode'] == 310
    assert result['mode'] == 'merge'
    print("✓ Test passed: SET_MERGE convenience function")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*70)
    print("Agent 20: Fill/Merge Pattern Opcode Tests")
    print("="*70 + "\n")

    print("Testing Opcode 363 - PENPAT_OPTIONS...")
    test_opcode_363_penpat_options()
    print()

    print("Testing Opcode 381 - USER_FILL_PATTERN...")
    test_opcode_381_user_fill_pattern()
    print()

    print("Testing Opcode 383 - USER_HATCH_PATTERN...")
    test_opcode_383_user_hatch_pattern()
    print()

    print("Testing Opcode 308 - MERGE_CONTROL...")
    test_opcode_308_merge_control()
    print()

    print("Testing Convenience Functions (309, 310)...")
    test_convenience_functions()
    print()

    print("="*70)
    print("All tests passed! ✓")
    print("="*70)


if __name__ == '__main__':
    run_all_tests()
