#!/usr/bin/env python3
"""
Agent 22: DWF Extended ASCII Text and Font Opcodes Translation
================================================================

Translates 6 Extended ASCII text and font opcodes from DWF to Python with
full Unicode/UTF-8 and Hebrew text support.

Opcodes Implemented:
-------------------
1. WD_EXAO_SET_FONT (273) - `(Font` - Font definition
2. WD_EXAO_DRAW_TEXT (287) - `(Text` - Text drawing (HEBREW SUPPORT)
3. WD_EXAO_EMBEDDED_FONT (319) - `(Embedded_Font` - Embedded font data
4. WD_EXAO_TRUSTED_FONT_LIST (320) - `(TrustedFontList` - Trusted fonts
5. WD_EXAO_SET_FONT_EXTENSION (362) - `(FontExtension` - Font extensions
6. WD_EXAO_TEXT_HALIGN (372) - `(TextHAlign` - Horizontal alignment

Author: Agent 22
Date: 2025-10-22
Priority: HIGH - Hebrew/Unicode text support
"""

import struct
import io
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import IntEnum, IntFlag


# ==============================================================================
# CONSTANTS AND ENUMERATIONS
# ==============================================================================

class FontFieldBits(IntFlag):
    """Font option bit flags"""
    FONT_NO_FIELDS = 0x0000
    FONT_NAME_BIT = 0x0001
    FONT_CHARSET_BIT = 0x0002
    FONT_PITCH_BIT = 0x0004
    FONT_FAMILY_BIT = 0x0008
    FONT_STYLE_BIT = 0x0010
    FONT_HEIGHT_BIT = 0x0020
    FONT_ROTATION_BIT = 0x0040
    FONT_WIDTH_SCALE_BIT = 0x0080
    FONT_SPACING_BIT = 0x0100
    FONT_OBLIQUE_BIT = 0x0200
    FONT_FLAGS_BIT = 0x0400
    FONT_ALL_FIELDS = 0xFFFF


class FontStyleFlags(IntFlag):
    """Font style bit flags"""
    BOLD = 0x01
    ITALIC = 0x02
    UNDERLINED = 0x04


class FontCharset(IntEnum):
    """Font character set codes (Windows charset values)"""
    ANSI_CHARSET = 0
    DEFAULT_CHARSET = 1
    SYMBOL_CHARSET = 2
    SHIFTJIS_CHARSET = 128
    HANGEUL_CHARSET = 129
    GB2312_CHARSET = 134
    CHINESEBIG5_CHARSET = 136
    GREEK_CHARSET = 161
    TURKISH_CHARSET = 162
    HEBREW_CHARSET = 177  # CRITICAL for Hebrew support
    ARABIC_CHARSET = 178
    BALTIC_CHARSET = 186
    RUSSIAN_CHARSET = 204
    THAI_CHARSET = 222
    EASTEUROPE_CHARSET = 238
    OEM_CHARSET = 255


class EmbeddedFontRequest(IntFlag):
    """Embedded font request type flags"""
    RAW = 0x00000001
    SUBSET = 0x00000002
    COMPRESSED = 0x00000004
    FAIL_IF_VARIATIONS_SIMULATED = 0x00000008
    EUDC = 0x00000010
    VALIDATION_TESTS = 0x00000020
    WEB_OBJECT = 0x00000040
    ENCRYPT_DATA = 0x00000080


class EmbeddedFontPrivilege(IntEnum):
    """Embedded font privilege levels"""
    PREVIEW_PRINT = 0
    EDITABLE = 1
    INSTALLABLE = 2
    NON_EMBEDDING = 3


class EmbeddedFontCharacterSetType(IntEnum):
    """Embedded font character set types"""
    UNICODE = 0
    SYMBOL = 1
    GLYPHIDX = 2


class TextHAlign(IntEnum):
    """Text horizontal alignment"""
    LEFT = 0
    RIGHT = 1
    CENTER = 2


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class LogicalPoint:
    """2D logical point in DWF coordinate space"""
    x: int
    y: int

    def __str__(self):
        return f"({self.x},{self.y})"


@dataclass
class FontData:
    """Font definition data"""
    fields_defined: int = FontFieldBits.FONT_NO_FIELDS
    name: str = ""
    charset: int = FontCharset.DEFAULT_CHARSET
    pitch: int = 0
    family: int = 0
    bold: bool = False
    italic: bool = False
    underlined: bool = False
    height: int = 0
    rotation: int = 0  # in 360/65536ths of a degree
    width_scale: int = 1024  # 1024 = 100%
    spacing: int = 1024  # 1024 = 100%
    oblique: int = 0
    flags: int = 0

    def __str__(self):
        style = []
        if self.bold:
            style.append("Bold")
        if self.italic:
            style.append("Italic")
        if self.underlined:
            style.append("Underlined")
        style_str = "+".join(style) if style else "Regular"
        return f"Font('{self.name}', {self.height}pt, {style_str})"


@dataclass
class TextData:
    """Text drawing data with full Unicode support"""
    position: LogicalPoint
    text: str  # UTF-8 string supporting all Unicode including Hebrew
    bounds: Optional[List[LogicalPoint]] = None
    overscore_positions: Optional[List[int]] = None
    underscore_positions: Optional[List[int]] = None

    def is_hebrew(self) -> bool:
        """Check if text contains Hebrew characters"""
        # Hebrew Unicode range: U+0590 to U+05FF
        return any(0x0590 <= ord(c) <= 0x05FF for c in self.text)

    def is_rtl(self) -> bool:
        """Check if text is right-to-left (Hebrew, Arabic)"""
        # Check for Hebrew (0x0590-0x05FF) or Arabic (0x0600-0x06FF)
        return any((0x0590 <= ord(c) <= 0x05FF) or (0x0600 <= ord(c) <= 0x06FF)
                   for c in self.text)

    def __str__(self):
        direction = " [RTL]" if self.is_rtl() else ""
        hebrew = " [HEBREW]" if self.is_hebrew() else ""
        return f"Text{direction}{hebrew} at {self.position}: '{self.text}'"


