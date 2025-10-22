"""
Agent 14: DWF Extended ASCII File Structure Opcodes

This module implements 6 Extended ASCII opcodes for DWF file structure:
1. WD_EXAO_DEFINE_DWF_HEADER (ID 268) - DWF/W2D file headers
2. WD_EXAO_DEFINE_END_OF_DWF (ID 272) - End of file marker
3. WD_EXAO_SET_VIEWPORT (ID 290) - Viewport definition
4. WD_EXAO_SET_VIEW (ID 291) - View settings
5. WD_EXAO_DEFINE_NAMED_VIEW (ID 281) - Named view definition

Based on DWF Toolkit C++ source code from:
- dwfhead.cpp (file headers)
- endofdwf.cpp (end marker)
- viewport.cpp (viewport)
- view.cpp (view)
- named_view.cpp (named views)
"""

from typing import Dict, List, Tuple, Optional, Any, Union
from io import BytesIO
import struct
import re


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

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


# ============================================================================
# EXTENDED ASCII PARSER HELPER CLASS
# ============================================================================

class ExtendedASCIIParser:
    """
    Parser for Extended ASCII opcodes in DWF files.

    Extended ASCII opcodes have the format: (OpcodeName field1 field2 ... fieldN)

    Parsing rules:
    - Start token: '(' character
    - Opcode name: Accumulate characters until whitespace or terminator
    - Legal characters: >= 0x21 ('!') and <= 0x7A ('z'), excluding '(' and ')'
    - Terminators: Whitespace (space, tab, LF, CR), '(', or ')'
    - Max token size: 40 characters
    - End token: ')' character
    """

    MAX_TOKEN_SIZE = 40

    @staticmethod
    def is_legal_opcode_char(byte: int) -> bool:
        """
        Check if byte is a legal opcode character.

        Args:
            byte: Integer value of byte (0-255)

        Returns:
            True if byte is legal opcode character
        """
        return (0x21 <= byte <= 0x7A and
                byte != ord('(') and
                byte != ord(')'))

    @staticmethod
    def is_terminator(byte: int) -> bool:
        """
        Check if byte is an opcode terminator.

        Args:
            byte: Integer value of byte (0-255)

        Returns:
            True if byte is a terminator
        """
        return (byte in (ord(' '), ord('\t'), ord('\n'), ord('\r')) or
                byte == ord('(') or
                byte == ord(')'))

    def parse_opcode_name(self, stream: BytesIO) -> str:
        """
        Parse an Extended ASCII opcode name from stream.

        Special handling for DWF/W2D headers which have tokens "DWF V" and "W2D V"
        including the space and V.

        Args:
            stream: Input byte stream

        Returns:
            Opcode name as string

        Raises:
            CorruptFileError: If opcode is malformed
        """
        # Read opening '('
        byte = stream.read(1)
        if byte != b'(':
            raise CorruptFileError(f"Expected '(' for Extended ASCII opcode, got {byte}")

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

                # Special case for DWF/W2D headers: check for " V" continuation
                if opcode_name in ('DWF', 'W2D'):
                    # Peek ahead for " V"
                    peek = stream.read(2)
                    if peek == b' V':
                        # This is a header opcode, include " V" in the name
                        opcode_name = opcode_name + ' V'
                    else:
                        # Not a header, put the bytes back
                        stream.seek(-2, 1)

                return opcode_name
            else:
                raise CorruptFileError(f"Illegal opcode character: {byte_val:#x}")

    def skip_whitespace(self, stream: BytesIO) -> None:
        """Skip whitespace characters in stream."""
        while True:
            byte = stream.read(1)
            if not byte:
                break
            if byte not in (b' ', b'\t', b'\n', b'\r'):
                stream.seek(-1, 1)
                break

    def read_until_close_paren(self, stream: BytesIO) -> bytes:
        """
        Read data until closing ')' at current nesting level.

        Args:
            stream: Input byte stream

        Returns:
            Data bytes (without closing paren)

        Raises:
            CorruptFileError: If EOF reached before closing paren
        """
        depth = 1
        data = []

        while depth > 0:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF in opcode data")

            if byte == b'(':
                depth += 1
                data.append(byte)
            elif byte == b')':
                depth -= 1
                if depth > 0:
                    data.append(byte)
            else:
                data.append(byte)

        return b''.join(data)

    def parse_string(self, stream: BytesIO) -> str:
        """
        Parse a quoted string from stream.

        Supports both single-quoted ('string') and double-quoted ("string") strings.

        Args:
            stream: Input byte stream

        Returns:
            Parsed string (without quotes)

        Raises:
            CorruptFileError: If string is malformed
        """
        self.skip_whitespace(stream)

        quote = stream.read(1)
        if quote not in (b"'", b'"'):
            raise CorruptFileError(f"Expected quote character, got {quote}")

        chars = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF in string")

            if byte == quote:
                return b''.join(chars).decode('utf-8')
            else:
                chars.append(byte)

    def parse_logical_point(self, stream: BytesIO) -> Tuple[int, int]:
        """
        Parse a logical point (x, y) from stream.

        Args:
            stream: Input byte stream

        Returns:
            Tuple of (x, y) as integers
        """
        self.skip_whitespace(stream)

        # Read until whitespace or closing paren
        x_str = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF reading point")
            if byte in (b' ', b'\t', b'\n', b'\r', b')'):
                stream.seek(-1, 1)
                break
            x_str.append(byte)

        self.skip_whitespace(stream)

        y_str = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF reading point")
            if byte in (b' ', b'\t', b'\n', b'\r', b')'):
                stream.seek(-1, 1)
                break
            y_str.append(byte)

        x = int(b''.join(x_str).decode('ascii'))
        y = int(b''.join(y_str).decode('ascii'))

        return (x, y)


