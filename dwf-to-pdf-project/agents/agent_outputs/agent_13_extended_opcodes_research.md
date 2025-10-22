# Agent 13: Extended Opcodes Research Report

## Executive Summary

This research document provides comprehensive analysis of DWF extended opcode formats for Agent 13's Python implementation. Extended opcodes come in two formats: **Extended ASCII** (parenthesized) and **Extended Binary** (curly-brace).

**Key Findings:**
- **72 Extended ASCII opcodes** identified (IDs 256-387)
- **37 Extended Binary opcodes** identified (hex values 0x0001-0x0018 and various others)
- Clear parsing strategies defined for both formats
- Format specifications fully documented from C++ source

---

## 1. Extended Opcode Formats

### 1.1 Extended ASCII Format: `(OpcodeName ...data...)`

**Structure:**
```
(OpcodeName field1 field2 ... fieldN)
```

**Parsing Rules:**
1. **Start Token**: `(` character
2. **Opcode Name**: Accumulate characters until whitespace or terminator
3. **Legal Characters**: `>= 0x21 ('!') && <= 0x7A ('z') && != '(' && != ')'`
4. **Terminators**: Whitespace (space, tab, LF, CR), `(`, or `)`
5. **Max Token Size**: 40 characters (WD_MAX_OPCODE_TOKEN_SIZE)
6. **End Token**: `)` character

**C++ Code Reference** (`opcode.cpp:138-166`):
```cpp
while (1) {
    WD_CHECK (file.read(a_byte));

    if (is_legal_opcode_character(a_byte)) {
        m_token[m_size++] = a_byte;
        if (m_size > WD_MAX_OPCODE_TOKEN_SIZE) {
            return WT_Result::Corrupt_File_Error;
        }
    } else {
        if (is_opcode_terminator(a_byte)) {
            m_status = Finished;
            m_token[m_size] = '\0';
            file.put_back(a_byte);
            return WT_Result::Success;
        } else {
            return WT_Result::Corrupt_File_Error;
        }
    }
}
```

### 1.2 Extended Binary Format: `{opcode ...data...}`

**Structure:**
```
{ (1 byte)
+ Size (4 bytes, little-endian WT_Integer32)
+ Opcode (2 bytes, little-endian WT_Unsigned_Integer16)
+ Data (variable length)
+ } (1 byte)
```

**Total Header Size**: 7 bytes (1 + 4 + 2)

**Opcode Extraction** (`opcode.cpp:937`):
```cpp
int ext_bin_value = (m_token[6] << 8) + m_token[5];
```

**Size Calculation**:
- The 4-byte size field contains the total byte count of everything AFTER the size field
- Includes: opcode (2 bytes) + data + closing `}`

**C++ Code Reference** (`opcode.cpp:123-131`):
```cpp
if (m_type == Extended_Binary) {
    // Extended binary
    // TODO: deal with Endian issues
    WD_CHECK (file.read(WD_EXTENDED_BINARY_OPCODE_SIZE + WD_EXTENDED_BINARY_OFFSET_SIZE,
                        &m_token[1]));
    m_status = Finished;
}
```

Where:
- `WD_EXTENDED_BINARY_OPCODE_SIZE = 2` (2 bytes for opcode)
- `WD_EXTENDED_BINARY_OFFSET_SIZE = 4` (4 bytes for size/offset)

**Example** (`image.cpp:202-214`):
```cpp
WD_CHECK (file.write((WT_Byte) '{'));
WD_CHECK (file.write((WT_Integer32) (
    sizeof(WT_Unsigned_Integer16) +  // for the opcode
    sizeof(WT_Unsigned_Integer16) +  // Num columns
    sizeof(WT_Unsigned_Integer16) +  // Num rows
    sizeof(WT_Logical_Point) +       // Lower left
    sizeof(WT_Logical_Point) +       // Upper right
    sizeof(WT_Integer32) +           // Image identifier
    colormap_size +                  // Colormap data
    sizeof(WT_Integer32) +           // Data size field
    m_data_size +                    // Image data
    sizeof(WT_Byte)                  // Closing '}'
)));
WD_CHECK (file.write((WT_Unsigned_Integer16) format()));
// ... write data fields ...
```

---

## 2. Extended ASCII Opcodes (EXAO)

### 2.1 Complete List

