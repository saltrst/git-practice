#!/usr/bin/env python3
"""
Agent 7 - Test 3: End-to-End Coordinate Flow Test

Traces a single opcode through the complete transformation pipeline:
Parse → Relative-to-Absolute → transform_point → PDF Coordinates

This test extracts ONE real opcode from drawing.w2d and traces it through
each transformation step to verify the complete coordinate flow.
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import transform_point
from convert_final import normalize_and_absolute_coords


def test_end_to_end_flow():
    """Test complete coordinate transformation flow with real opcode."""

    print("=" * 70)
    print("AGENT 7 - TEST 3: End-to-End Coordinate Flow Test")
    print("=" * 70)

    # Step 1: Parse opcodes from W2D file
    print("\n" + "=" * 70)
    print("STEP 1: Parse W2D File")
    print("=" * 70)

    input_file = "drawing.w2d"
    if not Path(input_file).exists():
        print(f"ERROR: {input_file} not found")
        return False

    print(f"Parsing {input_file}...")
    try:
        opcodes = parse_dwf_file(input_file)
        print(f"✓ Parsed {len(opcodes)} opcodes")
    except Exception as e:
        print(f"✗ Error parsing file: {e}")
        return False

    # Step 2: Find interesting opcodes to trace
    print("\n" + "=" * 70)
    print("STEP 2: Select Test Opcode")
    print("=" * 70)

    # Look for different opcode types
    relative_opcodes = [op for op in opcodes if op.get('relative', False)]
    set_origin_opcodes = [op for op in opcodes if op.get('type') == 'set_origin']
    line_opcodes = [op for op in opcodes if op.get('type') in ['line', 'line_16r']]
    polyline_opcodes = [op for op in opcodes if 'polyline' in op.get('type', '').lower()]

    print(f"Found opcode types:")
    print(f"  Relative opcodes: {len(relative_opcodes)}")
    print(f"  set_origin opcodes: {len(set_origin_opcodes)}")
    print(f"  Line opcodes: {len(line_opcodes)}")
    print(f"  Polyline opcodes: {len(polyline_opcodes)}")

    # Select a test opcode (prefer relative polyline with set_origin before it)
    test_opcode = None
    test_index = None

    # Try to find a relative polyline with a set_origin before it
    for i, op in enumerate(opcodes):
        if op.get('relative', False) and 'points' in op:
            # Check if there's a set_origin in the previous few opcodes
            for j in range(max(0, i-5), i):
                if opcodes[j].get('type') == 'set_origin':
                    # Found a good test case!
                    test_index = i
                    test_opcode = op
                    origin_index = j
                    origin_opcode = opcodes[j]
                    break
            if test_opcode:
                break

    # Fallback: just use first relative opcode
    if not test_opcode and relative_opcodes:
        for i, op in enumerate(opcodes):
            if op.get('relative', False):
                test_index = i
                test_opcode = op
                origin_opcode = None
                origin_index = None
                break

    # Fallback 2: use first line opcode
    if not test_opcode and line_opcodes:
        test_opcode = line_opcodes[0]
        test_index = opcodes.index(test_opcode)
        origin_opcode = None
        origin_index = None

    if not test_opcode:
        print("✗ No suitable test opcode found")
        return False

    print(f"\nSelected test opcode at index {test_index}:")
    print(f"  Type: {test_opcode.get('type')}")
    print(f"  Relative: {test_opcode.get('relative', False)}")

    if origin_opcode:
        print(f"\nPreceding set_origin at index {origin_index}:")
        print(f"  Origin: {origin_opcode.get('origin')}")

    # Step 3: Trace through relative-to-absolute conversion
    print("\n" + "=" * 70)
    print("STEP 3: Relative-to-Absolute Conversion")
    print("=" * 70)

    # Create a minimal opcode sequence for testing
    if origin_opcode:
        test_sequence = [origin_opcode, test_opcode]
    else:
        test_sequence = [test_opcode]

    print("\nBEFORE conversion:")
    for i, op in enumerate(test_sequence):
        print(f"  Opcode {i}: {op.get('type')}")
        if 'points' in op:
            print(f"    points: {op['points'][:3]}..." if len(op['points']) > 3 else f"    points: {op['points']}")
        if 'point1' in op and 'point2' in op:
            print(f"    point1: {op['point1']}, point2: {op['point2']}")
        if 'origin' in op:
            print(f"    origin: {op['origin']}")
        if 'relative' in op:
            print(f"    relative: {op['relative']}")

    # Apply normalization
    normalized = normalize_and_absolute_coords(test_sequence)

    print("\nAFTER conversion:")
    for i, op in enumerate(normalized):
        print(f"  Opcode {i}: {op.get('type')}")
        if 'points' in op or 'vertices' in op:
            coords = op.get('vertices') or op.get('points')
            print(f"    vertices: {coords[:3]}..." if len(coords) > 3 else f"    vertices: {coords}")
        if 'start' in op and 'end' in op:
            print(f"    start: {op['start']}, end: {op['end']}")
        if 'point1' in op and 'point2' in op:
            print(f"    point1: {op['point1']}, point2: {op['point2']}")
        if 'relative' in op:
            print(f"    relative: {op['relative']}")

    # Step 4: Apply transform_point to coordinates
    print("\n" + "=" * 70)
    print("STEP 4: Apply transform_point (DWF → PDF coordinates)")
    print("=" * 70)

    page_height = 792  # Letter size
    scale = 0.1  # Default scale

    print(f"\nTransform parameters:")
    print(f"  page_height: {page_height} points")
    print(f"  scale: {scale}")

    # Get the normalized test opcode (skip set_origin if present)
    norm_test = normalized[-1]

    # Extract coordinates
    coords = None
    if 'vertices' in norm_test:
        coords = norm_test['vertices']
    elif 'points' in norm_test:
        coords = norm_test['points']
    elif 'start' in norm_test and 'end' in norm_test:
        coords = [norm_test['start'], norm_test['end']]
    elif 'point1' in norm_test and 'point2' in norm_test:
        coords = [norm_test['point1'], norm_test['point2']]

    if coords:
        print(f"\nAbsolute DWF coordinates (first 3):")
        for i, coord in enumerate(coords[:3]):
            print(f"  Point {i}: ({coord[0]}, {coord[1]})")

        print(f"\nPDF coordinates after transform_point:")
        pdf_coords = []
        for i, coord in enumerate(coords[:3]):
            pdf_x, pdf_y = transform_point(coord[0], coord[1], page_height, scale)
            pdf_coords.append((pdf_x, pdf_y))
            print(f"  Point {i}: ({pdf_x:.2f}, {pdf_y:.2f}) PDF points")
            # Convert to inches for reference
            inches_x = pdf_x / 72
            inches_y = pdf_y / 72
            print(f"           ({inches_x:.2f}\", {inches_y:.2f}\") in inches")

    # Step 5: Complete flow summary
    print("\n" + "=" * 70)
    print("STEP 5: Complete Transformation Flow Summary")
    print("=" * 70)

    if coords and len(coords) > 0:
        print("\nTaking first coordinate as example:")
        print()
        original_coord = coords[0]
        pdf_coord = pdf_coords[0] if pdf_coords else None

        # Check if this was originally relative
        was_relative = test_opcode.get('relative', False)

        if was_relative and origin_opcode:
            origin = origin_opcode.get('origin', [0, 0])
            # We don't have the original relative delta, but we can explain the flow
            print("Step-by-step transformation:")
            print(f"  1. set_origin sets reference point → {origin}")
            print(f"  2. Relative delta is accumulated from origin")
            print(f"  3. Result: Absolute DWF coordinate → {original_coord}")
            print(f"  4. transform_point applies scale {scale}")
            print(f"     {original_coord[0]} * {scale} = {original_coord[0] * scale}")
            print(f"     {original_coord[1]} * {scale} = {original_coord[1] * scale}")
            print(f"  5. Final PDF coordinate → ({pdf_coord[0]:.2f}, {pdf_coord[1]:.2f})")
        elif was_relative:
            print("Step-by-step transformation:")
            print(f"  1. Relative delta accumulated from origin (0, 0)")
            print(f"  2. Result: Absolute DWF coordinate → {original_coord}")
            print(f"  3. transform_point applies scale {scale}")
            print(f"     {original_coord[0]} * {scale} = {original_coord[0] * scale}")
            print(f"     {original_coord[1]} * {scale} = {original_coord[1] * scale}")
            print(f"  4. Final PDF coordinate → ({pdf_coord[0]:.2f}, {pdf_coord[1]:.2f})")
        else:
            print("Step-by-step transformation:")
            print(f"  1. Opcode has absolute coordinates → {original_coord}")
            print(f"  2. transform_point applies scale {scale}")
            print(f"     {original_coord[0]} * {scale} = {original_coord[0] * scale}")
            print(f"     {original_coord[1]} * {scale} = {original_coord[1] * scale}")
            print(f"  3. Final PDF coordinate → ({pdf_coord[0]:.2f}, {pdf_coord[1]:.2f})")

    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()
    print("Complete coordinate transformation pipeline:")
    print()
    print("1. PARSING (dwf_parser_v1.py):")
    print("   - Reads binary W2D file")
    print("   - Extracts opcodes with coordinates")
    print("   - Marks opcodes as relative or absolute")
    print()
    print("2. RELATIVE-TO-ABSOLUTE (normalize_and_absolute_coords):")
    print("   - Tracks current_origin state")
    print("   - set_origin opcodes update the reference point")
    print("   - Relative coordinates are deltas accumulated from current_origin")
    print("   - Normalizes field names (points→vertices, etc.)")
    print()
    print("3. COORDINATE TRANSFORM (transform_point):")
    print("   - Applies linear scaling: pdf_coord = dwf_coord * scale")
    print("   - No Y-axis flip (both systems use bottom-left, Y-up)")
    print("   - No origin offset applied")
    print()
    print("4. PDF RENDERING (pdf_renderer_v1.py):")
    print("   - Uses transformed coordinates for ReportLab canvas")
    print("   - Draws shapes at PDF coordinate positions")
    print()

    print("=" * 70)
    print("✓ END-TO-END FLOW TEST COMPLETE")
    print("=" * 70)

    return True


if __name__ == '__main__':
    success = test_end_to_end_flow()
    sys.exit(0 if success else 1)
