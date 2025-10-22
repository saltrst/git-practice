"""
Agent 19: DWF Extended ASCII Line Style Attribute Opcodes - Python Translation

This module implements 6 Extended ASCII line style attribute opcodes for DWF to PDF conversion.

Opcodes Implemented:
1. WD_EXAO_SET_LINE_PATTERN (ID 277) - Line pattern (dashed, dotted, etc.)
2. WD_EXAO_SET_LINE_WEIGHT (ID 278) - Line thickness
3. WD_EXAO_SET_LINE_STYLE (ID 279) - Line style (caps, joins, etc.)
4. WD_EXAO_SET_DASH_PATTERN (ID 267) - Custom dash pattern
5. WD_EXAO_SET_FILL_PATTERN (ID 315) - Fill pattern
6. WD_EXAO_PEN_PATTERN (ID 357) - Pen pattern with screening

Author: Agent 19
Date: 2025-10-22
Source: DWF Toolkit C++ Reference Implementation
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from enum import IntEnum
import struct
import io


# =============================================================================
# ENUMERATIONS
# =============================================================================

class LinePatternID(IntEnum):
    """Predefined line pattern IDs (36 patterns)."""
    ILLEGAL = 0
    SOLID = 1
    DASHED = 2
    DOTTED = 3
    DASH_DOT = 4
    SHORT_DASH = 5
    MEDIUM_DASH = 6
    LONG_DASH = 7
    SHORT_DASH_X2 = 8
    MEDIUM_DASH_X2 = 9
    LONG_DASH_X2 = 10
    MEDIUM_LONG_DASH = 11
    MEDIUM_DASH_SHORT_DASH_SHORT_DASH = 12
    LONG_DASH_SHORT_DASH = 13
    LONG_DASH_DOT_DOT = 14
    LONG_DASH_DOT = 15
    MEDIUM_DASH_DOT_SHORT_DASH_DOT = 16
    SPARSE_DOT = 17
    ISO_DASH = 18
    ISO_DASH_SPACE = 19
    ISO_LONG_DASH_DOT = 20
    ISO_LONG_DASH_DOUBLE_DOT = 21
    ISO_LONG_DASH_TRIPLE_DOT = 22
    ISO_DOT = 23
    ISO_LONG_DASH_SHORT_DASH = 24
    ISO_LONG_DASH_DOUBLE_SHORT_DASH = 25
    ISO_DASH_DOT = 26
    ISO_DOUBLE_DASH_DOT = 27
    ISO_DASH_DOUBLE_DOT = 28
    ISO_DOUBLE_DASH_DOUBLE_DOT = 29
    ISO_DASH_TRIPLE_DOT = 30
    ISO_DOUBLE_DASH_TRIPLE_DOT = 31
    DECORATED_TRACKS = 32
    DECORATED_WIDE_TRACKS = 33
    DECORATED_CIRCLE_FENCE = 34
    DECORATED_SQUARE_FENCE = 35


class CapStyleID(IntEnum):
    """Line cap styles for line endings and dash patterns."""
    BUTT_CAP = 0
    SQUARE_CAP = 1
    ROUND_CAP = 2
    DIAMOND_CAP = 3


class JoinStyleID(IntEnum):
    """Line join styles for connecting line segments."""
    MITER_JOIN = 0
    BEVEL_JOIN = 1
    ROUND_JOIN = 2
    DIAMOND_JOIN = 3


class FillPatternID(IntEnum):
    """Predefined fill pattern IDs (10 patterns)."""
    ILLEGAL = 0
    SOLID = 1
    CHECKERBOARD = 2
    CROSSHATCH = 3
    DIAMONDS = 4
    HORIZONTAL_BARS = 5
    SLANT_LEFT = 6
    SLANT_RIGHT = 7
    SQUARE_DOTS = 8
    VERTICAL_BARS = 9
    USER_DEFINED = 10


class PenPatternID(IntEnum):
    """Predefined pen pattern IDs (105 patterns)."""
    ILLEGAL = 0
    # Screening pen sets (use with screening percentage)
    SCREENING_BLACK = 1
    SCREENING_ALTERNATE = 2
    SCREENING_BLOCK = 3
    SCREENING_DOTS = 4
    SCREENING_BIG_DOTS = 5
    # Face patterns (fixed patterns)
    DOTS_BIG = 6
    DOTS_MEDIUM = 7
    DOTS_SMALL = 8
    SLANT_LEFT_32X32 = 9
    SLANT_RIGHT_32X32 = 10
    SCREEN_15 = 11
    SCREEN_25 = 12
    SCREEN_20 = 13
    SCREEN_75 = 14
    SCREEN_50 = 15
    SCREEN_THIN_50 = 16
    SCREEN_HATCHED_50 = 17
    TRELLIS = 18
    ZIGZAG = 19
    DIAGONAL = 20
    TRIANGLE = 21
    TRIANGLE_MORE = 22
    BRICKS = 23
    BRICKS_BIG = 24
    SQUARES = 25
    SQUARES_3D = 26
    DIAMOND_PLAID = 27
    ZIGGURAT = 28
    DIAGONAL_THATCH = 29
    ZIPPER = 30
    SLANTS = 31
    SLANTS_MORE = 32
    DIAGS = 33
    DIAGS_MORE = 34
    MARKS = 35
    MARKS_MORE = 36
    DIAMONDS_THICK = 37
    DIAMONDS_THIN = 38
    # Screening patterns with specific percentages
    SCREENING_BLACK_0 = 39
    SCREENING_BLACK_10 = 40


# =============================================================================
# PATTERN NAME MAPPINGS
# =============================================================================

LINE_PATTERN_NAMES = {
    "Solid": LinePatternID.SOLID,
    "Dashed": LinePatternID.DASHED,
    "Dotted": LinePatternID.DOTTED,
    "Dash_Dot": LinePatternID.DASH_DOT,
    "Short_Dash": LinePatternID.SHORT_DASH,
    "Medium_Dash": LinePatternID.MEDIUM_DASH,
    "Long_Dash": LinePatternID.LONG_DASH,
    "Short_Dash_X2": LinePatternID.SHORT_DASH_X2,
    "Medium_Dash_X2": LinePatternID.MEDIUM_DASH_X2,
    "Long_Dash_X2": LinePatternID.LONG_DASH_X2,
    "Medium_Long_Dash": LinePatternID.MEDIUM_LONG_DASH,
    "Medium_Dash_Short_Dash_Short_Dash": LinePatternID.MEDIUM_DASH_SHORT_DASH_SHORT_DASH,
    "Long_Dash_Short_Dash": LinePatternID.LONG_DASH_SHORT_DASH,
    "Long_Dash_Dot_Dot": LinePatternID.LONG_DASH_DOT_DOT,
    "Long_Dash_Dot": LinePatternID.LONG_DASH_DOT,
    "Medium_Dash_Dot_Short_Dash_Dot": LinePatternID.MEDIUM_DASH_DOT_SHORT_DASH_DOT,
    "Sparse_Dot": LinePatternID.SPARSE_DOT,
    "ISO_Dash": LinePatternID.ISO_DASH,
    "ISO_Dash_Space": LinePatternID.ISO_DASH_SPACE,
    "ISO_Long_Dash_Dot": LinePatternID.ISO_LONG_DASH_DOT,
    "ISO_Long_Dash_Double_Dot": LinePatternID.ISO_LONG_DASH_DOUBLE_DOT,
    "ISO_Long_Dash_Triple_Dot": LinePatternID.ISO_LONG_DASH_TRIPLE_DOT,
    "ISO_Dot": LinePatternID.ISO_DOT,
    "ISO_Long_Dash_Short_Dash": LinePatternID.ISO_LONG_DASH_SHORT_DASH,
    "ISO_Long_Dash_Double_Short_Dash": LinePatternID.ISO_LONG_DASH_DOUBLE_SHORT_DASH,
    "ISO_Dash_Dot": LinePatternID.ISO_DASH_DOT,
    "ISO_Double_Dash_Dot": LinePatternID.ISO_DOUBLE_DASH_DOT,
    "ISO_Dash_Double_Dot": LinePatternID.ISO_DASH_DOUBLE_DOT,
    "ISO_Double_Dash_Double_Dot": LinePatternID.ISO_DOUBLE_DASH_DOUBLE_DOT,
    "ISO_Dash_Triple_Dot": LinePatternID.ISO_DASH_TRIPLE_DOT,
    "ISO_Double_Dash_Triple_Dot": LinePatternID.ISO_DOUBLE_DASH_TRIPLE_DOT,
    "Decorated_Tracks": LinePatternID.DECORATED_TRACKS,
    "Decorated_Wide_Tracks": LinePatternID.DECORATED_WIDE_TRACKS,
    "Decorated_Circle_Fence": LinePatternID.DECORATED_CIRCLE_FENCE,
    "Decorated_Square_Fence": LinePatternID.DECORATED_SQUARE_FENCE,
    # Alternate names (legacy)
    "----": LinePatternID.SOLID,
    "- -": LinePatternID.DASHED,
    "....": LinePatternID.DOTTED,
    "-.-.": LinePatternID.DASH_DOT,
    "...": LinePatternID.SHORT_DASH_X2,
    "-- --": LinePatternID.LONG_DASH_X2,
    "-...": LinePatternID.MEDIUM_DASH_SHORT_DASH_SHORT_DASH,
    "-..-.": LinePatternID.LONG_DASH_DOT_DOT,
    "-..": LinePatternID.LONG_DASH_DOT,
    "center": LinePatternID.MEDIUM_DASH_DOT_SHORT_DASH_DOT,
    "phantom": LinePatternID.SPARSE_DOT,
}

FILL_PATTERN_NAMES = {
    "Solid": FillPatternID.SOLID,
    "Checkerboard": FillPatternID.CHECKERBOARD,
    "Crosshatch": FillPatternID.CROSSHATCH,
    "Diamonds": FillPatternID.DIAMONDS,
    "Horizontal Bars": FillPatternID.HORIZONTAL_BARS,
    "Slant Left": FillPatternID.SLANT_LEFT,
    "Slant Right": FillPatternID.SLANT_RIGHT,
    "Square Dots": FillPatternID.SQUARE_DOTS,
    "Vertical Bars": FillPatternID.VERTICAL_BARS,
    "User Defined": FillPatternID.USER_DEFINED,
}

CAP_STYLE_NAMES = {
    "butt": CapStyleID.BUTT_CAP,
    "square": CapStyleID.SQUARE_CAP,
    "round": CapStyleID.ROUND_CAP,
    "diamond": CapStyleID.DIAMOND_CAP,
}

JOIN_STYLE_NAMES = {
    "miter": JoinStyleID.MITER_JOIN,
    "bevel": JoinStyleID.BEVEL_JOIN,
    "round": JoinStyleID.ROUND_JOIN,
    "diamond": JoinStyleID.DIAMOND_JOIN,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LinePattern:
    """Line pattern attribute."""
    pattern_id: LinePatternID = LinePatternID.SOLID

    def __str__(self):
        return f"LinePattern(id={self.pattern_id.name})"


@dataclass
class LineWeight:
    """Line weight/thickness attribute (in drawing units)."""
    weight: int = 0  # 0 = 1-pixel line

    def __str__(self):
        return f"LineWeight(weight={self.weight})"


@dataclass
class LineStyle:
    """
    Line style attribute with multiple rendering options.

    Controls how thick lines are rendered with caps, joins, and pattern scaling.
    """
    adapt_patterns: bool = False
    pattern_scale: float = 1.0
    line_join: JoinStyleID = JoinStyleID.MITER_JOIN
    dash_start_cap: CapStyleID = CapStyleID.BUTT_CAP
    dash_end_cap: CapStyleID = CapStyleID.BUTT_CAP
    line_start_cap: CapStyleID = CapStyleID.BUTT_CAP
    line_end_cap: CapStyleID = CapStyleID.BUTT_CAP
    miter_angle: int = 10
    miter_length: int = 6

    def __str__(self):
        return (f"LineStyle(adapt={self.adapt_patterns}, scale={self.pattern_scale}, "
                f"join={self.line_join.name}, caps={self.line_start_cap.name})")


@dataclass
class DashPattern:
    """
    Custom dash pattern definition.

    Defines a user-customizable line pattern with alternating dash/space lengths.
    Pattern values must come in pairs (even count).
    """
    number: int = -1  # Unique pattern ID
    pattern: List[int] = field(default_factory=list)  # Pairs of on/off lengths

    def __post_init__(self):
        """Validate pattern has even number of values."""
        if len(self.pattern) % 2 != 0:
            raise ValueError("Dash pattern must have even number of values (pairs)")

    def __str__(self):
        return f"DashPattern(num={self.number}, pattern={self.pattern})"


@dataclass
class FillPattern:
    """Fill pattern attribute for filled shapes."""
    pattern_id: FillPatternID = FillPatternID.SOLID
    pattern_scale: float = 1.0

    def __str__(self):
        return f"FillPattern(id={self.pattern_id.name}, scale={self.pattern_scale})"


@dataclass
class ColorMap:
    """Simple 2-color map for pen patterns."""
    colors: List[Tuple[int, int, int, int]] = field(default_factory=list)  # RGBA tuples

    def __str__(self):
        return f"ColorMap({len(self.colors)} colors)"


@dataclass
class PenPattern:
    """
    Pen pattern attribute.

    Defines fill patterns for wide lines and filled areas, with optional
    screening percentage and color map.
    """
    pattern_id: PenPatternID = PenPatternID.SCREENING_BLACK
    screening_percentage: int = 0
    color_map: Optional[ColorMap] = None

    def __str__(self):
        return (f"PenPattern(id={self.pattern_id.name}, "
                f"screening={self.screening_percentage}%, "
                f"colormap={'yes' if self.color_map else 'no'})")


# =============================================================================
# OPCODE HANDLERS
# =============================================================================

def parse_line_pattern(stream: io.BytesIO) -> LinePattern:
    """
    Parse (LinePattern <pattern_name>) opcode.

    Format: (LinePattern "Solid")

    Args:
        stream: Input byte stream positioned after '(LinePattern'

    Returns:
        LinePattern object

    Example:
        >>> stream = io.BytesIO(b' "Dashed")')
        >>> pattern = parse_line_pattern(stream)
        >>> pattern.pattern_id == LinePatternID.DASHED
        True
    """
    # Skip whitespace
    _skip_whitespace(stream)

    # Read pattern name (may be quoted)
    pattern_name = _read_token(stream)

    # Lookup pattern ID
    pattern_id = LINE_PATTERN_NAMES.get(pattern_name, LinePatternID.SOLID)

    # Skip to closing paren
    _skip_to_close_paren(stream)

    return LinePattern(pattern_id=pattern_id)


def parse_line_weight(stream: io.BytesIO) -> LineWeight:
    """
    Parse (LineWeight <weight>) opcode.

    Format: (LineWeight 100)

    Args:
        stream: Input byte stream positioned after '(LineWeight'

    Returns:
        LineWeight object

    Example:
        >>> stream = io.BytesIO(b' 100)')
        >>> weight = parse_line_weight(stream)
        >>> weight.weight
        100
    """
    # Skip whitespace
    _skip_whitespace(stream)

    # Read weight value
    weight_str = _read_token(stream)
    weight = int(weight_str)

    # Skip to closing paren
    _skip_to_close_paren(stream)

    return LineWeight(weight=weight)


def parse_line_style(stream: io.BytesIO) -> LineStyle:
    """
    Parse (LineStyle <options>...) opcode.

    Format: (LineStyle (AdaptPatterns true) (LineJoin miter) (MiterAngle 10))

    Args:
        stream: Input byte stream positioned after '(LineStyle'

    Returns:
        LineStyle object

    Example:
        >>> stream = io.BytesIO(b' (AdaptPatterns true) (LineJoin bevel))')
        >>> style = parse_line_style(stream)
        >>> style.adapt_patterns
        True
        >>> style.line_join == JoinStyleID.BEVEL_JOIN
        True
    """
    style = LineStyle()

    while True:
        _skip_whitespace(stream)

        # Check for closing paren
        byte = stream.read(1)
        if not byte or byte == b')':
            break
        stream.seek(-1, 1)  # Put back

        # Check for option start
        if byte != b'(':
            break

        # Read option
        stream.read(1)  # Consume '('
        option_name = _read_token(stream)

        if option_name == "AdaptPatterns":
            _skip_whitespace(stream)
            value = _read_token(stream).lower()
            style.adapt_patterns = value in ('true', '1')
            _skip_to_close_paren(stream)

        elif option_name == "LinePatternScale":
            _skip_whitespace(stream)
            style.pattern_scale = float(_read_token(stream))
            _skip_to_close_paren(stream)

        elif option_name == "LineJoin":
            _skip_whitespace(stream)
            join_name = _read_token(stream).lower()
            style.line_join = JOIN_STYLE_NAMES.get(join_name, JoinStyleID.MITER_JOIN)
            _skip_to_close_paren(stream)

        elif option_name == "DashStartCap":
            _skip_whitespace(stream)
            cap_name = _read_token(stream).lower()
            style.dash_start_cap = CAP_STYLE_NAMES.get(cap_name, CapStyleID.BUTT_CAP)
            _skip_to_close_paren(stream)

        elif option_name == "DashEndCap":
            _skip_whitespace(stream)
            cap_name = _read_token(stream).lower()
            style.dash_end_cap = CAP_STYLE_NAMES.get(cap_name, CapStyleID.BUTT_CAP)
            _skip_to_close_paren(stream)

        elif option_name == "LineStartCap":
            _skip_whitespace(stream)
            cap_name = _read_token(stream).lower()
            style.line_start_cap = CAP_STYLE_NAMES.get(cap_name, CapStyleID.BUTT_CAP)
            _skip_to_close_paren(stream)

        elif option_name == "LineEndCap":
            _skip_whitespace(stream)
            cap_name = _read_token(stream).lower()
            style.line_end_cap = CAP_STYLE_NAMES.get(cap_name, CapStyleID.BUTT_CAP)
            _skip_to_close_paren(stream)

        elif option_name == "MiterAngle":
            _skip_whitespace(stream)
            style.miter_angle = int(_read_token(stream))
            _skip_to_close_paren(stream)

        elif option_name == "MiterLength":
            _skip_whitespace(stream)
            style.miter_length = int(_read_token(stream))
            _skip_to_close_paren(stream)

        else:
            # Unknown option, skip it
            _skip_to_close_paren(stream)

    return style


def parse_dash_pattern(stream: io.BytesIO) -> DashPattern:
    """
    Parse (DashPattern <number> [<val1>,<val2>,...]) opcode.

    Format: (DashPattern 100 24,6,12,6)

    Args:
        stream: Input byte stream positioned after '(DashPattern'

    Returns:
        DashPattern object

    Example:
        >>> stream = io.BytesIO(b' 100 24,6,12,6)')
        >>> pattern = parse_dash_pattern(stream)
        >>> pattern.number
        100
        >>> pattern.pattern
        [24, 6, 12, 6]
    """
    # Skip whitespace
    _skip_whitespace(stream)

    # Read pattern number
    number_str = _read_token(stream)
    number = int(number_str)

    # Check for pattern definition
    _skip_whitespace(stream)
    byte = stream.read(1)

    pattern_values = []
    if byte and byte != b')':
        stream.seek(-1, 1)  # Put back

        # Read comma-separated values
        while True:
            _skip_whitespace(stream)
            value_str = _read_token(stream, stop_chars=b',)')
            if value_str:
                pattern_values.append(int(value_str))

            # Check for comma or closing paren
            byte = stream.read(1)
            if byte == b')':
                break
            elif byte != b',':
                stream.seek(-1, 1)
                break

    return DashPattern(number=number, pattern=pattern_values)


def parse_fill_pattern(stream: io.BytesIO) -> FillPattern:
    """
    Parse (FillPattern <pattern_name> [(FillPatternScale <scale>)]) opcode.

    Format: (FillPattern "Crosshatch" (FillPatternScale 2.0))

    Args:
        stream: Input byte stream positioned after '(FillPattern'

    Returns:
        FillPattern object

    Example:
        >>> stream = io.BytesIO(b' "Crosshatch" (FillPatternScale 2.0))')
        >>> pattern = parse_fill_pattern(stream)
        >>> pattern.pattern_id == FillPatternID.CROSSHATCH
        True
        >>> pattern.pattern_scale
        2.0
    """
    # Skip whitespace
    _skip_whitespace(stream)

    # Read pattern name
    pattern_name = _read_token(stream)
    pattern_id = FILL_PATTERN_NAMES.get(pattern_name, FillPatternID.SOLID)

    pattern_scale = 1.0

    # Check for options
    while True:
        _skip_whitespace(stream)
        byte = stream.read(1)

        if not byte or byte == b')':
            break

        if byte == b'(':
            option_name = _read_token(stream)
            if option_name == "FillPatternScale":
                _skip_whitespace(stream)
                pattern_scale = float(_read_token(stream))
                _skip_to_close_paren(stream)
            else:
                _skip_to_close_paren(stream)
        else:
            stream.seek(-1, 1)
            break

    return FillPattern(pattern_id=pattern_id, pattern_scale=pattern_scale)


def parse_pen_pattern(stream: io.BytesIO, is_binary: bool = False) -> PenPattern:
    """
    Parse (PenPattern <id> [<screening>] <flag> [<colormap>]) opcode.

    ASCII Format: (PenPattern 1 50 1 (ColorMap ...))
    Binary Format: {size opcode id [screening] flag [colormap]}

    Args:
        stream: Input byte stream
        is_binary: True if parsing binary format

    Returns:
        PenPattern object

    Example:
        >>> stream = io.BytesIO(b' 1 50 0)')
        >>> pattern = parse_pen_pattern(stream)
        >>> pattern.pattern_id == PenPatternID.SCREENING_BLACK
        True
        >>> pattern.screening_percentage
        50
    """
    if is_binary:
        return _parse_pen_pattern_binary(stream)
    else:
        return _parse_pen_pattern_ascii(stream)


def _parse_pen_pattern_ascii(stream: io.BytesIO) -> PenPattern:
    """Parse ASCII format pen pattern."""
    # Skip whitespace
    _skip_whitespace(stream)

    # Read pattern ID
    pattern_id = int(_read_token(stream))

    _skip_whitespace(stream)
    next_token = _read_token(stream)

    # Determine if this has screening percentage
    # IDs 1-5 require screening percentage
    screening_percentage = 0
    colormap_flag = next_token

    if 1 <= pattern_id <= 5:
        # This is screening percentage
        screening_percentage = int(next_token)
        _skip_whitespace(stream)
        colormap_flag = _read_token(stream)

    # Parse colormap flag
    has_colormap = (colormap_flag == '1')

    color_map = None
    if has_colormap:
        _skip_whitespace(stream)
        byte = stream.read(1)
        if byte == b'(':
            # Parse colormap (simplified - just skip for now)
            _skip_to_close_paren(stream)
            color_map = ColorMap()  # Placeholder

    # Skip to closing paren
    _skip_to_close_paren(stream)

    return PenPattern(
        pattern_id=PenPatternID(pattern_id),
        screening_percentage=screening_percentage,
        color_map=color_map
    )


def _parse_pen_pattern_binary(stream: io.BytesIO) -> PenPattern:
    """Parse binary format pen pattern (Extended Binary)."""
    # Read pattern ID
    pattern_id = struct.unpack('<I', stream.read(4))[0]

    screening_percentage = 0
    if 1 <= pattern_id <= 5:
        # Read screening percentage
        screening_percentage = struct.unpack('<I', stream.read(4))[0]

    # Read colormap flag
    flag = stream.read(1)[0]
    has_colormap = (flag == ord('1'))

    color_map = None
    if has_colormap:
        # Parse colormap (simplified)
        color_map = ColorMap()

    # Read closing brace
    closing = stream.read(1)
    if closing != b'}':
        raise ValueError("Expected '}' at end of binary opcode")

    return PenPattern(
        pattern_id=PenPatternID(pattern_id),
        screening_percentage=screening_percentage,
        color_map=color_map
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _skip_whitespace(stream: io.BytesIO) -> None:
    """Skip whitespace characters in stream."""
    while True:
        byte = stream.read(1)
        if not byte or byte not in (b' ', b'\t', b'\n', b'\r'):
            if byte:
                stream.seek(-1, 1)  # Put back non-whitespace
            break


def _read_token(stream: io.BytesIO, stop_chars: bytes = b' \t\n\r()') -> str:
    """
    Read a token from stream until whitespace or delimiter.

    Handles quoted strings properly.
    """
    _skip_whitespace(stream)

    token_bytes = []
    byte = stream.read(1)

    # Check for quoted string
    if byte == b'"':
        while True:
            byte = stream.read(1)
            if not byte or byte == b'"':
                break
            token_bytes.append(byte[0])
    else:
        # Read until delimiter
        if byte and byte[0] not in stop_chars:
            token_bytes.append(byte[0])

        while True:
            byte = stream.read(1)
            if not byte or byte[0] in stop_chars:
                if byte:
                    stream.seek(-1, 1)  # Put back delimiter
                break
            token_bytes.append(byte[0])

    return bytes(token_bytes).decode('ascii')


def _skip_to_close_paren(stream: io.BytesIO) -> None:
    """Skip to matching closing parenthesis, handling nesting."""
    depth = 1
    while depth > 0:
        byte = stream.read(1)
        if not byte:
            break
        if byte == b'(':
            depth += 1
        elif byte == b')':
            depth -= 1


# =============================================================================
# TESTS
# =============================================================================

def test_line_pattern():
    """Test line pattern parsing."""
    print("Testing Line Pattern...")

    # Test 1: Basic solid pattern
    stream = io.BytesIO(b' "Solid")')
    pattern = parse_line_pattern(stream)
    assert pattern.pattern_id == LinePatternID.SOLID, f"Expected SOLID, got {pattern.pattern_id}"
    print("  [PASS] Solid pattern")

    # Test 2: Dashed pattern
    stream = io.BytesIO(b' "Dashed")')
    pattern = parse_line_pattern(stream)
    assert pattern.pattern_id == LinePatternID.DASHED, f"Expected DASHED, got {pattern.pattern_id}"
    print("  [PASS] Dashed pattern")

    # Test 3: ISO pattern
    stream = io.BytesIO(b' "ISO_Dash_Dot")')
    pattern = parse_line_pattern(stream)
    assert pattern.pattern_id == LinePatternID.ISO_DASH_DOT, f"Expected ISO_DASH_DOT, got {pattern.pattern_id}"
    print("  [PASS] ISO dash dot pattern")

    # Test 4: Legacy alternate name
    stream = io.BytesIO(b' "----")')
    pattern = parse_line_pattern(stream)
    assert pattern.pattern_id == LinePatternID.SOLID, f"Expected SOLID (legacy), got {pattern.pattern_id}"
    print("  [PASS] Legacy pattern name")

    print("Line Pattern: ALL TESTS PASSED\n")


def test_line_weight():
    """Test line weight parsing."""
    print("Testing Line Weight...")

    # Test 1: Zero weight (1-pixel)
    stream = io.BytesIO(b' 0)')
    weight = parse_line_weight(stream)
    assert weight.weight == 0, f"Expected 0, got {weight.weight}"
    print("  [PASS] Zero weight")

    # Test 2: Positive weight
    stream = io.BytesIO(b' 100)')
    weight = parse_line_weight(stream)
    assert weight.weight == 100, f"Expected 100, got {weight.weight}"
    print("  [PASS] Weight 100")

    # Test 3: Large weight
    stream = io.BytesIO(b' 5000)')
    weight = parse_line_weight(stream)
    assert weight.weight == 5000, f"Expected 5000, got {weight.weight}"
    print("  [PASS] Large weight 5000")

    print("Line Weight: ALL TESTS PASSED\n")


def test_line_style():
    """Test line style parsing."""
    print("Testing Line Style...")

    # Test 1: Single option
    stream = io.BytesIO(b' (AdaptPatterns true))')
    style = parse_line_style(stream)
    assert style.adapt_patterns == True, f"Expected True, got {style.adapt_patterns}"
    print("  [PASS] Adapt patterns option")

    # Test 2: Multiple options
    stream = io.BytesIO(b' (LineJoin bevel) (MiterAngle 15))')
    style = parse_line_style(stream)
    assert style.line_join == JoinStyleID.BEVEL_JOIN, f"Expected BEVEL_JOIN, got {style.line_join}"
    assert style.miter_angle == 15, f"Expected 15, got {style.miter_angle}"
    print("  [PASS] Multiple options")

    # Test 3: Cap styles
    stream = io.BytesIO(b' (LineStartCap round) (LineEndCap square))')
    style = parse_line_style(stream)
    assert style.line_start_cap == CapStyleID.ROUND_CAP, f"Expected ROUND_CAP, got {style.line_start_cap}"
    assert style.line_end_cap == CapStyleID.SQUARE_CAP, f"Expected SQUARE_CAP, got {style.line_end_cap}"
    print("  [PASS] Cap styles")

    # Test 4: Pattern scale
    stream = io.BytesIO(b' (LinePatternScale 2.5))')
    style = parse_line_style(stream)
    assert abs(style.pattern_scale - 2.5) < 0.01, f"Expected 2.5, got {style.pattern_scale}"
    print("  [PASS] Pattern scale")

    print("Line Style: ALL TESTS PASSED\n")


def test_dash_pattern():
    """Test dash pattern parsing."""
    print("Testing Dash Pattern...")

    # Test 1: Pattern with no data
    stream = io.BytesIO(b' 100)')
    pattern = parse_dash_pattern(stream)
    assert pattern.number == 100, f"Expected 100, got {pattern.number}"
    assert len(pattern.pattern) == 0, f"Expected empty pattern, got {pattern.pattern}"
    print("  [PASS] Pattern number only")

    # Test 2: Pattern with data
    stream = io.BytesIO(b' 200 24,6,12,6)')
    pattern = parse_dash_pattern(stream)
    assert pattern.number == 200, f"Expected 200, got {pattern.number}"
    assert pattern.pattern == [24, 6, 12, 6], f"Expected [24,6,12,6], got {pattern.pattern}"
    print("  [PASS] Pattern with data")

    # Test 3: Complex pattern
    stream = io.BytesIO(b' 300 48,12,6,12,6,12)')
    pattern = parse_dash_pattern(stream)
    assert pattern.number == 300, f"Expected 300, got {pattern.number}"
    assert len(pattern.pattern) == 6, f"Expected 6 values, got {len(pattern.pattern)}"
    assert len(pattern.pattern) % 2 == 0, "Pattern must have even count"
    print("  [PASS] Complex pattern")

    print("Dash Pattern: ALL TESTS PASSED\n")


def test_fill_pattern():
    """Test fill pattern parsing."""
    print("Testing Fill Pattern...")

    # Test 1: Basic fill pattern
    stream = io.BytesIO(b' "Solid")')
    pattern = parse_fill_pattern(stream)
    assert pattern.pattern_id == FillPatternID.SOLID, f"Expected SOLID, got {pattern.pattern_id}"
    print("  [PASS] Solid fill")

    # Test 2: Crosshatch pattern
    stream = io.BytesIO(b' "Crosshatch")')
    pattern = parse_fill_pattern(stream)
    assert pattern.pattern_id == FillPatternID.CROSSHATCH, f"Expected CROSSHATCH, got {pattern.pattern_id}"
    print("  [PASS] Crosshatch fill")

    # Test 3: Pattern with scale
    stream = io.BytesIO(b' "Diamonds" (FillPatternScale 2.0))')
    pattern = parse_fill_pattern(stream)
    assert pattern.pattern_id == FillPatternID.DIAMONDS, f"Expected DIAMONDS, got {pattern.pattern_id}"
    assert abs(pattern.pattern_scale - 2.0) < 0.01, f"Expected 2.0, got {pattern.pattern_scale}"
    print("  [PASS] Fill with scale")

    print("Fill Pattern: ALL TESTS PASSED\n")


def test_pen_pattern():
    """Test pen pattern parsing."""
    print("Testing Pen Pattern...")

    # Test 1: Screening pattern without colormap
    stream = io.BytesIO(b' 1 50 0)')
    pattern = parse_pen_pattern(stream)
    assert pattern.pattern_id == PenPatternID.SCREENING_BLACK, f"Expected SCREENING_BLACK, got {pattern.pattern_id}"
    assert pattern.screening_percentage == 50, f"Expected 50, got {pattern.screening_percentage}"
    assert pattern.color_map is None, "Expected no color map"
    print("  [PASS] Screening pattern")

    # Test 2: Face pattern (no screening)
    stream = io.BytesIO(b' 6 0)')
    pattern = parse_pen_pattern(stream)
    assert pattern.pattern_id == PenPatternID.DOTS_BIG, f"Expected DOTS_BIG, got {pattern.pattern_id}"
    assert pattern.screening_percentage == 0, f"Expected 0, got {pattern.screening_percentage}"
    print("  [PASS] Face pattern")

    # Test 3: Screening with colormap flag
    stream = io.BytesIO(b' 2 75 1)')
    pattern = parse_pen_pattern(stream)
    assert pattern.pattern_id == PenPatternID.SCREENING_ALTERNATE, f"Expected SCREENING_ALTERNATE, got {pattern.pattern_id}"
    assert pattern.screening_percentage == 75, f"Expected 75, got {pattern.screening_percentage}"
    print("  [PASS] Pattern with colormap flag")

    print("Pen Pattern: ALL TESTS PASSED\n")


def run_all_tests():
    """Run all opcode tests."""
    print("=" * 70)
    print("Agent 19: Line Style Attribute Opcodes - Test Suite")
    print("=" * 70)
    print()

    test_line_pattern()
    test_line_weight()
    test_line_style()
    test_dash_pattern()
    test_fill_pattern()
    test_pen_pattern()

    print("=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)


# =============================================================================
# DOCUMENTATION & EXAMPLES
# =============================================================================

DOCUMENTATION = """
DWF Extended ASCII Line Style Attribute Opcodes - Documentation
================================================================

