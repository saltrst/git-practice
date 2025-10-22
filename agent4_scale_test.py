#!/usr/bin/env python3
"""
Agent 4 - Scale Factor Testing Script
Tests multiple scale factors with 3.dwf to find correct scaling.
"""

import sys
from pathlib import Path
from PyPDF2 import PdfReader

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
from integration.pdf_renderer_v1 import render_dwf_to_pdf


def normalize_and_absolute_coords(opcodes):
    """
    Convert relative coordinates to absolute and normalize field names.
    Returns: (normalized_opcodes, bounding_box_dict)
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


def apply_scale_to_opcodes(opcodes, scale):
    """Apply scale factor to all coordinates in opcodes."""
    import copy
    scaled_opcodes = copy.deepcopy(opcodes)

    for op in scaled_opcodes:
        if 'vertices' in op:
            op['vertices'] = [[x * scale, y * scale] for x, y in op['vertices']]
        if 'start' in op:
            op['start'] = [op['start'][0] * scale, op['start'][1] * scale]
        if 'end' in op:
            op['end'] = [op['end'][0] * scale, op['end'][1] * scale]

    return scaled_opcodes


def test_bounding_box():
    """Test 1: Parse drawing.w2d and calculate bounding box."""
    print("=" * 80)
    print("TEST 1: PARSE DRAWING.W2D AND CALCULATE BOUNDING BOX")
    print("=" * 80)

    input_file = "drawing.w2d"
    print(f"\nParsing: {input_file}")
    print(f"File size: {Path(input_file).stat().st_size / (1024*1024):.2f} MB")

    # Parse W2D file
    opcodes = parse_dwf_file(input_file)
    print(f"Parsed {len(opcodes)} opcodes")

    # Count opcode types
    from collections import Counter
    type_counts = Counter(op.get('type', 'NO TYPE') for op in opcodes)
    print(f"\nTop 10 opcode types:")
    for opcode_type, count in type_counts.most_common(10):
        print(f"  {opcode_type}: {count}")

    # Convert to absolute and calculate bounding box
    normalized_opcodes, bbox = normalize_and_absolute_coords(opcodes)

    if bbox:
        print(f"\nBOUNDING BOX:")
        print(f"  Min X: {bbox['min_x']:.2f}")
        print(f"  Max X: {bbox['max_x']:.2f}")
        print(f"  Min Y: {bbox['min_y']:.2f}")
        print(f"  Max Y: {bbox['max_y']:.2f}")
        print(f"  Width: {bbox['width']:.2f} DWF units")
        print(f"  Height: {bbox['height']:.2f} DWF units")
        print(f"  Aspect ratio: {bbox['width']/bbox['height']:.3f}")
    else:
        print("ERROR: No coordinates found!")
        return None, None

    return normalized_opcodes, bbox


def test_scale_factors(normalized_opcodes):
    """Test 2: Try converting with multiple scale factors."""
    print("\n" + "=" * 80)
    print("TEST 2: TEST MULTIPLE SCALE FACTORS")
    print("=" * 80)

    scale_factors = [0.001, 0.01, 0.1, 1.0, 10.0]
    results = []

    page_width = 17 * 72  # 17 inches in points
    page_height = 11 * 72  # 11 inches in points

    for scale in scale_factors:
        print(f"\nTesting scale factor: {scale}")

        # Apply scale to opcodes
        scaled_opcodes = apply_scale_to_opcodes(normalized_opcodes, scale)

        # Render to PDF
        output_file = f"agent4_test_scale_{scale}.pdf"
        try:
            render_dwf_to_pdf(scaled_opcodes, output_file,
                            pagesize=(page_width, page_height))

            # Check output file
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                print(f"  Output: {output_file}")
                print(f"  Size: {file_size / 1024:.2f} KB")

                results.append({
                    'scale': scale,
                    'output_file': output_file,
                    'size_kb': file_size / 1024
                })
            else:
                print(f"  ERROR: Output file not created")

        except Exception as e:
            print(f"  ERROR: {e}")

    return results


def analyze_reference_pdf():
    """Test 3: Analyze reference 3.pdf metadata and calculate optimal scale."""
    print("\n" + "=" * 80)
    print("TEST 3: ANALYZE REFERENCE 3.PDF")
    print("=" * 80)

    ref_file = "3.pdf"
    print(f"\nAnalyzing: {ref_file}")
    print(f"File size: {Path(ref_file).stat().st_size / (1024*1024):.2f} MB")

    try:
        reader = PdfReader(ref_file)

        print(f"\nPDF Metadata:")
        print(f"  Number of pages: {len(reader.pages)}")

        # Get first page dimensions
        first_page = reader.pages[0]
        mediabox = first_page.mediabox

        # Convert to points (PDF units)
        width_pts = float(mediabox.width)
        height_pts = float(mediabox.height)

        # Convert to inches
        width_inches = width_pts / 72
        height_inches = height_pts / 72

        print(f"\nPage 1 dimensions:")
        print(f"  Width: {width_pts:.2f} points ({width_inches:.2f} inches)")
        print(f"  Height: {height_pts:.2f} points ({height_inches:.2f} inches)")
        print(f"  Aspect ratio: {width_pts/height_pts:.3f}")

        return {
            'pages': len(reader.pages),
            'width_pts': width_pts,
            'height_pts': height_pts,
            'width_inches': width_inches,
            'height_inches': height_inches
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return None


def calculate_optimal_scale(bbox, ref_pdf_info):
    """Calculate optimal scale factor based on bounding box and reference PDF."""
    print("\n" + "=" * 80)
    print("CALCULATING OPTIMAL SCALE FACTOR")
    print("=" * 80)

    if not bbox or not ref_pdf_info:
        print("ERROR: Missing bbox or reference PDF info")
        return None

    # Target dimensions from reference PDF
    target_width = ref_pdf_info['width_pts']
    target_height = ref_pdf_info['height_pts']

    # Source dimensions from DWF
    source_width = bbox['width']
    source_height = bbox['height']

    # Calculate scale factors for each dimension
    scale_x = target_width / source_width
    scale_y = target_height / source_height

    # Use smaller scale to ensure it fits
    optimal_scale = min(scale_x, scale_y)

    print(f"\nCalculation:")
    print(f"  DWF dimensions: {source_width:.2f} x {source_height:.2f} units")
    print(f"  Target (3.pdf): {target_width:.2f} x {target_height:.2f} points")
    print(f"  Scale X: {scale_x:.6f}")
    print(f"  Scale Y: {scale_y:.6f}")
    print(f"  Optimal scale (min): {optimal_scale:.6f}")

    # Calculate resulting dimensions
    result_width = source_width * optimal_scale
    result_height = source_height * optimal_scale

    print(f"\nResult with optimal scale:")
    print(f"  Scaled dimensions: {result_width:.2f} x {result_height:.2f} points")
    print(f"  Fits in target: {'YES' if result_width <= target_width and result_height <= target_height else 'NO'}")

    return optimal_scale


def test_optimal_scale(normalized_opcodes, optimal_scale):
    """Test the calculated optimal scale factor."""
    print("\n" + "=" * 80)
    print("TEST 4: APPLY OPTIMAL SCALE FACTOR")
    print("=" * 80)

    print(f"\nTesting optimal scale factor: {optimal_scale:.6f}")

    # Apply scale to opcodes
    scaled_opcodes = apply_scale_to_opcodes(normalized_opcodes, optimal_scale)

    # Use reference PDF page size
    page_width = 17 * 72  # Can be adjusted based on reference
    page_height = 11 * 72

    # Render to PDF
    output_file = f"agent4_test_scale_optimal.pdf"
    try:
        render_dwf_to_pdf(scaled_opcodes, output_file,
                        pagesize=(page_width, page_height))

        # Check output file
        if Path(output_file).exists():
            file_size = Path(output_file).stat().st_size
            print(f"  Output: {output_file}")
            print(f"  Size: {file_size / 1024:.2f} KB")
            return output_file
        else:
            print(f"  ERROR: Output file not created")
            return None

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    """Main test runner."""
    print("AGENT 4 - SCALE FACTOR TESTING")
    print("Testing file: 3.dwf (drawing.w2d)")
    print("Reference: 3.pdf")
    print()

    # Test 1: Parse and get bounding box
    normalized_opcodes, bbox = test_bounding_box()
    if not bbox:
        print("\nFATAL ERROR: Could not parse drawing or calculate bounding box")
        return 1

    # Test 2: Test multiple scale factors
    scale_test_results = test_scale_factors(normalized_opcodes)

    # Test 3: Analyze reference PDF
    ref_pdf_info = analyze_reference_pdf()

    # Calculate optimal scale
    optimal_scale = None
    if bbox and ref_pdf_info:
        optimal_scale = calculate_optimal_scale(bbox, ref_pdf_info)

        # Test optimal scale
        if optimal_scale:
            test_optimal_scale(normalized_opcodes, optimal_scale)

    # Generate summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n1. Bounding Box:")
    if bbox:
        print(f"   Range: ({bbox['min_x']:.2f}, {bbox['min_y']:.2f}) to ({bbox['max_x']:.2f}, {bbox['max_y']:.2f})")
        print(f"   Size: {bbox['width']:.2f} x {bbox['height']:.2f} DWF units")

    print("\n2. Scale Factor Tests:")
    for result in scale_test_results:
        print(f"   Scale {result['scale']}: {result['output_file']} ({result['size_kb']:.2f} KB)")

    print("\n3. Reference PDF (3.pdf):")
    if ref_pdf_info:
        print(f"   Dimensions: {ref_pdf_info['width_pts']:.2f} x {ref_pdf_info['height_pts']:.2f} points")
        print(f"   Size: {ref_pdf_info['width_inches']:.2f}\" x {ref_pdf_info['height_inches']:.2f}\"")

    print("\n4. Optimal Scale Factor:")
    if optimal_scale:
        print(f"   Calculated: {optimal_scale:.6f}")
        print(f"   Test output: agent4_test_scale_optimal.pdf")

    print("\n" + "=" * 80)
    print("All tests complete! Review outputs and generate agent4_scale_results.md")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
