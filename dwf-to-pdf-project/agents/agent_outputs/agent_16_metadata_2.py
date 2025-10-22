"""
DWF Opcode Agent 16: Extended ASCII Metadata Opcodes (2/3) - Timestamps & Creator

This module implements parsing for DWF Extended ASCII metadata opcodes related to
timestamps and creator information. These opcodes provide document metadata for
legacy DWF files (version 00.55 and earlier).

Opcodes Implemented:
- 263 WD_EXAO_DEFINE_COPYRIGHT: Copyright information
- 264 WD_EXAO_DEFINE_CREATOR: Creator application name
- 265 WD_EXAO_DEFINE_CREATION_TIME: Creation timestamp
- 280 WD_EXAO_DEFINE_MODIFICATION_TIME: Modification timestamp
- 284 WD_EXAO_DEFINE_SOURCE_CREATION_TIME: Source creation timestamp
- 285 WD_EXAO_DEFINE_SOURCE_MODIFICATION_TIME: Source modification timestamp

Reference:
- C++ Source: /home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/
- Key Files: informational.cpp, timestamp.cpp, informational.h, timestamp.h
- Research: /home/user/git-practice/dwf-to-pdf-project/agents/agent_outputs/agent_13_extended_opcodes_research.md
"""

import struct
from io import BytesIO
from typing import Dict, BinaryIO, Optional, Any
from datetime import datetime


# ============================================================================
# Opcode Constants
# ============================================================================

WD_EXAO_DEFINE_COPYRIGHT = 263
WD_EXAO_DEFINE_CREATOR = 264
WD_EXAO_DEFINE_CREATION_TIME = 265
WD_EXAO_DEFINE_MODIFICATION_TIME = 280
WD_EXAO_DEFINE_SOURCE_CREATION_TIME = 284
WD_EXAO_DEFINE_SOURCE_MODIFICATION_TIME = 285

# Opcode name mappings
OPCODE_NAMES = {
    263: "Copyright",
    264: "Creator",
    265: "Created",
    280: "Modified",
    284: "SourceCreated",
    285: "SourceModified"
}


# ============================================================================
# Helper Functions - String Parsing
# ============================================================================

def read_quoted_string(stream: BinaryIO) -> str:
    """
    Read a quoted string from DWF stream.

    DWF Extended ASCII strings are quoted with double quotes and can contain
    escape sequences. The format is: "string content"

    Args:
        stream: Binary stream positioned at opening quote

    Returns:
        Decoded string (without quotes)

    Raises:
        ValueError: If string format is invalid

    Example:
        >>> stream = BytesIO(b'"Hello World"')
        >>> read_quoted_string(stream)
        'Hello World'
    """
    # Skip opening quote
    quote = stream.read(1)
    if quote != b'"':
        raise ValueError(f"Expected opening quote, got {quote!r}")

    chars = []
    escaped = False

    while True:
        byte = stream.read(1)
        if not byte:
            raise ValueError("Unexpected EOF in quoted string")

        char = byte[0]

        if escaped:
            # Handle escape sequences
            if char == ord('n'):
                chars.append(ord('\n'))
            elif char == ord('t'):
                chars.append(ord('\t'))
            elif char == ord('r'):
                chars.append(ord('\r'))
            elif char == ord('\\'):
                chars.append(ord('\\'))
            elif char == ord('"'):
                chars.append(ord('"'))
            else:
                # Unknown escape, just use the character
                chars.append(char)
            escaped = False
        elif char == ord('\\'):
            escaped = True
        elif char == ord('"'):
            # End of string
            break
        else:
            chars.append(char)

    # Decode as UTF-8
    try:
        return bytes(chars).decode('utf-8')
    except UnicodeDecodeError:
        # Fallback to latin-1 for legacy files
        return bytes(chars).decode('latin-1')


def skip_whitespace(stream: BinaryIO) -> None:
    """
    Skip whitespace characters in stream.

    Whitespace includes: space, tab, LF, CR

    Args:
        stream: Binary stream to read from
    """
    while True:
        byte = stream.read(1)
        if not byte:
            break
        if byte[0] not in (ord(' '), ord('\t'), ord('\n'), ord('\r')):
            # Put non-whitespace back
            stream.seek(-1, 1)
            break


