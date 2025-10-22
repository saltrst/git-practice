#!/usr/bin/env python3
"""
Agent 15: DWF Extended ASCII Metadata Opcodes (1/3) - Python Translation

This module provides Python implementations for 6 DWF Extended ASCII metadata opcodes
that store document information such as author, title, subject, description, comments,
and keywords.

Opcodes Implemented:
    1. WD_EXAO_DEFINE_AUTHOR (256)      - (Author "...") - Document author
    2. WD_EXAO_DEFINE_TITLE (303)       - (Title "...") - Document title
    3. WD_EXAO_DEFINE_SUBJECT (304)     - (Subject "...") - Document subject
    4. WD_EXAO_DEFINE_DESCRIPTION (269) - (Description "...") - Document description
    5. WD_EXAO_DEFINE_COMMENTS (262)    - (Comment* "...") - Comments (prefix match)
    6. WD_EXAO_DEFINE_KEYWORDS (275)    - (Keywords "...") - Search keywords

Format: All are Extended ASCII with quoted string data after opcode name.
    Example: (Author "John Doe")

Source Files:
    - informational.cpp: Common implementation for all metadata opcodes
    - informational.h: Class declarations and macro definitions
    - wtstring.cpp: String serialization/materialization

Author: Agent 15
Date: 2025-10-22
"""

import io
import struct
from typing import Optional, Dict, Any, Tuple
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

# Opcode IDs from opcode_defs.h
WD_EXAO_DEFINE_AUTHOR = 256
WD_EXAO_DEFINE_COMMENTS = 262
WD_EXAO_DEFINE_DESCRIPTION = 269
WD_EXAO_DEFINE_KEYWORDS = 275
WD_EXAO_DEFINE_TITLE = 303
WD_EXAO_DEFINE_SUBJECT = 304

# Parser constants
MAX_OPCODE_TOKEN_SIZE = 40


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DWFParseError(Exception):
    """Base exception for DWF parsing errors."""
    pass


class CorruptFileError(DWFParseError):
    """File structure is corrupted."""
    pass


class UnexpectedEOFError(DWFParseError):
    """Unexpected end of file."""
    pass


# =============================================================================
# EXTENDED ASCII PARSER
# =============================================================================