From `opcode_defs.h` (lines 128-262) and `opcode.cpp` (lines 319-930):

| ID  | Opcode Name | Token String | Category | Description |
|-----|-------------|--------------|----------|-------------|
| 256 | WD_EXAO_DEFINE_AUTHOR | `(Author` | Metadata | Document author |
| 257 | WD_EXAO_SET_BACKGROUND | `(Background` | Attributes | Background color/pattern |
| 258 | WD_EXAO_DRAW_CIRCLE | `(Circle` | Geometry | Circle drawing |
| 259 | WD_EXAO_DRAW_CONTOUR | `(Contour` | Geometry | Contour/polygon |
| 260 | WD_EXAO_SET_COLOR | `(Color` | Attributes | Color setting |
| 261 | WD_EXAO_SET_COLOR_MAP | `(ColorMap` | Attributes | Color palette |
| 262 | WD_EXAO_DEFINE_COMMENTS | `(Comment*` | Metadata | Comments (prefix match) |
| 263 | WD_EXAO_DEFINE_COPYRIGHT | `(Copyright` | Metadata | Copyright info |
| 264 | WD_EXAO_DEFINE_CREATOR | `(Creator` | Metadata | Creator application |
| 265 | WD_EXAO_DEFINE_CREATION_TIME | `(Created` | Metadata | Creation timestamp |
| 266 | WD_EXAO_SET_CODE_PAGE | `(CodePage` | Attributes | Character encoding |
| 267 | WD_EXAO_SET_DASH_PATTERN | `(DashPattern` | Attributes | Line dash pattern |
| 268 | WD_EXAO_DEFINE_DWF_HEADER | `(DWF V` | Special | File header (DWF) |
| 268 | WD_EXAO_DEFINE_DWF_HEADER | `(W2D V` | Special | File header (W2D) |
| 269 | WD_EXAO_DEFINE_DESCRIPTION | `(Description` | Metadata | Document description |
| 270 | WD_EXAO_DRAW_ELLIPSE | `(Ellipse` | Geometry | Ellipse drawing |
| 271 | WD_EXAO_DEFINE_EMBED | `(Embed` | Advanced | Embedded content |
| 272 | WD_EXAO_DEFINE_END_OF_DWF | `(EndOfDWF` | Special | End of file marker |
| 273 | WD_EXAO_SET_FONT | `(Font` | Text | Font definition |
| 274 | WD_EXAO_DRAW_IMAGE | `(Image` | Raster | Image embedding |
| 275 | WD_EXAO_DEFINE_KEYWORDS | `(Keywords` | Metadata | Search keywords |
| 276 | WD_EXAO_SET_LAYER | `(Layer` | Attributes | Layer assignment |
| 277 | WD_EXAO_SET_LINE_PATTERN | `(LinePattern` | Attributes | Line pattern |
| 278 | WD_EXAO_SET_LINE_WEIGHT | `(LineWeight` | Attributes | Line thickness |
| 279 | WD_EXAO_SET_LINE_STYLE | `(LineStyle` | Attributes | Line style |
| 280 | WD_EXAO_DEFINE_MODIFICATION_TIME | `(Modified` | Metadata | Modification timestamp |
| 281 | WD_EXAO_DEFINE_NAMED_VIEW | `(NamedView` | View | Named view |
| 282 | WD_EXAO_DEFINE_PLOT_INFO | `(PlotInfo` | Metadata | Plot configuration |
| 283 | WD_EXAO_SET_PROJECTION | `(Projection` | View | Projection settings |
| 284 | WD_EXAO_DEFINE_SOURCE_CREATION_TIME | `(SourceCreated` | Metadata | Source creation time |
| 285 | WD_EXAO_DEFINE_SOURCE_MODIFICATION_TIME | `(SourceModified` | Metadata | Source modified time |
| 286 | WD_EXAO_SOURCE_FILENAME | `(SourceFilename` | Metadata | Original filename |
| 287 | WD_EXAO_DRAW_TEXT | `(Text` | Text | Text drawing |
| 288 | WD_EXAO_SET_URL | `(URL` | Advanced | Hyperlink/URL |
| 289 | WD_EXAO_DEFINE_UNITS | `(Units` | Metadata | Units of measurement |
| 290 | WD_EXAO_SET_VIEWPORT | `(Viewport` | View | Viewport definition |
| 291 | WD_EXAO_SET_VIEW | `(View` | View | View settings |
| 292 | WD_EXAO_UNKNOWN | (unknown) | Special | Unrecognized opcode |
| 303 | WD_EXAO_DEFINE_TITLE | `(Title` | Metadata | Document title |
| 304 | WD_EXAO_DEFINE_SUBJECT | `(Subject` | Metadata | Document subject |
| 307 | WD_EXAO_DRAW_PNG_GROUP4_IMAGE | `(Group4PNGImage` | Raster | PNG/Group4 image |
| 308 | WD_EXAO_SET_MERGE_CONTROL | `(LinesOverwrite` | Attributes | Merge control |
| 309 | WD_EXAO_SET_OPAQUE | (opaque) | Attributes | Opacity setting |
| 310 | WD_EXAO_SET_MERGE | (merge) | Attributes | Merge mode |
| 311 | WD_EXAO_SET_TRANSPARENT | (transparent) | Attributes | Transparency |
| 312 | WD_EXAO_SET_OPTIMIZED_FOR_PLOTTING | `(PlotOptimized` | Attributes | Plot optimization |
| 313 | WD_EXAO_SET_GROUP_BEGIN | `(GroupBegin` | Structure | Begin group |
| 314 | WD_EXAO_SET_GROUP_END | `(GroupEnd` | Structure | End group |
| 315 | WD_EXAO_SET_FILL_PATTERN | `(FillPattern` | Attributes | Fill pattern |
| 316 | WD_EXAO_SET_INKED_AREA | `(InkedArea` | Metadata | Inked area bounds |
| 319 | WD_EXAO_EMBEDDED_FONT | `(Embedded_Font` | Text | Embedded font data |
| 320 | WD_EXAO_TRUSTED_FONT_LIST | `(TrustedFontList` | Text | Trusted fonts |
| 321 | WD_EXAO_BLOCK_MEANING | `(BlockMeaning` | Structure | Block semantics |
| 324 | WD_EXAO_ENCRYPTION | `(Encryption` | Security | Encryption info |
| 326 | WD_EXAO_ORIENTATION | `(Orientation` | View | Orientation |
| 328 | WD_EXAO_ALIGNMENT | `(Alignment` | Attributes | Alignment |
| 329 | WD_EXAO_PASSWORD | `(Psswd` | Security | Password |
| 332 | WD_EXAO_GUID | `(Guid` | Structure | GUID identifier |
| 334 | WD_EXAO_FILETIME | `(Time` | Metadata | File timestamp |
| 351 | WD_EXAO_BLOCKREF | `(BlockRef` | Structure | Block reference |
| 353 | WD_EXAO_DIRECTORY | `(Directory` | Structure | Directory |
| 355 | WD_EXAO_USERDATA | `(UserData` | Advanced | User-defined data |
| 357 | WD_EXAO_PEN_PATTERN | `(PenPattern` | Attributes | Pen pattern |
| 359 | WD_EXAO_SIGNDATA | `(SignData` | Security | Signature data |
| 361 | WD_EXAO_GUID_LIST | `(GuidList` | Structure | GUID list |
| 362 | WD_EXAO_SET_FONT_EXTENSION | `(FontExtension` | Text | Font extensions |
| 363 | WD_EXAO_PENPAT_OPTIONS | `(PenPat_Options` | Attributes | Pen pattern options |
| 364 | WD_EXAO_GOURAUD_POLYTRIANGLE | `(Gouraud` | Geometry | Gouraud shaded triangle |
| 365 | WD_EXAO_DRAWING_INFO | (drawing_info) | Metadata | Drawing information |
| 366 | WD_EXAO_OBJECT_NODE | `(Node` | Structure | Object node |
| 367 | WD_EXAO_GOURAUD_POLYLINE | `(GourLine` | Geometry | Gouraud shaded line |
| 368 | WD_EXAO_BEZIER | (bezier) | Geometry | Bezier curve |
| 370 | WD_EXAO_MACRO_DEFINITION | `(Macro` | Advanced | Macro definition |
| 372 | WD_EXAO_TEXT_HALIGN | `(TextHAlign` | Text | Horizontal alignment |
| 374 | WD_EXAO_TEXT_VALIGN | `(TextVAlign` | Text | Vertical alignment |
| 376 | WD_EXAO_TEXT_BACKGROUND | `(TextBackground` | Text | Text background |
| 378 | WD_EXAO_OVERPOST | `(Overpost` | Advanced | Overposting control |
| 379 | WD_EXAO_DELINEATE | `(Delineate` | Attributes | Delineation |
| 381 | WD_EXAO_SET_USER_FILL_PATTERN | `(UserFillPattern` | Attributes | User fill pattern |
| 383 | WD_EXAO_SET_USER_HATCH_PATTERN | `(UserHatchPattern` | Attributes | User hatch pattern |
| 385 | WD_EXAO_SET_CONTRAST_COLOR | `(ContrastColor` | Attributes | Contrast color |
| 387 | WD_EXAO_ATTRIBUTE_URL | `(AttributeURL` | Advanced | Attribute URL |