def read_integer(stream: BinaryIO) -> int:
    """
    Read an ASCII-encoded integer from stream.

    Reads digits until whitespace or non-digit character is encountered.

    Args:
        stream: Binary stream positioned at first digit

    Returns:
        Integer value

    Raises:
        ValueError: If no valid integer found

    Example:
        >>> stream = BytesIO(b'12345 ')
        >>> read_integer(stream)
        12345
    """
    digits = []
    negative = False

    # Check for negative sign
    first = stream.read(1)
    if not first:
        raise ValueError("Expected integer, got EOF")

    if first == b'-':
        negative = True
    else:
        stream.seek(-1, 1)

    while True:
        byte = stream.read(1)
        if not byte:
            break

        char = byte[0]
        if ord('0') <= char <= ord('9'):
            digits.append(chr(char))
        else:
            # Put back non-digit
            stream.seek(-1, 1)
            break

    if not digits:
        raise ValueError("No digits found for integer")

    value = int(''.join(digits))
    return -value if negative else value


# ============================================================================
# Helper Functions - Timestamp Conversion
# ============================================================================

def unix_timestamp_to_datetime(seconds: int) -> datetime:
    """
    Convert Unix timestamp (seconds since 1970-01-01 00:00:00 UTC) to datetime.

    Args:
        seconds: Unix timestamp in seconds

    Returns:
        datetime object in UTC

    Example:
        >>> unix_timestamp_to_datetime(1640000000)
        datetime.datetime(2021, 12, 20, 8, 0)
    """
    return datetime.utcfromtimestamp(seconds)


def format_timestamp(seconds: int) -> str:
    """
    Format Unix timestamp as ISO 8601 string.

    Args:
        seconds: Unix timestamp in seconds

    Returns:
        ISO 8601 formatted string (YYYY-MM-DD HH:MM:SS)

    Example:
        >>> format_timestamp(1640000000)
        '2021-12-20 08:00:00'
    """
    dt = unix_timestamp_to_datetime(seconds)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def parse_timestamp_string(timestamp_str: str) -> Optional[datetime]:
    """
    Parse a timestamp string to datetime object.

    Attempts to parse various timestamp formats found in DWF files:
    - ISO format: YYYY-MM-DD HH:MM:SS
    - US format: MM/DD/YYYY HH:MM:SS
    - Compact: YYYYMMDDHHMMSS

    Args:
        timestamp_str: Timestamp string to parse

    Returns:
        datetime object or None if parsing fails

    Example:
        >>> parse_timestamp_string('2021-12-20 08:00:00')
        datetime.datetime(2021, 12, 20, 8, 0)
    """
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%m/%d/%Y %H:%M:%S',
        '%Y%m%d%H%M%S',
        '%Y-%m-%d',
        '%m/%d/%Y'
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    return None


# ============================================================================
# Informational Metadata Opcodes (String-based)
# ============================================================================

