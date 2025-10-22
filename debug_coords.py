#!/usr/bin/env python3
"""
Debug script to examine converted coordinates
"""

import sys
from pathlib import Path
import json

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file

def normalize_and_absolute_coords(opcodes):
    """
    Normalize opcodes and convert relative coordinates to absolute.
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
                new_op['relative'] = False

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
    print("Parsing drawing.w2d...")
    opcodes = parse_dwf_file("drawing.w2d")

    print("\n=== BEFORE CONVERSION ===")
    print("\nFirst 3 polytriangle_16r opcodes (raw):")
    count = 0
    for i, op in enumerate(opcodes):
        if op.get('type') == 'polytriangle_16r' and count < 3:
            print(f"\nOpcode {i}:")
            print(json.dumps(op, indent=2, default=str)[:500])
            count += 1

    print("\n\n=== AFTER CONVERSION ===")
    normalized = normalize_and_absolute_coords(opcodes)

    print("\nFirst 3 polytriangle_16r opcodes (converted):")
    count = 0
    for i, op in enumerate(normalized):
        if op.get('type') == 'polytriangle_16r' and count < 3:
            print(f"\nOpcode {i}:")
            print(json.dumps(op, indent=2, default=str)[:500])
            count += 1

    # Calculate bounding box
    print("\n\n=== BOUNDING BOX ANALYSIS ===")
    all_coords = []
    for op in normalized:
        if 'vertices' in op:
            all_coords.extend(op['vertices'])
        if 'start' in op:
            all_coords.append(op['start'])
        if 'end' in op:
            all_coords.append(op['end'])

    if all_coords:
        min_x = min(c[0] for c in all_coords)
        max_x = max(c[0] for c in all_coords)
        min_y = min(c[1] for c in all_coords)
        max_y = max(c[1] for c in all_coords)

        print(f"X range: {min_x} to {max_x} (width: {max_x - min_x})")
        print(f"Y range: {min_y} to {max_y} (height: {max_y - min_y})")
        print(f"Total coordinates: {len(all_coords)}")

if __name__ == "__main__":
    main()
