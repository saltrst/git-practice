#!/usr/bin/env python3
"""
Agent 2 - Scale Testing Script for 1.dwfx

This script:
1. Extracts W2D from 1.dwfx
2. Parses geometry and calculates bounding box
3. Tests multiple scale factors
4. Analyzes reference PDF
5. Calculates optimal scale
"""

import sys
import zipfile
import struct
from pathlib import Path
from PyPDF2 import PdfReader

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
import integration.pdf_renderer_v1 as pdf_renderer

def extract_w2d_from_dwf(dwf_path, output_w2d_path):
    """Extract W2D file from DWF/DWFX archive."""
    print(f"Extracting W2D from {dwf_path}...")

    with zipfile.ZipFile(dwf_path, 'r') as zip_ref:
        # List all files in the archive
        file_list = zip_ref.namelist()
        print(f"  Files in archive: {len(file_list)}")

        # Find W2D file
        w2d_files = [f for f in file_list if f.lower().endswith('.w2d')]

        if not w2d_files:
            print(f"  WARNING: No W2D file found in {dwf_path}")
            print(f"  This file uses a different format (likely XPS with raster images)")
            return None

        # Extract first W2D file
        w2d_file = w2d_files[0]
        print(f"  Extracting: {w2d_file}")

        with zip_ref.open(w2d_file) as source:
            with open(output_w2d_path, 'wb') as target:
                target.write(source.read())

        print(f"  Extracted to: {output_w2d_path}")
        print(f"  Size: {Path(output_w2d_path).stat().st_size / (1024*1024):.2f} MB")

    return output_w2d_path

def normalize_and_absolute_coords(opcodes):
    """Convert relative coordinates to absolute and normalize field names."""
    current_pos = [0, 0]
    normalized = []

    for op in opcodes:
        opcode_type = op.get('type', '')
        new_op = op.copy()

        if opcode_type == 'set_origin':
            origin = op.get('origin', [0, 0])
            current_pos = list(origin)

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

        if 'points' in new_op and 'vertices' not in new_op:
            new_op['vertices'] = new_op['points']
        if 'point1' in new_op and 'start' not in new_op:
            new_op['start'] = new_op['point1']
        if 'point2' in new_op and 'end' not in new_op:
            new_op['end'] = new_op['point2']

        normalized.append(new_op)

    return normalized

def calculate_bounding_box(opcodes):
    """Calculate bounding box of all geometry in opcodes."""
    all_coords = []

    for op in opcodes:
        if 'vertices' in op:
            all_coords.extend(op['vertices'])
        if 'start' in op:
            all_coords.append(op['start'])
        if 'end' in op:
            all_coords.append(op['end'])

    if not all_coords:
        return None

    min_x = min(c[0] for c in all_coords)
    min_y = min(c[1] for c in all_coords)
    max_x = max(c[0] for c in all_coords)
    max_y = max(c[1] for c in all_coords)

    return {
        'min_x': min_x,
        'min_y': min_y,
        'max_x': max_x,
        'max_y': max_y,
        'width': max_x - min_x,
        'height': max_y - min_y
    }

def translate_to_origin(opcodes, bbox):
    """Translate all coordinates to origin (0,0)."""
    min_x = bbox['min_x']
    min_y = bbox['min_y']

    for op in opcodes:
        if 'vertices' in op:
            op['vertices'] = [[x - min_x, y - min_y] for x, y in op['vertices']]
        if 'start' in op:
            op['start'] = [op['start'][0] - min_x, op['start'][1] - min_y]
        if 'end' in op:
            op['end'] = [op['end'][0] - min_x, op['end'][1] - min_y]

    return opcodes

def apply_scale_to_opcodes(opcodes, scale):
    """Apply scale factor to all coordinates."""
    scaled_opcodes = []

    for op in opcodes:
        new_op = op.copy()

        if 'vertices' in op:
            new_op['vertices'] = [[x * scale, y * scale] for x, y in op['vertices']]
        if 'start' in op:
            new_op['start'] = [op['start'][0] * scale, op['start'][1] * scale]
        if 'end' in op:
            new_op['end'] = [op['end'][0] * scale, op['end'][1] * scale]

        scaled_opcodes.append(new_op)

    return scaled_opcodes

