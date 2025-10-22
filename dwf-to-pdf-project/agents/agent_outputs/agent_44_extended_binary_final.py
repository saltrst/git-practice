"""
DWF Extended Binary Opcodes (Final) - Agent 44

This module implements parsers for 3 final DWF extended binary opcodes:
- WD_EXBO_ENCRYPTION (0x0027 / ID 323): Encryption metadata
- WD_EXBO_PASSWORD (ID 331): Password hash
- WD_EXBO_UNKNOWN (ID 302): Fallback handler for unknown extended binary opcodes

These opcodes use the Extended Binary format: {(1 byte) + Size(4 bytes LE) +
Opcode(2 bytes LE) + Data(variable) + }(1 byte)

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/opcode.cpp
- develop/global/src/dwf/whiptk/encryption.cpp
- develop/global/src/dwf/whiptk/password.cpp
- Agent 13 Extended Opcodes Research (section 1.2)

Author: Agent 44 (Extended Binary Final Specialist)
"""

import struct
from typing import Dict, Tuple, BinaryIO


# Encryption method enumeration
ENCRYPTION_METHODS = {
    0: 'none',
    1: 'aes128',
    2: 'aes256'
}

# Password hash type enumeration
PASSWORD_HASH_TYPES = {
    0: 'md5',
    1: 'sha256'
}


# =============================================================================
# EXTENDED BINARY PARSER HELPER
# =============================================================================

def parse_extended_binary_header(stream: BinaryIO) -> Tuple[int, int]:
    """
    Parse the header of an Extended Binary opcode block.

    Extended Binary Format:
        { (1 byte) + Size (4 bytes LE) + Opcode (2 bytes LE) + Data + } (1 byte)

    This helper function reads and validates the opening brace, size field,
    and opcode value. It returns the opcode and data size for further processing.

    Args:
        stream: Binary stream positioned at start of Extended Binary block

    Returns:
        Tuple containing:
            - opcode_value (int): The 16-bit opcode identifier (0-65535)
            - data_size (int): Size of data portion (excludes header and closing brace)

    Raises:
        ValueError: If format is invalid (missing braces, insufficient data)
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> # Build Extended Binary block: { + size(7) + opcode(0x0027) + data + }
        >>> size = struct.pack('<I', 2 + 5 + 1)  # opcode + data + closing brace
        >>> opcode = struct.pack('<H', 0x0027)
        >>> data = b'hello'
        >>> block = b'{' + size + opcode + data + b'}'
        >>> stream = io.BytesIO(block)
        >>> opcode_val, data_size = parse_extended_binary_header(stream)
        >>> opcode_val
        39  # 0x0027
        >>> data_size
        5

    Notes:
        - Total header size: 7 bytes (1 + 4 + 2)
        - Size field includes: opcode (2 bytes) + data + closing brace (1 byte)
        - Data size calculation: size_field - 2 - 1
        - Little-endian byte order for size and opcode
        - Opening '{' must be present at current stream position
    """
    # Read opening brace
    opening_brace = stream.read(1)
    if not opening_brace:
        raise ValueError("Unexpected end of stream reading Extended Binary opening brace")
    if opening_brace != b'{':
        raise ValueError(f"Expected '{{' for Extended Binary opcode, got {opening_brace!r}")

    # Read size field (4 bytes, little-endian unsigned 32-bit integer)
    size_bytes = stream.read(4)
    if len(size_bytes) != 4:
        raise ValueError(f"Expected 4 bytes for size field, got {len(size_bytes)} bytes")
    size = struct.unpack('<I', size_bytes)[0]

    # Read opcode value (2 bytes, little-endian unsigned 16-bit integer)
    opcode_bytes = stream.read(2)
    if len(opcode_bytes) != 2:
        raise ValueError(f"Expected 2 bytes for opcode field, got {len(opcode_bytes)} bytes")
    opcode_value = struct.unpack('<H', opcode_bytes)[0]

    # Calculate data size
    # Size field includes: opcode (2 bytes) + data + closing brace (1 byte)
    # Therefore: data_size = size - 2 - 1
    if size < 3:
        raise ValueError(f"Invalid size field: {size} (must be at least 3)")
    data_size = size - 2 - 1

    return opcode_value, data_size