@dataclass
class EmbeddedFontData:
    """Embedded font data"""
    request_type: int
    privilege: int
    character_set_type: int
    font_type_face_name: str
    font_logfont_name: str
    data: bytes

    def __str__(self):
        return (f"EmbeddedFont('{self.font_type_face_name}', "
                f"{len(self.data)} bytes)")


@dataclass
class TrustedFontListData:
    """Trusted font list data"""
    fonts: List[str]

    def __str__(self):
        return f"TrustedFontList({len(self.fonts)} fonts: {', '.join(self.fonts)})"


@dataclass
class FontExtensionData:
    """Font extension data"""
    logfont_name: str
    canonical_name: str

    def __str__(self):
        return f"FontExtension(logfont='{self.logfont_name}', canonical='{self.canonical_name}')"


@dataclass
class TextHAlignData:
    """Text horizontal alignment data"""
    alignment: TextHAlign

    def __str__(self):
        align_names = {
            TextHAlign.LEFT: "Left",
            TextHAlign.RIGHT: "Right",
            TextHAlign.CENTER: "Center"
        }
        return f"TextHAlign({align_names.get(self.alignment, 'Unknown')})"


# ==============================================================================
# PARSING UTILITIES
# ==============================================================================

class DWFParseError(Exception):
    """Base exception for DWF parsing errors"""
    pass


class CorruptFileError(DWFParseError):
    """File structure is corrupted"""
    pass


def read_bytes(stream: io.BytesIO, count: int) -> bytes:
    """Read exact number of bytes from stream"""
    data = stream.read(count)
    if len(data) != count:
        raise CorruptFileError(f"Expected {count} bytes, got {len(data)}")
    return data


def read_int32_le(stream: io.BytesIO) -> int:
    """Read little-endian 32-bit signed integer"""
    return struct.unpack('<i', read_bytes(stream, 4))[0]


def read_uint16_le(stream: io.BytesIO) -> int:
    """Read little-endian 16-bit unsigned integer"""
    return struct.unpack('<H', read_bytes(stream, 2))[0]


def read_uint32_le(stream: io.BytesIO) -> int:
    """Read little-endian 32-bit unsigned integer"""
    return struct.unpack('<I', read_bytes(stream, 4))[0]


def read_byte(stream: io.BytesIO) -> int:
    """Read single byte as unsigned integer"""
    data = stream.read(1)
    if len(data) != 1:
        raise CorruptFileError("Unexpected EOF reading byte")
    return data[0]


def skip_whitespace(stream: io.BytesIO) -> None:
    """Skip whitespace characters in ASCII stream"""
    while True:
        pos = stream.tell()
        byte = stream.read(1)
        if not byte or byte not in (b' ', b'\t', b'\n', b'\r'):
            stream.seek(pos)
            break


def read_ascii_token(stream: io.BytesIO, max_length: int = 256) -> str:
    """Read ASCII token until whitespace or parenthesis"""
    token = []
    while len(token) < max_length:
        pos = stream.tell()
        byte = stream.read(1)
        if not byte:
            break
        if byte in (b' ', b'\t', b'\n', b'\r', b'(', b')'):
            stream.seek(pos)  # Put back delimiter
            break
        token.append(byte)
    return b''.join(token).decode('ascii', errors='replace')


def read_quoted_string(stream: io.BytesIO) -> str:
    """
    Read quoted string with full Unicode/UTF-8 support.

    CRITICAL: This function handles Hebrew and other Unicode text properly.
    DWF stores Unicode text as UTF-16LE (2 bytes per character).
    """
    skip_whitespace(stream)

    # Check for opening quote (could be " or ')
    quote = stream.read(1)
    if quote not in (b'"', b"'"):
        raise CorruptFileError(f"Expected quote, got {quote}")

    chars = []
    escaped = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise CorruptFileError("Unexpected EOF in quoted string")

        if escaped:
            # Handle escape sequences
            if byte == b'n':
                chars.append(b'\n')
            elif byte == b't':
                chars.append(b'\t')
            elif byte == b'r':
                chars.append(b'\r')
            elif byte == b'\\':
                chars.append(b'\\')
            elif byte == quote:
                chars.append(quote)
            else:
                chars.append(byte)
            escaped = False
        elif byte == b'\\':
            escaped = True
        elif byte == quote:
            break
        else:
            chars.append(byte)

    # Join bytes and decode as UTF-8 (DWF encodes Unicode as UTF-8 in ASCII mode)
    string_bytes = b''.join(chars)

    try:
        # Try UTF-8 first (most common for international text)
        return string_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # Fallback to Latin-1 if UTF-8 fails
        return string_bytes.decode('latin-1', errors='replace')


def read_binary_string(stream: io.BytesIO, count: int) -> str:
    """
    Read binary Unicode string (UTF-16LE format).

    CRITICAL: DWF stores Unicode text as UTF-16LE in binary mode.
    This is essential for Hebrew and other non-ASCII languages.
    """
    # Read count indicates number of 16-bit characters
    byte_count = count * 2
    data = read_bytes(stream, byte_count)

    try:
        # Decode as UTF-16LE (little-endian)
        return data.decode('utf-16-le')
    except UnicodeDecodeError:
        # Fallback to UTF-8 if UTF-16LE fails
        try:
            return data.decode('utf-8', errors='replace')
        except:
            return data.decode('latin-1', errors='replace')


def read_hex_bytes(stream: io.BytesIO, count: int) -> bytes:
    """Read hex-encoded bytes from ASCII stream"""
    skip_whitespace(stream)
    hex_str = read_bytes(stream, count * 2).decode('ascii')
    return bytes.fromhex(hex_str)


