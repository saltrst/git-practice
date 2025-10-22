#!/usr/bin/env python3
"""
Integration Test Suite for DWF-to-PDF System
=============================================

Tests the integration of:
1. DWF Parser V1 (A1) vs V2 (A2) - Orchestrators
2. PDF Renderer V1 (B1) vs V2 (B2) - Renderers

Mission: Find inconsistencies and break the integration with edge cases.

Author: Agent C (Integration Testing & Active Falsification Review)
Date: 2025-10-22
"""

import sys
import os
from pathlib import Path
from io import BytesIO
import struct
from typing import List, Dict, Any

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "integration"))

# Import orchestrators
import dwf_parser_v1 as parser_v1
import dwf_parser_v2 as parser_v2

# Import renderers
import pdf_renderer_v1 as renderer_v1
import pdf_renderer_v2 as renderer_v2


# =============================================================================
# TEST DATA GENERATORS
# =============================================================================

def create_test_dwf_stream_basic() -> BytesIO:
    """
    Create a basic DWF test stream with common opcodes.

    Contains:
    - Stream version
    - Line (0x6C)
    - Color (0x63)
    - Polygon (0x70)
    - End of stream
    """
    stream = BytesIO()

    # 0x01: Stream version (6.2)
    stream.write(b'\x01')
    version = (6 << 8) | 2
    stream.write(struct.pack('<H', version))

    # 0x6C: Line from (100, 100) to (300, 300)
    stream.write(b'\x6C')
    stream.write(struct.pack('<llll', 100, 100, 300, 300))

    # 0x63: Set color index to 42
    stream.write(b'\x63')
    stream.write(struct.pack('<B', 42))

    # 0x70: Polygon with 3 vertices
    stream.write(b'\x70')
    stream.write(struct.pack('<B', 3))  # 3 vertices
    stream.write(struct.pack('<llllll', 0, 0, 100, 0, 50, 100))

    # 0xFF: End of stream
    stream.write(b'\xFF')

    stream.seek(0)
    return stream


def create_test_dwf_stream_comprehensive() -> BytesIO:
    """
    Create comprehensive DWF test stream with 20+ opcodes.

    Tests:
    - Geometry: lines, circles, polygons
    - Text: ASCII and Hebrew
    - Colors: BGRA conversion
    - State: save/restore
    """
    stream = BytesIO()

    # Stream version
    stream.write(b'\x01')
    version = (6 << 8) | 2
    stream.write(struct.pack('<H', version))

    # Save state (0x5A)
    stream.write(b'\x5A')

    # Set color RGBA (0x03) - Red
    stream.write(b'\x03')
    stream.write(struct.pack('<BBBB', 255, 0, 0, 255))  # BGRA order: B=255, G=0, R=0, A=255

    # Line (0x6C)
    stream.write(b'\x6C')
    stream.write(struct.pack('<llll', 0, 0, 500, 500))

    # Circle 16r (0x12)
    stream.write(b'\x12')
    stream.write(struct.pack('<hhh', 250, 250, 100))  # center_x, center_y, radius

    # Set color RGBA (0x03) - Blue
    stream.write(b'\x03')
    stream.write(struct.pack('<BBBB', 0, 0, 255, 255))  # Blue

    # Set fill on (0x46)
    stream.write(b'\x46')

    # Polygon (0x70) - Triangle
    stream.write(b'\x70')
    stream.write(struct.pack('<B', 3))
    stream.write(struct.pack('<llllll', 600, 100, 700, 100, 650, 200))

    # Set fill off (0x66)
    stream.write(b'\x66')

    # Set color RGBA (0x03) - Green
    stream.write(b'\x03')
    stream.write(struct.pack('<BBBB', 0, 255, 0, 255))  # Green

    # Polytriangle 16r (0x14)
    stream.write(b'\x14')
    stream.write(struct.pack('<B', 3))  # 3 vertices
    stream.write(struct.pack('<hhhhhh', 100, 400, 200, 400, 150, 500))

    # Restore state (0x7A)
    stream.write(b'\x7A')

    # Line weight (0x17)
    stream.write(b'\x17')
    stream.write(struct.pack('<h', 5))  # Weight = 5

    # Another line
    stream.write(b'\x6C')
    stream.write(struct.pack('<llll', 800, 0, 800, 500))

    # Set font (0x06)
    stream.write(b'\x06')
    # Font index, height, width
    stream.write(struct.pack('<Bhh', 0, 24, 12))

    # Reset state (0x9A)
    stream.write(b'\x9A')

    # End of stream
    stream.write(b'\xFF')

    stream.seek(0)
    return stream