def read_extended_binary_data(stream: BinaryIO, data_size: int) -> bytes:
    """
    Read the data portion of an Extended Binary block and validate closing brace.

    Args:
        stream: Binary stream positioned after Extended Binary header
        data_size: Number of data bytes to read

    Returns:
        bytes: The raw data from the Extended Binary block

    Raises:
        ValueError: If insufficient data or missing closing brace

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'hello}')
        >>> data = read_extended_binary_data(stream, 5)
        >>> data
        b'hello'

    Notes:
        - Reads exactly data_size bytes
        - Validates closing '}' after data
        - Raises error if closing brace is missing or incorrect
    """
    # Read data
    data = stream.read(data_size)
    if len(data) != data_size:
        raise ValueError(f"Expected {data_size} bytes of data, got {len(data)} bytes")

    # Read and validate closing brace
    closing_brace = stream.read(1)
    if not closing_brace:
        raise ValueError("Unexpected end of stream reading Extended Binary closing brace")
    if closing_brace != b'}':
        raise ValueError(f"Expected '}}' at end of Extended Binary block, got {closing_brace!r}")

    return data


# =============================================================================
# OPCODE WD_EXBO_ENCRYPTION (0x0027 / ID 323)
# =============================================================================

def parse_opcode_exbo_encryption(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended Binary opcode WD_EXBO_ENCRYPTION (0x0027, ID 323).

    This opcode contains encryption metadata describing the encryption method
    and key hash used to protect the DWF content.

    Format Specification:
    - Extended Binary format: { + Size + Opcode + Data + }
    - Opcode value: 0x0027 (39 decimal, alternative ID 323)
    - Data structure:
        * Method (1 byte): 0=none, 1=AES128, 2=AES256
        * Key hash (16 bytes): MD5 hash of encryption key
    - Total data size: 17 bytes (1 + 16)

    C++ Reference:
    From encryption.cpp - WT_Encryption::materialize():
        // Read Extended Binary block
        WT_Byte method;
        WD_CHECK(file.read(method));
        WT_Byte key_hash[16];
        WD_CHECK(file.read(16, key_hash));
        m_method = method;
        memcpy(m_key_hash, key_hash, 16);

    Args:
        stream: Binary stream positioned at start of Extended Binary block

    Returns:
        Dictionary containing:
            - 'type': 'encryption'
            - 'method': Integer method ID (0-2)
            - 'method_name': String method name ('none', 'aes128', 'aes256')
            - 'key_hash': bytes (16 bytes MD5 hash)

    Raises:
        ValueError: If format is invalid, insufficient data, or method is invalid
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> # Build Extended Binary block for AES256 encryption
        >>> method = struct.pack('B', 2)  # AES256
        >>> key_hash = b'\\x01\\x23\\x45\\x67\\x89\\xAB\\xCD\\xEF' * 2  # 16 bytes
        >>> data = method + key_hash
        >>> size = struct.pack('<I', 2 + len(data) + 1)
        >>> opcode = struct.pack('<H', 0x0027)
        >>> block = b'{' + size + opcode + data + b'}'
        >>> stream = io.BytesIO(block)
        >>> result = parse_opcode_exbo_encryption(stream)
        >>> result['method_name']
        'aes256'

    Notes:
        - Corresponds to WT_Encryption::materialize() in C++
        - Method 0 (none): No encryption applied
        - Method 1 (AES128): AES encryption with 128-bit key
        - Method 2 (AES256): AES encryption with 256-bit key
        - Key hash is MD5 (16 bytes) for key verification
        - Invalid methods (3+) raise ValueError
        - Actual decryption requires the full encryption key
    """
    # Parse Extended Binary header
    opcode_value, data_size = parse_extended_binary_header(stream)

    # Verify opcode value (should be 0x0027 = 39)
    if opcode_value != 0x0027:
        raise ValueError(f"Expected opcode 0x0027 (ENCRYPTION), got 0x{opcode_value:04X}")

    # Verify data size (should be 17 bytes: 1 byte method + 16 bytes key_hash)
    if data_size != 17:
        raise ValueError(f"Expected 17 bytes of data for ENCRYPTION, got {data_size} bytes")

    # Read data
    data = read_extended_binary_data(stream, data_size)

    # Parse method (1 byte)
    method = struct.unpack('B', data[0:1])[0]
    if method > 2:
        raise ValueError(f"Invalid encryption method: {method} (valid range: 0-2)")

    # Parse key hash (16 bytes)
    key_hash = data[1:17]
    if len(key_hash) != 16:
        raise ValueError(f"Expected 16 bytes for key_hash, got {len(key_hash)} bytes")

    # Get method name
    method_name = ENCRYPTION_METHODS.get(method, 'unknown')

    return {
        'type': 'encryption',
        'method': method,
        'method_name': method_name,
        'key_hash': key_hash
    }


# =============================================================================
# OPCODE WD_EXBO_PASSWORD (ID 331)
# =============================================================================

def parse_opcode_exbo_password(stream: BinaryIO) -> Dict:
    """
    Parse DWF Extended Binary opcode WD_EXBO_PASSWORD (ID 331).

    This opcode contains a password hash used for DWF file access control.
    The hash type and hash value are stored in the Extended Binary block.

    Format Specification:
    - Extended Binary format: { + Size + Opcode + Data + }
    - Opcode value: Variable (ID 331, exact value depends on implementation)
    - Data structure:
        * Hash type (1 byte): 0=MD5, 1=SHA256
        * Hash value (32 bytes): Password hash (MD5 padded or SHA256)
    - Total data size: 33 bytes (1 + 32)

    C++ Reference:
    From password.cpp - WT_Password::materialize():
        // Read Extended Binary block
        WT_Byte hash_type;
        WD_CHECK(file.read(hash_type));
        WT_Byte hash[32];
        WD_CHECK(file.read(32, hash));
        m_hash_type = hash_type;
        memcpy(m_hash, hash, 32);

    Args:
        stream: Binary stream positioned at start of Extended Binary block

    Returns:
        Dictionary containing:
            - 'type': 'password'
            - 'hash_type': Integer hash type (0-1)
            - 'hash': bytes (32 bytes hash value)

    Raises:
        ValueError: If format is invalid, insufficient data, or hash_type is invalid
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> # Build Extended Binary block for SHA256 password hash
        >>> hash_type = struct.pack('B', 1)  # SHA256
        >>> hash_val = b'\\x00' * 32  # 32-byte hash
        >>> data = hash_type + hash_val
        >>> size = struct.pack('<I', 2 + len(data) + 1)
        >>> opcode = struct.pack('<H', 331)
        >>> block = b'{' + size + opcode + data + b'}'
        >>> stream = io.BytesIO(block)
        >>> result = parse_opcode_exbo_password(stream)
        >>> result['hash_type']
        1

    Notes:
        - Corresponds to WT_Password::materialize() in C++
        - Hash type 0 (MD5): 16-byte MD5 hash, padded to 32 bytes
        - Hash type 1 (SHA256): 32-byte SHA256 hash
        - Invalid hash types (2+) raise ValueError
        - Password verification compares hash of input with stored hash
        - Actual password is never stored, only the hash
    """
    # Parse Extended Binary header
    opcode_value, data_size = parse_extended_binary_header(stream)

    # Verify data size (should be 33 bytes: 1 byte hash_type + 32 bytes hash)
    if data_size != 33:
        raise ValueError(f"Expected 33 bytes of data for PASSWORD, got {data_size} bytes")

    # Read data
    data = read_extended_binary_data(stream, data_size)

    # Parse hash type (1 byte)
    hash_type = struct.unpack('B', data[0:1])[0]
    if hash_type > 1:
        raise ValueError(f"Invalid password hash type: {hash_type} (valid range: 0-1)")

    # Parse hash (32 bytes)
    hash_value = data[1:33]
    if len(hash_value) != 32:
        raise ValueError(f"Expected 32 bytes for hash, got {len(hash_value)} bytes")

    return {
        'type': 'password',
        'hash_type': hash_type,
        'hash': hash_value
    }


# =============================================================================
# OPCODE WD_EXBO_UNKNOWN (ID 302) - Fallback Handler
# =============================================================================

def parse_opcode_exbo_unknown(stream: BinaryIO) -> Dict:
    """
    Parse unknown DWF Extended Binary opcode (WD_EXBO_UNKNOWN, ID 302).

    This is a fallback handler for Extended Binary opcodes that are not
    recognized by the parser. It reads and skips the opcode data, allowing
    the parser to continue processing subsequent opcodes.

    Format Specification:
    - Extended Binary format: { + Size + Opcode + Data + }
    - Opcode value: Any unrecognized value
    - Data structure: Variable (opaque binary data)

    C++ Reference:
    From opcode.cpp - WT_Opcode::materialize():
        default:  // Unknown Extended Binary opcode
            // Skip opcode data
            WD_CHECK(file.seek(size - 2 - 1, SEEK_CUR));
            WD_CHECK(file.read(closing_brace));
            return WT_Result::Unsupported_DWF_Opcode_Warning;

    Args:
        stream: Binary stream positioned at start of Extended Binary block

    Returns:
        Dictionary containing:
            - 'type': 'unknown_binary'
            - 'opcode': Integer opcode value (0-65535)
            - 'data_size': Size of data portion in bytes
            - 'data': bytes (raw opcode data)

    Raises:
        ValueError: If format is invalid or insufficient data
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> # Build Extended Binary block with unknown opcode 0x9999
        >>> data = b'arbitrary_data'
        >>> size = struct.pack('<I', 2 + len(data) + 1)
        >>> opcode = struct.pack('<H', 0x9999)
        >>> block = b'{' + size + opcode + data + b'}'
        >>> stream = io.BytesIO(block)
        >>> result = parse_opcode_exbo_unknown(stream)
        >>> result['opcode']
        39321  # 0x9999
        >>> result['data_size']
        14

    Notes:
        - Corresponds to default case in WT_Opcode::materialize() in C++
        - Handles any Extended Binary opcode not explicitly supported
        - Allows forward compatibility (newer DWF versions)
        - Data is read but not interpreted
        - Parser can continue after skipping unknown opcode
        - Common for proprietary or custom opcodes
        - Useful for debugging and format analysis
    """
    # Parse Extended Binary header
    opcode_value, data_size = parse_extended_binary_header(stream)

    # Read data (opaque binary data)
    data = read_extended_binary_data(stream, data_size)

    return {
        'type': 'unknown_binary',
        'opcode': opcode_value,
        'data_size': data_size,
        'data': data
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_extended_binary_parser_helper():
    """Test suite for Extended Binary parser helper functions."""
    import io

    print("=" * 70)
    print("TESTING EXTENDED BINARY PARSER HELPERS")
    print("=" * 70)

    # Test 1: Basic header parsing
    print("\nTest 1: Parse Extended Binary header (opcode 0x0027, data size 17)")
    size = struct.pack('<I', 2 + 17 + 1)  # opcode + data + closing brace = 20
    opcode = struct.pack('<H', 0x0027)
    data = b'x' * 17
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)

    opcode_val, data_size = parse_extended_binary_header(stream)
    assert opcode_val == 0x0027, f"Expected opcode 0x0027, got 0x{opcode_val:04X}"
    assert data_size == 17, f"Expected data_size 17, got {data_size}"
    print(f"  PASS: opcode=0x{opcode_val:04X}, data_size={data_size}")

    # Test 2: Read data and validate closing brace
    print("\nTest 2: Read Extended Binary data")
    data = read_extended_binary_data(stream, data_size)
    assert len(data) == 17, f"Expected 17 bytes, got {len(data)}"
    print(f"  PASS: Read {len(data)} bytes successfully")

    # Test 3: Error handling - missing opening brace
    print("\nTest 3: Error handling - missing opening brace")
    stream = io.BytesIO(b'X' + size + opcode)
    try:
        opcode_val, data_size = parse_extended_binary_header(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 4: Error handling - missing closing brace
    print("\nTest 4: Error handling - missing closing brace")
    stream = io.BytesIO(b'{' + size + opcode + b'x' * 17 + b'X')
    opcode_val, data_size = parse_extended_binary_header(stream)
    try:
        data = read_extended_binary_data(stream, data_size)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 5: Error handling - insufficient data
    print("\nTest 5: Error handling - insufficient data")
    stream = io.BytesIO(b'{' + size + opcode + b'x' * 10)  # Only 10 bytes instead of 17
    opcode_val, data_size = parse_extended_binary_header(stream)
    try:
        data = read_extended_binary_data(stream, data_size)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("EXTENDED BINARY PARSER HELPERS: ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_exbo_encryption():
    """Test suite for WD_EXBO_ENCRYPTION opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE WD_EXBO_ENCRYPTION (0x0027)")
    print("=" * 70)

    # Test 1: None encryption method
    print("\nTest 1: None encryption method (0)")
    method = struct.pack('B', 0)
    key_hash = b'\x00' * 16
    data = method + key_hash
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x0027)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_encryption(stream)

    assert result['type'] == 'encryption', f"Expected type='encryption', got {result['type']}"
    assert result['method'] == 0, f"Expected method=0, got {result['method']}"
    assert result['method_name'] == 'none', f"Expected method_name='none', got {result['method_name']}"
    assert len(result['key_hash']) == 16, f"Expected 16-byte key_hash, got {len(result['key_hash'])}"
    print(f"  PASS: {result['method_name']}, key_hash={result['key_hash'].hex()[:32]}...")

    # Test 2: AES128 encryption method
    print("\nTest 2: AES128 encryption method (1)")
    method = struct.pack('B', 1)
    key_hash = b'\x01\x23\x45\x67\x89\xAB\xCD\xEF' * 2
    data = method + key_hash
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x0027)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_encryption(stream)

    assert result['method'] == 1
    assert result['method_name'] == 'aes128'
    print(f"  PASS: {result['method_name']}, key_hash={result['key_hash'].hex()[:32]}...")

    # Test 3: AES256 encryption method
    print("\nTest 3: AES256 encryption method (2)")
    method = struct.pack('B', 2)
    key_hash = b'\xFF' * 16
    data = method + key_hash
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x0027)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_encryption(stream)

    assert result['method'] == 2
    assert result['method_name'] == 'aes256'
    print(f"  PASS: {result['method_name']}, key_hash={result['key_hash'].hex()[:32]}...")

    # Test 4: All encryption methods
    print("\nTest 4: All encryption methods (0-2)")
    methods = [(0, 'none'), (1, 'aes128'), (2, 'aes256')]
    for method_id, method_name in methods:
        method = struct.pack('B', method_id)
        key_hash = bytes([method_id] * 16)
        data = method + key_hash
        size = struct.pack('<I', 2 + len(data) + 1)
        opcode = struct.pack('<H', 0x0027)
        block = b'{' + size + opcode + data + b'}'
        stream = io.BytesIO(block)
        result = parse_opcode_exbo_encryption(stream)
        assert result['method'] == method_id
        assert result['method_name'] == method_name
    print(f"  PASS: All 3 encryption methods validated")

    # Test 5: Error handling - invalid method
    print("\nTest 5: Error handling - invalid encryption method (3)")
    method = struct.pack('B', 3)
    key_hash = b'\x00' * 16
    data = method + key_hash
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x0027)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    try:
        result = parse_opcode_exbo_encryption(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 6: Error handling - wrong data size
    print("\nTest 6: Error handling - wrong data size")
    method = struct.pack('B', 0)
    key_hash = b'\x00' * 10  # Only 10 bytes instead of 16
    data = method + key_hash
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x0027)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    try:
        result = parse_opcode_exbo_encryption(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE WD_EXBO_ENCRYPTION: ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_exbo_password():
    """Test suite for WD_EXBO_PASSWORD opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE WD_EXBO_PASSWORD (ID 331)")
    print("=" * 70)

    # Test 1: MD5 hash type
    print("\nTest 1: MD5 hash type (0)")
    hash_type = struct.pack('B', 0)
    hash_val = b'\x00' * 32
    data = hash_type + hash_val
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 331)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_password(stream)

    assert result['type'] == 'password', f"Expected type='password', got {result['type']}"
    assert result['hash_type'] == 0, f"Expected hash_type=0, got {result['hash_type']}"
    assert len(result['hash']) == 32, f"Expected 32-byte hash, got {len(result['hash'])}"
    print(f"  PASS: hash_type=0 (MD5), hash={result['hash'].hex()[:32]}...")

    # Test 2: SHA256 hash type
    print("\nTest 2: SHA256 hash type (1)")
    hash_type = struct.pack('B', 1)
    hash_val = b'\xFF' * 32
    data = hash_type + hash_val
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 331)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_password(stream)

    assert result['hash_type'] == 1
    print(f"  PASS: hash_type=1 (SHA256), hash={result['hash'].hex()[:32]}...")

    # Test 3: All hash types
    print("\nTest 3: All hash types (0-1)")
    hash_types = [0, 1]
    for ht in hash_types:
        hash_type = struct.pack('B', ht)
        hash_val = bytes([ht] * 32)
        data = hash_type + hash_val
        size = struct.pack('<I', 2 + len(data) + 1)
        opcode = struct.pack('<H', 331)
        block = b'{' + size + opcode + data + b'}'
        stream = io.BytesIO(block)
        result = parse_opcode_exbo_password(stream)
        assert result['hash_type'] == ht
    print(f"  PASS: All 2 hash types validated")

    # Test 4: Error handling - invalid hash type
    print("\nTest 4: Error handling - invalid hash type (2)")
    hash_type = struct.pack('B', 2)
    hash_val = b'\x00' * 32
    data = hash_type + hash_val
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 331)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    try:
        result = parse_opcode_exbo_password(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 5: Error handling - wrong data size
    print("\nTest 5: Error handling - wrong data size")
    hash_type = struct.pack('B', 0)
    hash_val = b'\x00' * 20  # Only 20 bytes instead of 32
    data = hash_type + hash_val
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 331)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    try:
        result = parse_opcode_exbo_password(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE WD_EXBO_PASSWORD: ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_exbo_unknown():
    """Test suite for WD_EXBO_UNKNOWN opcode."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE WD_EXBO_UNKNOWN (ID 302) - Fallback Handler")
    print("=" * 70)

    # Test 1: Unknown opcode with small data
    print("\nTest 1: Unknown opcode (0x9999) with small data")
    data = b'test_data'
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x9999)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_unknown(stream)

    assert result['type'] == 'unknown_binary', f"Expected type='unknown_binary', got {result['type']}"
    assert result['opcode'] == 0x9999, f"Expected opcode=0x9999, got 0x{result['opcode']:04X}"
    assert result['data_size'] == len(data), f"Expected data_size={len(data)}, got {result['data_size']}"
    assert result['data'] == data, f"Data mismatch"
    print(f"  PASS: opcode=0x{result['opcode']:04X}, data_size={result['data_size']}, data={result['data']}")

    # Test 2: Unknown opcode with larger data
    print("\nTest 2: Unknown opcode (0xABCD) with larger data")
    data = b'x' * 100
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0xABCD)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_unknown(stream)

    assert result['opcode'] == 0xABCD
    assert result['data_size'] == 100
    assert len(result['data']) == 100
    print(f"  PASS: opcode=0x{result['opcode']:04X}, data_size={result['data_size']}")

    # Test 3: Unknown opcode with zero data
    print("\nTest 3: Unknown opcode (0x1234) with zero data")
    data = b''
    size = struct.pack('<I', 2 + len(data) + 1)
    opcode = struct.pack('<H', 0x1234)
    block = b'{' + size + opcode + data + b'}'
    stream = io.BytesIO(block)
    result = parse_opcode_exbo_unknown(stream)

    assert result['opcode'] == 0x1234
    assert result['data_size'] == 0
    assert result['data'] == b''
    print(f"  PASS: opcode=0x{result['opcode']:04X}, data_size=0, data=empty")

    # Test 4: Multiple unknown opcodes
    print("\nTest 4: Multiple unknown opcodes")
    opcodes = [0x1111, 0x2222, 0x3333]
    for opc in opcodes:
        data = bytes([opc & 0xFF] * 10)
        size = struct.pack('<I', 2 + len(data) + 1)
        opcode = struct.pack('<H', opc)
        block = b'{' + size + opcode + data + b'}'
        stream = io.BytesIO(block)
        result = parse_opcode_exbo_unknown(stream)
        assert result['opcode'] == opc
        assert result['data_size'] == 10
    print(f"  PASS: 3 different unknown opcodes handled")

    print("\n" + "=" * 70)
    print("OPCODE WD_EXBO_UNKNOWN: ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 44 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 44: EXTENDED BINARY FINAL TEST SUITE")
    print("=" * 70)
    print("Testing Extended Binary format and 3 opcodes:")
    print("  - Extended Binary Parser (helper functions)")
    print("  - WD_EXBO_ENCRYPTION (0x0027 / ID 323)")
    print("  - WD_EXBO_PASSWORD (ID 331)")
    print("  - WD_EXBO_UNKNOWN (ID 302) - Fallback handler")
    print("=" * 70)

    test_extended_binary_parser_helper()
    test_opcode_exbo_encryption()
    test_opcode_exbo_password()
    test_opcode_exbo_unknown()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Extended Binary Parser Helpers: 5 tests passed")
    print("  - WD_EXBO_ENCRYPTION (0x0027): 6 tests passed")
    print("  - WD_EXBO_PASSWORD (ID 331): 5 tests passed")
    print("  - WD_EXBO_UNKNOWN (ID 302): 4 tests passed")
    print("  - Total: 20 tests passed")
    print("\nSpecial Features:")
    print("  - Extended Binary format parser (parse_extended_binary_header)")
    print("  - Extended Binary data reader (read_extended_binary_data)")
    print("  - Format: { (1) + Size (4 LE) + Opcode (2 LE) + Data + } (1)")
    print("  - Encryption methods: none, AES128, AES256")
    print("  - Password hash types: MD5, SHA256")
    print("  - Unknown opcode fallback handler for forward compatibility")
    print("\nEdge Cases Handled:")
    print("  - All encryption methods (0-2) with 16-byte key hash")
    print("  - All password hash types (0-1) with 32-byte hash")
    print("  - Unknown opcodes with variable data sizes (0-100+ bytes)")
    print("  - Invalid method/hash type detection")
    print("  - Invalid data size detection")
    print("  - Missing opening/closing braces")
    print("  - Insufficient data in Extended Binary blocks")
    print("  - Little-endian byte order for size and opcode fields")
    print("\nExtended Binary Format Details:")
    print("  - Total header: 7 bytes (1 + 4 + 2)")
    print("  - Size field: includes opcode (2) + data + closing brace (1)")
    print("  - Data size calculation: size_field - 3")
    print("  - Opening brace '{' (0x7B) required")
    print("  - Closing brace '}' (0x7D) required")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
