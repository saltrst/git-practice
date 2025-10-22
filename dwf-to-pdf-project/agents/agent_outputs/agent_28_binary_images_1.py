"""
DWF Extended Binary Image Opcodes (Part 1/2)

Agent 28 - Extended Binary Image Opcodes (1/2)

This module implements parsing for 6 DWF Extended Binary image opcodes:
- 0x0006: WD_EXBO_DRAW_IMAGE_RGB (ID 298) - RGB image
- 0x0007: WD_EXBO_DRAW_IMAGE_RGBA (ID 299) - RGBA image
- 0x000C: WD_EXBO_DRAW_IMAGE_PNG (ID 305) - PNG image
- 0x0008: WD_EXBO_DRAW_IMAGE_JPEG (ID 300) - JPEG image
- 0x0004: WD_EXBO_DRAW_IMAGE_INDEXED (ID 296) - Indexed color image
- 0x0005: WD_EXBO_DRAW_IMAGE_MAPPED (ID 297) - Mapped image

Extended Binary Format: { + 4-byte size (LE int32) + 2-byte opcode (LE uint16) + data + }

Format specifications based on DWF Toolkit C++ source:
/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/

References:
- image.cpp: All image format implementations
- image.h: Image format enum definitions
- colormap.cpp: Color map serialization
- opcode_defs.h: Opcode constant definitions
- agent_13_extended_opcodes_research.md: Extended Binary format research

Extended Binary Format Structure:
1. Opening brace: { (1 byte)
2. Size: 4 bytes (little-endian int32) - includes everything after this field
3. Opcode: 2 bytes (little-endian uint16) - format value (0x0004-0x0008, 0x000C)
4. Data fields (variable length)
5. Closing brace: } (1 byte)

Image Data Structure (all formats):
- Columns: 2 bytes (uint16) - image width
- Rows: 2 bytes (uint16) - image height
- Min corner: 8 bytes (2 x int32) - lower left logical point
- Max corner: 8 bytes (2 x int32) - upper right logical point
- Identifier: 4 bytes (int32) - image ID
- Color map: variable (only for Mapped and Indexed formats)
- Data size: 4 bytes (int32) - pixel data size in bytes
- Image data: variable (pixel data in format-specific encoding)
"""

import struct
from io import BytesIO
from typing import Dict, List, Tuple, BinaryIO, Optional, Union


# ============================================================================
# Extended Binary Parser Base Class
# ============================================================================

class ExtendedBinaryParser:
    """
    Parser for Extended Binary opcodes: {size + opcode + data}

    Extended Binary Format:
    - Opening brace: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 2 bytes (little-endian uint16)
    - Data: variable length
    - Closing brace: } (1 byte)

    The size field contains the total byte count of everything AFTER the size field:
    opcode (2 bytes) + data + closing brace (1 byte)
    """

    @staticmethod
    def parse_header(stream: BinaryIO) -> Tuple[int, int, int]:
        """
        Parse Extended Binary opcode header.

        Args:
            stream: Binary stream positioned at the opening '{'

        Returns:
            Tuple of (opcode, total_size, data_size)
            - opcode: 2-byte opcode value
            - total_size: size field value (bytes after size field)
            - data_size: calculated data size (total_size - 2 - 1)

        Raises:
            ValueError: If header is malformed
        """
        # Read opening '{'
        opening = stream.read(1)
        if opening != b'{':
            raise ValueError(f"Expected '{{' for Extended Binary opcode, got {opening!r}")

        # Read size (4 bytes, little-endian)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise ValueError(f"Expected 4 bytes for size field, got {len(size_bytes)} bytes")
        total_size = struct.unpack('<I', size_bytes)[0]

        # Read opcode (2 bytes, little-endian)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise ValueError(f"Expected 2 bytes for opcode, got {len(opcode_bytes)} bytes")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Calculate data size: total_size - opcode (2) - closing brace (1)
        data_size = total_size - 2 - 1

        return opcode, total_size, data_size

    @staticmethod
    def verify_closing_brace(stream: BinaryIO) -> None:
        """
        Verify closing brace at end of Extended Binary opcode.

        Args:
            stream: Binary stream positioned at the closing '}'

        Raises:
            ValueError: If closing brace is not '}'
        """
        closing = stream.read(1)
        if closing != b'}':
            raise ValueError(f"Expected '}}' at end of Extended Binary opcode, got {closing!r}")


# ============================================================================
# Color Map Parser
# ============================================================================

def parse_color_map(stream: BinaryIO) -> Dict:
    """
    Parse color map data from Extended Binary image opcode.

    Color Map Format:
    - Size: 1 byte (0 means 256 colors)
    - Colors: size * 4 bytes (RGBA32 format)

    Each RGBA32 color is 4 bytes: R, G, B, A (all 0-255)

    C++ Reference (colormap.cpp lines 260-275):
        if (m_size == 256)
            WD_CHECK (file.write((WT_Byte) 0));
        else
            WD_CHECK (file.write((WT_Byte) m_size));

        for (int loop = 0; loop < m_size; loop++)
            WD_CHECK (file.write(m_map[loop]));

    Args:
        stream: Binary stream positioned at color map size byte

    Returns:
        Dictionary containing:
        - 'size': Number of colors in map
        - 'colors': List of (R, G, B, A) tuples
        - 'bytes_read': Total bytes consumed

    Raises:
        ValueError: If stream doesn't contain enough data
    """
    # Read size byte (0 = 256)
    size_byte = stream.read(1)
    if len(size_byte) != 1:
        raise ValueError(f"Expected 1 byte for color map size, got {len(size_byte)} bytes")

    size = size_byte[0]
    if size == 0:
        size = 256

    # Read colors (4 bytes each: R, G, B, A)
    colors = []
    for i in range(size):
        color_bytes = stream.read(4)
        if len(color_bytes) != 4:
            raise ValueError(f"Expected 4 bytes for color {i}, got {len(color_bytes)} bytes")

        r, g, b, a = struct.unpack('<BBBB', color_bytes)
        colors.append((r, g, b, a))

    bytes_read = 1 + (size * 4)

    return {
        'size': size,
        'colors': colors,
        'bytes_read': bytes_read
    }


