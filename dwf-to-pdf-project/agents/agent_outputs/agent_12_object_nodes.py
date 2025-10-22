"""
DWF Object Node Opcode Parsers (Agent 12)

This module implements binary parsers for three DWF object node opcodes:
- 0x0E: OBJECT_NODE_AUTO (auto-increment object node)
- 0x6E: OBJECT_NODE_16 (16-bit relative object node)
- 0x4E: OBJECT_NODE_32 (32-bit absolute object node)

Object nodes define hierarchical structure in DWF files, allowing for
grouping and nesting of drawing elements. They are used to organize
geometric primitives and attributes into logical hierarchies.

Reference C++ Source:
    /home/user/git-practice/dwf-to-pdf-project/dwf-toolkit-source/develop/global/src/dwf/whiptk/object_node.cpp

Format Specifications:
    - 0x0E: No data bytes (auto-increment by 1)
    - 0x6E: 2 bytes (int16 signed delta/offset, little-endian)
    - 0x4E: 4 bytes (int32 absolute value, little-endian)

Based on opcode_batches.json (agent_id: 12) and opcode_reference_initial.json.
"""

import struct
from typing import Dict, BinaryIO, Optional
from io import BytesIO


class ObjectNodeState:
    """
    State tracker for object node parsing.

    Object node opcodes are stateful - they maintain a reference to the
    previous object node number to enable relative addressing and
    auto-increment optimizations.

    Attributes:
        previous_node_num: The last object node number processed.
                          Initialized to -1 (invalid state).
    """

    def __init__(self):
        """Initialize state with invalid previous node number."""
        self.previous_node_num: int = -1

    def update(self, node_num: int) -> None:
        """
        Update the state with a new object node number.

        Args:
            node_num: The new object node number to store as previous.
        """
        self.previous_node_num = node_num

    def reset(self) -> None:
        """Reset state to initial invalid state."""
        self.previous_node_num = -1


def parse_opcode_0x0E_object_node_auto(
    stream: BinaryIO,
    state: Optional[ObjectNodeState] = None
) -> Dict:
    """
    Parse DWF opcode 0x0E (OBJECT_NODE_AUTO).

    This opcode represents an auto-increment object node operation.
    It reads NO data bytes from the stream and simply increments the
    previous object node number by 1.

    Format:
        - No data bytes (0 bytes)
        - Calculation: current = previous + 1

    Args:
        stream: Binary stream positioned after the 0x0E opcode byte.
                No bytes will be read from this stream.
        state: Optional ObjectNodeState tracking the previous node number.
               If None, assumes previous was 0 (resulting in node 1).

    Returns:
        Dictionary containing:
            - 'opcode': '0x0E'
            - 'name': 'OBJECT_NODE_AUTO'
            - 'object_node_num': The calculated object node number (previous + 1)
            - 'previous_node_num': The previous node number used
            - 'delta': Always 1 (auto-increment)

    Raises:
        ValueError: If state is None or previous_node_num is invalid (-1).

    Example:
        >>> state = ObjectNodeState()
        >>> state.previous_node_num = 100
        >>> stream = BytesIO(b'')  # No data to read
        >>> result = parse_opcode_0x0E_object_node_auto(stream, state)
        >>> result['object_node_num']
        101
        >>> result['delta']
        1

    C++ Reference (object_node.cpp, line 276-278):
        case WD_SBBO_OBJECT_NODE_AUTO:
            m_object_node_num = file.rendition().object_node().object_node_num() + 1;
            break;
    """
    # Validate state
    if state is None:
        raise ValueError("ObjectNodeState is required for opcode 0x0E")

    if state.previous_node_num == -1:
        raise ValueError(
            "Invalid state: previous node number is -1. "
            "Must process an absolute node (0x4E) or 16-bit node (0x6E) first."
        )

    # Calculate new node number (auto-increment by 1)
    previous = state.previous_node_num
    current = previous + 1

    # Update state
    state.update(current)

    return {
        'opcode': '0x0E',
        'name': 'OBJECT_NODE_AUTO',
        'object_node_num': current,
        'previous_node_num': previous,
        'delta': 1
    }