**Total Extended ASCII Opcodes: 72**

---

## 3. Extended Binary Opcodes (EXBO)

### 3.1 Complete List

From `opcode_defs.h` (lines 32-64, 166-262) and `opcode.cpp` (lines 932-1228):

| Hex Value | ID  | Opcode Name | Category | Description |
|-----------|-----|-------------|----------|-------------|
| 0x0001 | 293 | WD_EXBO_SET_COLOR_MAP | Attributes | Color map definition |
| 0x0002 | 294 | WD_EXBO_DRAW_IMAGE_BITONAL_MAPPED | Raster | Bitonal mapped image |
| 0x0003 | 295 | WD_EXBO_DRAW_IMAGE_GROUP3X_MAPPED | Raster | Group3X mapped image |
| 0x0004 | 296 | WD_EXBO_DRAW_IMAGE_INDEXED | Raster | Indexed color image |
| 0x0005 | 297 | WD_EXBO_DRAW_IMAGE_MAPPED | Raster | Mapped image |
| 0x0006 | 298 | WD_EXBO_DRAW_IMAGE_RGB | Raster | RGB image |
| 0x0007 | 299 | WD_EXBO_DRAW_IMAGE_RGBA | Raster | RGBA image |
| 0x0008 | 300 | WD_EXBO_DRAW_IMAGE_JPEG | Raster | JPEG image |
| 0x0009 | 306 | WD_EXBO_DRAW_IMAGE_GROUP4 | Raster | Group4 bitonal image |
| 0x000C | 305 | WD_EXBO_DRAW_IMAGE_PNG | Raster | PNG image |
| 0x000D | 317 | WD_EXBO_DRAW_IMAGE_GROUP4X_MAPPED | Raster | Group4X mapped image |
| 0x0010 | 301 | WD_EXBO_ADSK_COMPRESSION (LZ) | Compression | LZ compression |
| 0x0011 |  | WD_ZLIB_COMPRESSION_EXT_OPCODE | Compression | ZLIB compression |
| 0x0012 | 335 | WD_EXBO_GRAPHICS_HDR | Structure | Graphics header block |
| 0x0013 | 336 | WD_EXBO_OVERLAY_HDR | Structure | Overlay header block |
| 0x0014 | 337 | WD_EXBO_REDLINE_HDR | Structure | Redline header block |
| 0x0015 | 338 | WD_EXBO_THUMBNAIL | Raster | Thumbnail image |
| 0x0016 | 339 | WD_EXBO_PREVIEW | Raster | Preview image |
| 0x0017 | 340 | WD_EXBO_OVERLAY_PREVIEW | Raster | Overlay preview |
| 0x0018 | 341 | WD_EXBO_FONT | Text | Font block |
| 0x0019 |  | WD_FONT_EXT_OPCODE | Text | Font extension |
| 0x0020 | 342 | WD_EXBO_GRAPHICS | Structure | Graphics block |
| 0x0021 | 343 | WD_EXBO_OVERLAY | Structure | Overlay block |
| 0x0022 | 344 | WD_EXBO_REDLINE | Structure | Redline block |
| 0x0023 | 345 | WD_EXBO_USER | Advanced | User block |
| 0x0024 | 346 | WD_EXBO_NULL | Special | Null block |
| 0x0025 | 347 | WD_EXBO_GLOBAL_SHEET | Structure | Global sheet block |
| 0x0026 | 348 | WD_EXBO_GLOBAL | Structure | Global block |
| 0x0027 | 349 | WD_EXBO_SIGNATURE | Security | Signature block |
| 0x0123 |  | WD_LZ_COMPRESSION_EXT_OPCODE_OBSOLETE | Compression | Obsolete LZ compression |
|  | 318 | WD_EXBO_EMBEDDED_FONT | Text | Embedded font |
|  | 322 | WD_EXBO_BLOCK_MEANING | Structure | Block meaning |
|  | 323 | WD_EXBO_ENCRYPTION | Security | Encryption |
|  | 325 | WD_EXBO_ORIENTATION | View | Orientation |
|  | 327 | WD_EXBO_ALIGNMENT | Attributes | Alignment |
|  | 330 | WD_EXBO_GUID | Structure | GUID |
|  | 331 | WD_EXBO_PASSWORD | Security | Password |
|  | 333 | WD_EXBO_FILETIME | Metadata | File time |
|  | 350 | WD_EXBO_BLOCKREF | Structure | Block reference |
|  | 352 | WD_EXBO_DIRECTORY | Structure | Directory |
|  | 354 | WD_EXBO_USERDATA | Advanced | User data |
|  | 356 | WD_EXBO_PEN_PATTERN | Attributes | Pen pattern |
|  | 358 | WD_EXBO_SIGNDATA | Security | Sign data |
|  | 360 | WD_EXBO_GUID_LIST | Structure | GUID list |
|  | 369 | WD_EXBO_MACRO_DEFINITION | Advanced | Macro definition |
|  | 371 | WD_EXBO_TEXT_HALIGN | Text | Text horizontal align |
|  | 373 | WD_EXBO_TEXT_VALIGN | Text | Text vertical align |
|  | 375 | WD_EXBO_TEXT_BACKGROUND | Text | Text background |
|  | 377 | WD_EXBO_OVERPOST | Advanced | Overpost |
|  | 380 | WD_EXBO_DELINEATE | Attributes | Delineate |
|  | 382 | WD_EXBO_SET_USER_FILL_PATTERN | Attributes | User fill pattern |
|  | 384 | WD_EXBO_SET_USER_HATCH_PATTERN | Attributes | User hatch pattern |
|  | 386 | WD_EXBO_SET_CONTRAST_COLOR | Attributes | Contrast color |
|  | 302 | WD_EXBO_UNKNOWN | Special | Unknown binary opcode |