def read_ascii_int32(stream: io.BytesIO) -> int:
    """Read ASCII-encoded 32-bit integer"""
    skip_whitespace(stream)
    token = read_ascii_token(stream)
    return int(token)


def read_ascii_uint16(stream: io.BytesIO) -> int:
    """Read ASCII-encoded 16-bit unsigned integer"""
    skip_whitespace(stream)
    token = read_ascii_token(stream)
    return int(token) & 0xFFFF


def read_logical_point(stream: io.BytesIO, is_ascii: bool = False) -> LogicalPoint:
    """Read logical point in binary or ASCII format"""
    if is_ascii:
        skip_whitespace(stream)
        # ASCII format: x,y (no parens in DWF)
        # Read everything up to whitespace or closing paren
        token = read_ascii_token(stream, max_length=64)
        # Split by comma
        parts = token.split(',')
        if len(parts) != 2:
            raise CorruptFileError(f"Expected 'x,y' format, got '{token}'")
        x = int(parts[0])
        y = int(parts[1])
        return LogicalPoint(x, y)
    else:
        # Binary format: two 32-bit little-endian integers
        x = read_int32_le(stream)
        y = read_int32_le(stream)
        return LogicalPoint(x, y)


def skip_to_closing_paren(stream: io.BytesIO) -> None:
    """Skip to matching closing parenthesis, tracking nesting depth"""
    depth = 1
    while depth > 0:
        byte = stream.read(1)
        if not byte:
            raise CorruptFileError("Unexpected EOF looking for closing paren")
        if byte == b'(':
            depth += 1
        elif byte == b')':
            depth -= 1


# ==============================================================================
# OPCODE HANDLERS
# ==============================================================================

def handle_set_font_ascii(stream: io.BytesIO) -> FontData:
    """
    Handle WD_EXAO_SET_FONT (273) - Extended ASCII format

    Format: (Font [options...])
    Options can include: name, charset, pitch, family, style, height,
    rotation, width_scale, spacing, oblique, flags
    """
    font = FontData()
    font.fields_defined = FontFieldBits.FONT_NO_FIELDS

    # Parse font options until closing paren
    while True:
        skip_whitespace(stream)
        pos = stream.tell()
        byte = stream.read(1)

        if byte == b')':
            break
        elif byte == b'(':
            # Nested option: (OptionName value)
            skip_whitespace(stream)
            option_name = read_ascii_token(stream)

            if option_name == "Name":
                font.name = read_quoted_string(stream)
                font.fields_defined |= FontFieldBits.FONT_NAME_BIT
            elif option_name == "Charset":
                font.charset = read_ascii_int32(stream)
                font.fields_defined |= FontFieldBits.FONT_CHARSET_BIT
            elif option_name == "Pitch":
                font.pitch = read_ascii_int32(stream)
                font.fields_defined |= FontFieldBits.FONT_PITCH_BIT
            elif option_name == "Family":
                font.family = read_ascii_int32(stream)
                font.fields_defined |= FontFieldBits.FONT_FAMILY_BIT
            elif option_name == "Style":
                style = read_ascii_int32(stream)
                font.bold = bool(style & FontStyleFlags.BOLD)
                font.italic = bool(style & FontStyleFlags.ITALIC)
                font.underlined = bool(style & FontStyleFlags.UNDERLINED)
                font.fields_defined |= FontFieldBits.FONT_STYLE_BIT
            elif option_name == "Height":
                font.height = read_ascii_int32(stream)
                font.fields_defined |= FontFieldBits.FONT_HEIGHT_BIT
            elif option_name == "Rotation":
                font.rotation = read_ascii_uint16(stream)
                font.fields_defined |= FontFieldBits.FONT_ROTATION_BIT
            elif option_name == "Width_Scale":
                font.width_scale = read_ascii_uint16(stream)
                font.fields_defined |= FontFieldBits.FONT_WIDTH_SCALE_BIT
            elif option_name == "Spacing":
                font.spacing = read_ascii_uint16(stream)
                font.fields_defined |= FontFieldBits.FONT_SPACING_BIT
            elif option_name == "Oblique":
                font.oblique = read_ascii_uint16(stream)
                font.fields_defined |= FontFieldBits.FONT_OBLIQUE_BIT
            elif option_name == "Flags":
                font.flags = read_ascii_int32(stream)
                font.fields_defined |= FontFieldBits.FONT_FLAGS_BIT

            # Skip to closing paren of option
            skip_to_closing_paren(stream)
        else:
            stream.seek(pos)
            break

    return font


def handle_set_font_binary(stream: io.BytesIO) -> FontData:
    """
    Handle WD_EXAO_SET_FONT (273) - Binary format

    Format: 0x06 (CTRL-F) + fields_defined + field_data
    """
    font = FontData()

    # Read fields_defined bitmask
    font.fields_defined = read_uint16_le(stream)

    # Read fields in order based on bitmask
    if font.fields_defined & FontFieldBits.FONT_NAME_BIT:
        length = read_int32_le(stream)
        font.name = read_binary_string(stream, length)

    if font.fields_defined & FontFieldBits.FONT_CHARSET_BIT:
        font.charset = read_byte(stream)

    if font.fields_defined & FontFieldBits.FONT_PITCH_BIT:
        font.pitch = read_byte(stream)

    if font.fields_defined & FontFieldBits.FONT_FAMILY_BIT:
        font.family = read_byte(stream)

    if font.fields_defined & FontFieldBits.FONT_STYLE_BIT:
        style = read_byte(stream)
        font.bold = bool(style & FontStyleFlags.BOLD)
        font.italic = bool(style & FontStyleFlags.ITALIC)
        font.underlined = bool(style & FontStyleFlags.UNDERLINED)

    if font.fields_defined & FontFieldBits.FONT_HEIGHT_BIT:
        font.height = read_int32_le(stream)

    if font.fields_defined & FontFieldBits.FONT_ROTATION_BIT:
        font.rotation = read_uint16_le(stream)

    if font.fields_defined & FontFieldBits.FONT_WIDTH_SCALE_BIT:
        font.width_scale = read_uint16_le(stream)

    if font.fields_defined & FontFieldBits.FONT_SPACING_BIT:
        font.spacing = read_uint16_le(stream)

    if font.fields_defined & FontFieldBits.FONT_OBLIQUE_BIT:
        font.oblique = read_uint16_le(stream)

    if font.fields_defined & FontFieldBits.FONT_FLAGS_BIT:
        font.flags = read_int32_le(stream)

    return font


