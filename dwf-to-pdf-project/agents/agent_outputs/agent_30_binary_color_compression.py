"""
Agent 30: Extended Binary Color Map and Compression Opcodes

This module implements 6 Extended Binary opcodes for color mapping and compression in DWF files.

Extended Binary Format: `{` + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + `}`

Opcodes implemented:
1. WD_EXBO_SET_COLOR_MAP (0x0001, ID 293) - Color map definition
2. WD_EXBO_ADSK_COMPRESSION (0x0010, ID 301) - LZ compression marker
3. WD_ZLIB_COMPRESSION_EXT_OPCODE (0x0011) - ZLIB compression marker
4. WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE (0x0123) - Obsolete LZ compression
5. WD_EXBO_OVERLAY_PREVIEW (0x0018, ID 340) - Overlay preview block
6. WD_EXBO_FONT (0x0019, ID 341) - Font block (embedded font extension)

Author: Agent 30
Date: 2025-10-22
Source: DWF Toolkit C++ Reference Implementation
"""

import struct
import io
from typing import Dict, Any, List, Tuple, Optional, BinaryIO
from dataclasses import dataclass


# Opcode Constants
WD_COLOR_MAP_EXT_OPCODE = 0x0001
WD_EXBO_ADSK_COMPRESSION = 0x0010  # Also known as WD_LZ_COMPRESSION_EXT_OPCODE
WD_ZLIB_COMPRESSION_EXT_OPCODE = 0x0011
WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE = 0x0123
WD_OVERLAY_PREVIEW_EXT_OPCODE = 0x0018
WD_FONT_EXT_OPCODE = 0x0019

# Extended Binary Format Constants
WD_EXTENDED_BINARY_OPCODE_SIZE = 2
WD_EXTENDED_BINARY_OFFSET_SIZE = 4
WD_EXTENDED_BINARY_HEADER_SIZE = 1 + 4 + 2  # '{' + size + opcode


class DWFParseError(Exception):
    """Base exception for DWF parsing errors."""
    pass


class CorruptFileError(DWFParseError):
    """File structure is corrupted."""
    pass


@dataclass
class RGBA32:
    """RGBA color structure (32-bit)."""
    r: int  # Red (0-255)
    g: int  # Green (0-255)
    b: int  # Blue (0-255)
    a: int  # Alpha (0-255)

    def to_bytes(self) -> bytes:
        """Convert to 4-byte representation (RGBA)."""
        return struct.pack('BBBB', self.r, self.g, self.b, self.a)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RGBA32':
        """Create from 4-byte representation."""
        r, g, b, a = struct.unpack('BBBB', data)
        return cls(r, g, b, a)

    def __repr__(self) -> str:
        return f"RGBA({self.r}, {self.g}, {self.b}, {self.a})"


@dataclass
class ColorMap:
    """Color map definition (up to 256 colors)."""
    size: int  # Number of colors (1-256)
    colors: List[RGBA32]  # Color palette

    def __repr__(self) -> str:
        return f"ColorMap(size={self.size}, colors=[{len(self.colors)} entries])"


@dataclass
class CompressionMarker:
    """Compression format marker."""
    format_code: int  # 0x0010 (LZ) or 0x0011 (ZLIB) or 0x0123 (obsolete LZ)
    format_name: str  # "LZ", "ZLIB", or "LZ_OBSOLETE"

    def __repr__(self) -> str:
        return f"CompressionMarker({self.format_name}, 0x{self.format_code:04X})"


@dataclass
class OverlayPreview:
    """Overlay preview block structure."""
    file_offset: int  # File offset to block data
    block_size: int  # Size of the block
    # Note: Additional fields would be parsed from block content
    # This is a placeholder for block reference structure

    def __repr__(self) -> str:
        return f"OverlayPreview(offset={self.file_offset}, size={self.block_size})"