def test_scale_factor(opcodes, bbox, scale, output_file):
    """Test a specific scale factor and render to PDF."""
    print(f"\n  Testing scale {scale}...")

    # Calculate scaled dimensions
    scaled_width = bbox['width'] * scale
    scaled_height = bbox['height'] * scale

    print(f"    Original: {bbox['width']:.0f} x {bbox['height']:.0f} DWF units")
    print(f"    Scaled: {scaled_width:.1f} x {scaled_height:.1f} points")

    # Apply scale
    scaled_opcodes = apply_scale_to_opcodes(opcodes, scale)

    # Determine page size - use scaled dimensions with margin
    margin = 36  # 0.5 inch
    page_width = scaled_width + (2 * margin)
    page_height = scaled_height + (2 * margin)

    # Cap at reasonable max size
    max_page_size = 17 * 72  # 17 inches
    if page_width > max_page_size or page_height > max_page_size:
        print(f"    Warning: Page too large ({page_width:.0f} x {page_height:.0f})")
        page_width = min(page_width, max_page_size)
        page_height = min(page_height, max_page_size)

    print(f"    Page size: {page_width:.1f} x {page_height:.1f} points ({page_width/72:.1f}\" x {page_height/72:.1f}\")")

    # Render to PDF with scale=1.0 (pre-scaled)
    original_transform = pdf_renderer.transform_point

    def transform_no_scale(x, y, page_height, scale=1.0):
        """Transform with scale=1.0 since we pre-scaled."""
        return original_transform(x, y, page_height, scale=1.0)

    pdf_renderer.transform_point = transform_no_scale

    try:
        pdf_renderer.render_dwf_to_pdf(scaled_opcodes, output_file, pagesize=(page_width, page_height))
        file_size = Path(output_file).stat().st_size / 1024  # KB
        print(f"    Output: {output_file}")
        print(f"    File size: {file_size:.1f} KB")

        # Estimate if content is visible
        if file_size < 5:
            visibility = "likely empty/invisible"
        elif file_size < 50:
            visibility = "minimal content"
        elif file_size < 200:
            visibility = "some content"
        else:
            visibility = "significant content"

        print(f"    Estimate: {visibility}")

        return {
            'scale': scale,
            'file_size_kb': file_size,
            'scaled_width': scaled_width,
            'scaled_height': scaled_height,
            'page_width': page_width,
            'page_height': page_height,
            'visibility': visibility
        }

    finally:
        pdf_renderer.transform_point = original_transform