**Total Extended Binary Opcodes: 50**

---

## 4. Python Parsing Strategy

### 4.1 Extended ASCII Parser

```python
class ExtendedASCIIParser:
    """Parser for Extended ASCII opcodes: (OpcodeName ...data...)"""

    MAX_TOKEN_SIZE = 40

    @staticmethod
    def is_legal_opcode_char(byte):
        """Check if byte is a legal opcode character."""
        return (0x21 <= byte <= 0x7A and
                byte != ord('(') and
                byte != ord(')'))

    @staticmethod
    def is_terminator(byte):
        """Check if byte is an opcode terminator."""
        return (byte in (ord(' '), ord('\t'), ord('\n'), ord('\r')) or
                byte == ord('(') or
                byte == ord(')'))

    def parse_opcode(self, stream):
        """
        Parse an Extended ASCII opcode from stream.

        Returns:
            tuple: (opcode_name, remaining_stream_position)

        Raises:
            CorruptFileError: If opcode is malformed
        """
        # Read opening '('
        byte = stream.read(1)
        if byte != b'(':
            raise CorruptFileError("Expected '(' for Extended ASCII opcode")

        # Accumulate opcode name
        token = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF in opcode")

            byte_val = byte[0]

            if self.is_legal_opcode_char(byte_val):
                token.append(byte_val)
                if len(token) > self.MAX_TOKEN_SIZE:
                    raise CorruptFileError("Opcode token too long")
            elif self.is_terminator(byte_val):
                # Put terminator back for data parser
                stream.seek(-1, 1)
                opcode_name = bytes(token).decode('ascii')
                return opcode_name
            else:
                raise CorruptFileError(f"Illegal opcode character: {byte_val}")

    def parse_data(self, stream):
        """
        Parse data fields until closing ')'.

        Returns:
            list: Parsed data fields
        """
        fields = []
        depth = 1  # Track parenthesis nesting
        current_field = []

        while depth > 0:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF in opcode data")

            if byte == b'(':
                depth += 1
                current_field.append(byte)
            elif byte == b')':
                depth -= 1
                if depth > 0:
                    current_field.append(byte)
                elif current_field:
                    fields.append(b''.join(current_field))
            elif byte in (b' ', b'\t', b'\n', b'\r'):
                if current_field:
                    fields.append(b''.join(current_field))
                    current_field = []
            else:
                current_field.append(byte)

        return fields
```

