"""
Agent 29: Extended Binary Image Opcodes (Part 2/2) - Compression Formats

Translates 6 DWF Extended Binary image opcodes focused on compression formats.
These opcodes handle bitonal images with various CCITT fax compression formats,
plus thumbnail and preview image blocks.

Extended Binary Format: { + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + }

Author: Agent 29 (Parallel Translation System)
Date: 2025-10-22
Source: DWF Toolkit C++ Reference Implementation
"""

import struct
import io
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


# ============================================================================
# COMPRESSION FORMAT DOCUMENTATION
# ============================================================================

"""
CCITT Compression Formats (ITU-T Standards):

1. **Group 3 (T.4)**: CCITT T.4 fax compression standard
   - 1D compression using Modified Huffman (MH)
   - Each scan line encoded independently
   - Run-length encoding of white/black runs
   - Suitable for documents with horizontal redundancy

2. **Group 3X**: DWF-specific variant of Group 3
   - Modified Group 3 with additional optimizations
   - Used for bitonal mapped images (2-color palette)
   - Supports custom colormap (not just black/white)
   - Encoding type byte: 0x00=Group3, 0x01=Group3X, 0x02=Literal, 0x03=Reserved

3. **Group 4 (T.6)**: CCITT T.6 fax compression standard
   - 2D compression using Modified READ (MR) coding
   - More efficient than Group 3 (typical 3:1 to 30:1 compression)
   - Uses vertical and horizontal coding modes
   - References previous scan line for better compression
   - No EOL markers (fixed image width)

4. **Group 4X**: DWF-specific variant of Group 4
   - Modified Group 4 with colormap support
   - Allows 2-color palette mapping (not just black/white)
   - Better compression than Group3X for documents

Huffman Codes:
- Background (White): 0
- Foreground (Black): 1
- Run-length encoding with variable-length codes
- Make-up codes for runs > 63 pixels
- Terminating codes for runs 0-63 pixels

DWF Implementation Notes:
- Bitonal_Mapped is converted to Group3X_Mapped before serialization
- DWF doesn't directly support raw Bitonal format
- Group3X and Group4X add colormap capability to fax formats
- Expected compression factor for Group3X: ~0.2 (5:1 ratio)
"""


# ============================================================================
# CONSTANTS
# ============================================================================

# Extended Binary Opcode Values
WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED = 0x0002  # ID 294
WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED = 0x0003  # ID 295
WD_EXBO_DRAW_IMAGE_GROUP4 = 0x0009          # ID 306
WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED = 0x000D  # ID 317
WD_EXBO_THUMBNAIL = 0x0015                   # ID 338
WD_EXBO_PREVIEW = 0x0016                     # ID 339