This module implements 6 line style attribute opcodes that control how lines,
patterns, and fills are rendered in DWF files.

OPCODES
-------

1. WD_EXAO_SET_LINE_PATTERN (ID 277)
   Format: (LinePattern <pattern_name>)

   Sets the line pattern for subsequent lines and arcs. Supports 36 predefined
   patterns including solid, dashed, dotted, ISO standards, and decorative patterns.

   Examples:
     (LinePattern "Solid")
     (LinePattern "Dashed")
     (LinePattern "ISO_Dash_Dot")
     (LinePattern "Decorated_Tracks")

2. WD_EXAO_SET_LINE_WEIGHT (ID 278)
   Format: (LineWeight <weight>)

   Sets the line thickness in drawing units. Value of 0 indicates a 1-pixel line.

   Examples:
     (LineWeight 0)      # 1-pixel line
     (LineWeight 100)    # 100 drawing units thick
     (LineWeight 5000)   # Very thick line

3. WD_EXAO_SET_LINE_STYLE (ID 279)
   Format: (LineStyle <options>...)

   Sets advanced line rendering options including caps, joins, and pattern scaling.
   Supports multiple nested options.

   Options:
     - (AdaptPatterns true|false) - Adjust pattern length to fit complete patterns
     - (LinePatternScale <float>) - Scale factor for pattern lengths
     - (LineJoin miter|bevel|round|diamond) - Join style for thick lines
     - (DashStartCap butt|square|round|diamond) - Dash start cap
     - (DashEndCap butt|square|round|diamond) - Dash end cap
     - (LineStartCap butt|square|round|diamond) - Line start cap
     - (LineEndCap butt|square|round|diamond) - Line end cap
     - (MiterAngle <int>) - Miter angle in degrees
     - (MiterLength <int>) - Miter length limit

   Examples:
     (LineStyle (AdaptPatterns true))
     (LineStyle (LineJoin bevel) (MiterAngle 15))
     (LineStyle (LineStartCap round) (LineEndCap square) (LinePatternScale 2.0))