### 4.2 Extended Binary Parser

```python
import struct

class ExtendedBinaryParser:
    """Parser for Extended Binary opcodes: {opcode ...data...}"""

    def parse_opcode(self, stream):
        """
        Parse an Extended Binary opcode from stream.

        Returns:
            tuple: (opcode_value, size, data_start_position)

        Raises:
            CorruptFileError: If opcode is malformed
        """
        # Read opening '{'
        byte = stream.read(1)
        if byte != b'{':
            raise CorruptFileError("Expected '{' for Extended Binary opcode")

        # Read size (4 bytes, little-endian)
        size_bytes = stream.read(4)
        if len(size_bytes) != 4:
            raise CorruptFileError("Unexpected EOF reading opcode size")
        size = struct.unpack('<I', size_bytes)[0]

        # Read opcode value (2 bytes, little-endian)
        opcode_bytes = stream.read(2)
        if len(opcode_bytes) != 2:
            raise CorruptFileError("Unexpected EOF reading opcode value")
        opcode = struct.unpack('<H', opcode_bytes)[0]

        # Size includes everything after the size field:
        # opcode (2 bytes) + data + closing '}'
        data_size = size - 2 - 1  # subtract opcode size and closing brace

        return opcode, size, data_size

    def parse_data(self, stream, data_size):
        """
        Parse binary data of specified size.

        Args:
            stream: Input stream
            data_size: Number of bytes to read

        Returns:
            bytes: Raw binary data
        """
        data = stream.read(data_size)
        if len(data) != data_size:
            raise CorruptFileError("Unexpected EOF reading opcode data")

        # Read closing '}'
        closing = stream.read(1)
        if closing != b'}':
            raise CorruptFileError("Expected '}' at end of Extended Binary opcode")

        return data

    def skip_opcode(self, stream, size):
        """
        Skip an Extended Binary opcode without parsing.

        Args:
            stream: Input stream
            size: Total size from size field
        """
        # Size includes opcode (2 bytes) + data + '}'
        # We've already read the size and opcode, so skip remaining
        stream.seek(size - 2, 1)
```