# ============================================================================
# Common Image Data Parser
# ============================================================================

def parse_image_common_fields(stream: BinaryIO, has_colormap: bool = False) -> Dict:
    """
    Parse common fields present in all image opcodes.

    Common Image Fields:
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left logical point
    - Max corner: 8 bytes (2 x int32) - upper right logical point
    - Identifier: 4 bytes (int32) - image ID
    - Color map: variable (only if has_colormap=True)
    - Data size: 4 bytes (int32) - pixel data size

    C++ Reference (image.cpp lines 214-224):
        WD_CHECK (file.write(columns()));
        WD_CHECK (file.write(rows()));
        WD_CHECK (file.write(1, &min_corner()));
        WD_CHECK (file.write(1, &max_corner()));
        WD_CHECK (file.write(identifier()));

        if (colormap_size)
            WD_CHECK(m_color_map->serialize_just_colors(file));

        WD_CHECK (file.write(m_data_size));

    Args:
        stream: Binary stream positioned at columns field
        has_colormap: True if format includes a color map

    Returns:
        Dictionary containing common fields and bytes_read count

    Raises:
        ValueError: If stream doesn't contain enough data
    """
    result = {}
    bytes_read = 0

    # Columns (2 bytes, uint16)
    columns_bytes = stream.read(2)
    if len(columns_bytes) != 2:
        raise ValueError(f"Expected 2 bytes for columns, got {len(columns_bytes)} bytes")
    result['columns'] = struct.unpack('<H', columns_bytes)[0]
    bytes_read += 2

    # Rows (2 bytes, uint16)
    rows_bytes = stream.read(2)
    if len(rows_bytes) != 2:
        raise ValueError(f"Expected 2 bytes for rows, got {len(rows_bytes)} bytes")
    result['rows'] = struct.unpack('<H', rows_bytes)[0]
    bytes_read += 2

    # Min corner (8 bytes: 2 x int32)
    min_corner_bytes = stream.read(8)
    if len(min_corner_bytes) != 8:
        raise ValueError(f"Expected 8 bytes for min corner, got {len(min_corner_bytes)} bytes")
    min_x, min_y = struct.unpack('<ii', min_corner_bytes)
    result['min_corner'] = (min_x, min_y)
    bytes_read += 8

    # Max corner (8 bytes: 2 x int32)
    max_corner_bytes = stream.read(8)
    if len(max_corner_bytes) != 8:
        raise ValueError(f"Expected 8 bytes for max corner, got {len(max_corner_bytes)} bytes")
    max_x, max_y = struct.unpack('<ii', max_corner_bytes)
    result['max_corner'] = (max_x, max_y)
    bytes_read += 8

    # Identifier (4 bytes, int32)
    id_bytes = stream.read(4)
    if len(id_bytes) != 4:
        raise ValueError(f"Expected 4 bytes for identifier, got {len(id_bytes)} bytes")
    result['identifier'] = struct.unpack('<i', id_bytes)[0]
    bytes_read += 4

    # Color map (optional)
    if has_colormap:
        colormap = parse_color_map(stream)
        result['color_map'] = colormap
        bytes_read += colormap['bytes_read']

    # Data size (4 bytes, int32)
    data_size_bytes = stream.read(4)
    if len(data_size_bytes) != 4:
        raise ValueError(f"Expected 4 bytes for data size, got {len(data_size_bytes)} bytes")
    result['data_size'] = struct.unpack('<i', data_size_bytes)[0]
    bytes_read += 4

    result['common_bytes_read'] = bytes_read

    return result


# ============================================================================
# Opcode 0x0006: WD_EXBO_DRAW_IMAGE_RGB (ID 298)
# ============================================================================