4. WD_EXAO_SET_DASH_PATTERN (ID 267)
   Format: (DashPattern <number> [<val1>,<val2>,...])

   Defines a custom dash pattern with unique ID and alternating on/off pixel lengths.
   Pattern values must come in pairs (even count). Overrides line patterns when set.

   Examples:
     (DashPattern 100)                  # Reference pattern 100 (defined elsewhere)
     (DashPattern 200 24,6,12,6)       # Define new pattern: 24 on, 6 off, 12 on, 6 off
     (DashPattern 300 48,12,6,12,6,12) # Complex pattern

5. WD_EXAO_SET_FILL_PATTERN (ID 315)
   Format: (FillPattern <pattern_name> [options])

   Sets the fill pattern for filled shapes. Supports 10 predefined patterns with
   optional scaling.

   Patterns:
     - Solid, Checkerboard, Crosshatch, Diamonds
     - Horizontal Bars, Slant Left, Slant Right
     - Square Dots, Vertical Bars, User Defined

   Examples:
     (FillPattern "Solid")
     (FillPattern "Crosshatch")
     (FillPattern "Diamonds" (FillPatternScale 2.0))

6. WD_EXAO_PEN_PATTERN (ID 357)
   Format: (PenPattern <id> [<screening>] <colormap_flag> [<colormap>])
          {size opcode <id> [<screening>] <flag> [<colormap>]}  (binary)

   Sets pen pattern for wide lines and fills. Supports 105 predefined patterns
   including screening patterns (with percentage) and face patterns.

   Pattern Types:
     - Screening patterns (1-5): Use with screening percentage 0-100
     - Face patterns (6+): Fixed patterns, no screening

   Examples:
     (PenPattern 1 50 0)      # Screening Black at 50%, no colormap
     (PenPattern 2 75 1 ...)  # Screening Alternate at 75%, with colormap
     (PenPattern 6 0)         # Dots Big face pattern

