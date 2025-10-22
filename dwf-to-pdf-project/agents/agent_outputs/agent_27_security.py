"""
Agent 27: DWF Extended ASCII Security Opcodes

This module implements 4 Extended ASCII security opcodes + generic unknown handler:
1. WD_EXAO_ENCRYPTION (ID 324) - `(Encryption` - Encryption info
2. WD_EXAO_PASSWORD (ID 329) - `(Psswd` - Password (32 bytes)
3. WD_EXAO_SIGNDATA (ID 359) - `(SignData` - Digital signature data
4. WD_EXAO_UNKNOWN (ID 292) - Generic unknown opcode handler (catchall)

SECURITY WARNING:
================
These opcodes handle sensitive security-related data including:
- Encryption settings (deprecated, not fully implemented in DWF spec)
- Password data (32-byte fixed length, used for ZIP encryption)
- Digital signature data (deprecated, never fully implemented)

According to DWF Toolkit documentation:
- Encryption and SignData opcodes were deprecated and never completed
- These features were moved to DWF package format instead of 2D channel
- Password opcode is used for ZIP-level encryption in DWF containers
- All security opcodes remain for backward compatibility with DWF v00.55

Based on DWF Toolkit C++ source code from:
- blockref_defs.cpp (encryption, password implementations)
- signdata.cpp (signature data implementation)
- unknown.cpp (unknown opcode handler)
- opcode.cpp (opcode routing and identification)

Reference: Agent 13 Extended Opcodes Research
"""

from typing import Dict, List, Tuple, Optional, Any, Union, BinaryIO
from io import BytesIO
import struct


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class DWFParseError(Exception):
    """Base exception for DWF parsing errors."""
    pass


class CorruptFileError(DWFParseError):
    """File structure is corrupted."""
    pass


class SecurityOpcodeWarning(DWFParseError):
    """Security opcode encountered (deprecated features)."""
    pass


# ============================================================================
# EXTENDED ASCII PARSER HELPER CLASS
# ============================================================================