def opcode_0x0006_draw_image_rgb(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0006 (WD_EXBO_DRAW_IMAGE_RGB) - RGB image.

    This Extended Binary opcode represents an RGB image with 24-bit color.
    Each pixel is 3 bytes: R, G, B (no alpha channel).

    Format Specification:
    - Opening: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 0x0006 (2 bytes, little-endian uint16)
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left point
    - Max corner: 8 bytes (2 x int32) - upper right point
    - Identifier: 4 bytes (int32) - image ID
    - Data size: 4 bytes (int32) - pixel data size
    - Image data: data_size bytes (RGB pixel data, 3 bytes per pixel)
    - Closing: } (1 byte)

    C++ Reference (image.cpp lines 242-244):
        case RGB:
        case JPEG:
            WD_CHECK (file.write(m_data_size, m_data));
            break;

    From image.h line 87:
        RGB = WD_IMAGE_RGB_EXT_OPCODE,

    From opcode_defs.h line 38:
        #define WD_IMAGE_RGB_EXT_OPCODE 0x0006

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary containing:
        - 'opcode': 0x0006
        - 'opcode_name': 'DRAW_IMAGE_RGB'
        - 'type': 'image_rgb'
        - 'columns': Image width in pixels
        - 'rows': Image height in pixels
        - 'min_corner': (x, y) lower left point
        - 'max_corner': (x, y) upper right point
        - 'identifier': Image ID
        - 'data_size': Size of image data in bytes
        - 'image_data': Raw RGB pixel data (bytes)
        - 'bytes_read': Total bytes consumed (including braces)

    Raises:
        ValueError: If stream doesn't contain valid RGB image data

    Example:
        >>> # RGB image: 2x2 pixels
        >>> data = struct.pack('<I', 2 + 2 + 2 + 8 + 8 + 4 + 4 + 12 + 1)
        >>> data += struct.pack('<H', 0x0006)  # Opcode
        >>> data += struct.pack('<H', 2)  # Columns
        >>> data += struct.pack('<H', 2)  # Rows
        >>> data += struct.pack('<ii', 0, 0)  # Min corner
        >>> data += struct.pack('<ii', 100, 100)  # Max corner
        >>> data += struct.pack('<i', 1)  # Identifier
        >>> data += struct.pack('<i', 12)  # Data size (2*2*3=12)
        >>> data += b'\\xff\\x00\\x00' * 4  # 4 red pixels
        >>> stream = BytesIO(b'{' + data + b'}')
        >>> result = opcode_0x0006_draw_image_rgb(stream)
        >>> result['columns']
        2
        >>> result['rows']
        2
        >>> len(result['image_data'])
        12
    """
    # Parse Extended Binary header
    opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

    # Verify opcode
    if opcode != 0x0006:
        raise ValueError(f"Expected opcode 0x0006, got 0x{opcode:04X}")

    # Parse common image fields (no colormap for RGB)
    common = parse_image_common_fields(stream, has_colormap=False)

    # Read image data
    image_data = stream.read(common['data_size'])
    if len(image_data) != common['data_size']:
        raise ValueError(
            f"Expected {common['data_size']} bytes of image data, "
            f"got {len(image_data)} bytes"
        )

    # Verify closing brace
    ExtendedBinaryParser.verify_closing_brace(stream)

    # Calculate total bytes read: { + size + opcode + common + data + }
    total_bytes = 1 + 4 + 2 + common['common_bytes_read'] + common['data_size'] + 1

    return {
        'opcode': 0x0006,
        'opcode_name': 'DRAW_IMAGE_RGB',
        'type': 'image_rgb',
        'columns': common['columns'],
        'rows': common['rows'],
        'min_corner': common['min_corner'],
        'max_corner': common['max_corner'],
        'identifier': common['identifier'],
        'data_size': common['data_size'],
        'image_data': image_data,
        'bytes_read': total_bytes,
        'pixel_format': 'RGB24',  # 24-bit RGB (8 bits per channel)
        'expected_pixels': common['columns'] * common['rows'],
        'expected_data_size': common['columns'] * common['rows'] * 3
    }


# ============================================================================
# Opcode 0x0007: WD_EXBO_DRAW_IMAGE_RGBA (ID 299)
# ============================================================================

def opcode_0x0007_draw_image_rgba(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0007 (WD_EXBO_DRAW_IMAGE_RGBA) - RGBA image.

    This Extended Binary opcode represents an RGBA image with 32-bit color.
    Each pixel is 4 bytes: R, G, B, A (with alpha channel).

    IMPORTANT: The data is stored as raw RGBA bytes (R, G, B, A per pixel),
    not as WT_RGBA32 structures. The C++ code converts during materialization.

    Format Specification:
    - Opening: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 0x0007 (2 bytes, little-endian uint16)
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left point
    - Max corner: 8 bytes (2 x int32) - upper right point
    - Identifier: 4 bytes (int32) - image ID
    - Data size: 4 bytes (int32) - pixel data size
    - Image data: data_size bytes (RGBA pixel data, 4 bytes per pixel)
    - Closing: } (1 byte)

    C++ Reference (image.cpp lines 229-235):
        case RGBA:
            {
                int num_pixels = rows() * columns();

                for (int pixel = 0; pixel < num_pixels; pixel++)
                    WD_CHECK (file.write(((WT_RGBA32 *)m_data)[pixel]));
            } break;

    Materialization (image.cpp lines 419-445):
        case RGBA:
            WD_CHECK (file.read(m_data_size, m_data));

            // Need to remap the RGBA data into our native WT_RGBA32 format.
            long num_pixels = rows() * columns();
            WT_Byte * raw_pos = (WT_Byte *) m_data;
            WT_RGBA32 * cooked_pos = (WT_RGBA32 *) m_data;

            for (long pixel = 0; pixel < num_pixels; pixel++)
            {
                WT_RGBA32 color (raw_pos[0],  // R
                                 raw_pos[1],  // G
                                 raw_pos[2],  // B
                                 raw_pos[3]); // A
                raw_pos += 4;
                *cooked_pos++ = color;
            }

    From opcode_defs.h line 39:
        #define WD_IMAGE_RGBA_EXT_OPCODE 0x0007

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary containing:
        - 'opcode': 0x0007
        - 'opcode_name': 'DRAW_IMAGE_RGBA'
        - 'type': 'image_rgba'
        - 'columns': Image width in pixels
        - 'rows': Image height in pixels
        - 'min_corner': (x, y) lower left point
        - 'max_corner': (x, y) upper right point
        - 'identifier': Image ID
        - 'data_size': Size of image data in bytes
        - 'image_data': Raw RGBA pixel data (bytes)
        - 'rgba_pixels': List of (R, G, B, A) tuples
        - 'bytes_read': Total bytes consumed (including braces)

    Raises:
        ValueError: If stream doesn't contain valid RGBA image data

    Example:
        >>> # RGBA image: 1x1 pixel (semi-transparent red)
        >>> data = struct.pack('<I', 2 + 2 + 2 + 8 + 8 + 4 + 4 + 4 + 1)
        >>> data += struct.pack('<H', 0x0007)  # Opcode
        >>> data += struct.pack('<H', 1)  # Columns
        >>> data += struct.pack('<H', 1)  # Rows
        >>> data += struct.pack('<ii', 0, 0)  # Min corner
        >>> data += struct.pack('<ii', 100, 100)  # Max corner
        >>> data += struct.pack('<i', 1)  # Identifier
        >>> data += struct.pack('<i', 4)  # Data size (1*1*4=4)
        >>> data += b'\\xff\\x00\\x00\\x80'  # Red with 50% alpha
        >>> stream = BytesIO(b'{' + data + b'}')
        >>> result = opcode_0x0007_draw_image_rgba(stream)
        >>> result['rgba_pixels'][0]
        (255, 0, 0, 128)
    """
    # Parse Extended Binary header
    opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

    # Verify opcode
    if opcode != 0x0007:
        raise ValueError(f"Expected opcode 0x0007, got 0x{opcode:04X}")

    # Parse common image fields (no colormap for RGBA)
    common = parse_image_common_fields(stream, has_colormap=False)

    # Read image data
    image_data = stream.read(common['data_size'])
    if len(image_data) != common['data_size']:
        raise ValueError(
            f"Expected {common['data_size']} bytes of image data, "
            f"got {len(image_data)} bytes"
        )

    # Convert RGBA bytes to pixel tuples
    num_pixels = common['columns'] * common['rows']
    rgba_pixels = []
    for i in range(num_pixels):
        offset = i * 4
        r = image_data[offset]
        g = image_data[offset + 1]
        b = image_data[offset + 2]
        a = image_data[offset + 3]
        rgba_pixels.append((r, g, b, a))

    # Verify closing brace
    ExtendedBinaryParser.verify_closing_brace(stream)

    # Calculate total bytes read
    total_bytes = 1 + 4 + 2 + common['common_bytes_read'] + common['data_size'] + 1

    return {
        'opcode': 0x0007,
        'opcode_name': 'DRAW_IMAGE_RGBA',
        'type': 'image_rgba',
        'columns': common['columns'],
        'rows': common['rows'],
        'min_corner': common['min_corner'],
        'max_corner': common['max_corner'],
        'identifier': common['identifier'],
        'data_size': common['data_size'],
        'image_data': image_data,
        'rgba_pixels': rgba_pixels,
        'bytes_read': total_bytes,
        'pixel_format': 'RGBA32',  # 32-bit RGBA (8 bits per channel)
        'expected_pixels': num_pixels,
        'expected_data_size': num_pixels * 4
    }


