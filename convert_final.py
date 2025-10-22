#!/usr/bin/env python3
"""
DWF to PDF Converter - Final Working Version

Converts drawing.w2d to output.pdf with:
1. Field name normalization (points → vertices)
2. Relative coordinate conversion to absolute
3. Proper coordinate tracking
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
    Normalize opcodes and convert relative coordinates to absolute.

    Issues fixed:
    1. Field names: points → vertices, point1 → start, point2 → end
    2. Relative coordinates: accumulate deltas to get absolute positions
    3. Track current origin from set_origin opcodes
    """
    # Track current position for relative coordinates
    current_origin = [0, 0]

    normalized = []

    for op in opcodes:
        opcode_type = op.get('type', '')
        new_op = op.copy()

        # Handle set_origin - updates the current reference point
        if opcode_type == 'set_origin':
            origin = op.get('origin', [0, 0])
            current_origin = list(origin)

        # Convert relative coordinates to absolute
        if op.get('relative', False):
            if 'points' in op:
                # Accumulate relative deltas starting from current origin
                points = op['points']
                absolute_points = []
                current_pos = current_origin.copy()

                for delta in points:
                    current_pos[0] += delta[0]
                    current_pos[1] += delta[1]
                    absolute_points.append(current_pos.copy())

                new_op['points'] = absolute_points
                new_op['relative'] = False  # Mark as now absolute

                # Update origin to last point for chaining
                if absolute_points:
                    current_origin = absolute_points[-1].copy()

            elif 'point1' in op and 'point2' in op:
                # Line with relative endpoints
                p1 = op['point1']
                p2 = op['point2']
                abs_p1 = [current_origin[0] + p1[0], current_origin[1] + p1[1]]
                abs_p2 = [abs_p1[0] + p2[0], abs_p1[1] + p2[1]]
                new_op['point1'] = abs_p1
                new_op['point2'] = abs_p2
                new_op['relative'] = False
                current_origin = abs_p2.copy()

        # Normalize field names for renderer
        if 'points' in new_op and 'vertices' not in new_op:
            new_op['vertices'] = new_op['points']

        if 'point1' in new_op and 'start' not in new_op:
            new_op['start'] = new_op['point1']

        if 'point2' in new_op and 'end' not in new_op:
            new_op['end'] = new_op['point2']

        normalized.append(new_op)

    return normalized

def main():
    input_file = "drawing.w2d"
    output_file = "output_final.pdf"

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
        print("\n[2/3] Normalizing and converting relative→absolute coordinates...")
        normalized_opcodes = normalize_and_absolute_coords(opcodes)
        print(f"✓ Processed {len(normalized_opcodes)} opcodes")

        # Check relative count
        relative_count = sum(1 for op in opcodes if op.get('relative', False))
        print(f"  Converted {relative_count} relative coordinate opcodes to absolute")

        # Step 3: Render to PDF
        print("\n[3/3] Rendering to PDF...")
        # Use larger page size for CAD drawing
        render_dwf_to_pdf(normalized_opcodes, output_file, pagesize=(17*72, 11*72))
        print(f"✓ Created {output_file}")

        output_size = Path(output_file).stat().st_size / (1024*1024)
        print(f"Output size: {output_size:.2f} MB")

        if output_size < 0.05:
            print("\n⚠️  Warning: Output PDF is small - may need coordinate/scale adjustments")
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
