#!/usr/bin/env python3
"""
DWF to PDF Converter - Auto-scaling Version

Automatically calculates optimal scale factor to fit drawing on page.
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
    Also calculates bounding box and returns it.
    """
    # Track current position
    current_pos = [0, 0]
    normalized = []

    for op in opcodes:
        opcode_type = op.get('type', '')
        new_op = op.copy()

        # set_origin provides absolute position
        if opcode_type == 'set_origin':
            origin = op.get('origin', [0, 0])
            current_pos = list(origin)

        # Convert relative coordinates to absolute
        if op.get('relative', False):
            if 'points' in op:
                points = op['points']
                absolute_points = []
                pos = current_pos.copy()

                for delta in points:
                    pos[0] += delta[0]
                    pos[1] += delta[1]
                    absolute_points.append(pos.copy())

                new_op['points'] = absolute_points
                new_op['relative'] = False

                if absolute_points:
                    current_pos = absolute_points[-1].copy()

            elif 'point1' in op and 'point2' in op:
                p1 = op['point1']
                p2 = op['point2']
                abs_p1 = [current_pos[0] + p1[0], current_pos[1] + p1[1]]
                abs_p2 = [abs_p1[0] + p2[0], abs_p1[1] + p2[1]]
                new_op['point1'] = abs_p1
                new_op['point2'] = abs_p2
                new_op['relative'] = False
                current_pos = abs_p2.copy()

        # Normalize field names
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
        return normalized, None

    min_x = min(c[0] for c in all_coords)
    min_y = min(c[1] for c in all_coords)
    max_x = max(c[0] for c in all_coords)
    max_y = max(c[1] for c in all_coords)

    bbox = {
        'min_x': min_x,
        'min_y': min_y,
        'max_x': max_x,
        'max_y': max_y,
        'width': max_x - min_x,
        'height': max_y - min_y
    }

    # Translate to origin
    for op in normalized:
        if 'vertices' in op:
            op['vertices'] = [[x - min_x, y - min_y] for x, y in op['vertices']]
        if 'start' in op:
            op['start'] = [op['start'][0] - min_x, op['start'][1] - min_y]
        if 'end' in op:
            op['end'] = [op['end'][0] - min_x, op['end'][1] - min_y]

    return normalized, bbox

def calculate_optimal_scale(bbox, page_width, page_height, margin=36):
    """
    Calculate optimal scale factor to fit drawing on page with margin.

    Args:
        bbox: Bounding box dict with 'width' and 'height'
        page_width, page_height: PDF page dimensions in points
        margin: Margin in points (default 0.5 inch = 36 points)

    Returns:
        scale: Optimal scale factor
    """
    available_width = page_width - (2 * margin)
    available_height = page_height - (2 * margin)

    scale_x = available_width / bbox['width']
    scale_y = available_height / bbox['height']

    # Use smaller scale to fit both dimensions
    scale = min(scale_x, scale_y)

    return scale

def apply_scale_to_opcodes(opcodes, scale):
    """
    Apply scale factor to all coordinates in opcodes.
    """
    for op in opcodes:
        if 'vertices' in op:
            op['vertices'] = [[x * scale, y * scale] for x, y in op['vertices']]
        if 'start' in op:
            op['start'] = [op['start'][0] * scale, op['start'][1] * scale]
        if 'end' in op:
            op['end'] = [op['end'][0] * scale, op['end'][1] * scale]
    return opcodes

def main():
    input_file = "drawing.w2d"
    output_file = "output_auto_scale.pdf"

    print(f"Converting {input_file} to {output_file}...")
    print(f"Input size: {Path(input_file).stat().st_size / (1024*1024):.2f} MB")

    try:
        # Step 1: Parse W2D file
        print("\n[1/4] Parsing W2D file...")
        opcodes = parse_dwf_file(input_file)
        print(f"✓ Parsed {len(opcodes)} opcodes")

        # Step 2: Convert to absolute and calculate bounding box
        print("\n[2/4] Converting relative→absolute coordinates...")
        normalized_opcodes, bbox = normalize_and_absolute_coords(opcodes)
        print(f"✓ Processed {len(normalized_opcodes)} opcodes")

        if bbox:
            print(f"  Drawing size: {bbox['width']:.0f} x {bbox['height']:.0f} DWF units")
        else:
            print("  Warning: No coordinates found")
            return 1

        # Step 3: Calculate optimal scale
        print("\n[3/4] Calculating optimal scale...")
        page_width = 17 * 72  # 17 inches
        page_height = 11 * 72  # 11 inches
        scale = calculate_optimal_scale(bbox, page_width, page_height, margin=36)

        print(f"  Page size: {page_width} x {page_height} points (17\" x 11\")")
        print(f"  Optimal scale: {scale:.6f}")
        print(f"  Scaled drawing: {bbox['width']*scale:.1f} x {bbox['height']*scale:.1f} points")

        # Apply scale to opcodes
        scaled_opcodes = apply_scale_to_opcodes(normalized_opcodes, scale)

        # Step 4: Render to PDF (with scale=1.0 since we already scaled)
        print("\n[4/4] Rendering to PDF...")
        render_dwf_to_pdf(scaled_opcodes, output_file, pagesize=(page_width, page_height))
        print(f"✓ Created {output_file}")

        output_size = Path(output_file).stat().st_size / (1024*1024)
        print(f"Output size: {output_size:.2f} MB")

        if output_size < 0.1:
            print("\n⚠️  Warning: Output PDF is small - may indicate rendering issues")
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