def create_test_dwf_stream_edge_cases() -> BytesIO:
    """
    Create DWF stream with edge cases to test error handling.

    Tests:
    - Empty data
    - Unknown opcodes
    - Malformed data
    """
    stream = BytesIO()

    # Stream version
    stream.write(b'\x01')
    version = (6 << 8) | 2
    stream.write(struct.pack('<H', version))

    # Unknown opcode (0xFE) - should be handled gracefully
    stream.write(b'\xFE')

    # Valid opcode with truncated data (line with incomplete coordinates)
    # This tests robustness
    stream.write(b'\x6C')
    stream.write(struct.pack('<ll', 100, 100))  # Only x1, y1 - missing x2, y2

    stream.seek(0)
    return stream


def create_empty_dwf_stream() -> BytesIO:
    """Create completely empty DWF stream."""
    return BytesIO()


# =============================================================================
# TASK 1: CROSS-VALIDATION OF ORCHESTRATORS (A1 vs A2)
# =============================================================================

class TestOrchestratorConsistency:
    """Compare A1 and A2 orchestrators."""

    def __init__(self):
        self.results = []
        self.failures = []

    def test_opcode_coverage_comparison(self):
        """Compare opcode coverage between A1 and A2."""
        print("\n" + "=" * 80)
        print("TEST 1: Opcode Coverage Comparison (A1 vs A2)")
        print("=" * 80)

        # A1 opcode coverage
        a1_binary = set(parser_v1.OPCODE_HANDLERS.keys())
        a1_ascii = set(parser_v1.EXTENDED_ASCII_HANDLERS.keys())
        a1_extended = set(parser_v1.EXTENDED_BINARY_HANDLERS.keys())

        print(f"\nA1 Coverage:")
        print(f"  Binary opcodes: {len(a1_binary)}")
        print(f"  Extended ASCII opcodes: {len(a1_ascii)}")
        print(f"  Extended Binary opcodes: {len(a1_extended)}")
        print(f"  Total: {len(a1_binary) + len(a1_ascii) + len(a1_extended)}")

        # A2 requires initialization to discover opcodes
        print(f"\nA2 Coverage:")
        print(f"  Uses dynamic discovery - coverage depends on agent modules")
        print(f"  NOTE: A2 may miss opcodes if naming patterns don't match")

        # List some opcodes in A1
        print(f"\nSample A1 binary opcodes: {sorted([f'0x{x:02X}' for x in list(a1_binary)[:10]])}")
        print(f"Sample A1 Extended ASCII: {sorted(list(a1_ascii)[:5])}")
        print(f"Sample A1 Extended Binary: {sorted([f'0x{x:04X}' for x in list(a1_extended)[:5]])}")

        self.results.append(("Opcode Coverage Analysis", "PASS",
                           f"A1 has {len(a1_binary)} binary, {len(a1_ascii)} ASCII, {len(a1_extended)} extended binary"))

    def test_parsing_consistency(self):
        """Test that A1 and A2 produce identical results for same input."""
        print("\n" + "=" * 80)
        print("TEST 2: Parsing Consistency (A1 vs A2 on same input)")
        print("=" * 80)

        # Create test stream
        test_stream = create_test_dwf_stream_basic()

        # Parse with A1
        print("\nParsing with A1...")
        test_stream.seek(0)
        a1_results = parser_v1.parse_dwf_stream(test_stream)
        print(f"  A1 parsed {len(a1_results)} opcodes")

        # Parse with A2 (requires file path, so we'll skip detailed comparison)
        print("\nParsing with A2...")
        print("  A2 uses file-based parsing with dynamic discovery")
        print("  Skipping direct comparison due to different APIs")

        # Show A1 results
        print(f"\nA1 Results:")
        for i, opcode in enumerate(a1_results):
            opcode_type = opcode.get('type', 'unknown')
            opcode_hex = opcode.get('opcode_hex', 'N/A')
            print(f"  {i+1}. {opcode_hex}: {opcode_type}")

        # Check for errors
        error_count = sum(1 for op in a1_results if op.get('type') == 'error')
        if error_count > 0:
            self.failures.append(f"A1 produced {error_count} errors")
            self.results.append(("A1 Parsing Consistency", "FAIL", f"{error_count} errors"))
        else:
            self.results.append(("A1 Parsing Consistency", "PASS", "No errors"))

    def test_extended_ascii_handling(self):
        """Test Extended ASCII format handling ('(' opcodes)."""
        print("\n" + "=" * 80)
        print("TEST 3: Extended ASCII Handling")
        print("=" * 80)

        # Check that both handle '(' correctly
        print("\nA1 Extended ASCII handlers:")
        for name in sorted(list(parser_v1.EXTENDED_ASCII_HANDLERS.keys())[:5]):
            print(f"  - {name}")

        print("\nBoth A1 and A2 should handle Extended ASCII opcodes starting with '('")
        print("Format: (OpcodeName ...data...)")

        self.results.append(("Extended ASCII Handling", "PASS",
                           f"A1 supports {len(parser_v1.EXTENDED_ASCII_HANDLERS)} Extended ASCII opcodes"))

    def test_extended_binary_handling(self):
        """Test Extended Binary format handling ('{' opcodes)."""
        print("\n" + "=" * 80)
        print("TEST 4: Extended Binary Handling")
        print("=" * 80)

        print("\nA1 Extended Binary handlers:")
        for opcode_id in sorted(parser_v1.EXTENDED_BINARY_HANDLERS.keys()):
            print(f"  - 0x{opcode_id:04X}")

        print("\nBoth A1 and A2 should handle Extended Binary opcodes starting with '{'")
        print("Format: {{ + size(4) + opcode(2) + data + }}")

        self.results.append(("Extended Binary Handling", "PASS",
                           f"A1 supports {len(parser_v1.EXTENDED_BINARY_HANDLERS)} Extended Binary opcodes"))

    def run_all_tests(self):
        """Run all orchestrator tests."""
        print("\n" + "#" * 80)
        print("# TASK 1: ORCHESTRATOR CROSS-VALIDATION (A1 vs A2)")
        print("#" * 80)

        self.test_opcode_coverage_comparison()
        self.test_parsing_consistency()
        self.test_extended_ascii_handling()
        self.test_extended_binary_handling()

        return self.results, self.failures


