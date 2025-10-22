#!/usr/bin/env python3
"""
DWF to PDF Converter - Working Version with Proper Coordinate Handling

Fixes:
1. set_origin provides ABSOLUTE positions (not deltas)
2. Relative coordinates are deltas from current position
3. Translate entire drawing to origin (subtract bounding box min)
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf

def normalize_and_absolute_coords(opcodes):
    """
    Convert relative coordinates to absolute and normalize field names.

    DWF coordinate system:
    - set_origin provides ABSOLUTE position in DWF space
    - Relative flag means coordinates are deltas from current position
    - After conversion, translate entire drawing to fit on page
    """
    # Track current position (starts undefined until first set_origin)
    current_pos = [0, 0]

    normalized = []

    for op in opcodes:
        opcode_type = op.get('type', '')
        new_op = op.copy()

        # set_origin provides NEW absolute position (not a delta)
        if opcode_type == 'set_origin':
            origin = op.get('origin', [0, 0])
            current_pos = list(origin)  # This is absolute, not accumulated

        # Convert relative coordinates to absolute
        if op.get('relative', False):
            if 'points' in op:
                # Accumulate relative deltas from current position
                points = op['points']
                absolute_points = []
                pos = current_pos.copy()

                for delta in points:
                    pos[0] += delta[0]
                    pos[1] += delta[1]
                    absolute_points.append(pos.copy())

                new_op['points'] = absolute_points
                new_op['relative'] = False

                # Update current position to last point
                if absolute_points:
                    current_pos = absolute_points[-1].copy()

            elif 'point1' in op and 'point2' in op:
                # Line with relative endpoints
                p1 = op['point1']
                p2 = op['point2']
                abs_p1 = [current_pos[0] + p1[0], current_pos[1] + p1[1]]
                abs_p2 = [abs_p1[0] + p2[0], abs_p1[1] + p2[1]]
                new_op['point1'] = abs_p1
                new_op['point2'] = abs_p2
                new_op['relative'] = False
                current_pos = abs_p2.copy()

        # Normalize field names for renderer
        if 'points' in new_op and 'vertices' not in new_op:
            new_op['vertices'] = new_op['points']

        if 'point1' in new_op and 'start' not in new_op:
            new_op['start'] = new_op['point1']

        if 'point2' in new_op and 'end' not in new_op:
            new_op['end'] = new_op['point2']

        normalized.append(new_op)

    # Calculate bounding box
    all_coords = []
    for op in normalized:
        if 'vertices' in op:
            all_coords.extend(op['vertices'])
        if 'start' in op:
            all_coords.append(op['start'])
        if 'end' in op:
            all_coords.append(op['end'])

    if not all_coords:
        print("  Warning: No coordinates found")
        return normalized

    min_x = min(c[0] for c in all_coords)
    min_y = min(c[1] for c in all_coords)
    max_x = max(c[0] for c in all_coords)
    max_y = max(c[1] for c in all_coords)

    print(f"  Original bounding box: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"  Drawing size: {max_x - min_x} x {max_y - min_y}")

    # Translate entire drawing to start at origin
    for op in normalized:
        if 'vertices' in op:
            op['vertices'] = [[x - min_x, y - min_y] for x, y in op['vertices']]
        if 'start' in op:
            op['start'] = [op['start'][0] - min_x, op['start'][1] - min_y]
        if 'end' in op:
            op['end'] = [op['end'][0] - min_x, op['end'][1] - min_y]

    print(f"  Translated to origin: (0, 0) to ({max_x - min_x}, {max_y - min_y})")

    return normalized

def main():
    input_file = "drawing.w2d"
    output_file = "output_working.pdf"

    print(f"Converting {input_file} to {output_file}...")
    print(f"Input size: {Path(input_file).stat().st_size / (1024*1024):.2f} MB")

    try:
        # Step 1: Parse W2D file
        print("\n[1/3] Parsing W2D file...")
        opcodes = parse_dwf_file(input_file)
        print(f"✓ Parsed {len(opcodes)} opcodes")

        # Count opcode types
        from collections import Counter
        type_counts = Counter(op.get('type', 'NO TYPE') for op in opcodes)
        print(f"\nParsed opcode types:")
        for opcode_type, count in type_counts.most_common(5):
            print(f"  {opcode_type}: {count}")

        # Step 2: Normalize and convert coordinates
        print("\n[2/3] Converting relative→absolute and normalizing coordinates...")
        normalized_opcodes = normalize_and_absolute_coords(opcodes)
        print(f"✓ Processed {len(normalized_opcodes)} opcodes")

        # Check relative count
        relative_count = sum(1 for op in opcodes if op.get('relative', False))
        print(f"  Converted {relative_count} relative coordinate opcodes")

        # Step 3: Render to PDF
        print("\n[3/3] Rendering to PDF...")
        # Use larger page size for CAD drawing
        render_dwf_to_pdf(normalized_opcodes, output_file, pagesize=(17*72, 11*72))
        print(f"✓ Created {output_file}")

        output_size = Path(output_file).stat().st_size / (1024*1024)
        print(f"Output size: {output_size:.2f} MB")

        if output_size < 0.1:
            print("\n⚠️  Warning: Output PDF is small - may need further adjustments")
        else:
            print("\n✅ Conversion complete!")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