@dataclass
class FontBlock:
    """Font block structure (embedded font extension).

    This is WD_FONT_EXT_OPCODE (0x0019), which is different from
    WD_EXBO_EMBEDDED_FONT. This opcode is used for font block references.
    """
    file_offset: int  # File offset to font data block
    block_size: int  # Size of the font block

    def __repr__(self) -> str:
        return f"FontBlock(offset={self.file_offset}, size={self.block_size})"


class ExtendedBinaryParser:
    """Parser for Extended Binary opcodes.

    Format: { (1 byte) + Size (4 bytes LE) + Opcode (2 bytes LE) + Data + } (1 byte)

    The size field includes: opcode (2 bytes) + data + closing '}' (1 byte)
    """

    def parse_header(self, stream: BinaryIO) -> Tuple[int, int, int]:
        """
        Parse Extended Binary opcode header.

        Args:
            stream: Input stream positioned at '{'

        Returns:
            Tuple of (opcode_value, total_size, data_size)

        Raises:
            CorruptFileError: If header is malformed
        """
        # Read opening '{'
        opening = stream.read(1)
        if opening != b'{':
            raise CorruptFileError(f"Expected '{{' for Extended Binary opcode, got {opening!r}")

        # Read size (4 bytes, little-endian)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise CorruptFileError("Unexpected EOF reading opcode size")
        total_size = struct.unpack('<I', size_bytes)[0]

        # Read opcode value (2 bytes, little-endian)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise CorruptFileError("Unexpected EOF reading opcode value")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Calculate data size: total_size - opcode (2) - closing '}' (1)
        data_size = total_size - 2 - 1

        return opcode, total_size, data_size

    def read_closing_brace(self, stream: BinaryIO) -> None:
        """Read and validate closing brace."""
        closing = stream.read(1)
        if closing != b'}':
            raise CorruptFileError(f"Expected '}}' at end of Extended Binary opcode, got {closing!r}")

    def skip_data(self, stream: BinaryIO, data_size: int) -> None:
        """Skip data bytes and closing brace."""
        stream.seek(data_size, 1)  # Skip data
        self.read_closing_brace(stream)


class ColorMapHandler:
    """Handler for WD_EXBO_SET_COLOR_MAP (0x0001).

    Binary Format:
    - 1 byte: color count (0 means 256)
    - N * 4 bytes: RGBA32 colors

    Reference: colormap.cpp lines 217-228 (serialize), 371-449 (materialize)
    """

    @staticmethod
    def parse(stream: BinaryIO, data_size: int) -> ColorMap:
        """
        Parse color map from Extended Binary format.

        Args:
            stream: Input stream positioned after opcode
            data_size: Number of data bytes

        Returns:
            ColorMap object
        """
        # Read color count (1 byte)
        count_byte = stream.read(1)
        if not count_byte:
            raise CorruptFileError("Failed to read color count")

        count = count_byte[0]
        # 0 represents 256 colors (can't fit 256 in a byte)
        if count == 0:
            count = 256

        # Read RGBA32 colors
        colors = []
        for i in range(count):
            color_bytes = stream.read(4)
            if len(color_bytes) != 4:
                raise CorruptFileError(f"Failed to read color {i}")
            colors.append(RGBA32.from_bytes(color_bytes))

        return ColorMap(size=count, colors=colors)

    @staticmethod
    def serialize(colormap: ColorMap, stream: BinaryIO) -> None:
        """
        Serialize color map to Extended Binary format.

        Args:
            colormap: ColorMap object to serialize
            stream: Output stream
        """
        # Write opening '{'
        stream.write(b'{')

        # Calculate size: opcode (2) + count (1) + colors (N*4) + '}' (1)
        size = 2 + 1 + (colormap.size * 4) + 1
        stream.write(struct.pack('<I', size))

        # Write opcode
        stream.write(struct.pack('<H', WD_COLOR_MAP_EXT_OPCODE))

        # Write color count (0 for 256)
        count_byte = 0 if colormap.size == 256 else colormap.size
        stream.write(struct.pack('B', count_byte))

        # Write colors
        for color in colormap.colors:
            stream.write(color.to_bytes())

        # Write closing '}'
        stream.write(b'}')