# ============================================================================
# Opcode 0x000C: WD_EXBO_DRAW_IMAGE_PNG (ID 305)
# ============================================================================

def opcode_0x000C_draw_image_png(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x000C (WD_EXBO_DRAW_IMAGE_PNG) - PNG image.

    This Extended Binary opcode represents a PNG-encoded image.
    The image data is stored as a complete PNG file.

    Format Specification:
    - Opening: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 0x000C (2 bytes, little-endian uint16)
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left point
    - Max corner: 8 bytes (2 x int32) - upper right point
    - Identifier: 4 bytes (int32) - image ID
    - Data size: 4 bytes (int32) - PNG file size
    - Image data: data_size bytes (complete PNG file)
    - Closing: } (1 byte)

    C++ Reference (pnggroup4image.cpp lines 210-211):
        case PNG:
            WD_CHECK (file.write(m_data_size, m_data));

    From pnggroup4image.h line 50:
        PNG = WD_IMAGE_PNG_EXT_OPCODE

    From opcode_defs.h line 42:
        #define WD_IMAGE_PNG_EXT_OPCODE 0x000C

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary containing:
        - 'opcode': 0x000C
        - 'opcode_name': 'DRAW_IMAGE_PNG'
        - 'type': 'image_png'
        - 'columns': Image width in pixels
        - 'rows': Image height in pixels
        - 'min_corner': (x, y) lower left point
        - 'max_corner': (x, y) upper right point
        - 'identifier': Image ID
        - 'data_size': Size of PNG data in bytes
        - 'png_data': Complete PNG file data (bytes)
        - 'png_signature_valid': True if PNG signature is correct
        - 'bytes_read': Total bytes consumed (including braces)

    Raises:
        ValueError: If stream doesn't contain valid PNG image data

    Example:
        >>> # PNG image with valid PNG signature
        >>> png_sig = b'\\x89PNG\\r\\n\\x1a\\n'
        >>> png_data = png_sig + b'...rest of PNG...'
        >>> data = struct.pack('<I', 2 + 2 + 2 + 8 + 8 + 4 + 4 + len(png_data) + 1)
        >>> data += struct.pack('<H', 0x000C)  # Opcode
        >>> data += struct.pack('<H', 100)  # Columns
        >>> data += struct.pack('<H', 100)  # Rows
        >>> data += struct.pack('<ii', 0, 0)  # Min corner
        >>> data += struct.pack('<ii', 100, 100)  # Max corner
        >>> data += struct.pack('<i', 1)  # Identifier
        >>> data += struct.pack('<i', len(png_data))  # Data size
        >>> data += png_data
        >>> stream = BytesIO(b'{' + data + b'}')
        >>> result = opcode_0x000C_draw_image_png(stream)
        >>> result['png_signature_valid']
        True
    """
    # PNG file signature (first 8 bytes of valid PNG file)
    PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

    # Parse Extended Binary header
    opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

    # Verify opcode
    if opcode != 0x000C:
        raise ValueError(f"Expected opcode 0x000C, got 0x{opcode:04X}")

    # Parse common image fields (no colormap for PNG)
    common = parse_image_common_fields(stream, has_colormap=False)

    # Read PNG data
    png_data = stream.read(common['data_size'])
    if len(png_data) != common['data_size']:
        raise ValueError(
            f"Expected {common['data_size']} bytes of PNG data, "
            f"got {len(png_data)} bytes"
        )

    # Check PNG signature (optional validation)
    png_signature_valid = False
    if len(png_data) >= 8:
        png_signature_valid = png_data[:8] == PNG_SIGNATURE

    # Verify closing brace
    ExtendedBinaryParser.verify_closing_brace(stream)

    # Calculate total bytes read
    total_bytes = 1 + 4 + 2 + common['common_bytes_read'] + common['data_size'] + 1

    return {
        'opcode': 0x000C,
        'opcode_name': 'DRAW_IMAGE_PNG',
        'type': 'image_png',
        'columns': common['columns'],
        'rows': common['rows'],
        'min_corner': common['min_corner'],
        'max_corner': common['max_corner'],
        'identifier': common['identifier'],
        'data_size': common['data_size'],
        'png_data': png_data,
        'png_signature_valid': png_signature_valid,
        'bytes_read': total_bytes,
        'pixel_format': 'PNG',
        'encoding': 'PNG (Portable Network Graphics)'
    }


# ============================================================================
# Opcode 0x0008: WD_EXBO_DRAW_IMAGE_JPEG (ID 300)
# ============================================================================

def opcode_0x0008_draw_image_jpeg(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0008 (WD_EXBO_DRAW_IMAGE_JPEG) - JPEG image.

    This Extended Binary opcode represents a JPEG-encoded image.
    The image data is stored as a complete JPEG file.

    Format Specification:
    - Opening: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 0x0008 (2 bytes, little-endian uint16)
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left point
    - Max corner: 8 bytes (2 x int32) - upper right point
    - Identifier: 4 bytes (int32) - image ID
    - Data size: 4 bytes (int32) - JPEG file size
    - Image data: data_size bytes (complete JPEG file)
    - Closing: } (1 byte)

    C++ Reference (image.cpp lines 242-244):
        case RGB:
        case JPEG:
            WD_CHECK (file.write(m_data_size, m_data));
            break;

    From image.h line 89:
        JPEG = WD_IMAGE_JPEG_EXT_OPCODE

    From opcode_defs.h line 40:
        #define WD_IMAGE_JPEG_EXT_OPCODE 0x0008

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary containing:
        - 'opcode': 0x0008
        - 'opcode_name': 'DRAW_IMAGE_JPEG'
        - 'type': 'image_jpeg'
        - 'columns': Image width in pixels
        - 'rows': Image height in pixels
        - 'min_corner': (x, y) lower left point
        - 'max_corner': (x, y) upper right point
        - 'identifier': Image ID
        - 'data_size': Size of JPEG data in bytes
        - 'jpeg_data': Complete JPEG file data (bytes)
        - 'jpeg_signature_valid': True if JPEG signature is correct
        - 'bytes_read': Total bytes consumed (including braces)

    Raises:
        ValueError: If stream doesn't contain valid JPEG image data

    Example:
        >>> # JPEG image with valid JPEG signature
        >>> jpeg_sig = b'\\xff\\xd8\\xff'
        >>> jpeg_data = jpeg_sig + b'...rest of JPEG...'
        >>> data = struct.pack('<I', 2 + 2 + 2 + 8 + 8 + 4 + 4 + len(jpeg_data) + 1)
        >>> data += struct.pack('<H', 0x0008)  # Opcode
        >>> data += struct.pack('<H', 200)  # Columns
        >>> data += struct.pack('<H', 150)  # Rows
        >>> data += struct.pack('<ii', 0, 0)  # Min corner
        >>> data += struct.pack('<ii', 200, 150)  # Max corner
        >>> data += struct.pack('<i', 1)  # Identifier
        >>> data += struct.pack('<i', len(jpeg_data))  # Data size
        >>> data += jpeg_data
        >>> stream = BytesIO(b'{' + data + b'}')
        >>> result = opcode_0x0008_draw_image_jpeg(stream)
        >>> result['jpeg_signature_valid']
        True
    """
    # JPEG file signature (SOI marker: Start Of Image)
    JPEG_SOI = b'\xff\xd8\xff'

    # Parse Extended Binary header
    opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

    # Verify opcode
    if opcode != 0x0008:
        raise ValueError(f"Expected opcode 0x0008, got 0x{opcode:04X}")

    # Parse common image fields (no colormap for JPEG)
    common = parse_image_common_fields(stream, has_colormap=False)

    # Read JPEG data
    jpeg_data = stream.read(common['data_size'])
    if len(jpeg_data) != common['data_size']:
        raise ValueError(
            f"Expected {common['data_size']} bytes of JPEG data, "
            f"got {len(jpeg_data)} bytes"
        )

    # Check JPEG signature (optional validation)
    jpeg_signature_valid = False
    if len(jpeg_data) >= 3:
        jpeg_signature_valid = jpeg_data[:3] == JPEG_SOI

    # Verify closing brace
    ExtendedBinaryParser.verify_closing_brace(stream)

    # Calculate total bytes read
    total_bytes = 1 + 4 + 2 + common['common_bytes_read'] + common['data_size'] + 1

    return {
        'opcode': 0x0008,
        'opcode_name': 'DRAW_IMAGE_JPEG',
        'type': 'image_jpeg',
        'columns': common['columns'],
        'rows': common['rows'],
        'min_corner': common['min_corner'],
        'max_corner': common['max_corner'],
        'identifier': common['identifier'],
        'data_size': common['data_size'],
        'jpeg_data': jpeg_data,
        'jpeg_signature_valid': jpeg_signature_valid,
        'bytes_read': total_bytes,
        'pixel_format': 'JPEG',
        'encoding': 'JPEG (Joint Photographic Experts Group)'
    }