def handle_draw_text_ascii(stream: io.BytesIO) -> TextData:
    """
    Handle WD_EXAO_DRAW_TEXT (287) - Extended ASCII format

    CRITICAL: Full Unicode/Hebrew support

    Format: (Text position "string" [options...])
    """
    skip_whitespace(stream)

    # Read position
    position = read_logical_point(stream, is_ascii=True)

    # Read text string with full Unicode support
    text = read_quoted_string(stream)

    # Parse optional fields
    bounds = None
    overscore_pos = None
    underscore_pos = None

    while True:
        skip_whitespace(stream)
        pos = stream.tell()
        byte = stream.read(1)

        if byte == b')':
            break
        elif byte == b'(':
            stream.seek(pos)
            option_name = read_ascii_token(stream)
            stream.read(1)  # skip opening paren

            if option_name == "Bounds":
                # Read 4 corner points
                bounds = [read_logical_point(stream, is_ascii=True) for _ in range(4)]
            elif option_name == "Overscore":
                count = read_ascii_int32(stream)
                overscore_pos = [read_ascii_int32(stream) for _ in range(count)]
            elif option_name == "Underscore":
                count = read_ascii_int32(stream)
                underscore_pos = [read_ascii_int32(stream) for _ in range(count)]

            skip_to_closing_paren(stream)
        else:
            stream.seek(pos)
            break

    return TextData(
        position=position,
        text=text,
        bounds=bounds,
        overscore_positions=overscore_pos,
        underscore_positions=underscore_pos
    )


def handle_draw_text_binary(stream: io.BytesIO, opcode: int) -> TextData:
    """
    Handle WD_EXAO_DRAW_TEXT (287) - Binary format

    CRITICAL: Full Unicode/Hebrew support in binary format

    Format:
    - 'x' (0x78): position + string
    - 0x18 (CTRL-X): position + string + overscore + underscore + bounds
    """
    # Read position
    position = read_logical_point(stream, is_ascii=False)

    # Read string length and data
    string_length = read_int32_le(stream)
    text = read_binary_string(stream, string_length)

    bounds = None
    overscore_pos = None
    underscore_pos = None

    # If opcode is 0x18, read additional options
    if opcode == 0x18:
        # Read overscore
        overscore_count = read_uint16_le(stream)
        if overscore_count > 0:
            overscore_pos = [read_uint16_le(stream) for _ in range(overscore_count)]

        # Read underscore
        underscore_count = read_uint16_le(stream)
        if underscore_count > 0:
            underscore_pos = [read_uint16_le(stream) for _ in range(underscore_count)]

        # Read bounds (4 points)
        has_bounds = read_byte(stream)
        if has_bounds:
            bounds = [read_logical_point(stream, is_ascii=False) for _ in range(4)]

    return TextData(
        position=position,
        text=text,
        bounds=bounds,
        overscore_positions=overscore_pos,
        underscore_positions=underscore_pos
    )


def handle_embedded_font_ascii(stream: io.BytesIO) -> EmbeddedFontData:
    """
    Handle WD_EXAO_EMBEDDED_FONT (319) - Extended ASCII format

    Format: (Embedded_Font request privilege charset typeface_len typeface
             logfont_len logfont (data_size hex_data))
    """
    skip_whitespace(stream)

    request_type = read_ascii_int32(stream)
    privilege = read_ascii_uint16(stream)
    character_set_type = read_ascii_uint16(stream)

    # Font typeface name
    typeface_len = read_ascii_int32(stream)
    skip_whitespace(stream)
    typeface = read_bytes(stream, typeface_len).decode('utf-8', errors='replace')

    # Logfont name
    logfont_len = read_ascii_int32(stream)
    skip_whitespace(stream)
    logfont = read_bytes(stream, logfont_len).decode('utf-8', errors='replace')

    # Font data
    skip_whitespace(stream)
    stream.read(1)  # opening paren
    data_size = read_ascii_int32(stream)
    data = read_hex_bytes(stream, data_size)
    stream.read(1)  # closing paren

    # Skip to opcode closing paren
    stream.read(1)  # final closing paren

    return EmbeddedFontData(
        request_type=request_type,
        privilege=privilege,
        character_set_type=character_set_type,
        font_type_face_name=typeface,
        font_logfont_name=logfont,
        data=data
    )


def handle_embedded_font_binary(stream: io.BytesIO) -> EmbeddedFontData:
    """
    Handle WD_EXAO_EMBEDDED_FONT (319) - Extended Binary format

    Format: { + size + opcode + data + }
    """
    request_type = read_int32_le(stream)
    privilege = read_byte(stream)
    character_set_type = read_byte(stream)

    # Font typeface name
    typeface_len = read_int32_le(stream)
    typeface = read_bytes(stream, typeface_len).decode('utf-8', errors='replace')

    # Logfont name
    logfont_len = read_int32_le(stream)
    logfont = read_bytes(stream, logfont_len).decode('utf-8', errors='replace')

    # Font data
    data_size = read_int32_le(stream)
    data = read_bytes(stream, data_size)

    # Read closing brace
    close = read_byte(stream)
    if close != ord('}'):
        raise CorruptFileError(f"Expected closing brace, got {close}")

    return EmbeddedFontData(
        request_type=request_type,
        privilege=privilege,
        character_set_type=character_set_type,
        font_type_face_name=typeface,
        font_logfont_name=logfont,
        data=data
    )