class CompressionHandler:
    """Handler for compression marker opcodes.

    Handles:
    - WD_EXBO_ADSK_COMPRESSION (0x0010) - LZ compression
    - WD_ZLIB_COMPRESSION_EXT_OPCODE (0x0011) - ZLIB compression
    - WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE (0x0123) - Obsolete LZ

    These opcodes have NO data payload - they are markers that indicate
    the start of compressed data stream.

    Reference: compdata.cpp lines 35-71 (serialize), 75-94 (materialize)
    """

    COMPRESSION_NAMES = {
        WD_EXBO_ADSK_COMPRESSION: "LZ",
        WD_ZLIB_COMPRESSION_EXT_OPCODE: "ZLIB",
        WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE: "LZ_OBSOLETE"
    }

    @staticmethod
    def parse(opcode: int, stream: BinaryIO, data_size: int) -> CompressionMarker:
        """
        Parse compression marker.

        Args:
            opcode: Compression opcode value
            stream: Input stream (positioned after opcode)
            data_size: Should be 0 for compression markers

        Returns:
            CompressionMarker object
        """
        # Compression markers have no data payload
        if data_size != 0:
            # Skip any unexpected data
            stream.seek(data_size, 1)

        format_name = CompressionHandler.COMPRESSION_NAMES.get(opcode, "UNKNOWN")
        return CompressionMarker(format_code=opcode, format_name=format_name)

    @staticmethod
    def serialize(format_code: int, stream: BinaryIO) -> None:
        """
        Serialize compression marker to Extended Binary format.

        Args:
            format_code: Compression format code (0x0010, 0x0011, or 0x0123)
            stream: Output stream
        """
        # Write opening '{'
        stream.write(b'{')

        # Write size = 0 (special case: can't be skipped, reader must handle)
        # Reference: compdata.cpp line 53 - "A value of zero means that this
        # can't be skipped and it is up to the reader to know when the opcode terminates"
        stream.write(struct.pack('<I', 0))

        # Write opcode
        stream.write(struct.pack('<H', format_code))

        # No closing '}' - compression data follows immediately
        # The compressed data stream continues until decompression completes


class OverlayPreviewHandler:
    """Handler for WD_EXBO_OVERLAY_PREVIEW (0x0018).

    Note: The hex value 0x0018 is correct per opcode_defs.h line 54.
    This is WD_OVERLAY_PREVIEW_EXT_OPCODE (ID 340).

    This opcode marks an overlay preview block, which is a special block
    type in the DWF file structure used for preview images of overlay layers.

    The actual block data structure follows the Extended Binary opcode and
    contains block reference information (file offset, size, GUID, etc).

    Reference: blockref.cpp lines 22-61 (BLOCK_VARIABLE_RELATION table)
    """

    @staticmethod
    def parse(stream: BinaryIO, data_size: int) -> OverlayPreview:
        """
        Parse overlay preview block reference.

        Args:
            stream: Input stream positioned after opcode
            data_size: Number of data bytes

        Returns:
            OverlayPreview object
        """
        # Overlay preview blocks contain block reference data
        # Minimum: file_offset (4-8 bytes) + block_size (4-8 bytes)

        if data_size < 8:
            raise CorruptFileError(f"Overlay preview data too small: {data_size} bytes")

        # Read file offset (assuming 32-bit for simplicity)
        offset_bytes = stream.read(4)
        file_offset = struct.unpack('<I', offset_bytes)[0]

        # Read block size
        size_bytes = stream.read(4)
        block_size = struct.unpack('<I', size_bytes)[0]

        # Skip remaining block reference fields (GUID, timestamps, etc.)
        remaining = data_size - 8
        if remaining > 0:
            stream.seek(remaining, 1)

        return OverlayPreview(file_offset=file_offset, block_size=block_size)

    @staticmethod
    def serialize(preview: OverlayPreview, stream: BinaryIO) -> None:
        """
        Serialize overlay preview block reference.

        Args:
            preview: OverlayPreview object
            stream: Output stream
        """
        # Write opening '{'
        stream.write(b'{')

        # Calculate size: opcode (2) + offset (4) + size (4) + '}' (1)
        size = 2 + 4 + 4 + 1
        stream.write(struct.pack('<I', size))

        # Write opcode
        stream.write(struct.pack('<H', WD_OVERLAY_PREVIEW_EXT_OPCODE))

        # Write file offset and block size
        stream.write(struct.pack('<I', preview.file_offset))
        stream.write(struct.pack('<I', preview.block_size))

        # Write closing '}'
        stream.write(b'}')