def parse_opcode_0x6E_object_node_16(
    stream: BinaryIO,
    state: Optional[ObjectNodeState] = None
) -> Dict:
    """
    Parse DWF opcode 0x6E (OBJECT_NODE_16).

    This opcode represents a 16-bit relative object node operation.
    It reads a 16-bit signed integer as a delta/offset and adds it to
    the previous object node number.

    Format:
        - 2 bytes (int16, little-endian): signed delta value
        - Calculation: current = previous + delta
        - Valid delta range: -32768 to +32767

    Args:
        stream: Binary stream positioned after the 0x6E opcode byte.
        state: Optional ObjectNodeState tracking the previous node number.
               If None, assumes previous was 0.

    Returns:
        Dictionary containing:
            - 'opcode': '0x6E'
            - 'name': 'OBJECT_NODE_16'
            - 'object_node_num': The calculated object node number
            - 'previous_node_num': The previous node number used
            - 'delta': The 16-bit signed offset value read

    Raises:
        ValueError: If insufficient data or state is invalid.

    Example:
        >>> state = ObjectNodeState()
        >>> state.previous_node_num = 1000
        >>> # Delta of +50 as little-endian int16
        >>> stream = BytesIO(struct.pack('<h', 50))
        >>> result = parse_opcode_0x6E_object_node_16(stream, state)
        >>> result['object_node_num']
        1050
        >>> result['delta']
        50

    C++ Reference (object_node.cpp, line 269-274):
        case WD_SBBO_OBJECT_NODE_16:
        {
            WT_Integer16 value;
            file.read(value);
            m_object_node_num = file.rendition().object_node().object_node_num() + value;
            break;
        }
    """
    # Validate state
    if state is None:
        raise ValueError("ObjectNodeState is required for opcode 0x6E")

    if state.previous_node_num == -1:
        raise ValueError(
            "Invalid state: previous node number is -1. "
            "Must process an absolute node (0x4E) first."
        )

    # Read 16-bit signed delta (2 bytes)
    data = stream.read(2)
    if len(data) != 2:
        raise ValueError(
            f"Insufficient data for opcode 0x6E: expected 2 bytes, got {len(data)}"
        )

    # Unpack signed 16-bit integer (little-endian)
    delta = struct.unpack('<h', data)[0]

    # Calculate new node number
    previous = state.previous_node_num
    current = previous + delta

    # Update state
    state.update(current)

    return {
        'opcode': '0x6E',
        'name': 'OBJECT_NODE_16',
        'object_node_num': current,
        'previous_node_num': previous,
        'delta': delta
    }


def parse_opcode_0x4E_object_node_32(
    stream: BinaryIO,
    state: Optional[ObjectNodeState] = None
) -> Dict:
    """
    Parse DWF opcode 0x4E (OBJECT_NODE_32).

    This opcode represents a 32-bit absolute object node operation.
    It reads a 32-bit signed integer as an absolute object node number.
    This is typically the first node opcode encountered or used when
    the delta is too large for 16-bit representation.

    Format:
        - 4 bytes (int32, little-endian): absolute node number
        - No calculation needed - value is used directly

    Args:
        stream: Binary stream positioned after the 0x4E opcode byte.
        state: Optional ObjectNodeState to update. If None, a new state
               should be created by the caller after this call.

    Returns:
        Dictionary containing:
            - 'opcode': '0x4E'
            - 'name': 'OBJECT_NODE_32'
            - 'object_node_num': The absolute object node number
            - 'previous_node_num': The previous node number (if state provided)
            - 'delta': None (absolute addressing, no delta)

    Raises:
        ValueError: If insufficient data is available.

    Example:
        >>> state = ObjectNodeState()
        >>> # Absolute node number 5000 as little-endian int32
        >>> stream = BytesIO(struct.pack('<l', 5000))
        >>> result = parse_opcode_0x4E_object_node_32(stream, state)
        >>> result['object_node_num']
        5000
        >>> result['delta']
        None

    C++ Reference (object_node.cpp, line 264-268):
        case WD_SBBO_OBJECT_NODE_32:
        {
            file.read(m_object_node_num);
            break;
        }
    """
    # Store previous value for reporting
    previous = state.previous_node_num if state else None

    # Read 32-bit signed integer (4 bytes)
    data = stream.read(4)
    if len(data) != 4:
        raise ValueError(
            f"Insufficient data for opcode 0x4E: expected 4 bytes, got {len(data)}"
        )

    # Unpack signed 32-bit integer (little-endian)
    node_num = struct.unpack('<l', data)[0]

    # Update state if provided
    if state:
        state.update(node_num)

    return {
        'opcode': '0x4E',
        'name': 'OBJECT_NODE_32',
        'object_node_num': node_num,
        'previous_node_num': previous,
        'delta': None  # Absolute addressing
    }