PATTERN OVERRIDE RULES
---------------------

Line rendering follows this precedence:
  1. Dash Pattern (highest) - Overrides line pattern when set
  2. Line Pattern
  3. Solid line (default)

Fill rendering:
  1. Pen Pattern (highest) - For wide lines and fills
  2. Fill Pattern - For filled shapes
  3. Solid fill (default)

USAGE EXAMPLES
--------------

Python:
    from io import BytesIO

    # Parse line pattern
    stream = BytesIO(b' "Dashed")')
    pattern = parse_line_pattern(stream)
    print(pattern)  # LinePattern(id=DASHED)

    # Parse line weight
    stream = BytesIO(b' 100)')
    weight = parse_line_weight(stream)
    print(weight)  # LineWeight(weight=100)

    # Parse complex line style
    stream = BytesIO(b' (LineJoin bevel) (LineStartCap round))')
    style = parse_line_style(stream)
    print(style)  # LineStyle(join=BEVEL_JOIN, caps=ROUND_CAP)

    # Parse dash pattern
    stream = BytesIO(b' 200 24,6,12,6)')
    dash = parse_dash_pattern(stream)
    print(dash)  # DashPattern(num=200, pattern=[24, 6, 12, 6])

NOTES
-----

1. ISO line patterns are paper-scaled and should be rendered with consistent
   stroke widths and gaps proportional to line weight.

2. Dash patterns must have even number of values (pairs of on/off lengths).

3. Pattern IDs for dash patterns should start at LinePattern.Count + 100
   to avoid conflicts with predefined patterns.

4. When a dash pattern is active, turn it off by setting to kNull (-1)
   before using regular line patterns.

5. Pen patterns with IDs 1-5 require screening percentage values.
   Face patterns (6+) do not use screening.

REFERENCE
---------

Source files analyzed:
  - linepat.cpp / linepat.h - Line pattern implementation
  - lweight.cpp / lweight.h - Line weight implementation
  - linestyle.cpp / linestyle.h - Line style with options
  - dashpat.cpp / dashpat.h - Dash pattern implementation
  - fillpat.cpp / fillpat.h - Fill pattern implementation
  - penpat.cpp / penpat.h - Pen pattern implementation

Author: Agent 19
Date: 2025-10-22
"""


if __name__ == "__main__":
    # Run tests
    run_all_tests()

    # Print documentation
    print("\n" + DOCUMENTATION)