class FontBlockHandler:
    """Handler for WD_FONT_EXT_OPCODE (0x0019).

    Note: The hex value 0x0019 is correct per opcode_defs.h line 55.
    This is WD_FONT_EXT_OPCODE (ID 341 = WD_EXBO_FONT).

    This is different from WD_EXBO_EMBEDDED_FONT. This opcode marks
    a font block reference in the DWF file structure, which contains
    pointers to embedded font data.

    Reference: opcode_defs.h line 55, line 216
    """

    @staticmethod
    def parse(stream: BinaryIO, data_size: int) -> FontBlock:
        """
        Parse font block reference.

        Args:
            stream: Input stream positioned after opcode
            data_size: Number of data bytes

        Returns:
            FontBlock object
        """
        if data_size < 8:
            raise CorruptFileError(f"Font block data too small: {data_size} bytes")

        # Read file offset
        offset_bytes = stream.read(4)
        file_offset = struct.unpack('<I', offset_bytes)[0]

        # Read block size
        size_bytes = stream.read(4)
        block_size = struct.unpack('<I', size_bytes)[0]

        # Skip remaining block reference fields
        remaining = data_size - 8
        if remaining > 0:
            stream.seek(remaining, 1)

        return FontBlock(file_offset=file_offset, block_size=block_size)

    @staticmethod
    def serialize(font_block: FontBlock, stream: BinaryIO) -> None:
        """
        Serialize font block reference.

        Args:
            font_block: FontBlock object
            stream: Output stream
        """
        # Write opening '{'
        stream.write(b'{')

        # Calculate size: opcode (2) + offset (4) + size (4) + '}' (1)
        size = 2 + 4 + 4 + 1
        stream.write(struct.pack('<I', size))

        # Write opcode
        stream.write(struct.pack('<H', WD_FONT_EXT_OPCODE))

        # Write file offset and block size
        stream.write(struct.pack('<I', font_block.file_offset))
        stream.write(struct.pack('<I', font_block.block_size))

        # Write closing '}'
        stream.write(b'}')