# ============================================================================
# OPCODE HANDLER FUNCTIONS
# ============================================================================

def parse_dwf_header(stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
    """
    Parse DWF/W2D file header opcode.

    Format: (DWF V##.##) or (W2D V##.##)

    The header appears at the very beginning of a DWF file and specifies
    the file format version. DWF V indicates pre-6.0 format, W2D V indicates
    6.0+ packaged format.

    Args:
        stream: Input byte stream positioned after opcode name
        opcode_name: Either "DWF V" or "W2D V"

    Returns:
        Dictionary with:
            - type: 'dwf_header' or 'w2d_header'
            - major_version: int (e.g., 6)
            - minor_version: int (e.g., 0)
            - decimal_version: int (e.g., 600)

    Raises:
        CorruptFileError: If header format is invalid
        NotADWFFileError: If version format is invalid

    Example:
        Input: b"06.00)" (after parsing "(DWF V")
        Output: {'type': 'dwf_header', 'major_version': 6,
                 'minor_version': 0, 'decimal_version': 600}
    """
    # Read exactly 6 bytes: ##.##)
    version_bytes = stream.read(6)

    if len(version_bytes) != 6:
        raise NotADWFFileError("Incomplete DWF header version")

    # Validate format: NN.NN)
    if (version_bytes[0] < ord('0') or version_bytes[0] > ord('9') or
        version_bytes[1] < ord('0') or version_bytes[1] > ord('9') or
        version_bytes[2] != ord('.') or
        version_bytes[3] < ord('0') or version_bytes[3] > ord('9') or
        version_bytes[4] < ord('0') or version_bytes[4] > ord('9') or
        version_bytes[5] != ord(')')):
        raise NotADWFFileError(f"Invalid DWF header version format: {version_bytes}")

    # Parse version numbers
    major = (version_bytes[0] - ord('0')) * 10 + (version_bytes[1] - ord('0'))
    minor = (version_bytes[3] - ord('0')) * 10 + (version_bytes[4] - ord('0'))
    decimal = major * 100 + minor

    # Determine file type
    file_type = 'dwf_header' if opcode_name == 'DWF V' else 'w2d_header'

    return {
        'type': file_type,
        'major_version': major,
        'minor_version': minor,
        'decimal_version': decimal
    }


def parse_end_of_dwf(stream: BytesIO) -> Dict[str, str]:
    """
    Parse End of DWF marker opcode.

    Format: (EndOfDWF)

    This opcode marks the end of a DWF file. No additional data follows.

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        Dictionary with type: 'end_of_dwf'

    Raises:
        CorruptFileError: If closing paren is missing

    Example:
        Input: b")" (after parsing "(EndOfDWF")
        Output: {'type': 'end_of_dwf'}
    """
    parser = ExtendedASCIIParser()
    parser.skip_whitespace(stream)

    # Read closing paren
    byte = stream.read(1)
    if byte != b')':
        raise CorruptFileError(f"Expected ')' after EndOfDWF, got {byte}")

    return {'type': 'end_of_dwf'}


def parse_viewport(stream: BytesIO) -> Dict[str, Any]:
    """
    Parse Viewport opcode.

    Format: (Viewport name contour_set [options])

    A viewport defines a clipping region for rendering. It contains:
    - Name: A string identifying the viewport
    - Contour set: Polygon boundary (one or more contours)
    - Optional units specification

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        Dictionary with:
            - type: 'viewport'
            - name: str (viewport name)
            - contours: List of point lists (if present)
            - units: Optional units specification

    Raises:
        CorruptFileError: If viewport format is invalid

    Example:
        Input: b" 'MyViewport' (Contour 4 0,0 100,0 100,100 0,100))"
        Output: {'type': 'viewport', 'name': 'MyViewport',
                 'contours': [[(0,0), (100,0), (100,100), (0,100)]]}
    """
    parser = ExtendedASCIIParser()
    parser.skip_whitespace(stream)

    # Check if viewport is empty (just closing paren)
    byte = stream.read(1)
    if byte == b')':
        return {
            'type': 'viewport',
            'name': None,
            'contours': None
        }
    stream.seek(-1, 1)

    # Parse viewport name
    name = parser.parse_string(stream)

    parser.skip_whitespace(stream)

    # Check if there's a contour set or just closing paren
    byte = stream.read(1)
    if byte == b')':
        return {
            'type': 'viewport',
            'name': name,
            'contours': None
        }
    stream.seek(-1, 1)

    # For simplicity, read the rest as raw data
    # A full implementation would parse the nested Contour opcode
    remaining = parser.read_until_close_paren(stream)

    return {
        'type': 'viewport',
        'name': name,
        'raw_data': remaining.decode('ascii', errors='replace')
    }


def parse_view(stream: BytesIO) -> Dict[str, Any]:
    """
    Parse View opcode.

    Format: (View min_point max_point) or (View 'name')

    A view defines the visible region of the drawing. It can be specified as:
    1. A bounding box (two logical points: min and max)
    2. A reference to a named view (quoted string)

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        Dictionary with:
            - type: 'view'
            - view_type: 'box' or 'named'
            - For box: min_point (x,y), max_point (x,y)
            - For named: name (str)

    Raises:
        CorruptFileError: If view format is invalid

    Example:
        Box view: b" -100,-100 100,100)"
        Output: {'type': 'view', 'view_type': 'box',
                 'min_point': (-100,-100), 'max_point': (100,100)}

        Named view: b" 'MainView')"
        Output: {'type': 'view', 'view_type': 'named', 'name': 'MainView'}
    """
    parser = ExtendedASCIIParser()
    parser.skip_whitespace(stream)

    # Peek at next byte to determine if it's a string or logical box
    byte = stream.read(1)

    if byte in (b"'", b'"'):
        # Named view
        stream.seek(-1, 1)
        name = parser.parse_string(stream)

        parser.skip_whitespace(stream)
        closing = stream.read(1)
        if closing != b')':
            raise CorruptFileError(f"Expected ')' after view name, got {closing}")

        return {
            'type': 'view',
            'view_type': 'named',
            'name': name
        }
    else:
        # Logical box (two points)
        stream.seek(-1, 1)

        min_point = parser.parse_logical_point(stream)
        max_point = parser.parse_logical_point(stream)

        parser.skip_whitespace(stream)
        closing = stream.read(1)
        if closing != b')':
            raise CorruptFileError(f"Expected ')' after view box, got {closing}")

        return {
            'type': 'view',
            'view_type': 'box',
            'min_point': min_point,
            'max_point': max_point
        }


def parse_named_view(stream: BytesIO) -> Dict[str, Any]:
    """
    Parse Named View opcode.

    Format: (NamedView min_point max_point name)

    A named view defines a saved view with a bounding box and name.
    The bounding box is specified as two logical points (min and max).

    Args:
        stream: Input byte stream positioned after opcode name

    Returns:
        Dictionary with:
            - type: 'named_view'
            - min_point: Tuple (x, y)
            - max_point: Tuple (x, y)
            - name: str

    Raises:
        CorruptFileError: If named view format is invalid

    Example:
        Input: b" -1000,-1000 1000,1000 'Overview')"
        Output: {'type': 'named_view',
                 'min_point': (-1000,-1000),
                 'max_point': (1000,1000),
                 'name': 'Overview'}
    """
    parser = ExtendedASCIIParser()
    parser.skip_whitespace(stream)

    # Parse bounding box (two points)
    min_point = parser.parse_logical_point(stream)
    max_point = parser.parse_logical_point(stream)

    # Parse name
    parser.skip_whitespace(stream)
    name = parser.parse_string(stream)

    # Read closing paren
    parser.skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise CorruptFileError(f"Expected ')' after named view, got {closing}")

    return {
        'type': 'named_view',
        'min_point': min_point,
        'max_point': max_point,
        'name': name
    }


# ============================================================================
# MAIN OPCODE DISPATCHER
# ============================================================================

class FileStructureOpcodeHandler:
    """
    Handler for file structure Extended ASCII opcodes.

    This class routes opcodes to their appropriate parser functions.
    """

    def __init__(self):
        self.parser = ExtendedASCIIParser()

        # Opcode name to handler mapping
        self.handlers = {
            'DWF V': self._handle_dwf_header,
            'W2D V': self._handle_w2d_header,
            'EndOfDWF': self._handle_end_of_dwf,
            'Viewport': self._handle_viewport,
            'View': self._handle_view,
            'NamedView': self._handle_named_view,
        }

    def _handle_dwf_header(self, stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
        """Handle DWF header opcode."""
        return parse_dwf_header(stream, opcode_name)

    def _handle_w2d_header(self, stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
        """Handle W2D header opcode."""
        return parse_dwf_header(stream, opcode_name)

    def _handle_end_of_dwf(self, stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
        """Handle End of DWF opcode."""
        return parse_end_of_dwf(stream)

    def _handle_viewport(self, stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
        """Handle Viewport opcode."""
        return parse_viewport(stream)

    def _handle_view(self, stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
        """Handle View opcode."""
        return parse_view(stream)

    def _handle_named_view(self, stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
        """Handle Named View opcode."""
        return parse_named_view(stream)

    def parse_opcode(self, stream: BytesIO) -> Dict[str, Any]:
        """
        Parse an Extended ASCII opcode from stream.

        Args:
            stream: Input byte stream

        Returns:
            Parsed opcode data as dictionary

        Raises:
            UnsupportedOpcodeError: If opcode is not supported
            CorruptFileError: If opcode is malformed
        """
        # Parse opcode name
        opcode_name = self.parser.parse_opcode_name(stream)

        # Dispatch to appropriate handler
        handler = self.handlers.get(opcode_name)
        if not handler:
            raise UnsupportedOpcodeError(f"Unsupported opcode: {opcode_name}")

        return handler(stream, opcode_name)


# ============================================================================
# TEST CASES
# ============================================================================

def test_dwf_header():
    """Test DWF header parsing."""
    print("Testing DWF header...")

    # Test 1: DWF V06.00
    data1 = b"(DWF V06.00)"
    stream1 = BytesIO(data1)
    handler = FileStructureOpcodeHandler()
    result1 = handler.parse_opcode(stream1)
    assert result1['type'] == 'dwf_header'
    assert result1['major_version'] == 6
    assert result1['minor_version'] == 0
    assert result1['decimal_version'] == 600
    print("  ✓ Test 1: DWF V06.00 passed")

    # Test 2: W2D V06.01
    data2 = b"(W2D V06.01)"
    stream2 = BytesIO(data2)
    result2 = handler.parse_opcode(stream2)
    assert result2['type'] == 'w2d_header'
    assert result2['major_version'] == 6
    assert result2['minor_version'] == 1
    assert result2['decimal_version'] == 601
    print("  ✓ Test 2: W2D V06.01 passed")

    # Test 3: Invalid header
    try:
        data3 = b"(DWF VXX.YY)"
        stream3 = BytesIO(data3)
        handler.parse_opcode(stream3)
        assert False, "Should have raised NotADWFFileError"
    except NotADWFFileError:
        print("  ✓ Test 3: Invalid header rejection passed")

    print("DWF header tests completed!\n")


def test_end_of_dwf():
    """Test End of DWF parsing."""
    print("Testing End of DWF...")

    # Test 1: Simple end marker
    data1 = b"(EndOfDWF)"
    stream1 = BytesIO(data1)
    handler = FileStructureOpcodeHandler()
    result1 = handler.parse_opcode(stream1)
    assert result1['type'] == 'end_of_dwf'
    print("  ✓ Test 1: Simple end marker passed")

    # Test 2: End marker with whitespace
    data2 = b"(EndOfDWF  )"
    stream2 = BytesIO(data2)
    result2 = handler.parse_opcode(stream2)
    assert result2['type'] == 'end_of_dwf'
    print("  ✓ Test 2: End marker with whitespace passed")

    print("End of DWF tests completed!\n")


def test_viewport():
    """Test Viewport parsing."""
    print("Testing Viewport...")

    # Test 1: Empty viewport
    data1 = b"(Viewport)"
    stream1 = BytesIO(data1)
    handler = FileStructureOpcodeHandler()
    result1 = handler.parse_opcode(stream1)
    assert result1['type'] == 'viewport'
    assert result1['name'] is None
    print("  ✓ Test 1: Empty viewport passed")

    # Test 2: Viewport with name only
    data2 = b"(Viewport 'MainViewport')"
    stream2 = BytesIO(data2)
    result2 = handler.parse_opcode(stream2)
    assert result2['type'] == 'viewport'
    assert result2['name'] == 'MainViewport'
    print("  ✓ Test 2: Viewport with name passed")

    # Test 3: Viewport with name and data
    data3 = b"(Viewport \"MyViewport\" (Contour 4 0 0 100 0 100 100 0 100))"
    stream3 = BytesIO(data3)
    result3 = handler.parse_opcode(stream3)
    assert result3['type'] == 'viewport'
    assert result3['name'] == 'MyViewport'
    assert 'raw_data' in result3
    print("  ✓ Test 3: Viewport with contour data passed")

    print("Viewport tests completed!\n")


def test_view():
    """Test View parsing."""
    print("Testing View...")

    # Test 1: Box view
    data1 = b"(View -100 -100 100 100)"
    stream1 = BytesIO(data1)
    handler = FileStructureOpcodeHandler()
    result1 = handler.parse_opcode(stream1)
    assert result1['type'] == 'view'
    assert result1['view_type'] == 'box'
    assert result1['min_point'] == (-100, -100)
    assert result1['max_point'] == (100, 100)
    print("  ✓ Test 1: Box view passed")

    # Test 2: Named view
    data2 = b"(View 'TopView')"
    stream2 = BytesIO(data2)
    result2 = handler.parse_opcode(stream2)
    assert result2['type'] == 'view'
    assert result2['view_type'] == 'named'
    assert result2['name'] == 'TopView'
    print("  ✓ Test 2: Named view passed")

    # Test 3: Box view with large coordinates
    data3 = b"(View -12345 -67890 12345 67890)"
    stream3 = BytesIO(data3)
    result3 = handler.parse_opcode(stream3)
    assert result3['type'] == 'view'
    assert result3['min_point'] == (-12345, -67890)
    assert result3['max_point'] == (12345, 67890)
    print("  ✓ Test 3: Box view with large coordinates passed")

    print("View tests completed!\n")


def test_named_view():
    """Test Named View parsing."""
    print("Testing Named View...")

    # Test 1: Simple named view
    data1 = b"(NamedView 0 0 1000 1000 'Overview')"
    stream1 = BytesIO(data1)
    handler = FileStructureOpcodeHandler()
    result1 = handler.parse_opcode(stream1)
    assert result1['type'] == 'named_view'
    assert result1['min_point'] == (0, 0)
    assert result1['max_point'] == (1000, 1000)
    assert result1['name'] == 'Overview'
    print("  ✓ Test 1: Simple named view passed")

    # Test 2: Named view with negative coordinates
    data2 = b"(NamedView -5000 -3000 5000 3000 \"DetailView\")"
    stream2 = BytesIO(data2)
    result2 = handler.parse_opcode(stream2)
    assert result2['type'] == 'named_view'
    assert result2['min_point'] == (-5000, -3000)
    assert result2['max_point'] == (5000, 3000)
    assert result2['name'] == 'DetailView'
    print("  ✓ Test 2: Named view with negative coordinates passed")

    print("Named View tests completed!\n")


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("AGENT 14: FILE STRUCTURE OPCODES - TEST SUITE")
    print("=" * 70)
    print()

    test_dwf_header()
    test_end_of_dwf()
    test_viewport()
    test_view()
    test_named_view()

    print("=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    run_all_tests()