# ============================================================================
# TEST SUITE
# ============================================================================

def test_opcode_0x4E_object_node_32():
    """Test suite for opcode 0x4E (32-bit absolute object node)."""
    print("=" * 70)
    print("TESTING OPCODE 0x4E (OBJECT_NODE_32)")
    print("=" * 70)

    # Test 1: Basic absolute node number
    print("\nTest 1: Basic absolute node number (100)")
    state = ObjectNodeState()
    data = struct.pack('<l', 100)
    stream = BytesIO(data)
    result = parse_opcode_0x4E_object_node_32(stream, state)

    assert result['opcode'] == '0x4E', "Opcode mismatch"
    assert result['name'] == 'OBJECT_NODE_32', "Name mismatch"
    assert result['object_node_num'] == 100, f"Expected 100, got {result['object_node_num']}"
    assert result['delta'] is None, "Delta should be None for absolute addressing"
    assert state.previous_node_num == 100, "State not updated correctly"
    print(f"  PASS: {result}")

    # Test 2: Large positive node number
    print("\nTest 2: Large positive node number (1,000,000)")
    state = ObjectNodeState()
    data = struct.pack('<l', 1000000)
    stream = BytesIO(data)
    result = parse_opcode_0x4E_object_node_32(stream, state)

    assert result['object_node_num'] == 1000000
    assert state.previous_node_num == 1000000
    print(f"  PASS: {result}")

    # Test 3: Zero node number (edge case)
    print("\nTest 3: Zero node number")
    state = ObjectNodeState()
    data = struct.pack('<l', 0)
    stream = BytesIO(data)
    result = parse_opcode_0x4E_object_node_32(stream, state)

    assert result['object_node_num'] == 0
    assert state.previous_node_num == 0
    print(f"  PASS: {result}")

    # Test 4: Negative node number (valid in signed int32)
    print("\nTest 4: Negative node number (-500)")
    state = ObjectNodeState()
    data = struct.pack('<l', -500)
    stream = BytesIO(data)
    result = parse_opcode_0x4E_object_node_32(stream, state)

    assert result['object_node_num'] == -500
    assert state.previous_node_num == -500
    print(f"  PASS: {result}")

    # Test 5: Sequential absolute nodes (state tracking)
    print("\nTest 5: Sequential absolute nodes")
    state = ObjectNodeState()

    # First node: 50
    data1 = struct.pack('<l', 50)
    stream1 = BytesIO(data1)
    result1 = parse_opcode_0x4E_object_node_32(stream1, state)
    assert result1['object_node_num'] == 50
    assert result1['previous_node_num'] == -1  # Initial state

    # Second node: 200 (should track that previous was 50)
    data2 = struct.pack('<l', 200)
    stream2 = BytesIO(data2)
    result2 = parse_opcode_0x4E_object_node_32(stream2, state)
    assert result2['object_node_num'] == 200
    assert result2['previous_node_num'] == 50
    print(f"  PASS: Node 1={result1['object_node_num']}, Node 2={result2['object_node_num']}")

    # Test 6: Error handling - insufficient data
    print("\nTest 6: Error handling - insufficient data")
    state = ObjectNodeState()
    data = struct.pack('<h', 100)  # Only 2 bytes, need 4
    stream = BytesIO(data)
    try:
        result = parse_opcode_0x4E_object_node_32(stream, state)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 7: Maximum positive int32
    print("\nTest 7: Maximum positive int32 (2,147,483,647)")
    state = ObjectNodeState()
    data = struct.pack('<l', 2147483647)
    stream = BytesIO(data)
    result = parse_opcode_0x4E_object_node_32(stream, state)
    assert result['object_node_num'] == 2147483647
    print(f"  PASS: {result['object_node_num']}")

    # Test 8: Minimum negative int32
    print("\nTest 8: Minimum negative int32 (-2,147,483,648)")
    state = ObjectNodeState()
    data = struct.pack('<l', -2147483648)
    stream = BytesIO(data)
    result = parse_opcode_0x4E_object_node_32(stream, state)
    assert result['object_node_num'] == -2147483648
    print(f"  PASS: {result['object_node_num']}")

    print("\n" + "=" * 70)
    print("OPCODE 0x4E (OBJECT_NODE_32): ALL 8 TESTS PASSED")
    print("=" * 70)