# ============================================================================
# Opcode 0x0004: WD_EXBO_DRAW_IMAGE_INDEXED (ID 296)
# ============================================================================

def opcode_0x0004_draw_image_indexed(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0004 (WD_EXBO_DRAW_IMAGE_INDEXED) - Indexed color image.

    This Extended Binary opcode represents an indexed color image.
    Each pixel is an index into a color palette (no colormap in this format).

    Format Specification:
    - Opening: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 0x0004 (2 bytes, little-endian uint16)
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left point
    - Max corner: 8 bytes (2 x int32) - upper right point
    - Identifier: 4 bytes (int32) - image ID
    - Data size: 4 bytes (int32) - pixel data size
    - Image data: data_size bytes (indexed pixel data, 1 byte per pixel)
    - Closing: } (1 byte)

    C++ Reference (image.cpp lines 240-244):
        case Indexed:
        case Mapped:
        case RGB:
        case JPEG:
            WD_CHECK (file.write(m_data_size, m_data));
            break;

    From image.h line 85:
        Indexed = WD_IMAGE_INDEXED_EXT_OPCODE,

    From opcode_defs.h line 36:
        #define WD_IMAGE_INDEXED_EXT_OPCODE 0x0004

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary containing:
        - 'opcode': 0x0004
        - 'opcode_name': 'DRAW_IMAGE_INDEXED'
        - 'type': 'image_indexed'
        - 'columns': Image width in pixels
        - 'rows': Image height in pixels
        - 'min_corner': (x, y) lower left point
        - 'max_corner': (x, y) upper right point
        - 'identifier': Image ID
        - 'data_size': Size of image data in bytes
        - 'image_data': Raw indexed pixel data (bytes)
        - 'pixel_indices': List of color palette indices
        - 'bytes_read': Total bytes consumed (including braces)

    Raises:
        ValueError: If stream doesn't contain valid indexed image data

    Example:
        >>> # Indexed image: 2x2 pixels using palette indices
        >>> data = struct.pack('<I', 2 + 2 + 2 + 8 + 8 + 4 + 4 + 4 + 1)
        >>> data += struct.pack('<H', 0x0004)  # Opcode
        >>> data += struct.pack('<H', 2)  # Columns
        >>> data += struct.pack('<H', 2)  # Rows
        >>> data += struct.pack('<ii', 0, 0)  # Min corner
        >>> data += struct.pack('<ii', 100, 100)  # Max corner
        >>> data += struct.pack('<i', 1)  # Identifier
        >>> data += struct.pack('<i', 4)  # Data size (2*2=4)
        >>> data += b'\\x00\\x01\\x02\\x03'  # Palette indices
        >>> stream = BytesIO(b'{' + data + b'}')
        >>> result = opcode_0x0004_draw_image_indexed(stream)
        >>> result['pixel_indices']
        [0, 1, 2, 3]
    """
    # Parse Extended Binary header
    opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

    # Verify opcode
    if opcode != 0x0004:
        raise ValueError(f"Expected opcode 0x0004, got 0x{opcode:04X}")

    # Parse common image fields (no colormap - uses global color map)
    common = parse_image_common_fields(stream, has_colormap=False)

    # Read image data (palette indices)
    image_data = stream.read(common['data_size'])
    if len(image_data) != common['data_size']:
        raise ValueError(
            f"Expected {common['data_size']} bytes of image data, "
            f"got {len(image_data)} bytes"
        )

    # Convert bytes to list of indices
    pixel_indices = list(image_data)

    # Verify closing brace
    ExtendedBinaryParser.verify_closing_brace(stream)

    # Calculate total bytes read
    total_bytes = 1 + 4 + 2 + common['common_bytes_read'] + common['data_size'] + 1

    return {
        'opcode': 0x0004,
        'opcode_name': 'DRAW_IMAGE_INDEXED',
        'type': 'image_indexed',
        'columns': common['columns'],
        'rows': common['rows'],
        'min_corner': common['min_corner'],
        'max_corner': common['max_corner'],
        'identifier': common['identifier'],
        'data_size': common['data_size'],
        'image_data': image_data,
        'pixel_indices': pixel_indices,
        'bytes_read': total_bytes,
        'pixel_format': 'Indexed8',  # 8-bit palette indices
        'expected_pixels': common['columns'] * common['rows'],
        'note': 'Uses global color map from WD_EXBO_SET_COLOR_MAP (0x0001)'
    }


# ============================================================================
# Opcode 0x0005: WD_EXBO_DRAW_IMAGE_MAPPED (ID 297)
# ============================================================================

def opcode_0x0005_draw_image_mapped(stream: BinaryIO) -> Dict:
    """
    Parse DWF Opcode 0x0005 (WD_EXBO_DRAW_IMAGE_MAPPED) - Mapped image.

    This Extended Binary opcode represents a mapped color image.
    Each pixel is an index into a local color map embedded in this opcode.

    Format Specification:
    - Opening: { (1 byte)
    - Size: 4 bytes (little-endian int32)
    - Opcode: 0x0005 (2 bytes, little-endian uint16)
    - Columns: 2 bytes (uint16) - image width
    - Rows: 2 bytes (uint16) - image height
    - Min corner: 8 bytes (2 x int32) - lower left point
    - Max corner: 8 bytes (2 x int32) - upper right point
    - Identifier: 4 bytes (int32) - image ID
    - Color map size: 1 byte (0 = 256 colors)
    - Color map data: size * 4 bytes (RGBA32 colors)
    - Data size: 4 bytes (int32) - pixel data size
    - Image data: data_size bytes (indexed pixel data, 1 byte per pixel)
    - Closing: } (1 byte)

    C++ Reference (image.cpp lines 172-179):
        case Mapped:
            WD_Assert(m_color_map); // There had better be a colormap attached
            if (!m_color_map)
                return WT_Result::File_Write_Error;

            colormap_size = 1 +                         // For the colormap size byte
                            m_color_map->size() * 4;    // The colormap itself

    And lines 221-222:
        if (colormap_size)
            WD_CHECK(m_color_map->serialize_just_colors(file));

    From image.h line 86:
        Mapped = WD_IMAGE_MAPPED_EXT_OPCODE,

    From opcode_defs.h line 37:
        #define WD_IMAGE_MAPPED_EXT_OPCODE 0x0005

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary containing:
        - 'opcode': 0x0005
        - 'opcode_name': 'DRAW_IMAGE_MAPPED'
        - 'type': 'image_mapped'
        - 'columns': Image width in pixels
        - 'rows': Image height in pixels
        - 'min_corner': (x, y) lower left point
        - 'max_corner': (x, y) upper right point
        - 'identifier': Image ID
        - 'color_map': Color map dictionary (size, colors, bytes_read)
        - 'data_size': Size of image data in bytes
        - 'image_data': Raw indexed pixel data (bytes)
        - 'pixel_indices': List of color map indices
        - 'bytes_read': Total bytes consumed (including braces)

    Raises:
        ValueError: If stream doesn't contain valid mapped image data

    Example:
        >>> # Mapped image: 2x2 pixels with 4-color palette
        >>> colormap_data = struct.pack('<B', 4)  # 4 colors
        >>> colormap_data += struct.pack('<BBBB', 255, 0, 0, 255)  # Red
        >>> colormap_data += struct.pack('<BBBB', 0, 255, 0, 255)  # Green
        >>> colormap_data += struct.pack('<BBBB', 0, 0, 255, 255)  # Blue
        >>> colormap_data += struct.pack('<BBBB', 255, 255, 0, 255)  # Yellow
        >>> pixel_data = b'\\x00\\x01\\x02\\x03'  # 4 pixels
        >>> total_size = 2 + 2 + 2 + 8 + 8 + 4 + len(colormap_data) + 4 + 4 + 1
        >>> data = struct.pack('<I', total_size)
        >>> data += struct.pack('<H', 0x0005)  # Opcode
        >>> data += struct.pack('<H', 2)  # Columns
        >>> data += struct.pack('<H', 2)  # Rows
        >>> data += struct.pack('<ii', 0, 0)  # Min corner
        >>> data += struct.pack('<ii', 100, 100)  # Max corner
        >>> data += struct.pack('<i', 1)  # Identifier
        >>> data += colormap_data
        >>> data += struct.pack('<i', 4)  # Data size
        >>> data += pixel_data
        >>> stream = BytesIO(b'{' + data + b'}')
        >>> result = opcode_0x0005_draw_image_mapped(stream)
        >>> result['color_map']['size']
        4
        >>> result['pixel_indices']
        [0, 1, 2, 3]
    """
    # Parse Extended Binary header
    opcode, total_size, data_size = ExtendedBinaryParser.parse_header(stream)

    # Verify opcode
    if opcode != 0x0005:
        raise ValueError(f"Expected opcode 0x0005, got 0x{opcode:04X}")

    # Parse common image fields (WITH colormap for Mapped format)
    common = parse_image_common_fields(stream, has_colormap=True)

    # Read image data (palette indices)
    image_data = stream.read(common['data_size'])
    if len(image_data) != common['data_size']:
        raise ValueError(
            f"Expected {common['data_size']} bytes of image data, "
            f"got {len(image_data)} bytes"
        )

    # Convert bytes to list of indices
    pixel_indices = list(image_data)

    # Verify closing brace
    ExtendedBinaryParser.verify_closing_brace(stream)

    # Calculate total bytes read
    total_bytes = 1 + 4 + 2 + common['common_bytes_read'] + common['data_size'] + 1

    return {
        'opcode': 0x0005,
        'opcode_name': 'DRAW_IMAGE_MAPPED',
        'type': 'image_mapped',
        'columns': common['columns'],
        'rows': common['rows'],
        'min_corner': common['min_corner'],
        'max_corner': common['max_corner'],
        'identifier': common['identifier'],
        'color_map': common['color_map'],
        'data_size': common['data_size'],
        'image_data': image_data,
        'pixel_indices': pixel_indices,
        'bytes_read': total_bytes,
        'pixel_format': 'Indexed8',  # 8-bit palette indices
        'expected_pixels': common['columns'] * common['rows'],
        'note': 'Uses embedded local color map'
    }


# ============================================================================
# Opcode Dispatcher
# ============================================================================

def parse_extended_binary_image_opcode(stream: BinaryIO) -> Dict:
    """
    Parse any Extended Binary image opcode by dispatching to the appropriate handler.

    This function peeks at the opcode value and dispatches to the correct parser.
    The stream is rewound if the opcode is not recognized.

    Supported opcodes:
    - 0x0004: WD_EXBO_DRAW_IMAGE_INDEXED
    - 0x0005: WD_EXBO_DRAW_IMAGE_MAPPED
    - 0x0006: WD_EXBO_DRAW_IMAGE_RGB
    - 0x0007: WD_EXBO_DRAW_IMAGE_RGBA
    - 0x0008: WD_EXBO_DRAW_IMAGE_JPEG
    - 0x000C: WD_EXBO_DRAW_IMAGE_PNG

    Args:
        stream: Binary stream positioned at the opening '{'

    Returns:
        Dictionary from the appropriate opcode handler

    Raises:
        ValueError: If opcode is not a recognized image opcode
    """
    # Save current position
    start_pos = stream.tell()

    # Peek at opcode
    try:
        opening = stream.read(1)
        if opening != b'{':
            stream.seek(start_pos)
            raise ValueError(f"Expected '{{' for Extended Binary opcode, got {opening!r}")

        # Skip size field
        stream.read(4)

        # Read opcode
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            stream.seek(start_pos)
            raise ValueError(f"Expected 2 bytes for opcode, got {len(opcode_bytes)} bytes")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Rewind to start
        stream.seek(start_pos)

        # Dispatch to appropriate handler
        handlers = {
            0x0004: opcode_0x0004_draw_image_indexed,
            0x0005: opcode_0x0005_draw_image_mapped,
            0x0006: opcode_0x0006_draw_image_rgb,
            0x0007: opcode_0x0007_draw_image_rgba,
            0x0008: opcode_0x0008_draw_image_jpeg,
            0x000C: opcode_0x000C_draw_image_png,
        }

        handler = handlers.get(opcode)
        if handler is None:
            raise ValueError(
                f"Unsupported image opcode 0x{opcode:04X}. "
                f"Supported opcodes: {', '.join(f'0x{k:04X}' for k in sorted(handlers.keys()))}"
            )

        return handler(stream)

    except Exception as e:
        # Rewind on error
        stream.seek(start_pos)
        raise


# ============================================================================
# Tests
# ============================================================================

def test_opcode_0x0006_rgb_basic():
    """Test basic RGB image parsing."""
    print("Test: RGB image (2x2 pixels, red)")

    # Create 2x2 red image
    columns, rows = 2, 2
    pixel_data = b'\xff\x00\x00' * (columns * rows)  # Red pixels

    # Build Extended Binary packet
    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)  # Min corner
    data += struct.pack('<ii', 100, 100)  # Max corner
    data += struct.pack('<i', 42)  # Identifier
    data += struct.pack('<i', len(pixel_data))  # Data size
    data += pixel_data

    total_size = 2 + len(data) + 1  # opcode + data + }
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x0006) + data + b'}'

    stream = BytesIO(packet)
    result = opcode_0x0006_draw_image_rgb(stream)

    assert result['opcode'] == 0x0006
    assert result['type'] == 'image_rgb'
    assert result['columns'] == 2
    assert result['rows'] == 2
    assert result['identifier'] == 42
    assert len(result['image_data']) == 12
    assert result['image_data'][:3] == b'\xff\x00\x00'
    print(f"  ✓ Parsed {result['columns']}x{result['rows']} RGB image, ID={result['identifier']}")


def test_opcode_0x0007_rgba_basic():
    """Test basic RGBA image parsing."""
    print("Test: RGBA image (1x1 pixel, semi-transparent blue)")

    # Create 1x1 semi-transparent blue pixel
    columns, rows = 1, 1
    pixel_data = b'\x00\x00\xff\x80'  # Blue with 50% alpha

    # Build Extended Binary packet
    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)  # Min corner
    data += struct.pack('<ii', 100, 100)  # Max corner
    data += struct.pack('<i', 1)  # Identifier
    data += struct.pack('<i', len(pixel_data))  # Data size
    data += pixel_data

    total_size = 2 + len(data) + 1
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x0007) + data + b'}'

    stream = BytesIO(packet)
    result = opcode_0x0007_draw_image_rgba(stream)

    assert result['opcode'] == 0x0007
    assert result['type'] == 'image_rgba'
    assert result['rgba_pixels'][0] == (0, 0, 255, 128)
    print(f"  ✓ Parsed RGBA pixel: {result['rgba_pixels'][0]}")


def test_opcode_0x000C_png_signature():
    """Test PNG image with valid signature."""
    print("Test: PNG image with valid signature")

    # Create PNG with valid signature
    png_sig = b'\x89PNG\r\n\x1a\n'
    png_data = png_sig + b'\x00' * 100  # Fake PNG data

    columns, rows = 100, 100

    # Build Extended Binary packet
    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)
    data += struct.pack('<ii', 100, 100)
    data += struct.pack('<i', 10)
    data += struct.pack('<i', len(png_data))
    data += png_data

    total_size = 2 + len(data) + 1
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x000C) + data + b'}'

    stream = BytesIO(packet)
    result = opcode_0x000C_draw_image_png(stream)

    assert result['opcode'] == 0x000C
    assert result['png_signature_valid'] is True
    assert result['png_data'][:8] == png_sig
    print(f"  ✓ Valid PNG signature detected, size={len(result['png_data'])} bytes")


def test_opcode_0x0008_jpeg_signature():
    """Test JPEG image with valid signature."""
    print("Test: JPEG image with valid signature")

    # Create JPEG with valid SOI marker
    jpeg_sig = b'\xff\xd8\xff'
    jpeg_data = jpeg_sig + b'\x00' * 200

    columns, rows = 200, 150

    # Build Extended Binary packet
    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)
    data += struct.pack('<ii', 200, 150)
    data += struct.pack('<i', 20)
    data += struct.pack('<i', len(jpeg_data))
    data += jpeg_data

    total_size = 2 + len(data) + 1
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x0008) + data + b'}'

    stream = BytesIO(packet)
    result = opcode_0x0008_draw_image_jpeg(stream)

    assert result['opcode'] == 0x0008
    assert result['jpeg_signature_valid'] is True
    assert result['jpeg_data'][:3] == jpeg_sig
    print(f"  ✓ Valid JPEG signature detected, size={len(result['jpeg_data'])} bytes")


def test_opcode_0x0004_indexed_basic():
    """Test indexed color image."""
    print("Test: Indexed image (2x2 pixels)")

    # Create 2x2 indexed image
    columns, rows = 2, 2
    pixel_data = b'\x00\x01\x02\x03'  # Palette indices

    # Build Extended Binary packet
    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)
    data += struct.pack('<ii', 100, 100)
    data += struct.pack('<i', 5)
    data += struct.pack('<i', len(pixel_data))
    data += pixel_data

    total_size = 2 + len(data) + 1
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x0004) + data + b'}'

    stream = BytesIO(packet)
    result = opcode_0x0004_draw_image_indexed(stream)

    assert result['opcode'] == 0x0004
    assert result['pixel_indices'] == [0, 1, 2, 3]
    print(f"  ✓ Parsed indexed image, indices={result['pixel_indices']}")


def test_opcode_0x0005_mapped_with_colormap():
    """Test mapped image with embedded color map."""
    print("Test: Mapped image with 4-color palette")

    # Create 4-color palette
    colormap_data = struct.pack('<B', 4)  # 4 colors
    colormap_data += struct.pack('<BBBB', 255, 0, 0, 255)  # Red
    colormap_data += struct.pack('<BBBB', 0, 255, 0, 255)  # Green
    colormap_data += struct.pack('<BBBB', 0, 0, 255, 255)  # Blue
    colormap_data += struct.pack('<BBBB', 255, 255, 0, 255)  # Yellow

    # Create 2x2 image
    columns, rows = 2, 2
    pixel_data = b'\x00\x01\x02\x03'

    # Build Extended Binary packet
    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)
    data += struct.pack('<ii', 100, 100)
    data += struct.pack('<i', 6)
    data += colormap_data
    data += struct.pack('<i', len(pixel_data))
    data += pixel_data

    total_size = 2 + len(data) + 1
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x0005) + data + b'}'

    stream = BytesIO(packet)
    result = opcode_0x0005_draw_image_mapped(stream)

    assert result['opcode'] == 0x0005
    assert result['color_map']['size'] == 4
    assert result['color_map']['colors'][0] == (255, 0, 0, 255)  # Red
    assert result['pixel_indices'] == [0, 1, 2, 3]
    print(f"  ✓ Parsed mapped image with {result['color_map']['size']} colors")


def test_dispatcher():
    """Test opcode dispatcher."""
    print("Test: Opcode dispatcher")

    # Create RGB image
    columns, rows = 1, 1
    pixel_data = b'\xff\xff\xff'

    data = struct.pack('<H', columns)
    data += struct.pack('<H', rows)
    data += struct.pack('<ii', 0, 0)
    data += struct.pack('<ii', 10, 10)
    data += struct.pack('<i', 99)
    data += struct.pack('<i', len(pixel_data))
    data += pixel_data

    total_size = 2 + len(data) + 1
    packet = b'{' + struct.pack('<I', total_size) + struct.pack('<H', 0x0006) + data + b'}'

    stream = BytesIO(packet)
    result = parse_extended_binary_image_opcode(stream)

    assert result['opcode'] == 0x0006
    assert result['type'] == 'image_rgb'
    print(f"  ✓ Dispatcher correctly routed to RGB handler")


def test_colormap_256_colors():
    """Test color map with 256 colors (size byte = 0)."""
    print("Test: Color map with 256 colors")

    # Create color map with 256 colors
    colormap_data = struct.pack('<B', 0)  # 0 = 256 colors
    for i in range(256):
        colormap_data += struct.pack('<BBBB', i, i, i, 255)  # Grayscale

    stream = BytesIO(colormap_data)
    result = parse_color_map(stream)

    assert result['size'] == 256
    assert len(result['colors']) == 256
    assert result['colors'][0] == (0, 0, 0, 255)  # Black
    assert result['colors'][255] == (255, 255, 255, 255)  # White
    print(f"  ✓ Parsed 256-color grayscale palette")


def run_all_tests():
    """Run all tests for Extended Binary image opcodes."""
    print("\n" + "="*70)
    print("Agent 28: Extended Binary Image Opcodes Tests")
    print("="*70 + "\n")

    tests = [
        test_opcode_0x0006_rgb_basic,
        test_opcode_0x0007_rgba_basic,
        test_opcode_0x000C_png_signature,
        test_opcode_0x0008_jpeg_signature,
        test_opcode_0x0004_indexed_basic,
        test_opcode_0x0005_mapped_with_colormap,
        test_colormap_256_colors,
        test_dispatcher,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