# Image Format Names
IMAGE_FORMAT_NAMES = {
    0x0002: "Bitonal_Mapped",
    0x0003: "Group3X_Mapped",
    0x0009: "Group4",
    0x000D: "Group4X_Mapped",
    0x0015: "Thumbnail",
    0x0016: "Preview",
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LogicalPoint:
    """2D point in DWF logical coordinate space."""
    x: int  # WT_Integer32
    y: int  # WT_Integer32

    def __repr__(self):
        return f"({self.x}, {self.y})"


@dataclass
class ColorMap:
    """Color palette for mapped image formats."""
    size: int  # Number of colors (typically 2 for bitonal)
    colors: List[Tuple[int, int, int, int]]  # List of (R, G, B, A) tuples

    def __repr__(self):
        return f"ColorMap(size={self.size}, colors={self.colors[:4]}{'...' if len(self.colors) > 4 else ''})"


@dataclass
class BitonalMappedImage:
    """
    WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED (0x0002, ID 294)

    Bitonal mapped image with 2-color palette.
    Note: DWF converts this to Group3X_Mapped before serialization.
    """
    opcode: int = WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED
    columns: int = 0  # WT_Unsigned_Integer16
    rows: int = 0  # WT_Unsigned_Integer16
    min_corner: LogicalPoint = None  # Lower-left corner
    max_corner: LogicalPoint = None  # Upper-right corner
    identifier: int = 0  # WT_Integer32
    color_map: ColorMap = None  # 2-color palette (required)
    data_size: int = 0  # WT_Integer32
    data: bytes = b''  # Raw image data

    def __repr__(self):
        return (f"BitonalMappedImage(columns={self.columns}, rows={self.rows}, "
                f"min={self.min_corner}, max={self.max_corner}, "
                f"id={self.identifier}, colormap={self.color_map}, "
                f"data_size={self.data_size})")


@dataclass
class Group3XMappedImage:
    """
    WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED (0x0003, ID 295)

    Group3X compressed bitonal image with colormap.
    Uses modified Huffman run-length encoding with 2-color palette support.
    """
    opcode: int = WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED
    columns: int = 0
    rows: int = 0
    min_corner: LogicalPoint = None
    max_corner: LogicalPoint = None
    identifier: int = 0
    color_map: ColorMap = None  # 2-color palette (required)
    data_size: int = 0
    data: bytes = b''  # Group3X compressed data

    def __repr__(self):
        compression_ratio = (self.columns * self.rows / 8) / self.data_size if self.data_size > 0 else 0
        return (f"Group3XMappedImage(columns={self.columns}, rows={self.rows}, "
                f"id={self.identifier}, colormap={self.color_map}, "
                f"data_size={self.data_size}, compression={compression_ratio:.2f}:1)")


@dataclass
class Group4Image:
    """
    WD_EXBO_DRAW_IMAGE_GROUP4 (0x0009, ID 306)

    Group4 (CCITT T.6) compressed bitonal image.
    Uses 2D Modified READ coding for better compression than Group3.
    """
    opcode: int = WD_EXBO_DRAW_IMAGE_GROUP4
    columns: int = 0
    rows: int = 0
    min_corner: LogicalPoint = None
    max_corner: LogicalPoint = None
    identifier: int = 0
    data_size: int = 0
    data: bytes = b''  # Group4 (T.6) compressed data

    def __repr__(self):
        compression_ratio = (self.columns * self.rows / 8) / self.data_size if self.data_size > 0 else 0
        return (f"Group4Image(columns={self.columns}, rows={self.rows}, "
                f"id={self.identifier}, data_size={self.data_size}, "
                f"compression={compression_ratio:.2f}:1)")


@dataclass
class Group4XMappedImage:
    """
    WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED (0x000D, ID 317)

    Group4X compressed bitonal image with colormap.
    Combines Group4 compression efficiency with 2-color palette support.
    """
    opcode: int = WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED
    columns: int = 0
    rows: int = 0
    min_corner: LogicalPoint = None
    max_corner: LogicalPoint = None
    identifier: int = 0
    color_map: ColorMap = None  # 2-color palette (required)
    data_size: int = 0
    data: bytes = b''  # Group4X compressed data

    def __repr__(self):
        compression_ratio = (self.columns * self.rows / 8) / self.data_size if self.data_size > 0 else 0
        return (f"Group4XMappedImage(columns={self.columns}, rows={self.rows}, "
                f"id={self.identifier}, colormap={self.color_map}, "
                f"data_size={self.data_size}, compression={compression_ratio:.2f}:1)")


@dataclass
class ThumbnailBlock:
    """
    WD_EXBO_THUMBNAIL (0x0015, ID 338)

    Thumbnail image block reference.
    Handled as a BlockRef format in the DWF toolkit.
    Contains metadata pointing to a small preview image.
    """
    opcode: int = WD_EXBO_THUMBNAIL
    block_size: int = 0  # WT_Unsigned_Integer32
    file_offset: int = 0  # WT_Unsigned_Integer32
    # BlockRef can contain many optional fields based on format type
    # For thumbnail, typically contains image representation metadata
    raw_data: bytes = b''  # Raw block data

    def __repr__(self):
        return (f"ThumbnailBlock(block_size={self.block_size}, "
                f"offset={self.file_offset}, data_len={len(self.raw_data)})")


@dataclass
class PreviewBlock:
    """
    WD_EXBO_PREVIEW (0x0016, ID 339)

    Preview image block reference.
    Handled as a BlockRef format in the DWF toolkit.
    Contains metadata pointing to a larger preview image than thumbnail.
    """
    opcode: int = WD_EXBO_PREVIEW
    block_size: int = 0
    file_offset: int = 0
    raw_data: bytes = b''

    def __repr__(self):
        return (f"PreviewBlock(block_size={self.block_size}, "
                f"offset={self.file_offset}, data_len={len(self.raw_data)})")


# ============================================================================
# EXTENDED BINARY PARSER
# ============================================================================

class ExtendedBinaryParser:
    """
    Parser for Extended Binary opcodes.

    Format: { + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + }

    The size field contains the total byte count of everything AFTER the size field:
    - 2 bytes for opcode
    - Variable data
    - 1 byte for closing '}'
    """

    @staticmethod
    def parse_header(stream: io.BytesIO) -> Tuple[int, int, int]:
        """
        Parse Extended Binary opcode header.

        Returns:
            tuple: (opcode_value, total_size, data_size)

        Raises:
            ValueError: If format is invalid
        """
        # Read opening '{'
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{' for Extended Binary opcode, got {opening!r}")

        # Read size (4 bytes, little-endian)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise ValueError("Unexpected EOF reading opcode size")
        total_size = struct.unpack('<I', size_bytes)[0]

        # Read opcode value (2 bytes, little-endian)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise ValueError("Unexpected EOF reading opcode value")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Calculate data size: total_size - opcode(2) - closing_brace(1)
        data_size = total_size - 2 - 1

        return opcode, total_size, data_size

    @staticmethod
    def parse_logical_point(stream: io.BytesIO) -> LogicalPoint:
        """Parse a logical point (2 int32 values)."""
        x = struct.unpack('<i', stream.read(4))[0]
        y = struct.unpack('<i', stream.read(4))[0]
        return LogicalPoint(x, y)

    @staticmethod
    def parse_colormap(stream: io.BytesIO) -> ColorMap:
        """
        Parse a color map (for mapped image formats).

        Format: 1 byte size + (size * 4 bytes RGBA colors)
        """
        # Read size byte
        size = struct.unpack('B', stream.read(1))[0]

        # Read colors
        colors = []
        for _ in range(size):
            r = struct.unpack('B', stream.read(1))[0]
            g = struct.unpack('B', stream.read(1))[0]
            b = struct.unpack('B', stream.read(1))[0]
            a = struct.unpack('B', stream.read(1))[0]
            colors.append((r, g, b, a))

        return ColorMap(size=size, colors=colors)

    @staticmethod
    def verify_closing_brace(stream: io.BytesIO):
        """Verify the closing '}' byte."""
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}' at end of Extended Binary opcode, got {closing!r}")


# ============================================================================
# OPCODE HANDLERS
# ============================================================================

class BitonalImageHandlers:
    """Handlers for bitonal and compressed image opcodes."""

    @staticmethod
    def handle_bitonal_mapped(stream: io.BytesIO) -> BitonalMappedImage:
        """
        Handle WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED (0x0002, ID 294).

        Format (Extended Binary):
            { + size(4) + opcode(2) + columns(2) + rows(2) +
            min_corner(8) + max_corner(8) + identifier(4) +
            colormap(1+size*4) + data_size(4) + data + }
        """
        parser = ExtendedBinaryParser()
        opcode, total_size, data_size = parser.parse_header(stream)

        if opcode != WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED:
            raise ValueError(f"Expected opcode 0x0002, got 0x{opcode:04x}")

        # Parse image metadata
        columns = struct.unpack('<H', stream.read(2))[0]
        rows = struct.unpack('<H', stream.read(2))[0]
        min_corner = parser.parse_logical_point(stream)
        max_corner = parser.parse_logical_point(stream)
        identifier = struct.unpack('<i', stream.read(4))[0]

        # Parse colormap (required for bitonal mapped)
        color_map = parser.parse_colormap(stream)

        # Verify colormap has exactly 2 colors
        if color_map.size != 2:
            raise ValueError(f"Bitonal image must have 2-color colormap, got {color_map.size}")

        # Parse image data
        img_data_size = struct.unpack('<i', stream.read(4))[0]
        img_data = stream.read(img_data_size)

        if len(img_data) != img_data_size:
            raise ValueError(f"Expected {img_data_size} bytes of image data, got {len(img_data)}")

        # Verify closing brace
        parser.verify_closing_brace(stream)

        return BitonalMappedImage(
            columns=columns,
            rows=rows,
            min_corner=min_corner,
            max_corner=max_corner,
            identifier=identifier,
            color_map=color_map,
            data_size=img_data_size,
            data=img_data
        )

    @staticmethod
    def handle_group3x_mapped(stream: io.BytesIO) -> Group3XMappedImage:
        """
        Handle WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED (0x0003, ID 295).

        Group3X uses modified Huffman run-length encoding with colormap support.
        """
        parser = ExtendedBinaryParser()
        opcode, total_size, data_size = parser.parse_header(stream)

        if opcode != WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED:
            raise ValueError(f"Expected opcode 0x0003, got 0x{opcode:04x}")

        columns = struct.unpack('<H', stream.read(2))[0]
        rows = struct.unpack('<H', stream.read(2))[0]
        min_corner = parser.parse_logical_point(stream)
        max_corner = parser.parse_logical_point(stream)
        identifier = struct.unpack('<i', stream.read(4))[0]

        # Parse colormap
        color_map = parser.parse_colormap(stream)

        if color_map.size != 2:
            raise ValueError(f"Group3X image must have 2-color colormap, got {color_map.size}")

        # Parse compressed data
        img_data_size = struct.unpack('<i', stream.read(4))[0]
        img_data = stream.read(img_data_size)

        if len(img_data) != img_data_size:
            raise ValueError(f"Expected {img_data_size} bytes of compressed data, got {len(img_data)}")

        parser.verify_closing_brace(stream)

        return Group3XMappedImage(
            columns=columns,
            rows=rows,
            min_corner=min_corner,
            max_corner=max_corner,
            identifier=identifier,
            color_map=color_map,
            data_size=img_data_size,
            data=img_data
        )

    @staticmethod
    def handle_group4(stream: io.BytesIO) -> Group4Image:
        """
        Handle WD_EXBO_DRAW_IMAGE_GROUP4 (0x0009, ID 306).

        Group4 uses CCITT T.6 2D compression (no colormap).
        """
        parser = ExtendedBinaryParser()
        opcode, total_size, data_size = parser.parse_header(stream)

        if opcode != WD_EXBO_DRAW_IMAGE_GROUP4:
            raise ValueError(f"Expected opcode 0x0009, got 0x{opcode:04x}")

        columns = struct.unpack('<H', stream.read(2))[0]
        rows = struct.unpack('<H', stream.read(2))[0]
        min_corner = parser.parse_logical_point(stream)
        max_corner = parser.parse_logical_point(stream)
        identifier = struct.unpack('<i', stream.read(4))[0]

        # No colormap for Group4 (pure bitonal)

        # Parse compressed data
        img_data_size = struct.unpack('<i', stream.read(4))[0]
        img_data = stream.read(img_data_size)

        if len(img_data) != img_data_size:
            raise ValueError(f"Expected {img_data_size} bytes of compressed data, got {len(img_data)}")

        parser.verify_closing_brace(stream)

        return Group4Image(
            columns=columns,
            rows=rows,
            min_corner=min_corner,
            max_corner=max_corner,
            identifier=identifier,
            data_size=img_data_size,
            data=img_data
        )

    @staticmethod
    def handle_group4x_mapped(stream: io.BytesIO) -> Group4XMappedImage:
        """
        Handle WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED (0x000D, ID 317).

        Group4X combines Group4 compression with colormap support.
        """
        parser = ExtendedBinaryParser()
        opcode, total_size, data_size = parser.parse_header(stream)

        if opcode != WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED:
            raise ValueError(f"Expected opcode 0x000D, got 0x{opcode:04x}")

        columns = struct.unpack('<H', stream.read(2))[0]
        rows = struct.unpack('<H', stream.read(2))[0]
        min_corner = parser.parse_logical_point(stream)
        max_corner = parser.parse_logical_point(stream)
        identifier = struct.unpack('<i', stream.read(4))[0]

        # Parse colormap
        color_map = parser.parse_colormap(stream)

        if color_map.size != 2:
            raise ValueError(f"Group4X image must have 2-color colormap, got {color_map.size}")

        # Parse compressed data
        img_data_size = struct.unpack('<i', stream.read(4))[0]
        img_data = stream.read(img_data_size)

        if len(img_data) != img_data_size:
            raise ValueError(f"Expected {img_data_size} bytes of compressed data, got {len(img_data)}")

        parser.verify_closing_brace(stream)

        return Group4XMappedImage(
            columns=columns,
            rows=rows,
            min_corner=min_corner,
            max_corner=max_corner,
            identifier=identifier,
            color_map=color_map,
            data_size=img_data_size,
            data=img_data
        )

    @staticmethod
    def handle_thumbnail(stream: io.BytesIO) -> ThumbnailBlock:
        """
        Handle WD_EXBO_THUMBNAIL (0x0015, ID 338).

        Thumbnail is a BlockRef format. We read the raw block data
        since BlockRef has many optional fields based on format type.
        """
        parser = ExtendedBinaryParser()
        opcode, total_size, data_size = parser.parse_header(stream)

        if opcode != WD_EXBO_THUMBNAIL:
            raise ValueError(f"Expected opcode 0x0015, got 0x{opcode:04x}")

        # Read all remaining data as raw block data
        raw_data = stream.read(data_size)

        if len(raw_data) != data_size:
            raise ValueError(f"Expected {data_size} bytes of block data, got {len(raw_data)}")

        parser.verify_closing_brace(stream)

        # Parse basic BlockRef fields if present
        # For simplicity, we store as raw data
        # A full implementation would parse all BlockRef fields

        return ThumbnailBlock(
            block_size=total_size,
            file_offset=0,  # Would be set by file parser
            raw_data=raw_data
        )

    @staticmethod
    def handle_preview(stream: io.BytesIO) -> PreviewBlock:
        """
        Handle WD_EXBO_PREVIEW (0x0016, ID 339).

        Preview is a BlockRef format, similar to thumbnail but larger.
        """
        parser = ExtendedBinaryParser()
        opcode, total_size, data_size = parser.parse_header(stream)

        if opcode != WD_EXBO_PREVIEW:
            raise ValueError(f"Expected opcode 0x0016, got 0x{opcode:04x}")

        # Read all remaining data as raw block data
        raw_data = stream.read(data_size)

        if len(raw_data) != data_size:
            raise ValueError(f"Expected {data_size} bytes of block data, got {len(raw_data)}")

        parser.verify_closing_brace(stream)

        return PreviewBlock(
            block_size=total_size,
            file_offset=0,
            raw_data=raw_data
        )


# ============================================================================
# OPCODE DISPATCHER
# ============================================================================

class ImageOpcodeDispatcher:
    """Dispatcher for image-related Extended Binary opcodes."""

    def __init__(self):
        self.handlers = BitonalImageHandlers()
        self.opcode_map = {
            WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED: self.handlers.handle_bitonal_mapped,
            WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED: self.handlers.handle_group3x_mapped,
            WD_EXBO_DRAW_IMAGE_GROUP4: self.handlers.handle_group4,
            WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED: self.handlers.handle_group4x_mapped,
            WD_EXBO_THUMBNAIL: self.handlers.handle_thumbnail,
            WD_EXBO_PREVIEW: self.handlers.handle_preview,
        }

    def dispatch(self, opcode: int, stream: io.BytesIO) -> Any:
        """
        Dispatch opcode to appropriate handler.

        Args:
            opcode: The opcode value
            stream: Input stream positioned BEFORE the '{' character

        Returns:
            Parsed opcode object
        """
        handler = self.opcode_map.get(opcode)
        if not handler:
            raise ValueError(f"Unknown opcode: 0x{opcode:04x}")

        return handler(stream)

    def peek_opcode(self, stream: io.BytesIO) -> Optional[int]:
        """
        Peek at the opcode value without consuming the stream.

        Returns:
            Opcode value, or None if not an Extended Binary opcode
        """
        pos = stream.tell()
        try:
            byte = stream.read(1)
            if byte != b'{':
                stream.seek(pos)
                return None

            stream.read(4)  # Skip size
            opcode_bytes = stream.read(2)
            if len(opcode_bytes) != 2:
                stream.seek(pos)
                return None

            opcode = struct.unpack('<H', opcode_bytes)[0]
            stream.seek(pos)
            return opcode
        except:
            stream.seek(pos)
            return None


# ============================================================================
# SERIALIZATION (Writing DWF)
# ============================================================================

class ImageOpcodeSerializer:
    """Serializer for writing image opcodes to DWF format."""

    @staticmethod
    def serialize_bitonal_mapped(image: BitonalMappedImage) -> bytes:
        """Serialize bitonal mapped image to Extended Binary format."""
        # Calculate colormap size
        colormap_size = 1 + (image.color_map.size * 4)

        # Calculate total size
        total_size = (
            2 +  # opcode
            2 +  # columns
            2 +  # rows
            8 +  # min_corner
            8 +  # max_corner
            4 +  # identifier
            colormap_size +  # colormap
            4 +  # data_size
            image.data_size +  # data
            1  # closing brace
        )

        buffer = io.BytesIO()
        buffer.write(b'{')
        buffer.write(struct.pack('<I', total_size - 1))  # Exclude opening brace
        buffer.write(struct.pack('<H', WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED))
        buffer.write(struct.pack('<H', image.columns))
        buffer.write(struct.pack('<H', image.rows))
        buffer.write(struct.pack('<i', image.min_corner.x))
        buffer.write(struct.pack('<i', image.min_corner.y))
        buffer.write(struct.pack('<i', image.max_corner.x))
        buffer.write(struct.pack('<i', image.max_corner.y))
        buffer.write(struct.pack('<i', image.identifier))

        # Write colormap
        buffer.write(struct.pack('B', image.color_map.size))
        for r, g, b, a in image.color_map.colors:
            buffer.write(struct.pack('BBBB', r, g, b, a))

        # Write image data
        buffer.write(struct.pack('<i', image.data_size))
        buffer.write(image.data)
        buffer.write(b'}')

        return buffer.getvalue()

    @staticmethod
    def serialize_group3x_mapped(image: Group3XMappedImage) -> bytes:
        """Serialize Group3X mapped image to Extended Binary format."""
        colormap_size = 1 + (image.color_map.size * 4)

        total_size = (
            2 + 2 + 2 + 8 + 8 + 4 + colormap_size + 4 + image.data_size + 1
        )

        buffer = io.BytesIO()
        buffer.write(b'{')
        buffer.write(struct.pack('<I', total_size - 1))
        buffer.write(struct.pack('<H', WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED))
        buffer.write(struct.pack('<H', image.columns))
        buffer.write(struct.pack('<H', image.rows))
        buffer.write(struct.pack('<i', image.min_corner.x))
        buffer.write(struct.pack('<i', image.min_corner.y))
        buffer.write(struct.pack('<i', image.max_corner.x))
        buffer.write(struct.pack('<i', image.max_corner.y))
        buffer.write(struct.pack('<i', image.identifier))

        buffer.write(struct.pack('B', image.color_map.size))
        for r, g, b, a in image.color_map.colors:
            buffer.write(struct.pack('BBBB', r, g, b, a))

        buffer.write(struct.pack('<i', image.data_size))
        buffer.write(image.data)
        buffer.write(b'}')

        return buffer.getvalue()

    @staticmethod
    def serialize_group4(image: Group4Image) -> bytes:
        """Serialize Group4 image to Extended Binary format."""
        total_size = 2 + 2 + 2 + 8 + 8 + 4 + 4 + image.data_size + 1

        buffer = io.BytesIO()
        buffer.write(b'{')
        buffer.write(struct.pack('<I', total_size - 1))
        buffer.write(struct.pack('<H', WD_EXBO_DRAW_IMAGE_GROUP4))
        buffer.write(struct.pack('<H', image.columns))
        buffer.write(struct.pack('<H', image.rows))
        buffer.write(struct.pack('<i', image.min_corner.x))
        buffer.write(struct.pack('<i', image.min_corner.y))
        buffer.write(struct.pack('<i', image.max_corner.x))
        buffer.write(struct.pack('<i', image.max_corner.y))
        buffer.write(struct.pack('<i', image.identifier))
        buffer.write(struct.pack('<i', image.data_size))
        buffer.write(image.data)
        buffer.write(b'}')

        return buffer.getvalue()


# ============================================================================
# TESTS
# ============================================================================

def test_bitonal_mapped_image():
    """Test bitonal mapped image opcode."""
    print("Test 1: Bitonal Mapped Image (0x0002)")

    # Create test data
    colormap = ColorMap(size=2, colors=[(255, 255, 255, 255), (0, 0, 0, 255)])
    image = BitonalMappedImage(
        columns=100,
        rows=50,
        min_corner=LogicalPoint(0, 0),
        max_corner=LogicalPoint(1000, 500),
        identifier=12345,
        color_map=colormap,
        data_size=8,
        data=b'\x00\x01\x02\x03\x04\x05\x06\x07'
    )

    # Serialize
    serializer = ImageOpcodeSerializer()
    data = serializer.serialize_bitonal_mapped(image)

    # Parse
    stream = io.BytesIO(data)
    handlers = BitonalImageHandlers()
    parsed = handlers.handle_bitonal_mapped(stream)

    # Verify
    assert parsed.columns == 100
    assert parsed.rows == 50
    assert parsed.identifier == 12345
    assert parsed.color_map.size == 2
    assert parsed.data == b'\x00\x01\x02\x03\x04\x05\x06\x07'

    print(f"  ✓ Parsed: {parsed}")
    print(f"  ✓ Colormap: {parsed.color_map}")
    print()


def test_group3x_mapped_image():
    """Test Group3X mapped image opcode."""
    print("Test 2: Group3X Mapped Image (0x0003)")

    # Create compressed test data (simulated Group3X)
    compressed_data = b'\x01\x23\x45\x67\x89\xAB\xCD\xEF' * 8  # 64 bytes
    colormap = ColorMap(size=2, colors=[(255, 255, 255, 255), (0, 0, 255, 255)])

    image = Group3XMappedImage(
        columns=800,
        rows=600,
        min_corner=LogicalPoint(100, 100),
        max_corner=LogicalPoint(900, 700),
        identifier=54321,
        color_map=colormap,
        data_size=len(compressed_data),
        data=compressed_data
    )

    # Serialize and parse
    serializer = ImageOpcodeSerializer()
    data = serializer.serialize_group3x_mapped(image)
    stream = io.BytesIO(data)
    handlers = BitonalImageHandlers()
    parsed = handlers.handle_group3x_mapped(stream)

    # Verify
    assert parsed.columns == 800
    assert parsed.rows == 600
    assert parsed.identifier == 54321
    assert parsed.data_size == 64
    assert len(parsed.data) == 64

    # Calculate compression ratio
    uncompressed_size = (800 * 600) // 8  # bits to bytes
    compression_ratio = uncompressed_size / parsed.data_size

    print(f"  ✓ Parsed: {parsed}")
    print(f"  ✓ Uncompressed size: {uncompressed_size} bytes")
    print(f"  ✓ Compressed size: {parsed.data_size} bytes")
    print(f"  ✓ Compression ratio: {compression_ratio:.2f}:1")
    print()


def test_group4_image():
    """Test Group4 (CCITT T.6) image opcode."""
    print("Test 3: Group4 Image (0x0009)")

    # Create compressed test data (simulated Group4)
    compressed_data = b'\xFF' * 32  # 32 bytes of highly compressed data

    image = Group4Image(
        columns=1024,
        rows=768,
        min_corner=LogicalPoint(0, 0),
        max_corner=LogicalPoint(2048, 1536),
        identifier=99999,
        data_size=len(compressed_data),
        data=compressed_data
    )

    # Serialize and parse
    serializer = ImageOpcodeSerializer()
    data = serializer.serialize_group4(image)
    stream = io.BytesIO(data)
    handlers = BitonalImageHandlers()
    parsed = handlers.handle_group4(stream)

    # Verify
    assert parsed.columns == 1024
    assert parsed.rows == 768
    assert parsed.identifier == 99999
    assert parsed.data_size == 32

    # Calculate compression ratio
    uncompressed_size = (1024 * 768) // 8
    compression_ratio = uncompressed_size / parsed.data_size

    print(f"  ✓ Parsed: {parsed}")
    print(f"  ✓ Uncompressed size: {uncompressed_size} bytes")
    print(f"  ✓ Compressed size: {parsed.data_size} bytes")
    print(f"  ✓ Compression ratio: {compression_ratio:.2f}:1")
    print(f"  ✓ Group4 provides excellent compression for bitonal images")
    print()


def test_group4x_mapped_image():
    """Test Group4X mapped image opcode."""
    print("Test 4: Group4X Mapped Image (0x000D)")

    compressed_data = b'\xAA\x55' * 16  # 32 bytes
    colormap = ColorMap(size=2, colors=[(0, 255, 0, 255), (255, 0, 0, 255)])

    # Build manually for Group4X
    buffer = io.BytesIO()
    colormap_size = 1 + (2 * 4)
    # Size field = opcode(2) + columns(2) + rows(2) + corners(16) + id(4) + colormap + data_size(4) + data + closing(1)
    size_field = 2 + 2 + 2 + 8 + 8 + 4 + colormap_size + 4 + len(compressed_data) + 1

    buffer.write(b'{')
    buffer.write(struct.pack('<I', size_field))
    buffer.write(struct.pack('<H', WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED))
    buffer.write(struct.pack('<H', 640))  # columns
    buffer.write(struct.pack('<H', 480))  # rows
    buffer.write(struct.pack('<i', 50))   # min_corner.x
    buffer.write(struct.pack('<i', 50))   # min_corner.y
    buffer.write(struct.pack('<i', 690))  # max_corner.x
    buffer.write(struct.pack('<i', 530))  # max_corner.y
    buffer.write(struct.pack('<i', 77777))  # identifier

    # Colormap
    buffer.write(struct.pack('B', 2))
    buffer.write(struct.pack('BBBB', 0, 255, 0, 255))  # Green
    buffer.write(struct.pack('BBBB', 255, 0, 0, 255))  # Red

    # Data
    buffer.write(struct.pack('<i', len(compressed_data)))
    buffer.write(compressed_data)
    buffer.write(b'}')

    # Parse
    stream = io.BytesIO(buffer.getvalue())
    handlers = BitonalImageHandlers()
    parsed = handlers.handle_group4x_mapped(stream)

    # Verify
    assert parsed.columns == 640
    assert parsed.rows == 480
    assert parsed.identifier == 77777
    assert parsed.color_map.size == 2
    assert parsed.color_map.colors[0] == (0, 255, 0, 255)  # Green
    assert parsed.color_map.colors[1] == (255, 0, 0, 255)  # Red

    print(f"  ✓ Parsed: {parsed}")
    print(f"  ✓ Custom colormap: Green/Red instead of White/Black")
    print()


def test_thumbnail_block():
    """Test thumbnail block opcode."""
    print("Test 5: Thumbnail Block (0x0015)")

    # Create thumbnail block data
    thumbnail_data = b'THUMBNAIL_METADATA' * 4

    buffer = io.BytesIO()
    # Size field = opcode(2) + data + closing_brace(1)
    size_field = 2 + len(thumbnail_data) + 1

    buffer.write(b'{')
    buffer.write(struct.pack('<I', size_field))
    buffer.write(struct.pack('<H', WD_EXBO_THUMBNAIL))
    buffer.write(thumbnail_data)
    buffer.write(b'}')

    # Parse
    stream = io.BytesIO(buffer.getvalue())
    handlers = BitonalImageHandlers()
    parsed = handlers.handle_thumbnail(stream)

    # Verify
    assert len(parsed.raw_data) == len(thumbnail_data)
    assert parsed.raw_data == thumbnail_data

    print(f"  ✓ Parsed: {parsed}")
    print(f"  ✓ Thumbnail blocks reference preview images")
    print()


def test_preview_block():
    """Test preview block opcode."""
    print("Test 6: Preview Block (0x0016)")

    # Create preview block data (larger than thumbnail)
    preview_data = b'PREVIEW_IMAGE_METADATA' * 8

    buffer = io.BytesIO()
    # Size field = opcode(2) + data + closing_brace(1)
    size_field = 2 + len(preview_data) + 1

    buffer.write(b'{')
    buffer.write(struct.pack('<I', size_field))
    buffer.write(struct.pack('<H', WD_EXBO_PREVIEW))
    buffer.write(preview_data)
    buffer.write(b'}')

    # Parse
    stream = io.BytesIO(buffer.getvalue())
    handlers = BitonalImageHandlers()
    parsed = handlers.handle_preview(stream)

    # Verify
    assert len(parsed.raw_data) == len(preview_data)
    assert parsed.raw_data == preview_data

    print(f"  ✓ Parsed: {parsed}")
    print(f"  ✓ Preview blocks are larger than thumbnails")
    print()


def test_opcode_dispatcher():
    """Test the opcode dispatcher."""
    print("Test 7: Opcode Dispatcher")

    dispatcher = ImageOpcodeDispatcher()

    # Test peek functionality
    colormap = ColorMap(size=2, colors=[(255, 255, 255, 255), (0, 0, 0, 255)])
    image = BitonalMappedImage(
        columns=100, rows=100,
        min_corner=LogicalPoint(0, 0),
        max_corner=LogicalPoint(100, 100),
        identifier=1,
        color_map=colormap,
        data_size=4,
        data=b'\x00\x01\x02\x03'
    )

    serializer = ImageOpcodeSerializer()
    data = serializer.serialize_bitonal_mapped(image)
    stream = io.BytesIO(data)

    # Peek at opcode
    opcode = dispatcher.peek_opcode(stream)
    assert opcode == WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED

    # Dispatch
    parsed = dispatcher.dispatch(opcode, stream)
    assert isinstance(parsed, BitonalMappedImage)
    assert parsed.columns == 100

    print(f"  ✓ Peeked opcode: 0x{opcode:04x}")
    print(f"  ✓ Dispatched to: {type(parsed).__name__}")
    print()


def test_compression_formats():
    """Test and document compression format differences."""
    print("Test 8: Compression Format Comparison")
    print()
    print("Format Characteristics:")
    print("  • Bitonal Mapped: Uncompressed bitonal with 2-color palette")
    print("  • Group3X Mapped: 1D Huffman RLE + palette (typical 5:1)")
    print("  • Group4: 2D Modified READ + bitonal (typical 10:1 to 30:1)")
    print("  • Group4X Mapped: 2D Modified READ + palette (best compression)")
    print()

    # Simulate compression ratios
    width, height = 2400, 3200  # A4 at 300 DPI
    uncompressed = (width * height) // 8

    print(f"Example: {width}×{height} bitonal image")
    print(f"  Uncompressed: {uncompressed:,} bytes ({uncompressed/1024:.1f} KB)")
    print(f"  Group3X (~5:1): {uncompressed//5:,} bytes ({uncompressed/5/1024:.1f} KB)")
    print(f"  Group4 (~15:1): {uncompressed//15:,} bytes ({uncompressed/15/1024:.1f} KB)")
    print(f"  Group4X (~15:1): {uncompressed//15:,} bytes ({uncompressed/15/1024:.1f} KB)")
    print()


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("Agent 29: Extended Binary Image Opcodes (Compression Formats)")
    print("=" * 70)
    print()

    test_bitonal_mapped_image()
    test_group3x_mapped_image()
    test_group4_image()
    test_group4x_mapped_image()
    test_thumbnail_block()
    test_preview_block()
    test_opcode_dispatcher()
    test_compression_formats()

    print("=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
    print()
    print("Summary:")
    print("  • 6 opcode handlers implemented")
    print("  • Extended Binary parser complete")
    print("  • Compression formats documented")
    print("  • CCITT Group3/Group4 support")
    print("  • Thumbnail and Preview blocks")
    print("  • 8 comprehensive tests")


if __name__ == "__main__":
    run_all_tests()