class ExtendedASCIIParser:
    """
    Parser for Extended ASCII opcodes with format: (OpcodeName ...data...)

    This parser handles the parenthesized opcode format used in DWF files
    for human-readable opcodes.
    """

    MAX_TOKEN_SIZE = MAX_OPCODE_TOKEN_SIZE

    @staticmethod
    def is_legal_opcode_char(byte_val: int) -> bool:
        """
        Check if byte is a legal opcode character.

        Legal characters are in range 0x21 ('!') to 0x7A ('z'),
        excluding '(' and ')'.

        Args:
            byte_val: Integer value of byte (0-255)

        Returns:
            True if byte is legal opcode character
        """
        return (0x21 <= byte_val <= 0x7A and
                byte_val != ord('(') and
                byte_val != ord(')'))

    @staticmethod
    def is_terminator(byte_val: int) -> bool:
        """
        Check if byte is an opcode terminator.

        Terminators are whitespace (space, tab, LF, CR) or parentheses.

        Args:
            byte_val: Integer value of byte (0-255)

        Returns:
            True if byte is a terminator
        """
        return (byte_val in (ord(' '), ord('\t'), ord('\n'), ord('\r')) or
                byte_val == ord('(') or
                byte_val == ord(')'))

    @classmethod
    def parse_opcode_name(cls, stream: io.BytesIO) -> str:
        """
        Parse an Extended ASCII opcode name from stream.

        Expects stream positioned at opening '(' and reads until whitespace
        or terminator is encountered.

        Args:
            stream: Input byte stream

        Returns:
            Opcode name as string

        Raises:
            CorruptFileError: If opcode is malformed
            UnexpectedEOFError: If EOF reached unexpectedly
        """
        # Read opening '('
        byte = stream.read(1)
        if not byte:
            raise UnexpectedEOFError("Expected '(' for Extended ASCII opcode")
        if byte != b'(':
            raise CorruptFileError(f"Expected '(' for Extended ASCII opcode, got {byte!r}")

        # Accumulate opcode name
        token = []
        while True:
            byte = stream.read(1)
            if not byte:
                raise UnexpectedEOFError("Unexpected EOF in opcode name")

            byte_val = byte[0]

            if cls.is_legal_opcode_char(byte_val):
                token.append(byte_val)
                if len(token) > cls.MAX_TOKEN_SIZE:
                    raise CorruptFileError(
                        f"Opcode token too long (>{cls.MAX_TOKEN_SIZE} chars)"
                    )
            elif cls.is_terminator(byte_val):
                # Put terminator back for data parser
                stream.seek(-1, 1)
                if not token:
                    raise CorruptFileError("Empty opcode name")
                opcode_name = bytes(token).decode('ascii')
                return opcode_name
            else:
                raise CorruptFileError(
                    f"Illegal opcode character: 0x{byte_val:02X} ({chr(byte_val)!r})"
                )

    @staticmethod
    def eat_whitespace(stream: io.BytesIO) -> None:
        """
        Skip whitespace characters (space, tab, LF, CR).

        Args:
            stream: Input byte stream
        """
        while True:
            byte = stream.read(1)
            if not byte:
                break
            if byte not in (b' ', b'\t', b'\n', b'\r'):
                stream.seek(-1, 1)
                break

    @staticmethod
    def parse_quoted_string(stream: io.BytesIO) -> str:
        """
        Parse a quoted string from stream.

        Supports both ASCII strings ("...") and binary encoded strings ({...}).
        Handles escape sequences and special characters.

        Args:
            stream: Input byte stream

        Returns:
            Parsed string value

        Raises:
            CorruptFileError: If string format is invalid
            UnexpectedEOFError: If EOF reached unexpectedly
        """
        # Peek at first character to determine string type
        first_byte = stream.read(1)
        if not first_byte:
            raise UnexpectedEOFError("Expected string data")

        if first_byte == b'"':
            # Quoted string - collect all bytes first, then decode
            byte_buffer = []
            escaped = False

            while True:
                byte = stream.read(1)
                if not byte:
                    raise UnexpectedEOFError("Unterminated quoted string")

                if escaped:
                    # Handle escape sequences
                    if byte == b'n':
                        byte_buffer.append(ord('\n'))
                    elif byte == b't':
                        byte_buffer.append(ord('\t'))
                    elif byte == b'r':
                        byte_buffer.append(ord('\r'))
                    elif byte == b'\\':
                        byte_buffer.append(ord('\\'))
                    elif byte == b'"':
                        byte_buffer.append(ord('"'))
                    else:
                        # Unknown escape, keep as-is
                        byte_buffer.append(ord('\\'))
                        byte_buffer.append(byte[0])
                    escaped = False
                elif byte == b'\\':
                    escaped = True
                elif byte == b'"':
                    # End of string - decode entire buffer as UTF-8
                    return bytes(byte_buffer).decode('utf-8', errors='replace')
                else:
                    # Regular character - accumulate bytes
                    byte_buffer.append(byte[0])

        elif first_byte == b'{':
            # Binary encoded string (UTF-16 or other encoding)
            # Format: { + 4-byte length + UTF-16 data + }

            # Read length (4 bytes, little-endian)
            length_bytes = stream.read(4)
            if len(length_bytes) != 4:
                raise UnexpectedEOFError("Incomplete binary string length")

            length = struct.unpack('<I', length_bytes)[0]

            # Read string data
            data = stream.read(length)
            if len(data) != length:
                raise UnexpectedEOFError("Incomplete binary string data")

            # Read closing '}'
            closing = stream.read(1)
            if closing != b'}':
                raise CorruptFileError(f"Expected '}}' after binary string, got {closing!r}")

            # Decode as UTF-16LE (DWF uses WT_Unsigned_Integer16 for Unicode)
            try:
                return data.decode('utf-16le')
            except UnicodeDecodeError as e:
                raise CorruptFileError(f"Invalid UTF-16 string data: {e}")

        else:
            # Unquoted string (read until whitespace or ')')
            stream.seek(-1, 1)  # Put back first byte
            chars = []

            while True:
                byte = stream.read(1)
                if not byte:
                    break

                byte_val = byte[0]

                if byte_val in (ord(' '), ord('\t'), ord('\n'), ord('\r'), ord(')')):
                    stream.seek(-1, 1)  # Put back terminator
                    break

                chars.append(byte.decode('utf-8', errors='replace'))

            return ''.join(chars)

    @staticmethod
    def skip_to_matching_paren(stream: io.BytesIO) -> None:
        """
        Skip to the closing parenthesis that matches the current opcode.

        Handles nested parentheses correctly.

        Args:
            stream: Input byte stream

        Raises:
            UnexpectedEOFError: If EOF reached before finding closing paren
        """
        depth = 1

        while depth > 0:
            byte = stream.read(1)
            if not byte:
                raise UnexpectedEOFError("Unmatched opening parenthesis")

            if byte == b'(':
                depth += 1
            elif byte == b')':
                depth -= 1


# =============================================================================
# METADATA OPCODE HANDLERS
# =============================================================================