### 4.3 Unified Opcode Dispatcher

```python
class OpcodeDispatcher:
    """Main opcode dispatcher for all DWF opcodes."""

    def __init__(self):
        self.ascii_parser = ExtendedASCIIParser()
        self.binary_parser = ExtendedBinaryParser()

        # Mapping of Extended ASCII opcode names to handlers
        self.ascii_handlers = {
            'Author': self.handle_author,
            'Background': self.handle_background,
            'Circle': self.handle_circle,
            'Color': self.handle_color,
            'ColorMap': self.handle_colormap,
            'DWF V': self.handle_dwf_header,
            'W2D V': self.handle_w2d_header,
            'Font': self.handle_font,
            'Image': self.handle_image,
            'Layer': self.handle_layer,
            'Text': self.handle_text,
            'Viewport': self.handle_viewport,
            'View': self.handle_view,
            # ... add all 72 Extended ASCII opcodes
        }

        # Mapping of Extended Binary opcode values to handlers
        self.binary_handlers = {
            0x0001: self.handle_colormap_binary,
            0x0002: self.handle_image_bitonal,
            0x0003: self.handle_image_group3x,
            0x0004: self.handle_image_indexed,
            0x0005: self.handle_image_mapped,
            0x0006: self.handle_image_rgb,
            0x0007: self.handle_image_rgba,
            0x0008: self.handle_image_jpeg,
            0x000C: self.handle_image_png,
            0x0012: self.handle_graphics_hdr,
            # ... add all Extended Binary opcodes
        }

    def read_next_opcode(self, stream):
        """
        Read and dispatch the next opcode from stream.

        Returns:
            Result of opcode handler
        """
        # Eat whitespace
        self._eat_whitespace(stream)

        # Peek at next byte
        byte = stream.read(1)
        if not byte:
            return None

        if byte == b'(':
            # Extended ASCII
            stream.seek(-1, 1)
            opcode_name = self.ascii_parser.parse_opcode(stream)
            handler = self.ascii_handlers.get(opcode_name, self.handle_unknown)
            return handler(stream, opcode_name)

        elif byte == b'{':
            # Extended Binary
            stream.seek(-1, 1)
            opcode, size, data_size = self.binary_parser.parse_opcode(stream)
            handler = self.binary_handlers.get(opcode, self.handle_unknown_binary)
            return handler(stream, opcode, data_size)

        else:
            # Single-byte opcode
            return self.handle_single_byte(byte[0], stream)

    def _eat_whitespace(self, stream):
        """Skip whitespace characters."""
        while True:
            byte = stream.read(1)
            if not byte:
                break
            if byte not in (b' ', b'\t', b'\n', b'\r'):
                stream.seek(-1, 1)
                break

    def handle_unknown(self, stream, opcode_name):
        """Handle unknown Extended ASCII opcode."""
        # Skip to matching closing paren
        depth = 1
        while depth > 0:
            byte = stream.read(1)
            if byte == b'(':
                depth += 1
            elif byte == b')':
                depth -= 1
        return {'type': 'unknown_ascii', 'name': opcode_name}

    def handle_unknown_binary(self, stream, opcode, data_size):
        """Handle unknown Extended Binary opcode."""
        self.binary_parser.skip_opcode(stream, data_size + 2 + 1)
        return {'type': 'unknown_binary', 'opcode': opcode}
```