def handle_trusted_font_list(stream: io.BytesIO) -> TrustedFontListData:
    """
    Handle WD_EXAO_TRUSTED_FONT_LIST (320) - Extended ASCII only

    Format: (TrustedFontList "font1" "font2" ... "fontN")
    """
    fonts = []

    while True:
        skip_whitespace(stream)
        pos = stream.tell()
        byte = stream.read(1)

        if byte == b')':
            break
        elif byte in (b'"', b"'"):
            stream.seek(pos)
            font_name = read_quoted_string(stream)
            fonts.append(font_name)
        else:
            stream.seek(pos)
            break

    return TrustedFontListData(fonts=fonts)


def handle_font_extension(stream: io.BytesIO) -> FontExtensionData:
    """
    Handle WD_EXAO_SET_FONT_EXTENSION (362) - Extended ASCII only

    Format: (FontExtension "logfont_name" "canonical_name")
    """
    skip_whitespace(stream)
    logfont_name = read_quoted_string(stream)

    skip_whitespace(stream)
    canonical_name = read_quoted_string(stream)

    # Skip to closing paren
    skip_to_closing_paren(stream)

    return FontExtensionData(
        logfont_name=logfont_name,
        canonical_name=canonical_name
    )


def handle_text_halign_ascii(stream: io.BytesIO) -> TextHAlignData:
    """
    Handle WD_EXAO_TEXT_HALIGN (372) - Extended ASCII format

    Format: (TextHAlign Left|Right|Center)
    """
    skip_whitespace(stream)
    align_str = read_ascii_token(stream)

    # Map string to enum
    align_map = {
        "Left": TextHAlign.LEFT,
        "Right": TextHAlign.RIGHT,
        "Center": TextHAlign.CENTER
    }

    alignment = align_map.get(align_str, TextHAlign.LEFT)

    # Skip to closing paren
    skip_to_closing_paren(stream)

    return TextHAlignData(alignment=alignment)


def handle_text_halign_binary(stream: io.BytesIO) -> TextHAlignData:
    """
    Handle WD_EXAO_TEXT_HALIGN (372) - Extended Binary format

    Format: { + size + opcode + alignment_byte + }
    """
    alignment_byte = read_byte(stream)

    # Validate alignment value
    if alignment_byte > 2:
        alignment = TextHAlign.LEFT  # Default to left
    else:
        alignment = TextHAlign(alignment_byte)

    # Read closing brace
    close = read_byte(stream)
    if close != ord('}'):
        raise CorruptFileError(f"Expected closing brace, got {close}")

    return TextHAlignData(alignment=alignment)


# ==============================================================================
# MAIN OPCODE DISPATCHER
# ==============================================================================

class TextFontOpcodeHandler:
    """
    Handler for text and font opcodes with full Hebrew/Unicode support
    """

    def __init__(self):
        self.font_state = FontData()
        self.text_halign = TextHAlignData(alignment=TextHAlign.LEFT)
        self.font_extension = None
        self.embedded_fonts = []
        self.trusted_fonts = []

    def handle_opcode(self, opcode_name: str, stream: io.BytesIO,
                     is_binary: bool = False, opcode_byte: Optional[int] = None) -> Any:
        """
        Dispatch opcode to appropriate handler

        Args:
            opcode_name: Name of opcode (e.g., "Font", "Text")
            stream: Input byte stream
            is_binary: True if binary format, False if ASCII
            opcode_byte: Opcode byte value for binary format

        Returns:
            Parsed opcode data
        """
        if opcode_name == "Font":
            if is_binary:
                result = handle_set_font_binary(stream)
            else:
                result = handle_set_font_ascii(stream)
            self.font_state = result
            return result

        elif opcode_name == "Text":
            if is_binary:
                result = handle_draw_text_binary(stream, opcode_byte)
            else:
                result = handle_draw_text_ascii(stream)
            return result

        elif opcode_name == "Embedded_Font":
            if is_binary:
                result = handle_embedded_font_binary(stream)
            else:
                result = handle_embedded_font_ascii(stream)
            self.embedded_fonts.append(result)
            return result

        elif opcode_name == "TrustedFontList":
            result = handle_trusted_font_list(stream)
            self.trusted_fonts = result.fonts
            return result

        elif opcode_name == "FontExtension":
            result = handle_font_extension(stream)
            self.font_extension = result
            return result

        elif opcode_name == "TextHAlign":
            if is_binary:
                result = handle_text_halign_binary(stream)
            else:
                result = handle_text_halign_ascii(stream)
            self.text_halign = result
            return result

        else:
            raise DWFParseError(f"Unknown opcode: {opcode_name}")


# ==============================================================================
# TESTS
# ==============================================================================

def test_font_ascii():
    """Test Font opcode in ASCII format"""
    print("\n=== Test: Font ASCII ===")

    # Test data: Arial, 12pt, Bold+Italic, Hebrew charset
    # Note: Font opcode starts after opening paren, we parse until closing paren
    data = b'(Name "Arial") (Charset 177) (Height 12) (Style 3))'
    stream = io.BytesIO(data)

    font = handle_set_font_ascii(stream)

    assert font.name == "Arial", f"Expected 'Arial', got '{font.name}'"
    assert font.charset == FontCharset.HEBREW_CHARSET, f"Expected {FontCharset.HEBREW_CHARSET}, got {font.charset}"
    assert font.height == 12, f"Expected 12, got {font.height}"
    assert font.bold == True, f"Expected bold=True, got {font.bold}"
    assert font.italic == True, f"Expected italic=True, got {font.italic}"
    assert font.underlined == False, f"Expected underlined=False, got {font.underlined}"

    print(f"PASS: {font}")