class MetadataOpcode:
    """
    Base class for metadata opcodes.

    All metadata opcodes (Author, Title, Subject, etc.) share the same
    structure and behavior, differing only in their opcode name and ID.
    """

    # Subclasses should override these
    OPCODE_ID: int = 0
    OPCODE_NAME: str = ""
    DESCRIPTION: str = ""

    def __init__(self, value: str = ""):
        """
        Initialize metadata opcode with string value.

        Args:
            value: Metadata string value
        """
        self.value = value
        self.materialized = False

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}('{self.value}')"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}(value={self.value!r})"

    def serialize(self) -> bytes:
        """
        Serialize metadata opcode to DWF format.

        Format: (OpcodeName "value")

        Returns:
            Serialized bytes
        """
        if not self.value:
            return b''

        # Escape special characters in string
        escaped = self.value.replace('\\', '\\\\').replace('"', '\\"')

        # Build opcode: (OpcodeName "value")
        result = f'({self.OPCODE_NAME} "{escaped}")'.encode('utf-8')
        return result

    def materialize(self, stream: io.BytesIO) -> None:
        """
        Parse metadata opcode from DWF stream.

        Expected format: (OpcodeName "value")
        Stream should be positioned at opening '('.

        Args:
            stream: Input byte stream

        Raises:
            CorruptFileError: If opcode format is invalid
        """
        parser = ExtendedASCIIParser()

        # Parse opcode name
        opcode_name = parser.parse_opcode_name(stream)

        # Verify opcode name matches (support prefix matching for Comments)
        if not self._matches_opcode_name(opcode_name):
            raise CorruptFileError(
                f"Expected opcode '{self.OPCODE_NAME}', got '{opcode_name}'"
            )

        # Eat whitespace before string
        parser.eat_whitespace(stream)

        # Parse string value
        self.value = parser.parse_quoted_string(stream)

        # Skip to closing paren
        parser.eat_whitespace(stream)
        parser.skip_to_matching_paren(stream)

        self.materialized = True

    def _matches_opcode_name(self, name: str) -> bool:
        """
        Check if opcode name matches expected name.

        For most opcodes, this is exact match. Comments opcode uses
        prefix matching to support variations like "Comment", "Comments", etc.

        Args:
            name: Opcode name from file

        Returns:
            True if name matches
        """
        return name == self.OPCODE_NAME

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with opcode information
        """
        return {
            'opcode_id': self.OPCODE_ID,
            'opcode_name': self.OPCODE_NAME,
            'type': 'metadata',
            'value': self.value,
            'description': self.DESCRIPTION
        }


class AuthorOpcode(MetadataOpcode):
    """
    WD_EXAO_DEFINE_AUTHOR (256) - Document author metadata.

    Format: (Author "John Doe")

    Stores the name of the document author.
    """
    OPCODE_ID = WD_EXAO_DEFINE_AUTHOR
    OPCODE_NAME = "Author"
    DESCRIPTION = "Document author"


class TitleOpcode(MetadataOpcode):
    """
    WD_EXAO_DEFINE_TITLE (303) - Document title metadata.

    Format: (Title "Engineering Drawing #12345")

    Stores the document title.
    """
    OPCODE_ID = WD_EXAO_DEFINE_TITLE
    OPCODE_NAME = "Title"
    DESCRIPTION = "Document title"


class SubjectOpcode(MetadataOpcode):
    """
    WD_EXAO_DEFINE_SUBJECT (304) - Document subject metadata.

    Format: (Subject "Building Floor Plan")

    Stores the nature of the drawing such as discipline or type.
    """
    OPCODE_ID = WD_EXAO_DEFINE_SUBJECT
    OPCODE_NAME = "Subject"
    DESCRIPTION = "Document subject"


class DescriptionOpcode(MetadataOpcode):
    """
    WD_EXAO_DEFINE_DESCRIPTION (269) - Document description metadata.

    Format: (Description "Main lobby renovation plan")

    Stores a detailed description of the drawing.
    """
    OPCODE_ID = WD_EXAO_DEFINE_DESCRIPTION
    OPCODE_NAME = "Description"
    DESCRIPTION = "Document description"


class CommentsOpcode(MetadataOpcode):
    """
    WD_EXAO_DEFINE_COMMENTS (262) - Document comments metadata.

    Format: (Comments "Revised per client feedback")

    Stores comments regarding the drawing. Supports prefix matching
    for opcode name (e.g., "Comment", "Comments").
    """
    OPCODE_ID = WD_EXAO_DEFINE_COMMENTS
    OPCODE_NAME = "Comments"
    DESCRIPTION = "Document comments"

    def _matches_opcode_name(self, name: str) -> bool:
        """
        Comments opcode uses prefix matching.

        Accepts "Comment", "Comments", or any string starting with "Comment".

        Args:
            name: Opcode name from file

        Returns:
            True if name starts with "Comment"
        """
        return name.startswith("Comment")


class KeywordsOpcode(MetadataOpcode):
    """
    WD_EXAO_DEFINE_KEYWORDS (275) - Document keywords metadata.

    Format: (Keywords "architecture, floor plan, commercial")

    Stores keywords to facilitate text searches upon the drawing.
    """
    OPCODE_ID = WD_EXAO_DEFINE_KEYWORDS
    OPCODE_NAME = "Keywords"
    DESCRIPTION = "Search keywords"


# =============================================================================
# OPCODE DISPATCHER
# =============================================================================

class MetadataOpcodeDispatcher:
    """
    Dispatcher for metadata opcodes.

    Maps opcode names to handler classes and provides parsing functionality.
    """

    def __init__(self):
        """Initialize dispatcher with opcode handlers."""
        self.handlers = {
            'Author': AuthorOpcode,
            'Title': TitleOpcode,
            'Subject': SubjectOpcode,
            'Description': DescriptionOpcode,
            'Keywords': KeywordsOpcode,
        }

        # Comments uses prefix matching, handled specially
        self.prefix_handlers = {
            'Comment': CommentsOpcode,
        }

    def parse(self, stream: io.BytesIO) -> Optional[MetadataOpcode]:
        """
        Parse next metadata opcode from stream.

        Args:
            stream: Input byte stream positioned at '('

        Returns:
            Parsed metadata opcode instance, or None if not a metadata opcode

        Raises:
            CorruptFileError: If opcode format is invalid
        """
        # Save position in case we need to backtrack
        start_pos = stream.tell()

        try:
            # Peek at opcode name without consuming stream
            parser = ExtendedASCIIParser()
            opcode_name = parser.parse_opcode_name(stream)

            # Reset to start
            stream.seek(start_pos)

            # Look for exact match
            if opcode_name in self.handlers:
                handler_class = self.handlers[opcode_name]
                handler = handler_class()
                handler.materialize(stream)
                return handler

            # Look for prefix match
            for prefix, handler_class in self.prefix_handlers.items():
                if opcode_name.startswith(prefix):
                    handler = handler_class()
                    handler.materialize(stream)
                    return handler

            # Not a metadata opcode we handle
            return None

        except Exception:
            # Reset stream position on error
            stream.seek(start_pos)
            raise

    def get_handler(self, opcode_name: str) -> Optional[type]:
        """
        Get handler class for opcode name.

        Args:
            opcode_name: Name of opcode

        Returns:
            Handler class, or None if not found
        """
        # Check exact match
        if opcode_name in self.handlers:
            return self.handlers[opcode_name]

        # Check prefix match
        for prefix, handler_class in self.prefix_handlers.items():
            if opcode_name.startswith(prefix):
                return handler_class

        return None


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_metadata_opcode(data: bytes) -> MetadataOpcode:
    """
    Parse a metadata opcode from bytes.

    Convenience function for parsing a single metadata opcode.

    Args:
        data: Bytes containing opcode (e.g., b'(Author "John Doe")')

    Returns:
        Parsed metadata opcode instance

    Raises:
        CorruptFileError: If opcode format is invalid
        ValueError: If opcode is not recognized
    """
    stream = io.BytesIO(data)
    dispatcher = MetadataOpcodeDispatcher()

    result = dispatcher.parse(stream)
    if result is None:
        raise ValueError("Not a recognized metadata opcode")

    return result


def create_metadata(opcode_name: str, value: str) -> MetadataOpcode:
    """
    Create a metadata opcode programmatically.

    Args:
        opcode_name: Name of opcode (e.g., "Author", "Title")
        value: String value for metadata

    Returns:
        Metadata opcode instance

    Raises:
        ValueError: If opcode name is not recognized
    """
    dispatcher = MetadataOpcodeDispatcher()
    handler_class = dispatcher.get_handler(opcode_name)

    if handler_class is None:
        raise ValueError(f"Unknown metadata opcode: {opcode_name}")

    return handler_class(value)


# =============================================================================
# MAIN DEMO
# =============================================================================

def main():
    """Demonstration of metadata opcode parsing and serialization."""
    print("=" * 70)
    print("DWF Extended ASCII Metadata Opcodes - Agent 15")
    print("=" * 70)
    print()

    # Example 1: Parse metadata opcodes
    print("Example 1: Parsing Metadata Opcodes")
    print("-" * 70)

    test_cases = [
        (b'(Author "John Doe")', AuthorOpcode),
        (b'(Title "Engineering Drawing")', TitleOpcode),
        (b'(Subject "Floor Plan")', SubjectOpcode),
        (b'(Description "Main building layout")', DescriptionOpcode),
        (b'(Comments "Revised 2025-10-22")', CommentsOpcode),
        (b'(Keywords "architecture, commercial, lobby")', KeywordsOpcode),
    ]

    for data, expected_class in test_cases:
        try:
            opcode = parse_metadata_opcode(data)
            print(f"Input:  {data.decode('utf-8')}")
            print(f"Parsed: {opcode}")
            print(f"Type:   {opcode.__class__.__name__}")
            print(f"Value:  '{opcode.value}'")
            assert isinstance(opcode, expected_class)
            print("Status: PASS")
        except Exception as e:
            print(f"Status: FAIL - {e}")
        print()

    # Example 2: Create and serialize metadata
    print("Example 2: Creating and Serializing Metadata")
    print("-" * 70)

    metadata_items = [
        ("Author", "Jane Smith"),
        ("Title", "Site Plan Revision B"),
        ("Subject", "Architectural"),
        ("Description", "Updated parking layout with new entrance"),
        ("Comments", "Client approved 2025-10-15"),
        ("Keywords", "site plan, parking, commercial"),
    ]

    for opcode_name, value in metadata_items:
        opcode = create_metadata(opcode_name, value)
        serialized = opcode.serialize()
        print(f"Created: {opcode_name} = '{value}'")
        print(f"Serialized: {serialized.decode('utf-8')}")

        # Verify round-trip
        parsed = parse_metadata_opcode(serialized)
        assert parsed.value == value
        print("Round-trip: PASS")
        print()

    # Example 3: Special cases
    print("Example 3: Special Cases")
    print("-" * 70)

    # Test Comments prefix matching
    print("Testing Comments prefix matching:")
    for variant in [b'(Comment "Test")', b'(Comments "Test")', b'(Commentary "Test")']:
        try:
            opcode = parse_metadata_opcode(variant)
            print(f"  {variant.decode('utf-8')} -> {opcode.__class__.__name__}: PASS")
        except Exception as e:
            print(f"  {variant.decode('utf-8')} -> FAIL: {e}")
    print()

    # Test empty value
    print("Testing empty value:")
    empty_author = AuthorOpcode("")
    serialized = empty_author.serialize()
    print(f"  Empty author serialized: {serialized!r}")
    print(f"  (Empty values produce no output): {'PASS' if serialized == b'' else 'FAIL'}")
    print()

    # Test special characters
    print("Testing special characters:")
    special_value = 'Test "quoted" and \\backslash\\'
    title = TitleOpcode(special_value)
    serialized = title.serialize()
    print(f"  Original: {special_value}")
    print(f"  Serialized: {serialized.decode('utf-8')}")
    parsed = parse_metadata_opcode(serialized)
    print(f"  Parsed: {parsed.value}")
    print(f"  Round-trip: {'PASS' if parsed.value == special_value else 'FAIL'}")
    print()

    print("=" * 70)
    print("All demonstrations complete!")
    print("=" * 70)


# =============================================================================
# UNIT TESTS
# =============================================================================

import unittest


class TestExtendedASCIIParser(unittest.TestCase):
    """Unit tests for Extended ASCII parser."""

    def test_is_legal_opcode_char(self):
        """Test legal opcode character detection."""
        # Legal characters
        self.assertTrue(ExtendedASCIIParser.is_legal_opcode_char(ord('A')))
        self.assertTrue(ExtendedASCIIParser.is_legal_opcode_char(ord('z')))
        self.assertTrue(ExtendedASCIIParser.is_legal_opcode_char(ord('!')))
        self.assertTrue(ExtendedASCIIParser.is_legal_opcode_char(ord('0')))

        # Illegal characters
        self.assertFalse(ExtendedASCIIParser.is_legal_opcode_char(ord('(')))
        self.assertFalse(ExtendedASCIIParser.is_legal_opcode_char(ord(')')))
        self.assertFalse(ExtendedASCIIParser.is_legal_opcode_char(0x20))  # space
        self.assertFalse(ExtendedASCIIParser.is_legal_opcode_char(0x7B))  # '{'

    def test_is_terminator(self):
        """Test terminator character detection."""
        # Terminators
        self.assertTrue(ExtendedASCIIParser.is_terminator(ord(' ')))
        self.assertTrue(ExtendedASCIIParser.is_terminator(ord('\t')))
        self.assertTrue(ExtendedASCIIParser.is_terminator(ord('\n')))
        self.assertTrue(ExtendedASCIIParser.is_terminator(ord('\r')))
        self.assertTrue(ExtendedASCIIParser.is_terminator(ord('(')))
        self.assertTrue(ExtendedASCIIParser.is_terminator(ord(')')))

        # Non-terminators
        self.assertFalse(ExtendedASCIIParser.is_terminator(ord('A')))
        self.assertFalse(ExtendedASCIIParser.is_terminator(ord('0')))

    def test_parse_opcode_name_simple(self):
        """Test parsing simple opcode names."""
        test_cases = [
            (b'(Author ', 'Author'),
            (b'(Title\t', 'Title'),
            (b'(Subject\n', 'Subject'),
            (b'(Description)', 'Description'),
        ]

        for data, expected in test_cases:
            with self.subTest(data=data):
                stream = io.BytesIO(data)
                result = ExtendedASCIIParser.parse_opcode_name(stream)
                self.assertEqual(result, expected)

    def test_parse_opcode_name_errors(self):
        """Test opcode name parsing error cases."""
        # Missing opening paren
        with self.assertRaises(CorruptFileError):
            stream = io.BytesIO(b'Author ')
            ExtendedASCIIParser.parse_opcode_name(stream)

        # Empty name
        with self.assertRaises(CorruptFileError):
            stream = io.BytesIO(b'( ')
            ExtendedASCIIParser.parse_opcode_name(stream)

        # Illegal character
        with self.assertRaises(CorruptFileError):
            stream = io.BytesIO(b'(Auth{or ')
            ExtendedASCIIParser.parse_opcode_name(stream)

        # EOF
        with self.assertRaises(UnexpectedEOFError):
            stream = io.BytesIO(b'(Author')
            ExtendedASCIIParser.parse_opcode_name(stream)

    def test_parse_quoted_string_simple(self):
        """Test parsing simple quoted strings."""
        test_cases = [
            (b'"Hello"', 'Hello'),
            (b'"John Doe"', 'John Doe'),
            (b'"Test 123"', 'Test 123'),
            (b'""', ''),
        ]

        for data, expected in test_cases:
            with self.subTest(data=data):
                stream = io.BytesIO(data)
                result = ExtendedASCIIParser.parse_quoted_string(stream)
                self.assertEqual(result, expected)

    def test_parse_quoted_string_escapes(self):
        """Test parsing strings with escape sequences."""
        test_cases = [
            (b'"Test\\"quote"', 'Test"quote'),
            (b'"Back\\\\slash"', 'Back\\slash'),
            (b'"New\\nline"', 'New\nline'),
            (b'"Tab\\there"', 'Tab\there'),
        ]

        for data, expected in test_cases:
            with self.subTest(data=data):
                stream = io.BytesIO(data)
                result = ExtendedASCIIParser.parse_quoted_string(stream)
                self.assertEqual(result, expected)

    def test_parse_quoted_string_unquoted(self):
        """Test parsing unquoted strings."""
        test_cases = [
            (b'SimpleText ', 'SimpleText'),
            (b'NoSpaces)', 'NoSpaces'),
        ]

        for data, expected in test_cases:
            with self.subTest(data=data):
                stream = io.BytesIO(data)
                result = ExtendedASCIIParser.parse_quoted_string(stream)
                self.assertEqual(result, expected)

    def test_eat_whitespace(self):
        """Test whitespace consumption."""
        stream = io.BytesIO(b'   \t\n\r  Text')
        ExtendedASCIIParser.eat_whitespace(stream)
        self.assertEqual(stream.read(1), b'T')

    def test_skip_to_matching_paren(self):
        """Test skipping to matching parenthesis."""
        stream = io.BytesIO(b'some data (nested) more data)')
        ExtendedASCIIParser.skip_to_matching_paren(stream)
        # Should be at closing paren
        self.assertEqual(stream.tell(), len(b'some data (nested) more data)'))


class TestAuthorOpcode(unittest.TestCase):
    """Unit tests for AuthorOpcode."""

    def test_init(self):
        """Test initialization."""
        opcode = AuthorOpcode("John Doe")
        self.assertEqual(opcode.value, "John Doe")
        self.assertEqual(opcode.OPCODE_ID, WD_EXAO_DEFINE_AUTHOR)
        self.assertEqual(opcode.OPCODE_NAME, "Author")

    def test_serialize(self):
        """Test serialization."""
        opcode = AuthorOpcode("Jane Smith")
        result = opcode.serialize()
        self.assertEqual(result, b'(Author "Jane Smith")')

    def test_serialize_empty(self):
        """Test serialization of empty value."""
        opcode = AuthorOpcode("")
        result = opcode.serialize()
        self.assertEqual(result, b'')

    def test_materialize(self):
        """Test materialization from stream."""
        stream = io.BytesIO(b'(Author "John Doe")')
        opcode = AuthorOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "John Doe")
        self.assertTrue(opcode.materialized)

    def test_materialize_with_whitespace(self):
        """Test materialization with extra whitespace."""
        stream = io.BytesIO(b'(Author   "Jane Smith"  )')
        opcode = AuthorOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Jane Smith")

    def test_round_trip(self):
        """Test serialize/deserialize round trip."""
        original = AuthorOpcode("Test Author")
        serialized = original.serialize()

        parsed = AuthorOpcode()
        parsed.materialize(io.BytesIO(serialized))

        self.assertEqual(parsed.value, original.value)

    def test_to_dict(self):
        """Test dictionary conversion."""
        opcode = AuthorOpcode("John Doe")
        result = opcode.to_dict()
        self.assertEqual(result['opcode_id'], WD_EXAO_DEFINE_AUTHOR)
        self.assertEqual(result['opcode_name'], 'Author')
        self.assertEqual(result['value'], 'John Doe')


class TestTitleOpcode(unittest.TestCase):
    """Unit tests for TitleOpcode."""

    def test_serialize(self):
        """Test serialization."""
        opcode = TitleOpcode("Engineering Drawing")
        result = opcode.serialize()
        self.assertEqual(result, b'(Title "Engineering Drawing")')

    def test_materialize(self):
        """Test materialization."""
        stream = io.BytesIO(b'(Title "Test Title")')
        opcode = TitleOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Test Title")

    def test_round_trip(self):
        """Test round trip."""
        original = TitleOpcode("Drawing #12345")
        serialized = original.serialize()
        parsed = TitleOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, original.value)


class TestSubjectOpcode(unittest.TestCase):
    """Unit tests for SubjectOpcode."""

    def test_serialize(self):
        """Test serialization."""
        opcode = SubjectOpcode("Floor Plan")
        result = opcode.serialize()
        self.assertEqual(result, b'(Subject "Floor Plan")')

    def test_materialize(self):
        """Test materialization."""
        stream = io.BytesIO(b'(Subject "Architectural")')
        opcode = SubjectOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Architectural")

    def test_round_trip(self):
        """Test round trip."""
        original = SubjectOpcode("Electrical Schematic")
        serialized = original.serialize()
        parsed = SubjectOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, original.value)


class TestDescriptionOpcode(unittest.TestCase):
    """Unit tests for DescriptionOpcode."""

    def test_serialize(self):
        """Test serialization."""
        opcode = DescriptionOpcode("Main building layout")
        result = opcode.serialize()
        self.assertEqual(result, b'(Description "Main building layout")')

    def test_materialize(self):
        """Test materialization."""
        stream = io.BytesIO(b'(Description "Detailed floor plan")')
        opcode = DescriptionOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Detailed floor plan")

    def test_long_description(self):
        """Test with long description."""
        long_desc = "This is a very long description " * 10
        opcode = DescriptionOpcode(long_desc)
        serialized = opcode.serialize()

        parsed = DescriptionOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, long_desc)


class TestCommentsOpcode(unittest.TestCase):
    """Unit tests for CommentsOpcode."""

    def test_serialize(self):
        """Test serialization."""
        opcode = CommentsOpcode("Revised per client")
        result = opcode.serialize()
        self.assertEqual(result, b'(Comments "Revised per client")')

    def test_materialize_comments(self):
        """Test materialization with 'Comments'."""
        stream = io.BytesIO(b'(Comments "Test comment")')
        opcode = CommentsOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Test comment")

    def test_materialize_comment(self):
        """Test materialization with 'Comment' (singular)."""
        stream = io.BytesIO(b'(Comment "Single comment")')
        opcode = CommentsOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Single comment")

    def test_materialize_commentary(self):
        """Test materialization with 'Commentary' (prefix match)."""
        stream = io.BytesIO(b'(Commentary "Extended comment")')
        opcode = CommentsOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "Extended comment")

    def test_prefix_matching(self):
        """Test prefix matching behavior."""
        opcode = CommentsOpcode()
        self.assertTrue(opcode._matches_opcode_name("Comment"))
        self.assertTrue(opcode._matches_opcode_name("Comments"))
        self.assertTrue(opcode._matches_opcode_name("Commentary"))
        self.assertFalse(opcode._matches_opcode_name("Author"))


class TestKeywordsOpcode(unittest.TestCase):
    """Unit tests for KeywordsOpcode."""

    def test_serialize(self):
        """Test serialization."""
        opcode = KeywordsOpcode("architecture, floor plan, commercial")
        result = opcode.serialize()
        self.assertEqual(result, b'(Keywords "architecture, floor plan, commercial")')

    def test_materialize(self):
        """Test materialization."""
        stream = io.BytesIO(b'(Keywords "keyword1, keyword2, keyword3")')
        opcode = KeywordsOpcode()
        opcode.materialize(stream)
        self.assertEqual(opcode.value, "keyword1, keyword2, keyword3")

    def test_multiple_keywords(self):
        """Test with multiple keywords."""
        keywords = "CAD, DWF, engineering, 2D, drawing, technical"
        opcode = KeywordsOpcode(keywords)
        serialized = opcode.serialize()

        parsed = KeywordsOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, keywords)


class TestMetadataOpcodeDispatcher(unittest.TestCase):
    """Unit tests for MetadataOpcodeDispatcher."""

    def test_parse_author(self):
        """Test parsing Author opcode."""
        stream = io.BytesIO(b'(Author "John Doe")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsInstance(result, AuthorOpcode)
        self.assertEqual(result.value, "John Doe")

    def test_parse_title(self):
        """Test parsing Title opcode."""
        stream = io.BytesIO(b'(Title "Test Title")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsInstance(result, TitleOpcode)
        self.assertEqual(result.value, "Test Title")

    def test_parse_subject(self):
        """Test parsing Subject opcode."""
        stream = io.BytesIO(b'(Subject "Test Subject")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsInstance(result, SubjectOpcode)

    def test_parse_description(self):
        """Test parsing Description opcode."""
        stream = io.BytesIO(b'(Description "Test Description")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsInstance(result, DescriptionOpcode)

    def test_parse_comments(self):
        """Test parsing Comments opcode."""
        stream = io.BytesIO(b'(Comments "Test Comments")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsInstance(result, CommentsOpcode)

    def test_parse_keywords(self):
        """Test parsing Keywords opcode."""
        stream = io.BytesIO(b'(Keywords "test, keywords")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsInstance(result, KeywordsOpcode)

    def test_parse_unknown(self):
        """Test parsing unknown opcode returns None."""
        stream = io.BytesIO(b'(Unknown "data")')
        dispatcher = MetadataOpcodeDispatcher()
        result = dispatcher.parse(stream)
        self.assertIsNone(result)

    def test_get_handler(self):
        """Test getting handler class."""
        dispatcher = MetadataOpcodeDispatcher()

        self.assertEqual(dispatcher.get_handler('Author'), AuthorOpcode)
        self.assertEqual(dispatcher.get_handler('Title'), TitleOpcode)
        self.assertEqual(dispatcher.get_handler('Comment'), CommentsOpcode)
        self.assertEqual(dispatcher.get_handler('Comments'), CommentsOpcode)
        self.assertIsNone(dispatcher.get_handler('Unknown'))


class TestUtilityFunctions(unittest.TestCase):
    """Unit tests for utility functions."""

    def test_parse_metadata_opcode(self):
        """Test parse_metadata_opcode utility."""
        data = b'(Author "Test Author")'
        result = parse_metadata_opcode(data)
        self.assertIsInstance(result, AuthorOpcode)
        self.assertEqual(result.value, "Test Author")

    def test_parse_metadata_opcode_invalid(self):
        """Test parse_metadata_opcode with invalid opcode."""
        data = b'(Unknown "data")'
        with self.assertRaises(ValueError):
            parse_metadata_opcode(data)

    def test_create_metadata_author(self):
        """Test creating Author metadata."""
        opcode = create_metadata("Author", "John Doe")
        self.assertIsInstance(opcode, AuthorOpcode)
        self.assertEqual(opcode.value, "John Doe")

    def test_create_metadata_title(self):
        """Test creating Title metadata."""
        opcode = create_metadata("Title", "Test Title")
        self.assertIsInstance(opcode, TitleOpcode)
        self.assertEqual(opcode.value, "Test Title")

    def test_create_metadata_comments(self):
        """Test creating Comments metadata with prefix match."""
        opcode = create_metadata("Comment", "Test Comment")
        self.assertIsInstance(opcode, CommentsOpcode)
        self.assertEqual(opcode.value, "Test Comment")

    def test_create_metadata_invalid(self):
        """Test creating invalid metadata."""
        with self.assertRaises(ValueError):
            create_metadata("InvalidOpcode", "data")


class TestSpecialCases(unittest.TestCase):
    """Tests for special cases and edge conditions."""

    def test_unicode_content(self):
        """Test handling of Unicode characters."""
        # UTF-8 encoded Unicode
        value = "Test with Unicode: \u00e9\u00e0\u00fc\u4e2d\u6587"
        opcode = TitleOpcode(value)
        serialized = opcode.serialize()

        parsed = TitleOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, value)

    def test_special_characters_escaping(self):
        """Test proper escaping of special characters."""
        test_cases = [
            'Contains "quotes"',
            'Contains \\backslash\\',
            'Contains "both\\" special',
        ]

        for value in test_cases:
            with self.subTest(value=value):
                opcode = DescriptionOpcode(value)
                serialized = opcode.serialize()

                parsed = DescriptionOpcode()
                parsed.materialize(io.BytesIO(serialized))
                self.assertEqual(parsed.value, value)

    def test_multiline_value(self):
        """Test handling of multiline values."""
        value = "Line 1\nLine 2\nLine 3"
        opcode = DescriptionOpcode(value)
        serialized = opcode.serialize()

        parsed = DescriptionOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, value)

    def test_very_long_value(self):
        """Test handling of very long values."""
        value = "A" * 10000
        opcode = DescriptionOpcode(value)
        serialized = opcode.serialize()

        parsed = DescriptionOpcode()
        parsed.materialize(io.BytesIO(serialized))
        self.assertEqual(parsed.value, value)

    def test_stream_position_after_parse(self):
        """Test that stream position is correct after parsing."""
        data = b'(Author "John Doe")Next data'
        stream = io.BytesIO(data)

        opcode = AuthorOpcode()
        opcode.materialize(stream)

        # Stream should be positioned after closing paren
        remaining = stream.read()
        self.assertEqual(remaining, b'Next data')


def run_tests():
    """Run all unit tests."""
    print("=" * 70)
    print("Running Unit Tests for Agent 15 Metadata Opcodes")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestExtendedASCIIParser))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthorOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestTitleOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestSubjectOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestDescriptionOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestCommentsOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestKeywordsOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestMetadataOpcodeDispatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestSpecialCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 70)
    print("Test Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys

    # Check if running tests or demo
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        main()