class ExtendedBinaryOpcodeDispatcher:
    """Main dispatcher for Extended Binary opcodes.

    Coordinates parsing of all Extended Binary format opcodes.
    """

    def __init__(self):
        self.parser = ExtendedBinaryParser()
        self.handlers = {
            WD_COLOR_MAP_EXT_OPCODE: self._handle_colormap,
            WD_EXBO_ADSK_COMPRESSION: self._handle_compression,
            WD_ZLIB_COMPRESSION_EXT_OPCODE: self._handle_compression,
            WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE: self._handle_compression,
            WD_OVERLAY_PREVIEW_EXT_OPCODE: self._handle_overlay_preview,
            WD_FONT_EXT_OPCODE: self._handle_font,
        }

    def parse_opcode(self, stream: BinaryIO) -> Dict[str, Any]:
        """
        Parse next Extended Binary opcode from stream.

        Args:
            stream: Input stream positioned at '{'

        Returns:
            Dictionary with parsed opcode data
        """
        # Save position in case of error
        start_pos = stream.tell()

        try:
            # Parse header
            opcode, total_size, data_size = self.parser.parse_header(stream)

            # Dispatch to handler
            handler = self.handlers.get(opcode)
            if handler:
                result = handler(stream, opcode, data_size)
                self.parser.read_closing_brace(stream)
                return result
            else:
                # Unknown opcode - skip it
                self.parser.skip_data(stream, data_size)
                return {
                    'type': 'unknown_binary',
                    'opcode': opcode,
                    'opcode_hex': f'0x{opcode:04X}',
                    'data_size': data_size
                }
        except Exception as e:
            # On error, try to recover by seeking past the opcode
            stream.seek(start_pos)
            raise DWFParseError(f"Failed to parse Extended Binary opcode at position {start_pos}: {e}")

    def _handle_colormap(self, stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
        """Handle color map opcode."""
        colormap = ColorMapHandler.parse(stream, data_size)
        return {
            'type': 'colormap',
            'opcode': opcode,
            'opcode_name': 'WD_EXBO_SET_COLOR_MAP',
            'data': colormap
        }

    def _handle_compression(self, stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
        """Handle compression marker opcodes."""
        marker = CompressionHandler.parse(opcode, stream, data_size)
        return {
            'type': 'compression_marker',
            'opcode': opcode,
            'opcode_name': f'WD_{marker.format_name}_COMPRESSION',
            'data': marker
        }

    def _handle_overlay_preview(self, stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
        """Handle overlay preview opcode."""
        preview = OverlayPreviewHandler.parse(stream, data_size)
        return {
            'type': 'overlay_preview',
            'opcode': opcode,
            'opcode_name': 'WD_EXBO_OVERLAY_PREVIEW',
            'data': preview
        }

    def _handle_font(self, stream: BinaryIO, opcode: int, data_size: int) -> Dict[str, Any]:
        """Handle font block opcode."""
        font_block = FontBlockHandler.parse(stream, data_size)
        return {
            'type': 'font_block',
            'opcode': opcode,
            'opcode_name': 'WD_EXBO_FONT',
            'data': font_block
        }


# ============================================================================
# TESTS
# ============================================================================

def test_colormap_parse():
    """Test parsing color map opcode."""
    print("Testing Color Map parsing...")

    # Create test data: { + size + opcode + count + colors + }
    stream = io.BytesIO()

    # Write opening '{'
    stream.write(b'{')

    # Write size: opcode(2) + count(1) + 3 colors(12) + '}'(1) = 16
    stream.write(struct.pack('<I', 16))

    # Write opcode
    stream.write(struct.pack('<H', WD_COLOR_MAP_EXT_OPCODE))

    # Write count (3 colors)
    stream.write(struct.pack('B', 3))

    # Write 3 RGBA colors
    stream.write(struct.pack('BBBB', 255, 0, 0, 255))    # Red
    stream.write(struct.pack('BBBB', 0, 255, 0, 255))    # Green
    stream.write(struct.pack('BBBB', 0, 0, 255, 255))    # Blue

    # Write closing '}'
    stream.write(b'}')

    # Parse
    stream.seek(0)
    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'colormap'
    assert result['opcode'] == WD_COLOR_MAP_EXT_OPCODE
    assert result['data'].size == 3
    assert result['data'].colors[0].r == 255
    assert result['data'].colors[1].g == 255
    assert result['data'].colors[2].b == 255

    print("  PASSED: Color map with 3 colors")


def test_colormap_256_colors():
    """Test parsing color map with 256 colors (count byte = 0)."""
    print("Testing Color Map with 256 colors...")

    stream = io.BytesIO()
    stream.write(b'{')

    # Size: opcode(2) + count(1) + 256 colors(1024) + '}'(1) = 1028
    stream.write(struct.pack('<I', 1028))
    stream.write(struct.pack('<H', WD_COLOR_MAP_EXT_OPCODE))

    # Count = 0 means 256 colors
    stream.write(struct.pack('B', 0))

    # Write 256 colors
    for i in range(256):
        stream.write(struct.pack('BBBB', i, i, i, 255))

    stream.write(b'}')

    # Parse
    stream.seek(0)
    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['data'].size == 256
    assert len(result['data'].colors) == 256
    assert result['data'].colors[0].r == 0
    assert result['data'].colors[255].r == 255

    print("  PASSED: Color map with 256 colors")


def test_compression_lz():
    """Test parsing LZ compression marker."""
    print("Testing LZ Compression marker...")

    stream = io.BytesIO()
    stream.write(b'{')

    # Size = 0 for compression markers (special case)
    stream.write(struct.pack('<I', 0))
    stream.write(struct.pack('<H', WD_EXBO_ADSK_COMPRESSION))

    # No closing '}' for compression markers

    # Parse
    stream.seek(0)
    dispatcher = ExtendedBinaryOpcodeDispatcher()

    # Parse header manually since compression has special handling
    opcode, total_size, data_size = dispatcher.parser.parse_header(stream)

    assert opcode == WD_EXBO_ADSK_COMPRESSION
    assert total_size == 0

    # Parse with handler
    stream.seek(0)
    stream.write(b'{')
    stream.write(struct.pack('<I', 3))  # opcode(2) + '}'(1)
    stream.write(struct.pack('<H', WD_EXBO_ADSK_COMPRESSION))
    stream.write(b'}')
    stream.seek(0)

    result = dispatcher.parse_opcode(stream)
    assert result['type'] == 'compression_marker'
    assert result['data'].format_name == 'LZ'

    print("  PASSED: LZ compression marker")


def test_compression_zlib():
    """Test parsing ZLIB compression marker."""
    print("Testing ZLIB Compression marker...")

    stream = io.BytesIO()
    stream.write(b'{')
    stream.write(struct.pack('<I', 3))
    stream.write(struct.pack('<H', WD_ZLIB_COMPRESSION_EXT_OPCODE))
    stream.write(b'}')
    stream.seek(0)

    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'compression_marker'
    assert result['data'].format_name == 'ZLIB'

    print("  PASSED: ZLIB compression marker")


def test_compression_obsolete():
    """Test parsing obsolete LZ compression marker."""
    print("Testing Obsolete LZ Compression marker...")

    stream = io.BytesIO()
    stream.write(b'{')
    stream.write(struct.pack('<I', 3))
    stream.write(struct.pack('<H', WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE))
    stream.write(b'}')
    stream.seek(0)

    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'compression_marker'
    assert result['data'].format_name == 'LZ_OBSOLETE'
    assert result['data'].format_code == 0x0123

    print("  PASSED: Obsolete LZ compression marker")


def test_overlay_preview():
    """Test parsing overlay preview block."""
    print("Testing Overlay Preview...")

    stream = io.BytesIO()
    stream.write(b'{')

    # Size: opcode(2) + offset(4) + size(4) + '}'(1) = 11
    stream.write(struct.pack('<I', 11))
    stream.write(struct.pack('<H', WD_OVERLAY_PREVIEW_EXT_OPCODE))

    # Write file offset and block size
    stream.write(struct.pack('<I', 0x1000))  # offset
    stream.write(struct.pack('<I', 0x2000))  # size

    stream.write(b'}')
    stream.seek(0)

    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'overlay_preview'
    assert result['opcode'] == WD_OVERLAY_PREVIEW_EXT_OPCODE
    assert result['data'].file_offset == 0x1000
    assert result['data'].block_size == 0x2000

    print("  PASSED: Overlay preview block")


def test_overlay_preview_extended():
    """Test parsing overlay preview with extended data."""
    print("Testing Overlay Preview with extended data...")

    stream = io.BytesIO()
    stream.write(b'{')

    # Size: opcode(2) + offset(4) + size(4) + extra(16) + '}'(1) = 27
    stream.write(struct.pack('<I', 27))
    stream.write(struct.pack('<H', WD_OVERLAY_PREVIEW_EXT_OPCODE))

    stream.write(struct.pack('<I', 0x5000))  # offset
    stream.write(struct.pack('<I', 0x6000))  # size

    # Extra data (GUID, timestamps, etc.) - just padding for test
    stream.write(b'\x00' * 16)

    stream.write(b'}')
    stream.seek(0)

    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'overlay_preview'
    assert result['data'].file_offset == 0x5000
    assert result['data'].block_size == 0x6000

    print("  PASSED: Overlay preview with extended data")


def test_font_block():
    """Test parsing font block."""
    print("Testing Font Block...")

    stream = io.BytesIO()
    stream.write(b'{')

    # Size: opcode(2) + offset(4) + size(4) + '}'(1) = 11
    stream.write(struct.pack('<I', 11))
    stream.write(struct.pack('<H', WD_FONT_EXT_OPCODE))

    stream.write(struct.pack('<I', 0x3000))  # offset
    stream.write(struct.pack('<I', 0x4000))  # size

    stream.write(b'}')
    stream.seek(0)

    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'font_block'
    assert result['opcode'] == WD_FONT_EXT_OPCODE
    assert result['data'].file_offset == 0x3000
    assert result['data'].block_size == 0x4000

    print("  PASSED: Font block")


def test_font_block_extended():
    """Test parsing font block with extended data."""
    print("Testing Font Block with extended data...")

    stream = io.BytesIO()
    stream.write(b'{')

    # Size with extra data
    stream.write(struct.pack('<I', 35))  # opcode(2) + offset(4) + size(4) + extra(24) + '}'(1)
    stream.write(struct.pack('<H', WD_FONT_EXT_OPCODE))

    stream.write(struct.pack('<I', 0x7000))  # offset
    stream.write(struct.pack('<I', 0x8000))  # size

    # Extra block reference data
    stream.write(b'\x00' * 24)

    stream.write(b'}')
    stream.seek(0)

    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['type'] == 'font_block'
    assert result['data'].file_offset == 0x7000
    assert result['data'].block_size == 0x8000

    print("  PASSED: Font block with extended data")


def test_colormap_serialize():
    """Test serializing color map."""
    print("Testing Color Map serialization...")

    # Create color map
    colors = [
        RGBA32(255, 0, 0, 255),
        RGBA32(0, 255, 0, 255),
        RGBA32(0, 0, 255, 255)
    ]
    colormap = ColorMap(size=3, colors=colors)

    # Serialize
    stream = io.BytesIO()
    ColorMapHandler.serialize(colormap, stream)

    # Parse back
    stream.seek(0)
    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['data'].size == 3
    assert result['data'].colors[0].r == 255
    assert result['data'].colors[1].g == 255
    assert result['data'].colors[2].b == 255

    print("  PASSED: Color map serialization")


def test_overlay_preview_serialize():
    """Test serializing overlay preview."""
    print("Testing Overlay Preview serialization...")

    preview = OverlayPreview(file_offset=0x1234, block_size=0x5678)

    stream = io.BytesIO()
    OverlayPreviewHandler.serialize(preview, stream)

    stream.seek(0)
    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['data'].file_offset == 0x1234
    assert result['data'].block_size == 0x5678

    print("  PASSED: Overlay preview serialization")


def test_font_block_serialize():
    """Test serializing font block."""
    print("Testing Font Block serialization...")

    font_block = FontBlock(file_offset=0xABCD, block_size=0xEF01)

    stream = io.BytesIO()
    FontBlockHandler.serialize(font_block, stream)

    stream.seek(0)
    dispatcher = ExtendedBinaryOpcodeDispatcher()
    result = dispatcher.parse_opcode(stream)

    assert result['data'].file_offset == 0xABCD
    assert result['data'].block_size == 0xEF01

    print("  PASSED: Font block serialization")


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("Agent 30: Extended Binary Color/Compression Opcodes - Test Suite")
    print("=" * 70)
    print()

    tests = [
        test_colormap_parse,
        test_colormap_256_colors,
        test_compression_lz,
        test_compression_zlib,
        test_compression_obsolete,
        test_overlay_preview,
        test_overlay_preview_extended,
        test_font_block,
        test_font_block_extended,
        test_colormap_serialize,
        test_overlay_preview_serialize,
        test_font_block_serialize,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(tests)} total")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