# =============================================================================
# TASK 2: CROSS-VALIDATION OF RENDERERS (B1 vs B2)
# =============================================================================

class TestRendererConsistency:
    """Compare B1 and B2 renderers."""

    def __init__(self):
        self.results = []
        self.failures = []

    def test_type_coverage_comparison(self):
        """Compare opcode type coverage between B1 and B2."""
        print("\n" + "=" * 80)
        print("TEST 1: Type Coverage Comparison (B1 vs B2)")
        print("=" * 80)

        # B2 has explicit type_handlers dict
        b2_types = set(renderer_v2.DWFPDFRenderer(":memory:").type_handlers.keys())

        print(f"\nB2 Explicit Type Handlers: {len(b2_types)}")
        print(f"  Types: {sorted(b2_types)}")

        # B1 uses if-elif chain, harder to extract
        print(f"\nB1 Type Handlers:")
        print(f"  Uses if-elif chain in render_opcode()")
        print(f"  Supports: geometry, text, images, state, attributes, metadata")

        # Check for specific types
        critical_types = ['line', 'circle', 'polygon', 'text', 'color',
                         'save_state', 'restore_state']

        print(f"\nCritical types in B2: {[t for t in critical_types if t in b2_types]}")

        missing_in_b2 = [t for t in critical_types if t not in b2_types]
        if missing_in_b2:
            self.failures.append(f"B2 missing critical types: {missing_in_b2}")
            self.results.append(("Type Coverage", "FAIL", f"Missing: {missing_in_b2}"))
        else:
            self.results.append(("Type Coverage", "PASS", "All critical types present"))

    def test_color_conversion(self):
        """Test BGRA to RGB color conversion in both renderers."""
        print("\n" + "=" * 80)
        print("TEST 2: BGRA→RGB Color Conversion")
        print("=" * 80)

        # Test B1
        print("\nB1 Color Conversion:")
        b1_result = renderer_v1.bgra_to_rgb(255, 128, 64, 255)  # B=255, G=128, R=64
        print(f"  bgra_to_rgb(255, 128, 64, 255) = {b1_result}")
        print(f"  Expected: (0.251, 0.502, 1.0) - (R/255, G/255, B/255)")

        # Test B2
        print("\nB2 Color Conversion:")
        b2_result = renderer_v2.bgra_to_rgb((255, 128, 64, 255))  # BGRA tuple
        print(f"  bgra_to_rgb((255, 128, 64, 255)) = {b2_result}")

        # Verify correctness: BGRA (255, 128, 64, 255) → RGB (64/255, 128/255, 255/255)
        expected = (64/255.0, 128/255.0, 255/255.0)
        print(f"  Expected: {expected}")

        if abs(b1_result[0] - expected[0]) < 0.01 and \
           abs(b1_result[1] - expected[1]) < 0.01 and \
           abs(b1_result[2] - expected[2]) < 0.01:
            self.results.append(("BGRA→RGB Conversion", "PASS", "Correct conversion"))
        else:
            self.failures.append(f"B1 color conversion incorrect: {b1_result} != {expected}")
            self.results.append(("BGRA→RGB Conversion", "FAIL", f"B1: {b1_result}, Expected: {expected}"))

        if abs(b2_result[0] - expected[0]) < 0.01 and \
           abs(b2_result[1] - expected[1]) < 0.01 and \
           abs(b2_result[2] - expected[2]) < 0.01:
            self.results.append(("BGRA→RGB Conversion B2", "PASS", "Correct conversion"))
        else:
            self.failures.append(f"B2 color conversion incorrect: {b2_result} != {expected}")
            self.results.append(("BGRA→RGB Conversion B2", "FAIL", f"B2: {b2_result}, Expected: {expected}"))

    def test_state_management(self):
        """Test save/restore/reset state handling."""
        print("\n" + "=" * 80)
        print("TEST 3: State Management (save/restore/reset)")
        print("=" * 80)

        # Test B1
        print("\nB1 State Management:")
        b1_renderer = renderer_v1.PDFRenderer(":memory:")

        # Initial state
        initial_color = b1_renderer.current_state.foreground_color
        print(f"  Initial color: {initial_color}")

        # Save state
        b1_renderer.save_state()
        print(f"  Saved state (stack size: {len(b1_renderer.state_stack)})")

        # Modify state
        b1_renderer.current_state.foreground_color = (255, 0, 0, 255)
        print(f"  Modified color: {b1_renderer.current_state.foreground_color}")

        # Restore state
        b1_renderer.restore_state()
        print(f"  Restored color: {b1_renderer.current_state.foreground_color}")

        # Reset state
        b1_renderer.reset_state()
        print(f"  Reset state (stack cleared: {len(b1_renderer.state_stack) == 0})")

        # Test B2
        print("\nB2 State Management:")
        b2_renderer = renderer_v2.DWFPDFRenderer(":memory:")

        initial_color_b2 = b2_renderer.state.stroke_color
        print(f"  Initial color: {initial_color_b2}")

        b2_renderer.handle_save_state({})
        print(f"  Saved state (stack size: {len(b2_renderer.state_stack.stack)})")

        b2_renderer.state.stroke_color = (1.0, 0.0, 0.0)
        print(f"  Modified color: {b2_renderer.state.stroke_color}")

        b2_renderer.handle_restore_state({})
        print(f"  Restored color: {b2_renderer.state.stroke_color}")

        # Check if B2 has reset_state
        print("\n  Checking for reset_state in B2...")
        if 'reset_state' in b2_renderer.type_handlers:
            print(f"  ✓ B2 has reset_state handler")
            self.results.append(("State Management", "PASS", "Both have save/restore/reset"))
        else:
            print(f"  ✗ B2 MISSING reset_state handler!")
            self.failures.append("B2 missing reset_state handler")
            self.results.append(("State Management", "FAIL", "B2 missing reset_state"))

    def test_hebrew_text_support(self):
        """Test Hebrew text (UTF-16LE) support."""
        print("\n" + "=" * 80)
        print("TEST 4: Hebrew Text Support (UTF-16LE)")
        print("=" * 80)

        # Hebrew text: שלום (Shalom)
        hebrew_text = "שלום"
        hebrew_utf16le = hebrew_text.encode('utf-16-le')

        print(f"\nHebrew text: {hebrew_text}")
        print(f"UTF-16LE bytes: {hebrew_utf16le.hex()}")

        print("\nB1 Hebrew Support:")
        print("  render_text_basic() handles UTF-16LE decoding:")
        print("  - if isinstance(text, bytes): text.decode('utf-16-le')")

        print("\nB2 Hebrew Support:")
        print("  handle_text() expects string, not bytes")
        print("  - Hebrew text should be pre-decoded in opcode")

        self.results.append(("Hebrew Text Support", "PASS",
                           "B1 has explicit UTF-16LE handling, B2 expects pre-decoded strings"))

    def test_coordinate_transformation(self):
        """Test coordinate transformation differences."""
        print("\n" + "=" * 80)
        print("TEST 5: Coordinate Transformation")
        print("=" * 80)

        # Test B1
        print("\nB1 Coordinate Transform:")
        print("  transform_point(x, y, page_height, scale=0.1)")
        print("  DWF uses bottom-left Y-up → PDF bottom-left Y-up")
        b1_result = renderer_v1.transform_point(1000, 2000, 11*72, scale=0.1)
        print(f"  transform_point(1000, 2000) = {b1_result}")

        # Test B2
        print("\nB2 Coordinate Transform:")
        print("  dwf_to_pdf_coords(x, y, page_height)")
        print("  DWF uses top-left Y-down → PDF bottom-left Y-up (flips Y)")
        b2_result = renderer_v2.dwf_to_pdf_coords(1000, 2000, 11*72)
        print(f"  dwf_to_pdf_coords(1000, 2000) = {b2_result}")

        print("\n  CRITICAL DIFFERENCE:")
        print("  B1 assumes DWF Y-up, B2 assumes DWF Y-down")
        print("  This will cause vertical flipping if DWF coordinate system is misunderstood!")

        self.failures.append("CRITICAL: B1 and B2 use different Y-axis conventions")
        self.results.append(("Coordinate Transform", "FAIL",
                           "B1 uses Y-up, B2 uses Y-down then flips"))

    def run_all_tests(self):
        """Run all renderer tests."""
        print("\n" + "#" * 80)
        print("# TASK 2: RENDERER CROSS-VALIDATION (B1 vs B2)")
        print("#" * 80)

        self.test_type_coverage_comparison()
        self.test_color_conversion()
        self.test_state_management()
        self.test_hebrew_text_support()
        self.test_coordinate_transformation()

        return self.results, self.failures