class ExtendedASCIIParser:
    """
    Parser for Extended ASCII opcodes in DWF files.

    Extended ASCII opcodes have the format: (OpcodeName field1 field2 ... fieldN)

    Parsing rules (from opcode.cpp:138-166):
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
        """Check if byte is a legal opcode character."""
        return (0x21 <= byte <= 0x7A and
                byte != ord('(') and
                byte != ord(')'))

    @staticmethod
    def is_terminator(byte: int) -> bool:
        """Check if byte is an opcode terminator."""
        return (byte in (ord(' '), ord('\t'), ord('\n'), ord('\r')) or
                byte == ord('(') or
                byte == ord(')'))

    @staticmethod
    def eat_whitespace(stream: BytesIO) -> None:
        """Skip whitespace characters in stream."""
        while True:
            byte = stream.read(1)
            if not byte:
                break
            if byte not in (b' ', b'\t', b'\n', b'\r'):
                stream.seek(-1, 1)
                break

    def skip_to_matching_paren(self, stream: BytesIO) -> int:
        """
        Skip to the closing parenthesis matching the current level.

        Args:
            stream: Input byte stream

        Returns:
            Number of bytes skipped

        Raises:
            CorruptFileError: If EOF reached before matching paren
        """
        depth = 1
        bytes_skipped = 0

        while depth > 0:
            byte = stream.read(1)
            if not byte:
                raise CorruptFileError("Unexpected EOF while seeking matching paren")

            bytes_skipped += 1

            if byte == b'(':
                depth += 1
            elif byte == b')':
                depth -= 1

        return bytes_skipped


# ============================================================================
# OPCODE 1: WD_EXAO_ENCRYPTION (ID 324)
# ============================================================================

class EncryptionDescription:
    """Encryption description enumeration (from blockref_defs.h)"""
    NONE = 0x00000001
    RESERVED1 = 0x00000002
    RESERVED2 = 0x00000004
    RESERVED3 = 0x00000008


def parse_encryption_ascii(stream: BytesIO, parser: ExtendedASCIIParser) -> Dict[str, Any]:
    """
    Parse WD_EXAO_ENCRYPTION opcode in Extended ASCII format.

    Format (from blockref_defs.cpp:286-302):
        (Encryption "None     " | "Reserved1" | "Reserved2" | "Reserved3")

    WARNING: This opcode is DEPRECATED. According to DWF Toolkit documentation,
    encryption was never fully implemented and was moved to package-level security.

    Args:
        stream: Input byte stream positioned after "(Encryption"
        parser: Extended ASCII parser instance

    Returns:
        Dictionary containing:
        - 'type': 'encryption'
        - 'description': One of EncryptionDescription values
        - 'description_name': String name of description
        - 'deprecated': True (warning flag)

    Raises:
        CorruptFileError: If format is invalid
    """
    parser.eat_whitespace(stream)

    # Read quoted string (max 40 chars based on C++ code line 326)
    format_str = []
    in_quotes = False

    byte = stream.read(1)
    if byte == b'"':
        in_quotes = True
    else:
        stream.seek(-1, 1)

    while True:
        byte = stream.read(1)
        if not byte:
            raise CorruptFileError("Unexpected EOF reading encryption description")

        if byte == b'"':
            break
        elif byte == b')':
            stream.seek(-1, 1)
            break
        else:
            format_str.append(byte)

    format_text = b''.join(format_str).decode('ascii').strip()

    # Map string to description value
    if format_text == "None":
        description = EncryptionDescription.NONE
        desc_name = "None"
    elif format_text == "Reserved1":
        description = EncryptionDescription.RESERVED1
        desc_name = "Reserved1"
    elif format_text == "Reserved2":
        description = EncryptionDescription.RESERVED2
        desc_name = "Reserved2"
    elif format_text == "Reserved3":
        description = EncryptionDescription.RESERVED3
        desc_name = "Reserved3"
    else:
        raise CorruptFileError(f"Invalid encryption description: {format_text}")

    # Skip to closing paren
    parser.skip_to_matching_paren(stream)

    return {
        'type': 'encryption',
        'opcode_id': 324,
        'opcode_name': 'WD_EXAO_ENCRYPTION',
        'description': description,
        'description_name': desc_name,
        'deprecated': True,
        'warning': 'Encryption opcode is deprecated and was never fully implemented'
    }


def parse_encryption_binary(stream: BytesIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_ENCRYPTION opcode in Extended Binary format.

    Format (from blockref_defs.cpp:273-281):
        { + size(4 bytes) + opcode(2 bytes) + description(2 bytes) + }

    Args:
        stream: Input byte stream positioned after opening '{'

    Returns:
        Dictionary with encryption information

    Raises:
        CorruptFileError: If format is invalid
    """
    # Read size (4 bytes, little-endian)
    size_bytes = stream.read(4)
    if len(size_bytes) != 4:
        raise CorruptFileError("EOF reading encryption binary size")
    size = struct.unpack('<I', size_bytes)[0]

    # Read opcode (2 bytes)
    opcode_bytes = stream.read(2)
    if len(opcode_bytes) != 2:
        raise CorruptFileError("EOF reading encryption binary opcode")
    opcode = struct.unpack('<H', opcode_bytes)[0]

    # Verify opcode
    # Note: WD_EXBO_ENCRYPTION value from opcode_defs.h (ID 323 for binary)

    # Read description (2 bytes, unsigned)
    desc_bytes = stream.read(2)
    if len(desc_bytes) != 2:
        raise CorruptFileError("EOF reading encryption description")
    description = struct.unpack('<H', desc_bytes)[0]

    # Map to description name
    desc_map = {
        EncryptionDescription.NONE: "None",
        EncryptionDescription.RESERVED1: "Reserved1",
        EncryptionDescription.RESERVED2: "Reserved2",
        EncryptionDescription.RESERVED3: "Reserved3"
    }
    desc_name = desc_map.get(description, f"Unknown({description})")

    # Read closing brace
    close = stream.read(1)
    if close != b'}':
        raise CorruptFileError("Expected '}' at end of encryption binary opcode")

    return {
        'type': 'encryption',
        'opcode_id': 323,  # Binary opcode ID
        'opcode_name': 'WD_EXBO_ENCRYPTION',
        'description': description,
        'description_name': desc_name,
        'deprecated': True,
        'warning': 'Encryption opcode is deprecated and was never fully implemented'
    }