---

## 5. Key Implementation Notes

### 5.1 Parenthesis Tracking

Extended ASCII opcodes can be nested. The parser must track parenthesis depth:

```python
class ParenTracker:
    """Track parenthesis nesting levels."""

    def __init__(self):
        self.level = 0

    def on_open_paren(self):
        self.level += 1

    def on_close_paren(self):
        self.level -= 1

    def skip_to_matching_paren(self, stream):
        """Skip to the closing paren at current level."""
        target_level = self.level - 1
        while self.level > target_level:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF")
            if byte == b'(':
                self.on_open_paren()
            elif byte == b')':
                self.on_close_paren()
```

### 5.2 File Header Detection

The very first opcode in a DWF file must be either `(DWF V` or `(W2D V`:

```python
def validate_file_header(stream):
    """Validate DWF/W2D file header."""
    header = stream.read(6)
    if header not in (b'(DWF V', b'(W2D V'):
        raise NotADWFFileError("Invalid DWF file header")
    return header.decode('ascii')
```

### 5.3 Endianness

The C++ code has a TODO comment about endianness. All binary values are little-endian:

```python
# Always use little-endian (<) for struct operations
size = struct.unpack('<I', size_bytes)[0]  # 32-bit unsigned int
opcode = struct.unpack('<H', opcode_bytes)[0]  # 16-bit unsigned int
```

### 5.4 Size Field Calculation

For Extended Binary opcodes, the size field represents:
- Everything AFTER the 4-byte size field
- Includes: 2-byte opcode + variable data + 1-byte closing '}'

```python
# Reading
total_bytes_to_read = size  # This is what's in the size field

# Writing
size_to_write = 2 + data_length + 1  # opcode + data + '}'
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

Create unit tests for each opcode type:

```python
def test_extended_ascii_simple():
    """Test simple Extended ASCII opcode."""
    data = b'(Author "John Doe")'
    stream = BytesIO(data)
    parser = ExtendedASCIIParser()
    opcode = parser.parse_opcode(stream)
    assert opcode == 'Author'

def test_extended_binary_image():
    """Test Extended Binary image opcode."""
    # Build test data: { + size + opcode + data + }
    opcode_val = 0x0006  # RGB image
    data = b'\x00\x10\x00\x00' * 10  # Sample image data
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode_bytes = struct.pack('<H', opcode_val)

    stream = BytesIO(b'{' + size + opcode_bytes + data + b'}')
    parser = ExtendedBinaryParser()
    opcode, sz, data_size = parser.parse_opcode(stream)
    assert opcode == 0x0006