def parse_copyright(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_DEFINE_COPYRIGHT (263) - Copyright information.

    Format: (Copyright "copyright text")

    This opcode stores copyright information for the drawing. It is a simple
    string-based informational metadata field.

    Args:
        stream: Binary stream positioned after '(Copyright'

    Returns:
        Dictionary with:
            - type: 'copyright'
            - opcode_id: 263
            - copyright: Copyright text string

    Raises:
        ValueError: If data format is invalid

    Example:
        >>> stream = BytesIO(b' "Copyright 2024 Acme Corp")')
        >>> result = parse_copyright(stream)
        >>> result['copyright']
        'Copyright 2024 Acme Corp'
    """
    # Skip whitespace before string
    skip_whitespace(stream)

    # Read copyright string
    copyright_text = read_quoted_string(stream)

    # Skip to closing paren
    skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise ValueError(f"Expected closing paren, got {closing!r}")

    return {
        'type': 'copyright',
        'opcode_id': WD_EXAO_DEFINE_COPYRIGHT,
        'copyright': copyright_text
    }


def parse_creator(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_DEFINE_CREATOR (264) - Creator application name.

    Format: (Creator "application name and version")

    This opcode stores the name and version of the application that created
    the DWF file. Common values include "Autodesk AutoCAD", "Autodesk Revit", etc.

    Args:
        stream: Binary stream positioned after '(Creator'

    Returns:
        Dictionary with:
            - type: 'creator'
            - opcode_id: 264
            - creator: Creator application string

    Raises:
        ValueError: If data format is invalid

    Example:
        >>> stream = BytesIO(b' "Autodesk AutoCAD 2024")')
        >>> result = parse_creator(stream)
        >>> result['creator']
        'Autodesk AutoCAD 2024'
    """
    # Skip whitespace before string
    skip_whitespace(stream)

    # Read creator string
    creator_text = read_quoted_string(stream)

    # Skip to closing paren
    skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise ValueError(f"Expected closing paren, got {closing!r}")

    return {
        'type': 'creator',
        'opcode_id': WD_EXAO_DEFINE_CREATOR,
        'creator': creator_text
    }


# ============================================================================
# Timestamp Metadata Opcodes
# ============================================================================

def parse_creation_time(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_DEFINE_CREATION_TIME (265) - Creation timestamp.

    Format: (Created seconds "timestamp_string" "guid")

    This opcode stores the creation time of the drawing. The timestamp is
    stored both as Unix seconds (since 1970-01-01 00:00:00 UTC) and as a
    human-readable string. An optional GUID may also be included.

    Args:
        stream: Binary stream positioned after '(Created'

    Returns:
        Dictionary with:
            - type: 'creation_time'
            - opcode_id: 265
            - seconds: Unix timestamp (int)
            - timestamp: Formatted timestamp string
            - guid: GUID string (may be empty)
            - datetime: ISO formatted datetime

    Raises:
        ValueError: If data format is invalid

    Example:
        >>> stream = BytesIO(b' 1640000000 "2021-12-20 08:00:00" "{12345678-1234-1234-1234-123456789012}")')
        >>> result = parse_creation_time(stream)
        >>> result['seconds']
        1640000000
    """
    # Skip whitespace before seconds
    skip_whitespace(stream)

    # Read seconds (Unix timestamp)
    seconds = read_integer(stream)

    # Skip whitespace before timestamp string
    skip_whitespace(stream)

    # Read timestamp string
    timestamp_str = read_quoted_string(stream)

    # Skip whitespace before GUID
    skip_whitespace(stream)

    # Read GUID (may be empty)
    guid = read_quoted_string(stream)

    # Skip to closing paren
    skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise ValueError(f"Expected closing paren, got {closing!r}")

    return {
        'type': 'creation_time',
        'opcode_id': WD_EXAO_DEFINE_CREATION_TIME,
        'seconds': seconds,
        'timestamp': timestamp_str,
        'guid': guid,
        'datetime': format_timestamp(seconds)
    }


def parse_modification_time(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_DEFINE_MODIFICATION_TIME (280) - Modification timestamp.

    Format: (Modified seconds "timestamp_string" "guid")

    This opcode stores the last modification time of the drawing. Same format
    as creation time.

    Args:
        stream: Binary stream positioned after '(Modified'

    Returns:
        Dictionary with:
            - type: 'modification_time'
            - opcode_id: 280
            - seconds: Unix timestamp (int)
            - timestamp: Formatted timestamp string
            - guid: GUID string (may be empty)
            - datetime: ISO formatted datetime

    Raises:
        ValueError: If data format is invalid

    Example:
        >>> stream = BytesIO(b' 1640100000 "2021-12-21 12:00:00" "")')
        >>> result = parse_modification_time(stream)
        >>> result['seconds']
        1640100000
    """
    # Skip whitespace before seconds
    skip_whitespace(stream)

    # Read seconds (Unix timestamp)
    seconds = read_integer(stream)

    # Skip whitespace before timestamp string
    skip_whitespace(stream)

    # Read timestamp string
    timestamp_str = read_quoted_string(stream)

    # Skip whitespace before GUID
    skip_whitespace(stream)

    # Read GUID (may be empty)
    guid = read_quoted_string(stream)

    # Skip to closing paren
    skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise ValueError(f"Expected closing paren, got {closing!r}")

    return {
        'type': 'modification_time',
        'opcode_id': WD_EXAO_DEFINE_MODIFICATION_TIME,
        'seconds': seconds,
        'timestamp': timestamp_str,
        'guid': guid,
        'datetime': format_timestamp(seconds)
    }


def parse_source_creation_time(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_DEFINE_SOURCE_CREATION_TIME (284) - Source creation timestamp.

    Format: (SourceCreated seconds "timestamp_string" "guid")

    This opcode stores the creation time of the source file from which the
    DWF was generated (e.g., the original CAD drawing file).

    Args:
        stream: Binary stream positioned after '(SourceCreated'

    Returns:
        Dictionary with:
            - type: 'source_creation_time'
            - opcode_id: 284
            - seconds: Unix timestamp (int)
            - timestamp: Formatted timestamp string
            - guid: GUID string (may be empty)
            - datetime: ISO formatted datetime

    Raises:
        ValueError: If data format is invalid

    Example:
        >>> stream = BytesIO(b' 1639900000 "2021-12-19 04:00:00" "")')
        >>> result = parse_source_creation_time(stream)
        >>> result['type']
        'source_creation_time'
    """
    # Skip whitespace before seconds
    skip_whitespace(stream)

    # Read seconds (Unix timestamp)
    seconds = read_integer(stream)

    # Skip whitespace before timestamp string
    skip_whitespace(stream)

    # Read timestamp string
    timestamp_str = read_quoted_string(stream)

    # Skip whitespace before GUID
    skip_whitespace(stream)

    # Read GUID (may be empty)
    guid = read_quoted_string(stream)

    # Skip to closing paren
    skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise ValueError(f"Expected closing paren, got {closing!r}")

    return {
        'type': 'source_creation_time',
        'opcode_id': WD_EXAO_DEFINE_SOURCE_CREATION_TIME,
        'seconds': seconds,
        'timestamp': timestamp_str,
        'guid': guid,
        'datetime': format_timestamp(seconds)
    }


def parse_source_modification_time(stream: BinaryIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_DEFINE_SOURCE_MODIFICATION_TIME (285) - Source modification timestamp.

    Format: (SourceModified seconds "timestamp_string" "guid")

    This opcode stores the last modification time of the source file from which
    the DWF was generated.

    Args:
        stream: Binary stream positioned after '(SourceModified'

    Returns:
        Dictionary with:
            - type: 'source_modification_time'
            - opcode_id: 285
            - seconds: Unix timestamp (int)
            - timestamp: Formatted timestamp string
            - guid: GUID string (may be empty)
            - datetime: ISO formatted datetime

    Raises:
        ValueError: If data format is invalid

    Example:
        >>> stream = BytesIO(b' 1640000000 "2021-12-20 08:00:00" "")')
        >>> result = parse_source_modification_time(stream)
        >>> result['type']
        'source_modification_time'
    """
    # Skip whitespace before seconds
    skip_whitespace(stream)

    # Read seconds (Unix timestamp)
    seconds = read_integer(stream)

    # Skip whitespace before timestamp string
    skip_whitespace(stream)

    # Read timestamp string
    timestamp_str = read_quoted_string(stream)

    # Skip whitespace before GUID
    skip_whitespace(stream)

    # Read GUID (may be empty)
    guid = read_quoted_string(stream)

    # Skip to closing paren
    skip_whitespace(stream)
    closing = stream.read(1)
    if closing != b')':
        raise ValueError(f"Expected closing paren, got {closing!r}")

    return {
        'type': 'source_modification_time',
        'opcode_id': WD_EXAO_DEFINE_SOURCE_MODIFICATION_TIME,
        'seconds': seconds,
        'timestamp': timestamp_str,
        'guid': guid,
        'datetime': format_timestamp(seconds)
    }


# ============================================================================
# Dispatcher Function
# ============================================================================

def parse_metadata_opcode(opcode_name: str, stream: BinaryIO) -> Dict[str, Any]:
    """
    Dispatch Extended ASCII metadata opcode to appropriate parser.

    Args:
        opcode_name: Name of the opcode (e.g., 'Copyright', 'Creator', 'Created')
        stream: Binary stream positioned after opcode name

    Returns:
        Parsed opcode result dictionary

    Raises:
        ValueError: If opcode is not recognized or data is invalid
    """
    handlers = {
        'Copyright': parse_copyright,
        'Creator': parse_creator,
        'Created': parse_creation_time,
        'Modified': parse_modification_time,
        'SourceCreated': parse_source_creation_time,
        'SourceModified': parse_source_modification_time
    }

    handler = handlers.get(opcode_name)
    if not handler:
        raise ValueError(f"Unknown metadata opcode: {opcode_name}")

    return handler(stream)


# ============================================================================
# Test Suite
# ============================================================================

def test_copyright_basic():
    """Test basic copyright parsing."""
    data = b' "Copyright 2024 Acme Corporation")'
    stream = BytesIO(data)
    result = parse_copyright(stream)

    assert result['type'] == 'copyright'
    assert result['opcode_id'] == 263
    assert result['copyright'] == 'Copyright 2024 Acme Corporation'
    print("✓ test_copyright_basic passed")


def test_copyright_with_special_chars():
    """Test copyright with special characters and symbols."""
    data = b' "Copyright (c) 2024 Autodesk, Inc. All rights reserved.")'
    stream = BytesIO(data)
    result = parse_copyright(stream)

    assert result['copyright'] == 'Copyright (c) 2024 Autodesk, Inc. All rights reserved.'
    print("✓ test_copyright_with_special_chars passed")


def test_creator_basic():
    """Test basic creator parsing."""
    data = b' "Autodesk AutoCAD 2024")'
    stream = BytesIO(data)
    result = parse_creator(stream)

    assert result['type'] == 'creator'
    assert result['opcode_id'] == 264
    assert result['creator'] == 'Autodesk AutoCAD 2024'
    print("✓ test_creator_basic passed")


def test_creator_with_version():
    """Test creator with detailed version information."""
    data = b' "Genuine AutoCAD 2000i (15.05s.52.0)")'
    stream = BytesIO(data)
    result = parse_creator(stream)

    assert 'AutoCAD' in result['creator']
    assert '2000i' in result['creator']
    print("✓ test_creator_with_version passed")


def test_creation_time_basic():
    """Test basic creation time parsing."""
    data = b' 1640000000 "2021-12-20 08:00:00" "")'
    stream = BytesIO(data)
    result = parse_creation_time(stream)

    assert result['type'] == 'creation_time'
    assert result['opcode_id'] == 265
    assert result['seconds'] == 1640000000
    assert result['timestamp'] == '2021-12-20 08:00:00'
    assert result['guid'] == ''
    # Unix timestamp 1640000000 = 2021-12-20 11:33:20 UTC
    assert result['datetime'] == '2021-12-20 11:33:20'
    print("✓ test_creation_time_basic passed")


def test_creation_time_with_guid():
    """Test creation time with GUID."""
    data = b' 1640000000 "2021-12-20 08:00:00" "{12345678-1234-1234-1234-123456789012}")'
    stream = BytesIO(data)
    result = parse_creation_time(stream)

    assert result['seconds'] == 1640000000
    assert result['guid'] == '{12345678-1234-1234-1234-123456789012}'
    print("✓ test_creation_time_with_guid passed")


def test_modification_time_basic():
    """Test basic modification time parsing."""
    data = b' 1640100000 "2021-12-21 15:46:40" "")'
    stream = BytesIO(data)
    result = parse_modification_time(stream)

    assert result['type'] == 'modification_time'
    assert result['opcode_id'] == 280
    assert result['seconds'] == 1640100000
    print("✓ test_modification_time_basic passed")


def test_modification_time_later_than_creation():
    """Test that modification time can be later than creation time."""
    # Creation time
    data1 = b' 1640000000 "2021-12-20 08:00:00" "")'
    stream1 = BytesIO(data1)
    creation = parse_creation_time(stream1)

    # Modification time (1 day later)
    data2 = b' 1640086400 "2021-12-21 08:00:00" "")'
    stream2 = BytesIO(data2)
    modification = parse_modification_time(stream2)

    assert modification['seconds'] > creation['seconds']
    print("✓ test_modification_time_later_than_creation passed")


def test_source_creation_time():
    """Test source creation time parsing."""
    data = b' 1639900000 "2021-12-19 04:00:00" "")'
    stream = BytesIO(data)
    result = parse_source_creation_time(stream)

    assert result['type'] == 'source_creation_time'
    assert result['opcode_id'] == 284
    assert result['seconds'] == 1639900000
    print("✓ test_source_creation_time passed")


def test_source_modification_time():
    """Test source modification time parsing."""
    data = b' 1639950000 "2021-12-19 17:53:20" "")'
    stream = BytesIO(data)
    result = parse_source_modification_time(stream)

    assert result['type'] == 'source_modification_time'
    assert result['opcode_id'] == 285
    assert result['seconds'] == 1639950000
    print("✓ test_source_modification_time passed")


def test_timestamp_format_conversion():
    """Test Unix timestamp to datetime conversion."""
    timestamp = 1640000000
    dt = unix_timestamp_to_datetime(timestamp)
    formatted = format_timestamp(timestamp)

    assert dt.year == 2021
    assert dt.month == 12
    assert dt.day == 20
    # Unix timestamp 1640000000 = 2021-12-20 11:33:20 UTC
    assert formatted == '2021-12-20 11:33:20'
    print("✓ test_timestamp_format_conversion passed")


def test_dispatcher():
    """Test opcode dispatcher with multiple opcodes."""
    test_cases = [
        ('Copyright', b' "Test Copyright")', 'copyright'),
        ('Creator', b' "Test Creator")', 'creator'),
        ('Created', b' 1640000000 "2021-12-20" "")', 'creation_time'),
        ('Modified', b' 1640100000 "2021-12-21" "")', 'modification_time'),
    ]

    for opcode_name, data, expected_type in test_cases:
        stream = BytesIO(data)
        result = parse_metadata_opcode(opcode_name, stream)
        assert result['type'] == expected_type

    print("✓ test_dispatcher passed")


def test_quoted_string_with_escapes():
    """Test quoted string parsing with escape sequences."""
    data = b'"Line 1\\nLine 2\\tTabbed"'
    stream = BytesIO(data)
    result = read_quoted_string(stream)

    assert '\n' in result
    assert '\t' in result
    print("✓ test_quoted_string_with_escapes passed")


def test_read_integer_positive():
    """Test reading positive integers."""
    data = b'12345 '
    stream = BytesIO(data)
    result = read_integer(stream)

    assert result == 12345
    print("✓ test_read_integer_positive passed")


def test_read_integer_negative():
    """Test reading negative integers."""
    data = b'-999 '
    stream = BytesIO(data)
    result = read_integer(stream)

    assert result == -999
    print("✓ test_read_integer_negative passed")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*70)
    print("Agent 16: Extended ASCII Metadata Opcodes (2/3) - Test Suite")
    print("="*70 + "\n")

    tests = [
        test_copyright_basic,
        test_copyright_with_special_chars,
        test_creator_basic,
        test_creator_with_version,
        test_creation_time_basic,
        test_creation_time_with_guid,
        test_modification_time_basic,
        test_modification_time_later_than_creation,
        test_source_creation_time,
        test_source_modification_time,
        test_timestamp_format_conversion,
        test_dispatcher,
        test_quoted_string_with_escapes,
        test_read_integer_positive,
        test_read_integer_negative,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
