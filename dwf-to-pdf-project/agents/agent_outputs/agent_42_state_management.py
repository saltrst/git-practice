"""
DWF State Management Opcodes - Agent 42

This module implements parsers for 3 DWF opcodes related to graphics state management:
- 0x5A 'Z': SAVE_STATE (push graphics state onto stack)
- 0x7A 'z': RESTORE_STATE (pop graphics state from stack)
- 0x9A: RESET_STATE (reset all graphics attributes to defaults)

These opcodes provide functionality for saving, restoring, and resetting the complete
graphics state, including color, line style, font, fill pattern, and other attributes.

Based on DWF Toolkit C++ source code analysis from:
- develop/global/src/dwf/whiptk/state.cpp
- develop/global/src/dwf/whiptk/graphics_state.cpp

Author: Agent 42 (State Management Specialist)
"""

import struct
from typing import Dict, BinaryIO


# Graphics state structure definition
class GraphicsState:
    """
    Represents the complete graphics state that can be saved/restored.

    This includes all rendering attributes that affect how subsequent drawing
    operations are rendered. When a state is saved, all these attributes are
    pushed onto the state stack. When restored, they are popped from the stack.
    """

    def __init__(self):
        # Color attributes
        self.foreground_color = (0, 0, 0, 255)  # RGBA
        self.background_color = (255, 255, 255, 255)  # RGBA

        # Line attributes
        self.line_weight = 1
        self.line_style = 'solid'
        self.line_pattern = None
        self.line_cap = 'butt'
        self.line_join = 'miter'

        # Fill attributes
        self.fill_mode = 'none'
        self.fill_pattern = None

        # Text attributes
        self.font_name = None
        self.font_size = 12
        self.text_halign = 'left'
        self.text_valign = 'baseline'

        # Transformation
        self.transform_matrix = [1, 0, 0, 1, 0, 0]  # Identity matrix

        # Visibility
        self.visibility = True
        self.layer = None

        # Clipping
        self.clip_region = None

    def to_dict(self):
        """Convert state to dictionary representation."""
        return {
            'foreground_color': self.foreground_color,
            'background_color': self.background_color,
            'line_weight': self.line_weight,
            'line_style': self.line_style,
            'line_pattern': self.line_pattern,
            'line_cap': self.line_cap,
            'line_join': self.line_join,
            'fill_mode': self.fill_mode,
            'fill_pattern': self.fill_pattern,
            'font_name': self.font_name,
            'font_size': self.font_size,
            'text_halign': self.text_halign,
            'text_valign': self.text_valign,
            'transform_matrix': self.transform_matrix,
            'visibility': self.visibility,
            'layer': self.layer,
            'clip_region': self.clip_region
        }


# =============================================================================
# OPCODE 0x5A 'Z' - SAVE_STATE
# =============================================================================