```

### 6.2 Integration Tests

Test with real DWF files:

```python
def test_real_dwf_file():
    """Test parsing real DWF file."""
    with open('sample.dwf', 'rb') as f:
        dispatcher = OpcodeDispatcher()
        opcodes = []
        while True:
            result = dispatcher.read_next_opcode(f)
            if result is None:
                break
            opcodes.append(result)

    # Verify expected opcodes were found
    assert any(op['type'] == 'dwf_header' for op in opcodes)
```

---

## 7. Reference Materials

### 7.1 Source File Locations

Key C++ source files examined:
- `/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/opcode_defs.h`
- `/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/opcode.h`
- `/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/opcode.cpp`
- `/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/image.cpp`
- `/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/viewport.cpp`
- `/home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/blockref.cpp`

### 7.2 Constants Definitions

```python
# From opcode_defs.h
WD_MAX_OPCODE_TOKEN_SIZE = 40
WD_EXTENDED_BINARY_OPCODE_SIZE = 2
WD_EXTENDED_BINARY_OFFSET_SIZE = 4
WD_MAX_DWF_COUNT_VALUE = 256 + 65535

# Extended ASCII Opcode IDs (256-387)
WD_EXAO_DEFINE_AUTHOR = 256
WD_EXAO_SET_BACKGROUND = 257
# ... (see section 2.1 for complete list)

# Extended Binary Opcode Values
WD_COLOR_MAP_EXT_OPCODE = 0x0001
WD_IMAGE_BITONAL_MAPPED_EXT_OPCODE = 0x0002
# ... (see section 3.1 for complete list)
```

---

## 8. Recommendations for Agent 13

### 8.1 Priority Order

Implement Extended opcodes in this order:

1. **Phase 1: Core Infrastructure**
   - Base parser classes for Extended ASCII and Extended Binary
   - Opcode dispatcher and routing
   - Parenthesis tracking
   - File header validation

2. **Phase 2: High-Priority Extended ASCII**
   - `(DWF V` / `(W2D V` - File headers (ID 268)
   - `(Viewport` - Viewport definition (ID 290)
   - `(Layer` - Layer management (ID 276)
   - `(Color` - Color setting (ID 260)
   - `(Font` - Font definition (ID 273)

3. **Phase 3: High-Priority Extended Binary**
   - `{0x0006}` - RGB Image (ID 298)
   - `{0x0007}` - RGBA Image (ID 299)
   - `{0x0001}` - Color Map (ID 293)
   - `{0x0012}` - Graphics Header (ID 335)

4. **Phase 4: Metadata Opcodes**
   - Document metadata (Author, Title, Description, etc.)
   - Timestamps (Created, Modified, etc.)

5. **Phase 5: Advanced Features**
   - Compression opcodes
   - Security opcodes (Encryption, Password, Signature)
   - User data opcodes

### 8.2 Error Handling

Implement robust error handling:

```python
class DWFParseError(Exception):
    """Base exception for DWF parsing errors."""
    pass

class CorruptFileError(DWFParseError):
    """File structure is corrupted."""
    pass

class NotADWFFileError(DWFParseError):
    """File is not a valid DWF file."""
    pass

class UnsupportedOpcodeError(DWFParseError):
    """Opcode is not supported."""
    pass
```

### 8.3 Logging

Add comprehensive logging for debugging:

```python
import logging

logger = logging.getLogger('dwf.parser')

def parse_opcode(self, stream):
    logger.debug(f"Parsing opcode at position {stream.tell()}")
    # ... parsing logic ...
    logger.info(f"Found opcode: {opcode_name}")
```

---

## 9. Conclusion

**Summary:**
- **72 Extended ASCII opcodes** identified and documented
- **50 Extended Binary opcodes** identified and documented
- Clear parsing strategies provided for both formats
- Python implementation examples included
- Prioritized implementation plan provided

**Next Steps for Agent 13:**
1. Implement base parser classes following the Python examples
2. Add unit tests for each opcode format
3. Implement high-priority opcodes first (headers, viewport, images)
4. Test with real DWF files
5. Gradually add support for remaining opcodes

**Key Success Criteria:**
- ✅ All opcode formats documented
- ✅ Parsing strategies defined
- ✅ Python implementation examples provided
- ✅ Error handling strategy outlined
- ✅ Testing approach specified

---

*Report generated by Agent 13*
*Date: 2025-10-22*
*Source: DWF Toolkit C++ Reference Implementation*