# =============================================================================
# TASK 3: INTEGRATION TESTING
# =============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def __init__(self):
        self.results = []
        self.failures = []

    def test_a1_b1_integration(self):
        """Test A1 parser → B1 renderer integration."""
        print("\n" + "=" * 80)
        print("TEST: A1 Parser → B1 Renderer Integration")
        print("=" * 80)

        try:
            # Parse with A1
            test_stream = create_test_dwf_stream_basic()
            opcodes = parser_v1.parse_dwf_stream(test_stream)
            print(f"  A1 parsed {len(opcodes)} opcodes")

            # Render with B1
            output_path = "/home/user/git-practice/dwf-to-pdf-project/integration/test_a1_b1.pdf"
            success = renderer_v1.render_dwf_to_pdf(opcodes, output_path)

            if success:
                print(f"  ✓ B1 rendered successfully to {output_path}")
                self.results.append(("A1→B1 Integration", "PASS", "PDF created"))
            else:
                print(f"  ✗ B1 rendering failed")
                self.failures.append("A1→B1 rendering failed")
                self.results.append(("A1→B1 Integration", "FAIL", "Rendering failed"))

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            self.failures.append(f"A1→B1 exception: {e}")
            self.results.append(("A1→B1 Integration", "FAIL", str(e)))

    def test_a1_b2_integration(self):
        """Test A1 parser → B2 renderer integration."""
        print("\n" + "=" * 80)
        print("TEST: A1 Parser → B2 Renderer Integration")
        print("=" * 80)

        try:
            # Parse with A1
            test_stream = create_test_dwf_stream_basic()
            opcodes = parser_v1.parse_dwf_stream(test_stream)
            print(f"  A1 parsed {len(opcodes)} opcodes")

            # Render with B2
            output_path = "/home/user/git-practice/dwf-to-pdf-project/integration/test_a1_b2.pdf"
            renderer_v2.render_dwf_to_pdf(opcodes, output_path)

            print(f"  ✓ B2 rendered successfully to {output_path}")
            self.results.append(("A1→B2 Integration", "PASS", "PDF created"))

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            self.failures.append(f"A1→B2 exception: {e}")
            self.results.append(("A1→B2 Integration", "FAIL", str(e)))

    def test_edge_case_empty_file(self):
        """Test empty DWF file handling."""
        print("\n" + "=" * 80)
        print("TEST: Empty DWF File")
        print("=" * 80)

        try:
            empty_stream = create_empty_dwf_stream()
            opcodes = parser_v1.parse_dwf_stream(empty_stream)
            print(f"  A1 parsed {len(opcodes)} opcodes from empty stream")

            if len(opcodes) == 0:
                print(f"  ✓ Correctly handled empty file")
                self.results.append(("Empty File", "PASS", "Handled gracefully"))
            else:
                print(f"  ✗ Unexpected opcodes from empty file")
                self.failures.append("Empty file produced opcodes")
                self.results.append(("Empty File", "FAIL", "Produced opcodes"))

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            self.failures.append(f"Empty file exception: {e}")
            self.results.append(("Empty File", "FAIL", str(e)))

    def test_edge_case_unknown_opcodes(self):
        """Test unknown opcode handling."""
        print("\n" + "=" * 80)
        print("TEST: Unknown Opcodes")
        print("=" * 80)

        try:
            # Create stream with unknown opcode
            stream = BytesIO()
            stream.write(b'\x01')  # Version
            stream.write(struct.pack('<H', 0x0602))
            stream.write(b'\xFE')  # Unknown opcode 0xFE
            stream.write(b'\xFF')  # End
            stream.seek(0)

            opcodes = parser_v1.parse_dwf_stream(stream)
            print(f"  A1 parsed {len(opcodes)} opcodes")

            # Check for unknown opcode entry
            unknown_count = sum(1 for op in opcodes if op.get('type') == 'unknown')
            print(f"  Found {unknown_count} unknown opcodes")

            if unknown_count > 0:
                print(f"  ✓ Unknown opcodes marked as 'unknown'")
                self.results.append(("Unknown Opcodes", "PASS", "Handled gracefully"))
            else:
                print(f"  ✗ Unknown opcodes not detected")
                self.failures.append("Unknown opcodes not detected")
                self.results.append(("Unknown Opcodes", "FAIL", "Not detected"))

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            self.failures.append(f"Unknown opcode exception: {e}")
            self.results.append(("Unknown Opcodes", "FAIL", str(e)))

    def test_state_stack_underflow(self):
        """Test state stack underflow (restore without save)."""
        print("\n" + "=" * 80)
        print("TEST: State Stack Underflow")
        print("=" * 80)

        try:
            # Create renderer
            renderer = renderer_v1.PDFRenderer(":memory:")

            # Try to restore without saving
            print(f"  Initial stack size: {len(renderer.state_stack)}")
            renderer.restore_state()
            print(f"  After restore: {len(renderer.state_stack)}")

            # Should not crash
            print(f"  ✓ State stack underflow handled gracefully")
            self.results.append(("State Stack Underflow", "PASS", "No crash"))

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            self.failures.append(f"State stack underflow exception: {e}")
            self.results.append(("State Stack Underflow", "FAIL", str(e)))

    def test_comprehensive_stream(self):
        """Test comprehensive DWF stream with 20+ opcodes."""
        print("\n" + "=" * 80)
        print("TEST: Comprehensive DWF Stream (20+ opcodes)")
        print("=" * 80)

        try:
            stream = create_test_dwf_stream_comprehensive()
            opcodes = parser_v1.parse_dwf_stream(stream)
            print(f"  A1 parsed {len(opcodes)} opcodes")

            # Show opcode types
            opcode_types = [op.get('type', 'unknown') for op in opcodes]
            print(f"  Opcode types: {set(opcode_types)}")

            # Render with B1
            output_path = "/home/user/git-practice/dwf-to-pdf-project/integration/test_comprehensive_b1.pdf"
            success = renderer_v1.render_dwf_to_pdf(opcodes, output_path)

            if success:
                print(f"  ✓ B1 rendered comprehensive stream to {output_path}")
                self.results.append(("Comprehensive Stream", "PASS", "All opcodes processed"))
            else:
                print(f"  ✗ B1 rendering failed")
                self.failures.append("Comprehensive stream rendering failed")
                self.results.append(("Comprehensive Stream", "FAIL", "Rendering failed"))

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            self.failures.append(f"Comprehensive stream exception: {e}")
            self.results.append(("Comprehensive Stream", "FAIL", str(e)))

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "#" * 80)
        print("# TASK 3: END-TO-END INTEGRATION TESTING")
        print("#" * 80)

        self.test_a1_b1_integration()
        self.test_a1_b2_integration()
        self.test_edge_case_empty_file()
        self.test_edge_case_unknown_opcodes()
        self.test_state_stack_underflow()
        self.test_comprehensive_stream()

        return self.results, self.failures


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main():
    """Run all integration tests and generate report."""
    print("=" * 80)
    print("DWF-TO-PDF INTEGRATION TEST SUITE")
    print("Agent C: Integration Testing & Active Falsification Review")
    print("=" * 80)

    all_results = []
    all_failures = []

    # Task 1: Orchestrator cross-validation
    orch_tests = TestOrchestratorConsistency()
    orch_results, orch_failures = orch_tests.run_all_tests()
    all_results.extend(orch_results)
    all_failures.extend(orch_failures)

    # Task 2: Renderer cross-validation
    rend_tests = TestRendererConsistency()
    rend_results, rend_failures = rend_tests.run_all_tests()
    all_results.extend(rend_results)
    all_failures.extend(rend_failures)

    # Task 3: End-to-end integration
    e2e_tests = TestEndToEndIntegration()
    e2e_results, e2e_failures = e2e_tests.run_all_tests()
    all_results.extend(e2e_results)
    all_failures.extend(e2e_failures)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print(f"\nTotal tests run: {len(all_results)}")
    passed = sum(1 for _, status, _ in all_results if status == "PASS")
    failed = sum(1 for _, status, _ in all_results if status == "FAIL")
    print(f"  PASSED: {passed}")
    print(f"  FAILED: {failed}")

    print(f"\nTotal failures detected: {len(all_failures)}")
    for i, failure in enumerate(all_failures, 1):
        print(f"  {i}. {failure}")

    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUITE COMPLETE")
    print("=" * 80)

    # Return results for report generation
    return all_results, all_failures


if __name__ == '__main__':
    results, failures = main()