def test_font_binary():
    """Test Font opcode in binary format"""
    print("\n=== Test: Font Binary ===")

    # Build binary font data
    stream = io.BytesIO()

    # Fields defined: NAME + CHARSET + HEIGHT + STYLE
    fields = (FontFieldBits.FONT_NAME_BIT | FontFieldBits.FONT_CHARSET_BIT |
              FontFieldBits.FONT_HEIGHT_BIT | FontFieldBits.FONT_STYLE_BIT)
    stream.write(struct.pack('<H', fields))

    # Name: "David" (Hebrew font) - 5 characters in UTF-16LE
    name = "David"
    stream.write(struct.pack('<i', len(name)))
    stream.write(name.encode('utf-16-le'))

    # Charset: Hebrew
    stream.write(struct.pack('B', FontCharset.HEBREW_CHARSET))

    # Style: Bold
    stream.write(struct.pack('B', FontStyleFlags.BOLD))

    # Height: 14
    stream.write(struct.pack('<i', 14))

    stream.seek(0)
    font = handle_set_font_binary(stream)

    assert font.name == "David"
    assert font.charset == FontCharset.HEBREW_CHARSET
    assert font.height == 14
    assert font.bold == True

    print(f"PASS: {font}")


def test_text_ascii_english():
    """Test Text opcode with English text"""
    print("\n=== Test: Text ASCII (English) ===")

    data = b'100,200 "Hello World")'
    stream = io.BytesIO(data)

    text = handle_draw_text_ascii(stream)

    assert text.position.x == 100
    assert text.position.y == 200
    assert text.text == "Hello World"
    assert text.is_hebrew() == False
    assert text.is_rtl() == False

    print(f"PASS: {text}")


def test_text_ascii_hebrew():
    """Test Text opcode with Hebrew text - CRITICAL TEST"""
    print("\n=== Test: Text ASCII (Hebrew) ===")

    # Hebrew text: "שלום עולם" (Shalom Olam = Hello World)
    hebrew_text = "שלום עולם"
    data = f'500,600 "{hebrew_text}")'.encode('utf-8')
    stream = io.BytesIO(data)

    text = handle_draw_text_ascii(stream)

    assert text.position.x == 500
    assert text.position.y == 600
    assert text.text == hebrew_text
    assert text.is_hebrew() == True
    assert text.is_rtl() == True

    print(f"PASS: {text}")
    print(f"  Hebrew text verified: {text.text}")
    print(f"  RTL detected: {text.is_rtl()}")


def test_text_binary_hebrew():
    """Test Text opcode in binary format with Hebrew text"""
    print("\n=== Test: Text Binary (Hebrew) ===")

    stream = io.BytesIO()

    # Position
    stream.write(struct.pack('<ii', 300, 400))

    # Hebrew string: "דוד" (David)
    hebrew_text = "דוד"
    stream.write(struct.pack('<i', len(hebrew_text)))
    stream.write(hebrew_text.encode('utf-16-le'))

    stream.seek(0)
    text = handle_draw_text_binary(stream, 0x78)  # Simple 'x' opcode

    assert text.position.x == 300
    assert text.position.y == 400
    assert text.text == hebrew_text
    assert text.is_hebrew() == True

    print(f"PASS: {text}")
    print(f"  Hebrew name: {text.text}")


def test_text_mixed_languages():
    """Test Text opcode with mixed English and Hebrew"""
    print("\n=== Test: Text Mixed Languages ===")

    # Mixed text: "Version גרסה 2.0"
    mixed_text = "Version גרסה 2.0"
    data = f'100,100 "{mixed_text}")'.encode('utf-8')
    stream = io.BytesIO(data)

    text = handle_draw_text_ascii(stream)

    assert text.text == mixed_text
    assert text.is_hebrew() == True  # Contains Hebrew
    assert text.is_rtl() == True  # Contains RTL characters

    print(f"PASS: {text}")
    print(f"  Mixed text: {text.text}")


def test_embedded_font_ascii():
    """Test Embedded Font opcode in ASCII format"""
    print("\n=== Test: Embedded Font ASCII ===")

    # Sample font data (simplified)
    font_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'
    hex_data = font_data.hex().encode('ascii')

    data = (b'123 1 0 5 Arial 5 Arial (' +
            str(len(font_data)).encode('ascii') + b' ' +
            hex_data + b'))')
    stream = io.BytesIO(data)

    font = handle_embedded_font_ascii(stream)

    assert font.request_type == 123
    assert font.privilege == 1
    assert font.character_set_type == 0
    assert font.font_type_face_name == "Arial"
    assert len(font.data) == len(font_data)

    print(f"PASS: {font}")


def test_trusted_font_list():
    """Test Trusted Font List opcode"""
    print("\n=== Test: Trusted Font List ===")

    data = b'"Arial" "Times New Roman" "David" "Miriam")'
    stream = io.BytesIO(data)

    fonts = handle_trusted_font_list(stream)

    assert len(fonts.fonts) == 4
    assert "Arial" in fonts.fonts
    assert "David" in fonts.fonts  # Hebrew font
    assert "Miriam" in fonts.fonts  # Hebrew font

    print(f"PASS: {fonts}")


def test_font_extension():
    """Test Font Extension opcode"""
    print("\n=== Test: Font Extension ===")

    data = b'"Arial" "Arial-Regular")'
    stream = io.BytesIO(data)

    ext = handle_font_extension(stream)

    assert ext.logfont_name == "Arial"
    assert ext.canonical_name == "Arial-Regular"

    print(f"PASS: {ext}")