# ============================================================================
# OPCODE 2: WD_EXAO_PASSWORD (ID 329)
# ============================================================================

def parse_password_ascii(stream: BytesIO, parser: ExtendedASCIIParser) -> Dict[str, Any]:
    """
    Parse WD_EXAO_PASSWORD opcode in Extended ASCII format.

    Format (from blockref_defs.cpp:962-968):
        (Psswd '32-byte-password-string')

    The password is always exactly 32 bytes, enclosed in single quotes.

    SECURITY WARNING: This password is used for ZIP-level encryption in DWF
    containers. Handle with appropriate security measures.

    Args:
        stream: Input byte stream positioned after "(Psswd"
        parser: Extended ASCII parser instance

    Returns:
        Dictionary containing:
        - 'type': 'password'
        - 'password': bytes (32 bytes, may contain nulls)
        - 'has_password': bool (True if non-empty)

    Raises:
        CorruptFileError: If format is invalid
    """
    parser.eat_whitespace(stream)

    # Read opening single quote
    quote = stream.read(1)
    if quote != b"'":
        raise CorruptFileError(f"Expected single quote for password, got {quote}")

    # Read exactly 32 bytes (from blockref_defs.cpp:966)
    password_data = stream.read(32)
    if len(password_data) != 32:
        raise CorruptFileError(f"Expected 32-byte password, got {len(password_data)} bytes")

    # Read closing single quote
    quote = stream.read(1)
    if quote != b"'":
        raise CorruptFileError(f"Expected closing quote for password, got {quote}")

    # Skip to closing paren
    parser.skip_to_matching_paren(stream)

    # Check if password is empty (all nulls)
    has_password = any(b != 0 for b in password_data)

    return {
        'type': 'password',
        'opcode_id': 329,
        'opcode_name': 'WD_EXAO_PASSWORD',
        'password': password_data,
        'has_password': has_password,
        'warning': 'Password data for ZIP encryption - handle securely'
    }


