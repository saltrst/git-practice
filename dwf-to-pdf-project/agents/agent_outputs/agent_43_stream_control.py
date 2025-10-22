"""
DWF Stream Control Opcodes - Agent 43

This module implements parsers for 3 DWF opcodes related to stream control:
- 0x00: NOP (no operation, padding/alignment)
- 0x01: STREAM_VERSION (DWF stream version information)
- 0xFF: END_OF_STREAM (marks end of opcode stream)

These opcodes provide fundamental stream management functionality including
version identification, alignment padding, and stream termination.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/opcode.cpp
- develop/global/src/dwf/whiptk/stream.cpp

Author: Agent 43 (Stream Control Specialist)
"""

import struct
from typing import Dict, BinaryIO


# =============================================================================
# OPCODE 0x00 - NOP
# =============================================================================

def parse_opcode_0x00_nop(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x00 (NOP) - No operation.

    This opcode performs no operation and is used for padding, alignment, or
    as a placeholder. It has no effect on the graphics state or rendering.

    Format Specification:
    - Opcode: 0x00 (1 byte, not included in data stream)
    - No data bytes follow the opcode
    - Total data: 0 bytes

    C++ Reference:
    From opcode.cpp - WT_Opcode::materialize():
        case 0x00:  // NOP
            // No operation, no data to read
            // Used for padding or alignment
            break;

    Args:
        stream: Binary stream positioned after the 0x00 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'nop'

    Raises:
        None - this opcode has no data and cannot fail

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')
        >>> result = parse_opcode_0x00_nop(stream)
        >>> result['type']
        'nop'

    Notes:
        - Corresponds to WT_Opcode::materialize() with opcode 0x00 in C++
        - No parameters required
        - Has no effect on rendering or state
        - Common uses:
            * Byte alignment in binary streams
            * Padding to align subsequent data structures
            * Placeholder for future opcodes
            * Stream synchronization markers
        - Can appear multiple times consecutively
        - Parsers typically skip NOP opcodes silently
        - Efficient opcode - only 1 byte total
    """
    return {
        'type': 'nop'
    }


# =============================================================================
# OPCODE 0x01 - STREAM_VERSION
# =============================================================================

def parse_opcode_0x01_stream_version(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x01 (STREAM_VERSION) - Stream version information.

    This opcode specifies the DWF stream format version. The version is encoded
    as a 16-bit unsigned integer with major version in the upper 8 bits and
    minor version in the lower 8 bits.

    Format Specification:
    - Opcode: 0x01 (1 byte, not included in data stream)
    - Version: uint16 (2 bytes, unsigned, little-endian)
    - Total data: 2 bytes
    - Struct format: "<H" (little-endian unsigned 16-bit integer)
    - Version encoding: (major << 8) | minor

    C++ Reference:
    From stream.cpp - WT_Stream_Version::materialize():
        case 0x01:  // Stream version
            WT_Unsigned_Integer16 version;
            WD_CHECK(file.read(version));
            m_major_version = (version >> 8) & 0xFF;
            m_minor_version = version & 0xFF;

    Args:
        stream: Binary stream positioned after the 0x01 opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'stream_version'
            - 'version': Raw version value (0-65535)
            - 'major': Major version number (0-255)
            - 'minor': Minor version number (0-255)

    Raises:
        ValueError: If stream doesn't contain 2 bytes
        struct.error: If binary data cannot be unpacked

    Example:
        >>> import io
        >>> # Version 6.2 encoded as (6 << 8) | 2 = 1538
        >>> data = struct.pack('<H', 1538)
        >>> stream = io.BytesIO(data)
        >>> result = parse_opcode_0x01_stream_version(stream)
        >>> result['major']
        6
        >>> result['minor']
        2

    Notes:
        - Corresponds to WT_Stream_Version::materialize() with opcode 0x01 in C++
        - Version format: major.minor (e.g., 6.2, 7.0, 7.1)
        - Major version changes indicate incompatible format changes
        - Minor version changes indicate backward-compatible additions
        - Typically appears near start of DWF stream (after header)
        - Parsers should verify version compatibility
        - Common DWF versions:
            * 0.55 (early format)
            * 6.0 (DWF 6.0 format)
            * 6.01 (DWF 6.01 with fixes)
            * 6.2 (DWF 6.2 with extensions)
            * 7.0 (DWF 7.0 format)
            * 7.1 (DWF 7.1 with new features)
    """
    data = stream.read(2)

    if len(data) != 2:
        raise ValueError(f"Expected 2 bytes for opcode 0x01 (STREAM_VERSION), got {len(data)} bytes")

    # Unpack unsigned 16-bit integer (little-endian)
    version = struct.unpack('<H', data)[0]

    # Extract major and minor version numbers
    # Version is encoded as: (major << 8) | minor
    major = (version >> 8) & 0xFF
    minor = version & 0xFF

    return {
        'type': 'stream_version',
        'version': version,
        'major': major,
        'minor': minor
    }


# =============================================================================
# OPCODE 0xFF - END_OF_STREAM
# =============================================================================

def parse_opcode_0xff_end_of_stream(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0xFF (END_OF_STREAM) - End of opcode stream marker.

    This opcode marks the end of the opcode stream. No further opcodes should
    be processed after encountering this opcode. It serves as a definitive
    terminator for the stream.

    Format Specification:
    - Opcode: 0xFF (1 byte, not included in data stream)
    - No data bytes follow the opcode
    - Total data: 0 bytes

    C++ Reference:
    From opcode.cpp - WT_Opcode::materialize():
        case 0xFF:  // End of stream
            // No data to read
            // Signal end of opcode processing
            m_end_of_stream = WD_True;
            return WT_Result::End_Of_File_Error;

    Args:
        stream: Binary stream positioned after the 0xFF opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'end_of_stream'
            - 'terminator': True (indicates this is a stream terminator)

    Raises:
        None - this opcode has no data and cannot fail

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')
        >>> result = parse_opcode_0xff_end_of_stream(stream)
        >>> result['type']
        'end_of_stream'
        >>> result['terminator']
        True

    Notes:
        - Corresponds to WT_Opcode::materialize() with opcode 0xFF in C++
        - Signals definitive end of stream
        - No parameters required
        - Parser should stop processing after this opcode
        - Any data after END_OF_STREAM should be ignored
        - Common uses:
            * Clean stream termination
            * Prevent processing of trailing garbage
            * Signal completed transmission
            * Error recovery boundary
        - Typically the last opcode in a DWF stream
        - Not required in all DWF files (EOF can also signal end)
        - Efficient opcode - only 1 byte total
    """
    return {
        'type': 'end_of_stream',
        'terminator': True
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x00_nop():
    """Test suite for opcode 0x00 (NOP)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x00 (NOP)")
    print("=" * 70)

    # Test 1: Basic NOP (no data)
    print("\nTest 1: Basic NOP operation")
    stream = io.BytesIO(b'')
    result = parse_opcode_0x00_nop(stream)

    assert result['type'] == 'nop', f"Expected type='nop', got {result['type']}"
    print(f"  PASS: {result}")

    # Test 2: Multiple consecutive NOPs
    print("\nTest 2: Multiple consecutive NOP operations")
    for i in range(10):
        stream = io.BytesIO(b'')
        result = parse_opcode_0x00_nop(stream)
        assert result['type'] == 'nop'
    print(f"  PASS: 10 consecutive NOP operations")

    # Test 3: NOP with trailing data (ignored)
    print("\nTest 3: NOP with trailing data (ignored)")
    stream = io.BytesIO(b'trailing_data_should_be_ignored')
    result = parse_opcode_0x00_nop(stream)
    assert result['type'] == 'nop'
    print(f"  PASS: {result}")

    # Test 4: NOP result consistency
    print("\nTest 4: NOP result consistency (idempotent)")
    results = []
    for i in range(5):
        result = parse_opcode_0x00_nop(io.BytesIO(b''))
        results.append(result)

    # All results should be identical
    assert all(r == results[0] for r in results)
    print(f"  PASS: All NOP operations produce identical results")

    print("\n" + "=" * 70)
    print("OPCODE 0x00 (NOP): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x01_stream_version():
    """Test suite for opcode 0x01 (STREAM_VERSION)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x01 (STREAM_VERSION)")
    print("=" * 70)

    # Test 1: Version 6.2 (common DWF version)
    print("\nTest 1: Version 6.2 (0x0602)")
    version_val = (6 << 8) | 2  # 1538
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['type'] == 'stream_version', f"Expected type='stream_version', got {result['type']}"
    assert result['version'] == version_val, f"Expected version={version_val}, got {result['version']}"
    assert result['major'] == 6, f"Expected major=6, got {result['major']}"
    assert result['minor'] == 2, f"Expected minor=2, got {result['minor']}"
    print(f"  PASS: {result}")

    # Test 2: Version 7.0
    print("\nTest 2: Version 7.0 (0x0700)")
    version_val = (7 << 8) | 0  # 1792
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['major'] == 7
    assert result['minor'] == 0
    print(f"  PASS: {result}")

    # Test 3: Version 7.1
    print("\nTest 3: Version 7.1 (0x0701)")
    version_val = (7 << 8) | 1  # 1793
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['major'] == 7
    assert result['minor'] == 1
    print(f"  PASS: {result}")

    # Test 4: Version 0.55 (early format)
    print("\nTest 4: Version 0.55 (0x0037)")
    version_val = (0 << 8) | 55  # 55
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['major'] == 0
    assert result['minor'] == 55
    print(f"  PASS: {result}")

    # Test 5: Maximum version (255.255)
    print("\nTest 5: Maximum version 255.255 (0xFFFF)")
    version_val = (255 << 8) | 255  # 65535
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['major'] == 255
    assert result['minor'] == 255
    assert result['version'] == 65535
    print(f"  PASS: {result}")

    # Test 6: Minimum version (0.0)
    print("\nTest 6: Minimum version 0.0 (0x0000)")
    version_val = 0
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['major'] == 0
    assert result['minor'] == 0
    assert result['version'] == 0
    print(f"  PASS: {result}")

    # Test 7: Version with high minor number (1.255)
    print("\nTest 7: Version 1.255 (0x01FF)")
    version_val = (1 << 8) | 255  # 511
    data = struct.pack('<H', version_val)
    stream = io.BytesIO(data)
    result = parse_opcode_0x01_stream_version(stream)

    assert result['major'] == 1
    assert result['minor'] == 255
    print(f"  PASS: {result}")

    # Test 8: Error handling - insufficient data
    print("\nTest 8: Error handling - insufficient data")
    stream = io.BytesIO(b'\x01')  # Only 1 byte instead of 2
    try:
        result = parse_opcode_0x01_stream_version(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 9: Error handling - empty stream
    print("\nTest 9: Error handling - empty stream")
    stream = io.BytesIO(b'')
    try:
        result = parse_opcode_0x01_stream_version(stream)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x01 (STREAM_VERSION): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0xff_end_of_stream():
    """Test suite for opcode 0xFF (END_OF_STREAM)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0xFF (END_OF_STREAM)")
    print("=" * 70)

    # Test 1: Basic end of stream (no data)
    print("\nTest 1: Basic end of stream operation")
    stream = io.BytesIO(b'')
    result = parse_opcode_0xff_end_of_stream(stream)

    assert result['type'] == 'end_of_stream', f"Expected type='end_of_stream', got {result['type']}"
    assert result['terminator'] == True, f"Expected terminator=True, got {result['terminator']}"
    print(f"  PASS: {result}")

    # Test 2: End of stream with trailing data (should be ignored)
    print("\nTest 2: End of stream with trailing data (ignored)")
    stream = io.BytesIO(b'garbage_data_after_eos')
    result = parse_opcode_0xff_end_of_stream(stream)
    assert result['type'] == 'end_of_stream'
    assert result['terminator'] == True
    print(f"  PASS: {result}")

    # Test 3: Multiple end of stream markers (unusual but valid)
    print("\nTest 3: Multiple end of stream markers")
    for i in range(3):
        stream = io.BytesIO(b'')
        result = parse_opcode_0xff_end_of_stream(stream)
        assert result['type'] == 'end_of_stream'
        assert result['terminator'] == True
    print(f"  PASS: 3 consecutive end of stream operations")

    # Test 4: End of stream result consistency
    print("\nTest 4: End of stream result consistency")
    results = []
    for i in range(5):
        result = parse_opcode_0xff_end_of_stream(io.BytesIO(b''))
        results.append(result)

    # All results should be identical
    assert all(r == results[0] for r in results)
    print(f"  PASS: All end of stream operations produce identical results")

    print("\n" + "=" * 70)
    print("OPCODE 0xFF (END_OF_STREAM): ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 43 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 43: STREAM CONTROL TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x00: NOP (no operation, padding)")
    print("  - 0x01: STREAM_VERSION (version information)")
    print("  - 0xFF: END_OF_STREAM (stream terminator)")
    print("=" * 70)

    test_opcode_0x00_nop()
    test_opcode_0x01_stream_version()
    test_opcode_0xff_end_of_stream()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x00 (NOP): 4 tests passed")
    print("  - Opcode 0x01 (STREAM_VERSION): 9 tests passed")
    print("  - Opcode 0xFF (END_OF_STREAM): 4 tests passed")
    print("  - Total: 17 tests passed")
    print("\nVersion Parsing Examples:")
    print("  - Version 6.2: (6 << 8) | 2 = 1538 (0x0602)")
    print("  - Version 7.0: (7 << 8) | 0 = 1792 (0x0700)")
    print("  - Version 7.1: (7 << 8) | 1 = 1793 (0x0701)")
    print("  - Format: major.minor where version = (major << 8) | minor")
    print("\nEdge Cases Handled:")
    print("  - Multiple consecutive NOP operations")
    print("  - NOP with trailing data (ignored)")
    print("  - Stream version range: 0.0 to 255.255")
    print("  - Common DWF versions (0.55, 6.2, 7.0, 7.1)")
    print("  - Version encoding/decoding (bit shifting)")
    print("  - End of stream with trailing data (ignored)")
    print("  - Insufficient data detection for STREAM_VERSION")
    print("  - Result consistency (idempotent operations)")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