def test_text_halign_ascii():
    """Test Text HAlign opcode in ASCII format"""
    print("\n=== Test: Text HAlign ASCII ===")

    for align_str, align_enum in [("Left", TextHAlign.LEFT),
                                   ("Right", TextHAlign.RIGHT),
                                   ("Center", TextHAlign.CENTER)]:
        data = f'{align_str})'.encode('ascii')
        stream = io.BytesIO(data)

        halign = handle_text_halign_ascii(stream)
        assert halign.alignment == align_enum
        print(f"  PASS: {halign}")

    print("PASS: All alignments tested")


def test_text_halign_binary():
    """Test Text HAlign opcode in binary format"""
    print("\n=== Test: Text HAlign Binary ===")

    for align_val in [0, 1, 2]:
        stream = io.BytesIO(struct.pack('BB', align_val, ord('}')))
        halign = handle_text_halign_binary(stream)
        assert halign.alignment == TextHAlign(align_val)
        print(f"  PASS: {halign}")

    print("PASS: All alignments tested")


def test_hebrew_character_ranges():
    """Test Hebrew character detection across full Unicode range"""
    print("\n=== Test: Hebrew Character Range Detection ===")

    # Test individual Hebrew characters
    hebrew_chars = [
        "\u05D0",  # Aleph
        "\u05D1",  # Bet
        "\u05E9",  # Shin
        "\u05DC",  # Lamed
        "\u05DD",  # Final Mem
    ]

    for char in hebrew_chars:
        data = f'0,0 "{char}")'.encode('utf-8')
        stream = io.BytesIO(data)
        text = handle_draw_text_ascii(stream)
        assert text.is_hebrew() == True
        print(f"  PASS: Hebrew char {char} (U+{ord(char):04X}) detected")

    print("PASS: Hebrew character range validated")


def test_integration_hebrew_document():
    """Integration test: Complete Hebrew document simulation"""
    print("\n=== Integration Test: Hebrew Document ===")

    handler = TextFontOpcodeHandler()

    # 1. Set Hebrew font
    font_data = b'(Name "David")(Charset 177)(Height 14)(Style 1))'
    stream = io.BytesIO(font_data)
    font = handler.handle_opcode("Font", stream)
    print(f"  Font set: {font}")

    # 2. Set right alignment for RTL text
    align_data = b'Right)'
    stream = io.BytesIO(align_data)
    align = handler.handle_opcode("TextHAlign", stream)
    print(f"  Alignment: {align}")

    # 3. Draw Hebrew title
    title = "כותרת המסמך"  # Document Title
    title_data = f'100,500 "{title}")'.encode('utf-8')
    stream = io.BytesIO(title_data)
    text1 = handler.handle_opcode("Text", stream)
    print(f"  Title: {text1}")

    # 4. Draw Hebrew paragraph
    paragraph = "זהו מסמך בעברית עם תמיכה מלאה ב-Unicode"
    # "This is a document in Hebrew with full Unicode support"
    para_data = f'100,450 "{paragraph}")'.encode('utf-8')
    stream = io.BytesIO(para_data)
    text2 = handler.handle_opcode("Text", stream)
    print(f"  Paragraph: {text2}")

    # Verify state
    assert handler.font_state.name == "David"
    assert handler.font_state.charset == FontCharset.HEBREW_CHARSET
    assert handler.text_halign.alignment == TextHAlign.RIGHT

    print("PASS: Hebrew document integration test complete")