def parse_password_binary(stream: BytesIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_PASSWORD opcode in Extended Binary format.

    Format (from blockref_defs.cpp:952-956):
        { + size(4 bytes) + opcode(2 bytes) + password(32 bytes) + }

    Args:
        stream: Input byte stream positioned after opening '{'

    Returns:
        Dictionary with password information

    Raises:
        CorruptFileError: If format is invalid
    """
    # Read size (4 bytes, little-endian)
    size_bytes = stream.read(4)
    if len(size_bytes) != 4:
        raise CorruptFileError("EOF reading password binary size")
    size = struct.unpack('<I', size_bytes)[0]

    # Read opcode (2 bytes)
    opcode_bytes = stream.read(2)
    if len(opcode_bytes) != 2:
        raise CorruptFileError("EOF reading password binary opcode")
    opcode = struct.unpack('<H', opcode_bytes)[0]

    # Read 32 bytes of password data
    password_data = stream.read(32)
    if len(password_data) != 32:
        raise CorruptFileError(f"Expected 32-byte password, got {len(password_data)} bytes")

    # Read closing brace
    close = stream.read(1)
    if close != b'}':
        raise CorruptFileError("Expected '}' at end of password binary opcode")

    # Check if password is empty
    has_password = any(b != 0 for b in password_data)

    return {
        'type': 'password',
        'opcode_id': 331,  # Binary opcode ID
        'opcode_name': 'WD_EXBO_PASSWORD',
        'password': password_data,
        'has_password': has_password,
        'warning': 'Password data for ZIP encryption - handle securely'
    }


# ============================================================================
# OPCODE 3: WD_EXAO_SIGNDATA (ID 359)
# ============================================================================

def parse_signdata_ascii(stream: BytesIO, parser: ExtendedASCIIParser) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SIGNDATA opcode in Extended ASCII format.

    Format (from signdata.cpp:117-136):
        (SignData block_list_flag [guid_list] data_size hex_data)

    Where:
        - block_list_flag: '0' or '1' (whether GUID list is present)
        - guid_list: Optional GUID list opcode (if flag is '1')
        - data_size: Integer size of signature data
        - hex_data: Hexadecimal encoded signature data

    WARNING: This opcode is DEPRECATED. Digital signature support was never
    completed in the DWF 2D channel format and was moved to package level.

    Args:
        stream: Input byte stream positioned after "(SignData"
        parser: Extended ASCII parser instance

    Returns:
        Dictionary containing:
        - 'type': 'signdata'
        - 'has_guid_list': bool
        - 'data_size': int
        - 'data': bytes (raw signature data)
        - 'deprecated': True

    Raises:
        CorruptFileError: If format is invalid
    """
    parser.eat_whitespace(stream)

    # Read block list flag (from signdata.cpp:221)
    flag_byte = stream.read(1)
    if flag_byte not in (b'0', b'1'):
        raise CorruptFileError(f"Invalid signdata block list flag: {flag_byte}")

    has_guid_list = (flag_byte == b'1')
    guid_list_data = None

    # If flag is 1, read GUID list (would need to parse nested opcode)
    # For now, we'll skip it as GUID list parsing is complex
    if has_guid_list:
        parser.eat_whitespace(stream)
        # Skip the GUID list opcode (simplified - would need full opcode parser)
        # This would be a nested opcode like (GuidList ...)
        if stream.read(1) == b'(':
            stream.seek(-1, 1)
            parser.skip_to_matching_paren(stream)

    # Read data size
    parser.eat_whitespace(stream)
    data_size_str = []
    while True:
        byte = stream.read(1)
        if not byte:
            raise CorruptFileError("EOF reading signdata size")
        if byte in (b' ', b'\t', b'\n', b'\r'):
            break
        data_size_str.append(byte)

    data_size = int(b''.join(data_size_str).decode('ascii'))

    # Read hex-encoded signature data (from signdata.cpp:132)
    parser.eat_whitespace(stream)
    hex_data = []

    if data_size > 0:
        # Read hex characters (2 chars per byte)
        expected_hex_chars = data_size * 2
        hex_chars = stream.read(expected_hex_chars)
        if len(hex_chars) != expected_hex_chars:
            raise CorruptFileError(f"Expected {expected_hex_chars} hex chars, got {len(hex_chars)}")

        # Decode hex to bytes
        signature_data = bytes.fromhex(hex_chars.decode('ascii'))
    else:
        signature_data = b''

    # Skip to closing paren
    parser.eat_whitespace(stream)
    parser.skip_to_matching_paren(stream)

    return {
        'type': 'signdata',
        'opcode_id': 359,
        'opcode_name': 'WD_EXAO_SIGNDATA',
        'has_guid_list': has_guid_list,
        'data_size': data_size,
        'data': signature_data,
        'deprecated': True,
        'warning': 'SignData opcode is deprecated - signature support was never completed'
    }


def parse_signdata_binary(stream: BytesIO) -> Dict[str, Any]:
    """
    Parse WD_EXAO_SIGNDATA opcode in Extended Binary format.

    Format (from signdata.cpp:78-109):
        { + size(4) + opcode(2) + flag(1) + [guid_list] + data_size(4) + data + }

    Args:
        stream: Input byte stream positioned after opening '{'

    Returns:
        Dictionary with signature data information

    Raises:
        CorruptFileError: If format is invalid
    """
    # Read size (4 bytes, little-endian)
    size_bytes = stream.read(4)
    if len(size_bytes) != 4:
        raise CorruptFileError("EOF reading signdata binary size")
    size = struct.unpack('<I', size_bytes)[0]

    # Read opcode (2 bytes)
    opcode_bytes = stream.read(2)
    if len(opcode_bytes) != 2:
        raise CorruptFileError("EOF reading signdata binary opcode")
    opcode = struct.unpack('<H', opcode_bytes)[0]

    # Read block list flag (1 byte, from signdata.cpp:164)
    flag = stream.read(1)
    has_guid_list = (flag == b'1')

    # If flag is 1, skip GUID list (simplified)
    if has_guid_list:
        # Would need to parse nested binary opcode for GUID list
        # For now, skip it (this is complex and rarely used)
        pass

    # Read data size (4 bytes, from signdata.cpp:180)
    data_size_bytes = stream.read(4)
    if len(data_size_bytes) != 4:
        raise CorruptFileError("EOF reading signdata data size")
    data_size = struct.unpack('<i', data_size_bytes)[0]

    # Read signature data
    if data_size > 0:
        signature_data = stream.read(data_size)
        if len(signature_data) != data_size:
            raise CorruptFileError(f"Expected {data_size} bytes of signature data")
    else:
        signature_data = b''

    # Read closing brace
    close = stream.read(1)
    if close != b'}':
        raise CorruptFileError("Expected '}' at end of signdata binary opcode")

    return {
        'type': 'signdata',
        'opcode_id': 358,  # Binary opcode ID
        'opcode_name': 'WD_EXBO_SIGNDATA',
        'has_guid_list': has_guid_list,
        'data_size': data_size,
        'data': signature_data,
        'deprecated': True,
        'warning': 'SignData opcode is deprecated - signature support was never completed'
    }


# ============================================================================
# OPCODE 4: WD_EXAO_UNKNOWN (ID 292) - Generic Unknown Handler
# ============================================================================

def parse_unknown_ascii(stream: BytesIO, opcode_name: str, parser: ExtendedASCIIParser) -> Dict[str, Any]:
    """
    Generic handler for unknown Extended ASCII opcodes.

    This is a catchall handler that captures the raw bytes of any unrecognized
    opcode for pass-through or debugging purposes.

    Implementation based on unknown.cpp:94-119.

    Args:
        stream: Input byte stream
        opcode_name: The unrecognized opcode name
        parser: Extended ASCII parser instance

    Returns:
        Dictionary containing:
        - 'type': 'unknown'
        - 'opcode_name': The unrecognized opcode name
        - 'raw_data': bytes (all data including parens)
        - 'format': 'extended_ascii'

    Raises:
        CorruptFileError: If cannot skip to end
    """
    # Remember starting position
    start_pos = stream.tell()

    # Seek back to beginning of opcode (before the '(')
    # We need to capture the full opcode for pass-through
    stream.seek(-len(opcode_name) - 1, 1)
    capture_start = stream.tell()

    # Skip to matching closing paren
    stream.seek(len(opcode_name) + 1, 1)  # Back to where we were
    bytes_skipped = parser.skip_to_matching_paren(stream)

    # Now capture all the bytes
    end_pos = stream.tell()
    stream.seek(capture_start)
    raw_data = stream.read(end_pos - capture_start)

    return {
        'type': 'unknown',
        'opcode_id': 292,
        'opcode_name': opcode_name,
        'raw_data': raw_data,
        'data_size': len(raw_data),
        'format': 'extended_ascii',
        'warning': f'Unknown opcode "{opcode_name}" - captured for pass-through'
    }


def parse_unknown_binary(stream: BytesIO, opcode_value: int) -> Dict[str, Any]:
    """
    Generic handler for unknown Extended Binary opcodes.

    This captures the raw bytes of unrecognized binary opcodes.

    Implementation based on unknown.cpp:120-151.

    Args:
        stream: Input byte stream positioned after opening '{'
        opcode_value: The unrecognized opcode value (16-bit)

    Returns:
        Dictionary with unknown opcode information

    Raises:
        CorruptFileError: If format is invalid
    """
    # We've already read the '{', now read size
    size_bytes = stream.read(4)
    if len(size_bytes) != 4:
        raise CorruptFileError("EOF reading unknown binary size")
    size = struct.unpack('<I', size_bytes)[0]

    # Read opcode (2 bytes) - already know it's unknown
    opcode_bytes = stream.read(2)

    # Build raw data buffer to capture everything
    # Include the opening brace, size, and opcode
    raw_data = b'{' + size_bytes + opcode_bytes

    # Read remaining data (size includes opcode + data + closing brace)
    # We've read 2 bytes (opcode), so read (size - 2) more
    remaining = size - 2
    if remaining > 0:
        rest_data = stream.read(remaining)
        if len(rest_data) != remaining:
            raise CorruptFileError(f"Expected {remaining} more bytes for unknown opcode")
        raw_data += rest_data

    return {
        'type': 'unknown',
        'opcode_id': 302,  # WD_EXBO_UNKNOWN
        'opcode_value': opcode_value,
        'raw_data': raw_data,
        'data_size': len(raw_data),
        'format': 'extended_binary',
        'warning': f'Unknown binary opcode 0x{opcode_value:04X} - captured for pass-through'
    }


# ============================================================================
# MAIN OPCODE DISPATCHER
# ============================================================================

def parse_security_opcode(stream: BytesIO, opcode_name: str) -> Dict[str, Any]:
    """
    Main dispatcher for security-related Extended ASCII opcodes.

    Args:
        stream: Input byte stream
        opcode_name: Name of the opcode (e.g., "Encryption", "Psswd", "SignData")

    Returns:
        Parsed opcode data dictionary

    Raises:
        CorruptFileError: If parsing fails
    """
    parser = ExtendedASCIIParser()

    if opcode_name == "Encryption":
        return parse_encryption_ascii(stream, parser)
    elif opcode_name == "Psswd":
        return parse_password_ascii(stream, parser)
    elif opcode_name == "SignData":
        return parse_signdata_ascii(stream, parser)
    else:
        # Unknown opcode - use generic handler
        return parse_unknown_ascii(stream, opcode_name, parser)


# ============================================================================
# TESTS
# ============================================================================

def test_encryption_ascii():
    """Test WD_EXAO_ENCRYPTION ASCII parsing."""
    print("\n" + "=" * 70)
    print("TEST: WD_EXAO_ENCRYPTION (ASCII Format)")
    print("=" * 70)

    # Test 1: None encryption
    test_data1 = b' "None     ")'
    stream1 = BytesIO(test_data1)
    parser = ExtendedASCIIParser()
    result1 = parse_encryption_ascii(stream1, parser)

    print("\nTest 1: Encryption = None")
    print(f"  Input: {test_data1}")
    print(f"  Result: {result1}")
    assert result1['description'] == EncryptionDescription.NONE
    assert result1['description_name'] == "None"
    assert result1['deprecated'] == True
    print("  ✓ PASSED")

    # Test 2: Reserved1 encryption
    test_data2 = b' "Reserved1")'
    stream2 = BytesIO(test_data2)
    result2 = parse_encryption_ascii(stream2, parser)

    print("\nTest 2: Encryption = Reserved1")
    print(f"  Input: {test_data2}")
    print(f"  Result: {result2}")
    assert result2['description'] == EncryptionDescription.RESERVED1
    assert result2['description_name'] == "Reserved1"
    print("  ✓ PASSED")

    print("\n✓ All encryption ASCII tests passed!")


def test_password_ascii():
    """Test WD_EXAO_PASSWORD ASCII parsing."""
    print("\n" + "=" * 70)
    print("TEST: WD_EXAO_PASSWORD (ASCII Format)")
    print("=" * 70)

    # Test 1: Password with data
    password_bytes = b'MySecretPassword123456789012'  # 28 chars
    password_bytes += b'\x00' * 4  # Pad to 32 bytes
    test_data1 = b" '" + password_bytes + b"' )"

    stream1 = BytesIO(test_data1)
    parser = ExtendedASCIIParser()
    result1 = parse_password_ascii(stream1, parser)

    print("\nTest 1: Password with data")
    print(f"  Password length: {len(result1['password'])} bytes")
    print(f"  Has password: {result1['has_password']}")
    assert len(result1['password']) == 32
    assert result1['has_password'] == True
    assert result1['password'][:28] == b'MySecretPassword123456789012'
    print("  ✓ PASSED")

    # Test 2: Empty password (all nulls)
    test_data2 = b" '" + (b'\x00' * 32) + b"' )"
    stream2 = BytesIO(test_data2)
    result2 = parse_password_ascii(stream2, parser)

    print("\nTest 2: Empty password")
    print(f"  Has password: {result2['has_password']}")
    assert result2['has_password'] == False
    assert result2['password'] == b'\x00' * 32
    print("  ✓ PASSED")

    print("\n✓ All password ASCII tests passed!")


def test_signdata_ascii():
    """Test WD_EXAO_SIGNDATA ASCII parsing."""
    print("\n" + "=" * 70)
    print("TEST: WD_EXAO_SIGNDATA (ASCII Format)")
    print("=" * 70)

    # Test 1: SignData without GUID list
    sig_data = b'\x01\x02\x03\x04\xAA\xBB\xCC\xDD'
    hex_data = sig_data.hex().encode('ascii')
    test_data1 = b' 0 8 ' + hex_data + b' )'

    stream1 = BytesIO(test_data1)
    parser = ExtendedASCIIParser()
    result1 = parse_signdata_ascii(stream1, parser)

    print("\nTest 1: SignData without GUID list")
    print(f"  Input hex: {hex_data}")
    print(f"  Has GUID list: {result1['has_guid_list']}")
    print(f"  Data size: {result1['data_size']}")
    print(f"  Data: {result1['data'].hex()}")
    assert result1['has_guid_list'] == False
    assert result1['data_size'] == 8
    assert result1['data'] == sig_data
    assert result1['deprecated'] == True
    print("  ✓ PASSED")

    # Test 2: SignData with empty data
    test_data2 = b' 0 0 )'
    stream2 = BytesIO(test_data2)
    result2 = parse_signdata_ascii(stream2, parser)

    print("\nTest 2: SignData with empty data")
    print(f"  Data size: {result2['data_size']}")
    assert result2['data_size'] == 0
    assert result2['data'] == b''
    print("  ✓ PASSED")

    print("\n✓ All signdata ASCII tests passed!")


def test_unknown_handler():
    """Test WD_EXAO_UNKNOWN generic handler."""
    print("\n" + "=" * 70)
    print("TEST: WD_EXAO_UNKNOWN (Generic Handler)")
    print("=" * 70)

    # Test: Unknown opcode with simple data
    test_data = b'UnknownOpcode Field1 Field2 "Value")'
    stream = BytesIO(b'(' + test_data)
    parser = ExtendedASCIIParser()

    result = parse_unknown_ascii(stream, "UnknownOpcode", parser)

    print("\nTest: Unknown opcode capture")
    print(f"  Opcode name: {result['opcode_name']}")
    print(f"  Raw data size: {result['data_size']} bytes")
    print(f"  Format: {result['format']}")
    assert result['opcode_name'] == "UnknownOpcode"
    assert result['format'] == 'extended_ascii'
    assert len(result['raw_data']) > 0
    print("  ✓ PASSED")

    print("\n✓ Unknown handler test passed!")


def run_all_tests():
    """Run all security opcode tests."""
    print("\n" + "=" * 70)
    print("AGENT 27: SECURITY OPCODES TEST SUITE")
    print("=" * 70)
    print("\nTesting 4 security opcodes + unknown handler:")
    print("1. WD_EXAO_ENCRYPTION (ID 324)")
    print("2. WD_EXAO_PASSWORD (ID 329)")
    print("3. WD_EXAO_SIGNDATA (ID 359)")
    print("4. WD_EXAO_UNKNOWN (ID 292)")

    try:
        test_encryption_ascii()
        test_password_ascii()
        test_signdata_ascii()
        test_unknown_handler()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        print("\nSECURITY WARNINGS:")
        print("- Encryption and SignData opcodes are DEPRECATED")
        print("- These features were never fully implemented in DWF")
        print("- Password opcode handles ZIP encryption keys")
        print("- All security features moved to DWF package level")
        print("- These opcodes remain for backward compatibility only")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_all_tests()