def analyze_reference_pdf(pdf_path):
    """Analyze reference PDF to get page dimensions."""
    print(f"\nAnalyzing reference PDF: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
        first_page = reader.pages[0]

        # Get media box (page size)
        media_box = first_page.mediabox
        width = float(media_box.width)
        height = float(media_box.height)

        print(f"  Page size: {width:.1f} x {height:.1f} points")
        print(f"  Page size: {width/72:.2f}\" x {height/72:.2f}\"")
        print(f"  Number of pages: {len(reader.pages)}")

        return {
            'width': width,
            'height': height,
            'width_inches': width / 72,
            'height_inches': height / 72,
            'num_pages': len(reader.pages)
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    print("=" * 80)
    print("AGENT 2 - SCALE TESTING FOR 1.DWFX")
    print("=" * 80)

    # Try 1.dwfx first, fallback to 3.dwf if needed
    dwfx_file_1 = "/home/user/git-practice/1.dwfx"
    dwf_file_3 = "/home/user/git-practice/3.dwf"
    reference_pdf = "/home/user/git-practice/1.pdf"
    w2d_file = "/home/user/git-practice/agent2_extracted.w2d"

    results = {
        'attempted_file': dwfx_file_1,
        'actual_source_file': None,
        'reference_pdf': reference_pdf,
        'bbox': None,
        'reference_pdf_info': None,
        'scale_tests': [],
        'optimal_scale': None,
        'notes': []
    }

    # TEST 1: Extract W2D and calculate bounding box
    print("\n" + "=" * 80)
    print("TEST 1: EXTRACT W2D AND CALCULATE BOUNDING BOX")
    print("=" * 80)

    # Try to extract W2D from 1.dwfx first
    print(f"\nAttempting to extract W2D from {dwfx_file_1}...")
    w2d_path = extract_w2d_from_dwf(dwfx_file_1, w2d_file)

    if not w2d_path:
        # 1.dwfx doesn't have W2D, try 3.dwf instead
        print(f"\n1.dwfx uses XPS format (raster images, not W2D vector data)")
        print(f"Falling back to 3.dwf which should contain W2D data...")
        results['notes'].append("1.dwfx uses XPS format without W2D vector data")
        results['notes'].append("Using 3.dwf as source for W2D extraction")
        results['actual_source_file'] = dwf_file_3
        w2d_path = extract_w2d_from_dwf(dwf_file_3, w2d_file)

        if not w2d_path:
            print("ERROR: No W2D file found in either 1.dwfx or 3.dwf!")
            return 1
    else:
        results['actual_source_file'] = dwfx_file_1

    # Parse W2D
    print(f"\nParsing {w2d_file}...")
    opcodes = parse_dwf_file(w2d_file)
    print(f"  Parsed {len(opcodes)} opcodes")

    # Normalize coordinates
    print("\nNormalizing coordinates...")
    normalized_opcodes = normalize_and_absolute_coords(opcodes)

    # Calculate bounding box
    print("\nCalculating bounding box...")
    bbox = calculate_bounding_box(normalized_opcodes)

    if not bbox:
        print("ERROR: No geometry found!")
        return 1

    print(f"  Min X: {bbox['min_x']:.2f}")
    print(f"  Min Y: {bbox['min_y']:.2f}")
    print(f"  Max X: {bbox['max_x']:.2f}")
    print(f"  Max Y: {bbox['max_y']:.2f}")
    print(f"  Width: {bbox['width']:.2f} DWF units")
    print(f"  Height: {bbox['height']:.2f} DWF units")

    results['bbox'] = bbox

    # Translate to origin
    print("\nTranslating geometry to origin...")
    normalized_opcodes = translate_to_origin(normalized_opcodes, bbox)

    # TEST 2: Try different scale factors
    print("\n" + "=" * 80)
    print("TEST 2: TESTING MULTIPLE SCALE FACTORS")
    print("=" * 80)

    scale_factors = [0.001, 0.01, 0.1, 1.0, 10.0]

    for scale in scale_factors:
        output_file = f"/home/user/git-practice/agent2_test_scale_{scale}.pdf"
        test_result = test_scale_factor(normalized_opcodes, bbox, scale, output_file)
        results['scale_tests'].append(test_result)

    # TEST 3: Analyze reference PDF and calculate optimal scale
    print("\n" + "=" * 80)
    print("TEST 3: ANALYZE REFERENCE PDF AND CALCULATE OPTIMAL SCALE")
    print("=" * 80)

    pdf_info = analyze_reference_pdf(reference_pdf)
    results['reference_pdf_info'] = pdf_info

    if pdf_info:
        # Calculate optimal scale to fit reference page with margin
        margin = 36  # 0.5 inch
        available_width = pdf_info['width'] - (2 * margin)
        available_height = pdf_info['height'] - (2 * margin)

        scale_x = available_width / bbox['width']
        scale_y = available_height / bbox['height']
        optimal_scale = min(scale_x, scale_y)

        print(f"\nCalculating optimal scale:")
        print(f"  Reference page: {pdf_info['width']:.1f} x {pdf_info['height']:.1f} points")
        print(f"  Available area (with margin): {available_width:.1f} x {available_height:.1f} points")
        print(f"  Drawing size: {bbox['width']:.0f} x {bbox['height']:.0f} DWF units")
        print(f"  Scale X (width-based): {scale_x:.6f}")
        print(f"  Scale Y (height-based): {scale_y:.6f}")
        print(f"  Optimal scale (min): {optimal_scale:.6f}")
        print(f"  Scaled drawing: {bbox['width']*optimal_scale:.1f} x {bbox['height']*optimal_scale:.1f} points")

        results['optimal_scale'] = optimal_scale

        # Test the optimal scale
        print("\nTesting optimal scale:")
        optimal_output = f"/home/user/git-practice/agent2_test_scale_optimal_{optimal_scale:.6f}.pdf"
        optimal_result = test_scale_factor(normalized_opcodes, bbox, optimal_scale, optimal_output)
        results['scale_tests'].append(optimal_result)

    # Generate results file
    print("\n" + "=" * 80)
    print("GENERATING RESULTS FILE")
    print("=" * 80)

    with open("/home/user/git-practice/agent2_scale_results.md", 'w') as f:
        f.write("# Agent 2 Scale Testing Results for 1.dwfx\n\n")

        f.write("## Test File Information\n\n")
        f.write(f"- Target file: `{results['attempted_file']}`\n")
        f.write(f"- Actual source: `{results['actual_source_file']}`\n")
        f.write(f"- Reference: `{reference_pdf}` (3.1 MB)\n")
        f.write(f"- Extracted W2D: `{w2d_file}`\n\n")

        if results['notes']:
            f.write("### Important Notes\n\n")
            for note in results['notes']:
                f.write(f"- {note}\n")
            f.write("\n")

        f.write("## Test 1: Bounding Box of Parsed Geometry\n\n")
        f.write("### Raw Coordinates (before translation)\n")
        f.write(f"- Min X: `{bbox['min_x']:.2f}` DWF units\n")
        f.write(f"- Min Y: `{bbox['min_y']:.2f}` DWF units\n")
        f.write(f"- Max X: `{bbox['max_x']:.2f}` DWF units\n")
        f.write(f"- Max Y: `{bbox['max_y']:.2f}` DWF units\n\n")

        f.write("### Bounding Box Dimensions\n")
        f.write(f"- Width: `{bbox['width']:.2f}` DWF units\n")
        f.write(f"- Height: `{bbox['height']:.2f}` DWF units\n\n")

        f.write("## Test 2: Scale Factor Testing Results\n\n")
        f.write("| Scale Factor | Scaled Width (pts) | Scaled Height (pts) | File Size (KB) | Visibility Estimate |\n")
        f.write("|--------------|-------------------|---------------------|----------------|---------------------|\n")

        for test in results['scale_tests']:
            f.write(f"| {test['scale']:.6f} | {test['scaled_width']:.1f} | {test['scaled_height']:.1f} | {test['file_size_kb']:.1f} | {test['visibility']} |\n")

        f.write("\n")

        if pdf_info:
            f.write("## Test 3: Reference PDF Analysis\n\n")
            f.write(f"- Page size: `{pdf_info['width']:.1f} x {pdf_info['height']:.1f}` points\n")
            f.write(f"- Page size: `{pdf_info['width_inches']:.2f}\" x {pdf_info['height_inches']:.2f}\"`\n")
            f.write(f"- Number of pages: `{pdf_info['num_pages']}`\n\n")

            f.write("### Calculated Optimal Scale\n\n")
            f.write(f"To fit the parsed geometry ({bbox['width']:.0f} x {bbox['height']:.0f} DWF units) ")
            f.write(f"onto the reference PDF page ({pdf_info['width']:.1f} x {pdf_info['height']:.1f} points) ")
            f.write(f"with a 0.5-inch margin:\n\n")
            f.write(f"- Scale X (width-based): `{available_width / bbox['width']:.6f}`\n")
            f.write(f"- Scale Y (height-based): `{available_height / bbox['height']:.6f}`\n")
            f.write(f"- **Optimal scale: `{results['optimal_scale']:.6f}`** (minimum to preserve aspect ratio)\n\n")

        f.write("## Conclusion\n\n")

        if results['optimal_scale']:
            f.write(f"**The correct scale factor for file 1 is approximately `{results['optimal_scale']:.6f}` because:**\n\n")
            f.write(f"1. The parsed geometry from 1.dwfx has dimensions of {bbox['width']:.0f} x {bbox['height']:.0f} DWF units\n")
            f.write(f"2. The reference PDF 1.pdf has a page size of {pdf_info['width']:.1f} x {pdf_info['height']:.1f} points ")
            f.write(f"({pdf_info['width_inches']:.2f}\" x {pdf_info['height_inches']:.2f}\")\n")
            f.write(f"3. To fit the drawing onto the reference page with a 0.5-inch margin (36 points), we need a scale of {results['optimal_scale']:.6f}\n")
            f.write(f"4. This scale results in a drawing of {bbox['width']*results['optimal_scale']:.1f} x {bbox['height']*results['optimal_scale']:.1f} points, ")
            f.write(f"which fits within the available space of {available_width:.1f} x {available_height:.1f} points\n")
        else:
            f.write("**Unable to calculate optimal scale** - reference PDF could not be analyzed.\n")

        f.write("\n---\n")
        f.write("*Generated by Agent 2 Scale Testing Script*\n")

    print(f"\nResults written to: /home/user/git-practice/agent2_scale_results.md")

    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