def run_all_tests():
    """Run all test cases"""
    print("=" * 70)
    print("Agent 22: Text and Font Opcodes - Comprehensive Test Suite")
    print("=" * 70)

    tests = [
        test_font_ascii,
        test_font_binary,
        test_text_ascii_english,
        test_text_ascii_hebrew,
        test_text_binary_hebrew,
        test_text_mixed_languages,
        test_embedded_font_ascii,
        test_trusted_font_list,
        test_font_extension,
        test_text_halign_ascii,
        test_text_halign_binary,
        test_hebrew_character_ranges,
        test_integration_hebrew_document,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


# ==============================================================================
# DOCUMENTATION
# ==============================================================================

def print_documentation():
    """Print comprehensive documentation"""
    doc = """
Agent 22: DWF Text and Font Opcodes Implementation
===================================================

OPCODE SUMMARY
--------------

1. WD_EXAO_SET_FONT (273) - `(Font`
   - Sets current font with extensive options
   - Fields: name, charset, pitch, family, style, height, rotation,
             width_scale, spacing, oblique, flags
   - Supports Hebrew charset (177) and other international charsets
   - Binary opcode: 0x06 (CTRL-F)

2. WD_EXAO_DRAW_TEXT (287) - `(Text`
   - Draws text with full Unicode/Hebrew support
   - Fields: position, string, optional bounds/overscore/underscore
   - CRITICAL: Properly handles UTF-8 in ASCII mode, UTF-16LE in binary mode
   - Binary opcodes: 0x78 ('x') for simple, 0x18 (CTRL-X) for extended
   - RTL detection for Hebrew and Arabic text

3. WD_EXAO_EMBEDDED_FONT (319) - `(Embedded_Font`
   - Embeds complete font data in DWF file
   - Fields: request_type, privilege, charset_type, typeface, logfont, data
   - Both ASCII (hex-encoded) and binary formats supported

4. WD_EXAO_TRUSTED_FONT_LIST (320) - `(TrustedFontList`
   - List of trusted font names for document
   - ASCII format only: space-separated quoted strings
   - Important for Hebrew fonts: "David", "Miriam", "Arial Hebrew", etc.

5. WD_EXAO_SET_FONT_EXTENSION (362) - `(FontExtension`
   - Maps logical font name to canonical name
   - ASCII format only
   - Fields: logfont_name, canonical_name

6. WD_EXAO_TEXT_HALIGN (372) - `(TextHAlign`
   - Sets horizontal text alignment
   - Values: Left (0), Right (1), Center (2)
   - CRITICAL: Right alignment needed for Hebrew RTL text
   - Both ASCII (string) and binary (byte) formats

HEBREW/UNICODE SUPPORT
----------------------

Character Encoding:
- ASCII Mode: UTF-8 encoding for international text
- Binary Mode: UTF-16LE encoding (2 bytes per character)
- Hebrew Unicode range: U+0590 to U+05FF
- Arabic Unicode range: U+0600 to U+06FF

Hebrew Character Set:
- Windows charset code: 177 (HEBREW_CHARSET)
- Common Hebrew fonts: "David", "Miriam", "Arial Hebrew", "Times New Roman Hebrew"

RTL Text Detection:
- Automatically detects Hebrew and Arabic characters
- TextData.is_rtl() method checks for RTL characters
- TextData.is_hebrew() method specifically checks Hebrew range

Text Rendering Considerations:
- Hebrew text flows right-to-left
- Use TextHAlign.RIGHT for Hebrew paragraphs
- Mixed text (English + Hebrew) requires bidirectional algorithm
- Font must support Hebrew charset (177)

USAGE EXAMPLES
--------------

Example 1: English Text with Arial
```python
handler = TextFontOpcodeHandler()

# Set font
font_stream = io.BytesIO(b'(Name "Arial")(Height 12))')
font = handler.handle_opcode("Font", font_stream)

# Draw text
text_stream = io.BytesIO(b'100,200 "Hello World")')
text = handler.handle_opcode("Text", text_stream)
```

Example 2: Hebrew Text with Right Alignment
```python
handler = TextFontOpcodeHandler()

# Set Hebrew font
font_data = '(Name "David")(Charset 177)(Height 14))'.encode('utf-8')
font_stream = io.BytesIO(font_data)
font = handler.handle_opcode("Font", font_stream)

# Set right alignment
align_stream = io.BytesIO(b'Right)')
align = handler.handle_opcode("TextHAlign", align_stream)

# Draw Hebrew text
hebrew_text = "שלום עולם"  # Hello World
text_data = f'500,600 "{hebrew_text}")'.encode('utf-8')
text_stream = io.BytesIO(text_data)
text = handler.handle_opcode("Text", text_stream)

print(f"Drew Hebrew text: {text.text}")
print(f"Is RTL: {text.is_rtl()}")
```

Example 3: Embedded Hebrew Font
```python
# Load Hebrew font data from file
with open('david.ttf', 'rb') as f:
    font_data = f.read()

hex_data = font_data.hex().encode('ascii')
embedded_data = (
    f'127 1 0 5 David 5 David ({len(font_data)} {hex_data.decode()}))'.encode('ascii')
)
stream = io.BytesIO(embedded_data)
embedded = handler.handle_opcode("Embedded_Font", stream)
```

TESTING
-------

The implementation includes 13 comprehensive tests:
1. Font ASCII format
2. Font binary format
3. Text ASCII with English
4. Text ASCII with Hebrew (CRITICAL)
5. Text binary with Hebrew
6. Mixed English/Hebrew text
7. Embedded font ASCII
8. Trusted font list
9. Font extension
10. Text HAlign ASCII
11. Text HAlign binary
12. Hebrew character range detection
13. Integration test: Complete Hebrew document

Run tests with: run_all_tests()

TECHNICAL NOTES
---------------

Binary Encoding:
- All integers are little-endian
- int32: 4 bytes, signed
- uint16: 2 bytes, unsigned
- uint32: 4 bytes, unsigned
- byte: 1 byte, unsigned

String Encoding:
- ASCII mode strings: UTF-8 with quote delimiters
- Binary mode strings: Length prefix (int32) + UTF-16LE data
- Hebrew properly encoded in both modes

Font Style Flags:
- Bold: 0x01
- Italic: 0x02
- Underlined: 0x04
- Can be combined (e.g., Bold+Italic = 0x03)

Font Rotation:
- Value in 360/65536ths of a degree
- 0 = 0 degrees (horizontal)
- 16384 = 90 degrees
- 32768 = 180 degrees
- 49152 = 270 degrees

Width Scale / Spacing:
- Value of 1024 = 100% (normal)
- Value of 2048 = 200% (double)
- Value of 512 = 50% (half)
- Range: 1 to 65535

REFERENCES
----------

Source Files:
- font.cpp - Font opcode implementation
- text.cpp - Text drawing implementation
- embedded_font.cpp - Embedded font handling
- trusted_font_list.cpp - Trusted font list
- font_extension.cpp - Font extension mapping
- text_halign.cpp - Text alignment

Standards:
- Unicode 14.0+ for character ranges
- UTF-8 (RFC 3629) for ASCII mode encoding
- UTF-16LE for binary mode encoding
- Windows Font Charsets (GDI)

CRITICAL SUCCESS CRITERIA
--------------------------

✓ All 6 opcodes implemented (ASCII and binary where applicable)
✓ Full Unicode/UTF-8 support throughout
✓ Hebrew character detection and RTL identification
✓ Proper string encoding in both ASCII and binary modes
✓ 13+ comprehensive test cases including Hebrew text
✓ Integration test demonstrating Hebrew document workflow
✓ Complete documentation with examples

END OF DOCUMENTATION
"""
    print(doc)


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print_documentation()
    print("\nRunning test suite...\n")
    success = run_all_tests()

    if success:
        print("\n" + "=" * 70)
        print("SUCCESS: Agent 22 implementation complete and verified")
        print("All Hebrew/Unicode text support operational")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("FAILURE: Some tests failed - review output above")
        print("=" * 70)
        exit(1)