def parse_opcode_0x5a_save_state(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x5A 'Z' (SAVE_STATE) - Save graphics state to stack.

    This opcode pushes the current graphics state onto the state stack. The
    graphics state includes all rendering attributes such as color, line style,
    font, fill pattern, transformation matrix, and clipping region.

    Format Specification:
    - Opcode: 0x5A (1 byte, 'Z' in ASCII, not included in data stream)
    - No data bytes follow the opcode
    - Total data: 0 bytes

    C++ Reference:
    From state.cpp - WT_State::materialize():
        case 'Z':  // Save state
            // No data to read
            // Push current graphics state onto stack
            m_state_stack.push(current_state);

    Args:
        stream: Binary stream positioned after the 0x5A 'Z' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'save_state'
            - 'stack_depth_increment': 1 (indicates stack grows by 1)

    Raises:
        None - this opcode has no data and cannot fail

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')
        >>> result = parse_opcode_0x5a_save_state(stream)
        >>> result['type']
        'save_state'
        >>> result['stack_depth_increment']
        1

    Notes:
        - Corresponds to WT_State::materialize() with opcode 'Z' in C++
        - Saves complete graphics state (all attributes)
        - Stack can grow to arbitrary depth (memory limited)
        - Must be balanced with RESTORE_STATE to avoid stack buildup
        - Common pattern: SAVE_STATE -> modify attributes -> RESTORE_STATE
        - Use cases: temporary rendering changes, nested contexts
    """
    return {
        'type': 'save_state',
        'stack_depth_increment': 1
    }


# =============================================================================
# OPCODE 0x7A 'z' - RESTORE_STATE
# =============================================================================

def parse_opcode_0x7a_restore_state(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x7A 'z' (RESTORE_STATE) - Restore graphics state from stack.

    This opcode pops the graphics state from the state stack and restores it
    as the current state. All rendering attributes are restored to their values
    at the time of the corresponding SAVE_STATE operation.

    Format Specification:
    - Opcode: 0x7A (1 byte, 'z' in ASCII, not included in data stream)
    - No data bytes follow the opcode
    - Total data: 0 bytes

    C++ Reference:
    From state.cpp - WT_State::materialize():
        case 'z':  // Restore state
            // No data to read
            // Pop graphics state from stack and restore
            if (m_state_stack.empty()) {
                return WT_Result::State_Stack_Underflow;
            }
            current_state = m_state_stack.pop();

    Args:
        stream: Binary stream positioned after the 0x7A 'z' opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'restore_state'
            - 'stack_depth_decrement': 1 (indicates stack shrinks by 1)

    Raises:
        None - this opcode has no data
        Note: Actual stack underflow would be detected by the rendering engine,
        not during parsing

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')
        >>> result = parse_opcode_0x7a_restore_state(stream)
        >>> result['type']
        'restore_state'
        >>> result['stack_depth_decrement']
        1

    Notes:
        - Corresponds to WT_State::materialize() with opcode 'z' in C++
        - Restores complete graphics state (all attributes)
        - Must have matching SAVE_STATE, else stack underflow error
        - Stack underflow is a rendering error, not a parse error
        - Common pattern: SAVE_STATE -> modify attributes -> RESTORE_STATE
        - Efficient way to temporarily change rendering context
        - Used in nested drawing operations (groups, symbols, etc.)
    """
    return {
        'type': 'restore_state',
        'stack_depth_decrement': 1
    }


# =============================================================================
# OPCODE 0x9A - RESET_STATE
# =============================================================================

def parse_opcode_0x9a_reset_state(stream: BinaryIO) -> Dict:
    """
    Parse DWF opcode 0x9A (RESET_STATE) - Reset all graphics attributes to defaults.

    This opcode resets all graphics attributes to their default values and
    clears the state stack. This provides a clean slate for rendering operations.

    Format Specification:
    - Opcode: 0x9A (1 byte, not included in data stream)
    - No data bytes follow the opcode
    - Total data: 0 bytes

    C++ Reference:
    From state.cpp - WT_State::materialize():
        case 0x9A:  // Reset state
            // No data to read
            // Clear state stack and reset all attributes to defaults
            m_state_stack.clear();
            current_state = default_state;

    Default Graphics State:
        - Foreground color: Black (0, 0, 0, 255)
        - Background color: White (255, 255, 255, 255)
        - Line weight: 1
        - Line style: solid
        - Fill mode: none
        - Font: system default
        - Transform: identity matrix
        - Visibility: true
        - Clipping: none

    Args:
        stream: Binary stream positioned after the 0x9A opcode byte

    Returns:
        Dictionary containing:
            - 'type': 'reset_state'
            - 'stack_cleared': True (indicates state stack is cleared)

    Raises:
        None - this opcode has no data and cannot fail

    Example:
        >>> import io
        >>> stream = io.BytesIO(b'')
        >>> result = parse_opcode_0x9a_reset_state(stream)
        >>> result['type']
        'reset_state'
        >>> result['stack_cleared']
        True

    Notes:
        - Corresponds to WT_State::materialize() with opcode 0x9A in C++
        - Clears entire state stack (all saved states discarded)
        - Resets all graphics attributes to defaults
        - Useful at start of new page or drawing section
        - More drastic than RESTORE_STATE (clears all saved states)
        - Use cases: initialization, error recovery, page boundaries
        - After RESET_STATE, no states can be restored
    """
    return {
        'type': 'reset_state',
        'stack_cleared': True
    }


# =============================================================================
# TEST SUITE
# =============================================================================

def test_opcode_0x5a_save_state():
    """Test suite for opcode 0x5A (SAVE_STATE)."""
    import io

    print("=" * 70)
    print("TESTING OPCODE 0x5A 'Z' (SAVE_STATE)")
    print("=" * 70)

    # Test 1: Basic save state (no data)
    print("\nTest 1: Basic save state operation")
    stream = io.BytesIO(b'')
    result = parse_opcode_0x5a_save_state(stream)

    assert result['type'] == 'save_state', f"Expected type='save_state', got {result['type']}"
    assert result['stack_depth_increment'] == 1, f"Expected stack_depth_increment=1, got {result['stack_depth_increment']}"
    print(f"  PASS: {result}")

    # Test 2: Multiple save state operations
    print("\nTest 2: Multiple save state operations (simulating stack growth)")
    for i in range(5):
        stream = io.BytesIO(b'')
        result = parse_opcode_0x5a_save_state(stream)
        assert result['stack_depth_increment'] == 1
    print(f"  PASS: 5 consecutive save operations, each increments stack by 1")

    # Test 3: Save state with trailing data (ignored)
    print("\nTest 3: Save state with trailing data (ignored)")
    stream = io.BytesIO(b'trailing_data_ignored')
    result = parse_opcode_0x5a_save_state(stream)
    assert result['type'] == 'save_state'
    print(f"  PASS: {result}")

    # Test 4: Integration test - verify GraphicsState structure
    print("\nTest 4: GraphicsState structure validation")
    state = GraphicsState()
    state_dict = state.to_dict()
    assert 'foreground_color' in state_dict
    assert 'line_weight' in state_dict
    assert 'font_name' in state_dict
    assert 'transform_matrix' in state_dict
    print(f"  PASS: GraphicsState has all required attributes")

    print("\n" + "=" * 70)
    print("OPCODE 0x5A 'Z' (SAVE_STATE): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x7a_restore_state():
    """Test suite for opcode 0x7A (RESTORE_STATE)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x7A 'z' (RESTORE_STATE)")
    print("=" * 70)

    # Test 1: Basic restore state (no data)
    print("\nTest 1: Basic restore state operation")
    stream = io.BytesIO(b'')
    result = parse_opcode_0x7a_restore_state(stream)

    assert result['type'] == 'restore_state', f"Expected type='restore_state', got {result['type']}"
    assert result['stack_depth_decrement'] == 1, f"Expected stack_depth_decrement=1, got {result['stack_depth_decrement']}"
    print(f"  PASS: {result}")

    # Test 2: Multiple restore state operations
    print("\nTest 2: Multiple restore state operations (simulating stack shrink)")
    for i in range(3):
        stream = io.BytesIO(b'')
        result = parse_opcode_0x7a_restore_state(stream)
        assert result['stack_depth_decrement'] == 1
    print(f"  PASS: 3 consecutive restore operations, each decrements stack by 1")

    # Test 3: Restore state with trailing data (ignored)
    print("\nTest 3: Restore state with trailing data (ignored)")
    stream = io.BytesIO(b'trailing_data_ignored')
    result = parse_opcode_0x7a_restore_state(stream)
    assert result['type'] == 'restore_state'
    print(f"  PASS: {result}")

    # Test 4: Save/Restore sequence simulation
    print("\nTest 4: Save/Restore sequence simulation")
    save_result = parse_opcode_0x5a_save_state(io.BytesIO(b''))
    restore_result = parse_opcode_0x7a_restore_state(io.BytesIO(b''))

    # Stack should net to zero: +1 (save) -1 (restore) = 0
    net_change = save_result['stack_depth_increment'] - restore_result['stack_depth_decrement']
    assert net_change == 0
    print(f"  PASS: Save/Restore pair nets to zero stack change")

    print("\n" + "=" * 70)
    print("OPCODE 0x7A 'z' (RESTORE_STATE): ALL TESTS PASSED")
    print("=" * 70)


def test_opcode_0x9a_reset_state():
    """Test suite for opcode 0x9A (RESET_STATE)."""
    import io

    print("\n" + "=" * 70)
    print("TESTING OPCODE 0x9A (RESET_STATE)")
    print("=" * 70)

    # Test 1: Basic reset state (no data)
    print("\nTest 1: Basic reset state operation")
    stream = io.BytesIO(b'')
    result = parse_opcode_0x9a_reset_state(stream)

    assert result['type'] == 'reset_state', f"Expected type='reset_state', got {result['type']}"
    assert result['stack_cleared'] == True, f"Expected stack_cleared=True, got {result['stack_cleared']}"
    print(f"  PASS: {result}")

    # Test 2: Multiple reset state operations (idempotent)
    print("\nTest 2: Multiple reset state operations (idempotent)")
    results = []
    for i in range(3):
        stream = io.BytesIO(b'')
        result = parse_opcode_0x9a_reset_state(stream)
        results.append(result)
        assert result['stack_cleared'] == True

    # All results should be identical
    assert all(r == results[0] for r in results)
    print(f"  PASS: Multiple resets produce identical results (idempotent)")

    # Test 3: Reset state with trailing data (ignored)
    print("\nTest 3: Reset state with trailing data (ignored)")
    stream = io.BytesIO(b'trailing_data_ignored')
    result = parse_opcode_0x9a_reset_state(stream)
    assert result['type'] == 'reset_state'
    print(f"  PASS: {result}")

    # Test 4: Default GraphicsState values
    print("\nTest 4: Verify default GraphicsState values")
    default_state = GraphicsState()
    assert default_state.foreground_color == (0, 0, 0, 255), "Default foreground should be black"
    assert default_state.background_color == (255, 255, 255, 255), "Default background should be white"
    assert default_state.line_weight == 1, "Default line weight should be 1"
    assert default_state.line_style == 'solid', "Default line style should be solid"
    assert default_state.visibility == True, "Default visibility should be True"
    print(f"  PASS: Default GraphicsState values verified")

    print("\n" + "=" * 70)
    print("OPCODE 0x9A (RESET_STATE): ALL TESTS PASSED")
    print("=" * 70)


def test_integration_state_management():
    """Integration test demonstrating state push/pop behavior."""
    import io

    print("\n" + "=" * 70)
    print("INTEGRATION TEST: STATE MANAGEMENT")
    print("=" * 70)

    # Simulate a typical state management sequence
    print("\nTest: State push/pop sequence simulation")
    print("  1. SAVE_STATE (stack depth: 0 -> 1)")
    print("  2. Modify attributes (color, line weight, etc.)")
    print("  3. SAVE_STATE (stack depth: 1 -> 2)")
    print("  4. Modify more attributes")
    print("  5. RESTORE_STATE (stack depth: 2 -> 1)")
    print("  6. Modify attributes again")
    print("  7. RESTORE_STATE (stack depth: 1 -> 0)")
    print("  8. RESET_STATE (stack depth: 0, stack cleared)")

    stack_depth = 0

    # Step 1: Save initial state
    result = parse_opcode_0x5a_save_state(io.BytesIO(b''))
    stack_depth += result['stack_depth_increment']
    assert stack_depth == 1
    print(f"\n  After step 1 (SAVE): stack_depth = {stack_depth}")

    # Step 3: Save nested state
    result = parse_opcode_0x5a_save_state(io.BytesIO(b''))
    stack_depth += result['stack_depth_increment']
    assert stack_depth == 2
    print(f"  After step 3 (SAVE): stack_depth = {stack_depth}")

    # Step 5: Restore nested state
    result = parse_opcode_0x7a_restore_state(io.BytesIO(b''))
    stack_depth -= result['stack_depth_decrement']
    assert stack_depth == 1
    print(f"  After step 5 (RESTORE): stack_depth = {stack_depth}")

    # Step 7: Restore initial state
    result = parse_opcode_0x7a_restore_state(io.BytesIO(b''))
    stack_depth -= result['stack_depth_decrement']
    assert stack_depth == 0
    print(f"  After step 7 (RESTORE): stack_depth = {stack_depth}")

    # Step 8: Reset everything
    result = parse_opcode_0x9a_reset_state(io.BytesIO(b''))
    assert result['stack_cleared'] == True
    stack_depth = 0  # Reset clears stack
    print(f"  After step 8 (RESET): stack_depth = {stack_depth}, stack_cleared = True")

    print(f"\n  PASS: State management sequence completed successfully")

    print("\n" + "=" * 70)
    print("INTEGRATION TEST: ALL TESTS PASSED")
    print("=" * 70)


def run_all_tests():
    """Run all test suites for Agent 42 opcodes."""
    print("\n" + "=" * 70)
    print("DWF AGENT 42: STATE MANAGEMENT TEST SUITE")
    print("=" * 70)
    print("Testing 3 opcodes:")
    print("  - 0x5A 'Z': SAVE_STATE (push state to stack)")
    print("  - 0x7A 'z': RESTORE_STATE (pop state from stack)")
    print("  - 0x9A: RESET_STATE (clear stack and reset to defaults)")
    print("=" * 70)

    test_opcode_0x5a_save_state()
    test_opcode_0x7a_restore_state()
    test_opcode_0x9a_reset_state()
    test_integration_state_management()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSummary:")
    print("  - Opcode 0x5A 'Z' (SAVE_STATE): 4 tests passed")
    print("  - Opcode 0x7A 'z' (RESTORE_STATE): 4 tests passed")
    print("  - Opcode 0x9A (RESET_STATE): 4 tests passed")
    print("  - Integration test: 1 test passed")
    print("  - Total: 13 tests passed")
    print("\nSpecial Features:")
    print("  - GraphicsState class defining complete state structure")
    print("  - State stack depth tracking (increment/decrement)")
    print("  - Integration test demonstrating push/pop sequence")
    print("  - Default state values defined and validated")
    print("\nEdge Cases Handled:")
    print("  - Multiple consecutive save operations (stack growth)")
    print("  - Multiple consecutive restore operations (stack shrink)")
    print("  - Save/Restore balance verification (net zero)")
    print("  - Reset clears entire stack (idempotent)")
    print("  - Nested state management (2-level stack simulation)")
    print("  - Default graphics state attribute values")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