def test_opcode_0x6E_object_node_16():
    """Test suite for opcode 0x6E (16-bit relative object node)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x6E (OBJECT_NODE_16)")
    print("=" * 70)

    # Test 1: Basic positive delta
    print("\nTest 1: Basic positive delta (+50)")
    state = ObjectNodeState()
    state.previous_node_num = 1000
    data = struct.pack('<h', 50)
    stream = BytesIO(data)
    result = parse_opcode_0x6E_object_node_16(stream, state)

    assert result['opcode'] == '0x6E'
    assert result['name'] == 'OBJECT_NODE_16'
    assert result['object_node_num'] == 1050
    assert result['previous_node_num'] == 1000
    assert result['delta'] == 50
    assert state.previous_node_num == 1050
    print(f"  PASS: {result}")

    # Test 2: Negative delta
    print("\nTest 2: Negative delta (-200)")
    state = ObjectNodeState()
    state.previous_node_num = 500
    data = struct.pack('<h', -200)
    stream = BytesIO(data)
    result = parse_opcode_0x6E_object_node_16(stream, state)

    assert result['object_node_num'] == 300
    assert result['delta'] == -200
    assert state.previous_node_num == 300
    print(f"  PASS: {result}")

    # Test 3: Zero delta (no change)
    print("\nTest 3: Zero delta")
    state = ObjectNodeState()
    state.previous_node_num = 750
    data = struct.pack('<h', 0)
    stream = BytesIO(data)
    result = parse_opcode_0x6E_object_node_16(stream, state)

    assert result['object_node_num'] == 750
    assert result['delta'] == 0
    print(f"  PASS: {result}")

    # Test 4: Maximum positive delta (+32767)
    print("\nTest 4: Maximum positive delta (+32767)")
    state = ObjectNodeState()
    state.previous_node_num = 100
    data = struct.pack('<h', 32767)
    stream = BytesIO(data)
    result = parse_opcode_0x6E_object_node_16(stream, state)

    assert result['object_node_num'] == 32867
    assert result['delta'] == 32767
    print(f"  PASS: {result}")

    # Test 5: Maximum negative delta (-32768)
    print("\nTest 5: Maximum negative delta (-32768)")
    state = ObjectNodeState()
    state.previous_node_num = 40000
    data = struct.pack('<h', -32768)
    stream = BytesIO(data)
    result = parse_opcode_0x6E_object_node_16(stream, state)

    assert result['object_node_num'] == 7232  # 40000 - 32768
    assert result['delta'] == -32768
    print(f"  PASS: {result}")

    # Test 6: Chain of relative nodes
    print("\nTest 6: Chain of relative nodes")
    state = ObjectNodeState()
    state.previous_node_num = 100

    # First delta: +10
    data1 = struct.pack('<h', 10)
    result1 = parse_opcode_0x6E_object_node_16(BytesIO(data1), state)
    assert result1['object_node_num'] == 110

    # Second delta: +20
    data2 = struct.pack('<h', 20)
    result2 = parse_opcode_0x6E_object_node_16(BytesIO(data2), state)
    assert result2['object_node_num'] == 130

    # Third delta: -30
    data3 = struct.pack('<h', -30)
    result3 = parse_opcode_0x6E_object_node_16(BytesIO(data3), state)
    assert result3['object_node_num'] == 100

    print(f"  PASS: 100 -> 110 -> 130 -> 100")

    # Test 7: Error handling - invalid previous state
    print("\nTest 7: Error handling - invalid previous state")
    state = ObjectNodeState()  # previous_node_num = -1 (invalid)
    data = struct.pack('<h', 50)
    stream = BytesIO(data)
    try:
        result = parse_opcode_0x6E_object_node_16(stream, state)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 8: Error handling - insufficient data
    print("\nTest 8: Error handling - insufficient data")
    state = ObjectNodeState()
    state.previous_node_num = 100
    data = struct.pack('<B', 50)  # Only 1 byte, need 2
    stream = BytesIO(data)
    try:
        result = parse_opcode_0x6E_object_node_16(stream, state)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x6E (OBJECT_NODE_16): ALL 8 TESTS PASSED")
    print("=" * 70)


def test_opcode_0x0E_object_node_auto():
    """Test suite for opcode 0x0E (auto-increment object node)."""
    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x0E (OBJECT_NODE_AUTO)")
    print("=" * 70)

    # Test 1: Basic auto-increment
    print("\nTest 1: Basic auto-increment from 100 to 101")
    state = ObjectNodeState()
    state.previous_node_num = 100
    stream = BytesIO(b'')  # No data to read
    result = parse_opcode_0x0E_object_node_auto(stream, state)

    assert result['opcode'] == '0x0E'
    assert result['name'] == 'OBJECT_NODE_AUTO'
    assert result['object_node_num'] == 101
    assert result['previous_node_num'] == 100
    assert result['delta'] == 1
    assert state.previous_node_num == 101
    print(f"  PASS: {result}")

    # Test 2: Auto-increment from 0
    print("\nTest 2: Auto-increment from 0 to 1")
    state = ObjectNodeState()
    state.previous_node_num = 0
    stream = BytesIO(b'')
    result = parse_opcode_0x0E_object_node_auto(stream, state)

    assert result['object_node_num'] == 1
    assert result['previous_node_num'] == 0
    assert state.previous_node_num == 1
    print(f"  PASS: {result}")

    # Test 3: Chain of auto-increments
    print("\nTest 3: Chain of 5 auto-increments")
    state = ObjectNodeState()
    state.previous_node_num = 50

    expected_sequence = [51, 52, 53, 54, 55]
    for i, expected in enumerate(expected_sequence, 1):
        stream = BytesIO(b'')
        result = parse_opcode_0x0E_object_node_auto(stream, state)
        assert result['object_node_num'] == expected, \
            f"Step {i}: expected {expected}, got {result['object_node_num']}"

    print(f"  PASS: 50 -> 51 -> 52 -> 53 -> 54 -> 55")

    # Test 4: Large node number auto-increment
    print("\nTest 4: Auto-increment from large number (999,999)")
    state = ObjectNodeState()
    state.previous_node_num = 999999
    stream = BytesIO(b'')
    result = parse_opcode_0x0E_object_node_auto(stream, state)

    assert result['object_node_num'] == 1000000
    print(f"  PASS: {result}")

    # Test 5: Negative to less negative (edge case)
    print("\nTest 5: Auto-increment from negative (-5 to -4)")
    state = ObjectNodeState()
    state.previous_node_num = -5
    stream = BytesIO(b'')
    result = parse_opcode_0x0E_object_node_auto(stream, state)

    assert result['object_node_num'] == -4
    assert result['previous_node_num'] == -5
    print(f"  PASS: {result}")

    # Test 6: Mixed opcode sequence (0x4E -> 0x0E -> 0x6E -> 0x0E)
    print("\nTest 6: Mixed opcode sequence")
    state = ObjectNodeState()

    # Start with absolute node: 100
    data_32 = struct.pack('<l', 100)
    result_32 = parse_opcode_0x4E_object_node_32(BytesIO(data_32), state)
    assert result_32['object_node_num'] == 100

    # Auto-increment: 100 -> 101
    result_auto1 = parse_opcode_0x0E_object_node_auto(BytesIO(b''), state)
    assert result_auto1['object_node_num'] == 101

    # Relative: 101 + 50 = 151
    data_16 = struct.pack('<h', 50)
    result_16 = parse_opcode_0x6E_object_node_16(BytesIO(data_16), state)
    assert result_16['object_node_num'] == 151

    # Auto-increment: 151 -> 152
    result_auto2 = parse_opcode_0x0E_object_node_auto(BytesIO(b''), state)
    assert result_auto2['object_node_num'] == 152

    print(f"  PASS: 100 -> 101 -> 151 -> 152")

    # Test 7: Error handling - invalid previous state
    print("\nTest 7: Error handling - invalid previous state")
    state = ObjectNodeState()  # previous_node_num = -1 (invalid)
    stream = BytesIO(b'')
    try:
        result = parse_opcode_0x0E_object_node_auto(stream, state)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    # Test 8: Error handling - None state
    print("\nTest 8: Error handling - None state")
    stream = BytesIO(b'')
    try:
        result = parse_opcode_0x0E_object_node_auto(stream, None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  PASS: Correctly raised ValueError: {e}")

    print("\n" + "=" * 70)
    print("OPCODE 0x0E (OBJECT_NODE_AUTO): ALL 8 TESTS PASSED")
    print("=" * 70)


def test_integration_scenario():
    """
    Integration test demonstrating real-world usage patterns.

    This test simulates how object nodes would be used in a DWF file
    to define hierarchical structure with optimized encoding.
    """
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Real-world DWF Object Node Sequence")
    print("=" * 70)

    print("\nScenario: Drawing with layered object hierarchy")
    print("-" * 70)

    state = ObjectNodeState()
    results = []

    # Step 1: Set root node (absolute)
    print("\n1. Set root object node: 1000")
    data = struct.pack('<l', 1000)
    result = parse_opcode_0x4E_object_node_32(BytesIO(data), state)
    results.append(result)
    print(f"   Opcode 0x4E -> Node {result['object_node_num']}")

    # Step 2: Child nodes using auto-increment (1001, 1002, 1003)
    print("\n2. Add 3 child nodes using auto-increment:")
    for i in range(3):
        result = parse_opcode_0x0E_object_node_auto(BytesIO(b''), state)
        results.append(result)
        print(f"   Opcode 0x0E -> Node {result['object_node_num']}")

    # Step 3: Jump to a distant node using relative addressing
    print("\n3. Jump to layer 2 (node 2000) using 16-bit relative:")
    delta = 2000 - state.previous_node_num
    data = struct.pack('<h', delta)
    result = parse_opcode_0x6E_object_node_16(BytesIO(data), state)
    results.append(result)
    print(f"   Opcode 0x6E (delta={delta}) -> Node {result['object_node_num']}")

    # Step 4: More auto-increments
    print("\n4. Add 2 more child nodes:")
    for i in range(2):
        result = parse_opcode_0x0E_object_node_auto(BytesIO(b''), state)
        results.append(result)
        print(f"   Opcode 0x0E -> Node {result['object_node_num']}")

    # Step 5: Large jump requiring 32-bit absolute
    print("\n5. Jump to distant layer (node 100000) using 32-bit absolute:")
    data = struct.pack('<l', 100000)
    result = parse_opcode_0x4E_object_node_32(BytesIO(data), state)
    results.append(result)
    print(f"   Opcode 0x4E -> Node {result['object_node_num']}")

    # Verify sequence
    expected_nodes = [1000, 1001, 1002, 1003, 2000, 2001, 2002, 100000]
    actual_nodes = [r['object_node_num'] for r in results]

    print("\n" + "-" * 70)
    print("Verification:")
    print(f"  Expected sequence: {expected_nodes}")
    print(f"  Actual sequence:   {actual_nodes}")
    print(f"  Match: {expected_nodes == actual_nodes}")

    assert expected_nodes == actual_nodes, "Node sequence mismatch"

    # Calculate byte savings
    bytes_if_all_32bit = 8 * 5  # 8 nodes * 5 bytes each (1 opcode + 4 data)
    bytes_actual = (
        2 * 5 +  # Two 0x4E opcodes (1 + 4 bytes each)
        5 * 1 +  # Five 0x0E opcodes (1 byte each, no data)
        1 * 3    # One 0x6E opcode (1 + 2 bytes)
    )
    bytes_saved = bytes_if_all_32bit - bytes_actual

    print(f"\nByte efficiency:")
    print(f"  All 32-bit absolute:  {bytes_if_all_32bit} bytes")
    print(f"  Optimized encoding:   {bytes_actual} bytes")
    print(f"  Savings:              {bytes_saved} bytes ({bytes_saved/bytes_if_all_32bit*100:.1f}%)")

    print("\n" + "=" * 70)
    print("INTEGRATION TEST: PASSED")
    print("=" * 70)


def run_all_tests():
    """Run comprehensive test suite for all object node opcodes."""
    print("\n" + "=" * 70)
    print("DWF OBJECT NODE OPCODE TEST SUITE (AGENT 12)")
    print("=" * 70)
    print("Testing opcodes: 0x0E (AUTO), 0x6E (16-bit), 0x4E (32-bit)")
    print("=" * 70)

    # Run individual opcode tests
    test_opcode_0x4E_object_node_32()
    test_opcode_0x6E_object_node_16()
    test_opcode_0x0E_object_node_auto()

    # Run integration test
    test_integration_scenario()

    # Final summary
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nTest Summary:")
    print("  - Opcode 0x4E (OBJECT_NODE_32):   8 tests passed")
    print("  - Opcode 0x6E (OBJECT_NODE_16):   8 tests passed")
    print("  - Opcode 0x0E (OBJECT_NODE_AUTO): 8 tests passed")
    print("  - Integration test:                1 test passed")
    print("  - Total:                           25 tests passed")
    print("=" * 70)
    print("\nKey Features Tested:")
    print("  ✓ Absolute addressing (32-bit)")
    print("  ✓ Relative addressing (16-bit signed delta)")
    print("  ✓ Auto-increment optimization")
    print("  ✓ State tracking and chaining")
    print("  ✓ Edge cases (zero, negative, max/min values)")
    print("  ✓ Error handling (invalid state, insufficient data)")
    print("  ✓ Real-world integration scenario")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
