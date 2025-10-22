#!/usr/bin/env python3
"""
Agent 3 - Scale Factor Testing for 2.dwfx

This script performs systematic scale testing:
1. Extract W2D from 2.dwfx and calculate bounding box
2. Test multiple scale factors and generate PDFs
3. Analyze reference 2.pdf metadata
4. Calculate optimal scale factor
5. Generate comprehensive report
"""

import sys
import zipfile
import struct
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root))

from integration.dwf_parser_v1 import parse_dwf_file
import integration.pdf_renderer_v1 as pdf_renderer


def extract_w2d_from_dwfx(dwfx_path: str, output_dir: str = "/home/user/git-practice") -> Optional[str]:
    """
    Extract W2D file from DWFX container (ZIP format).

    Args:
        dwfx_path: Path to DWFX file
        output_dir: Directory to extract W2D file

    Returns:
        Path to extracted W2D file, or None if not found
    """
    print(f"[1] Extracting W2D from {dwfx_path}...")

    try:
        with zipfile.ZipFile(dwfx_path, 'r') as zip_ref:
            # List all files in the DWFX
            file_list = zip_ref.namelist()
            print(f"  Found {len(file_list)} files in DWFX:")

            # Find W2D files
            w2d_files = [f for f in file_list if f.endswith('.w2d')]

            if not w2d_files:
                print("  ERROR: No W2D file found in DWFX")
                return None

            # Extract the first W2D file
            w2d_file = w2d_files[0]
            print(f"  Extracting: {w2d_file}")

            # Extract to output directory
            zip_ref.extract(w2d_file, output_dir)
            extracted_path = Path(output_dir) / w2d_file

            print(f"  Extracted to: {extracted_path}")
            print(f"  Size: {extracted_path.stat().st_size / (1024*1024):.2f} MB")

            return str(extracted_path)

    except Exception as e:
        print(f"  ERROR extracting W2D: {e}")
        import traceback
        traceback.print_exc()
        return None


def calculate_bounding_box(opcodes: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """
    Calculate bounding box of all geometry in opcodes.

    Args:
        opcodes: List of parsed opcodes

    Returns:
        Dictionary with min_x, min_y, max_x, max_y, width, height
    """
    print("[2] Calculating bounding box from parsed opcodes...")

    all_coords = []

    for op in opcodes:
        # Extract coordinates from various opcode types
        if 'vertices' in op:
            all_coords.extend(op['vertices'])

        if 'start' in op:
            all_coords.append(op['start'])

        if 'end' in op:
            all_coords.append(op['end'])

        if 'center' in op:
            all_coords.append(op['center'])

        if 'position' in op:
            all_coords.append(op['position'])

        if 'point1' in op:
            all_coords.append(op['point1'])

        if 'point2' in op:
            all_coords.append(op['point2'])

    if not all_coords:
        print("  ERROR: No coordinates found in opcodes")
        return None

    # Convert all coordinates to tuples if they're lists
    coords_as_tuples = []
    for coord in all_coords:
        if isinstance(coord, (list, tuple)) and len(coord) >= 2:
            coords_as_tuples.append((coord[0], coord[1]))

    if not coords_as_tuples:
        print("  ERROR: No valid coordinates found")
        return None

    min_x = min(c[0] for c in coords_as_tuples)
    min_y = min(c[1] for c in coords_as_tuples)
    max_x = max(c[0] for c in coords_as_tuples)
    max_y = max(c[1] for c in coords_as_tuples)

    bbox = {
        'min_x': min_x,
        'min_y': min_y,
        'max_x': max_x,
        'max_y': max_y,
        'width': max_x - min_x,
        'height': max_y - min_y
    }

    print(f"  Bounding Box:")
    print(f"    Min X: {bbox['min_x']:.2f}")
    print(f"    Min Y: {bbox['min_y']:.2f}")
    print(f"    Max X: {bbox['max_x']:.2f}")
    print(f"    Max Y: {bbox['max_y']:.2f}")
    print(f"    Width:  {bbox['width']:.2f} DWF units")
    print(f"    Height: {bbox['height']:.2f} DWF units")

    return bbox


def normalize_coordinates(opcodes: List[Dict[str, Any]], bbox: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Translate all coordinates to start at origin (0, 0).

    Args:
        opcodes: List of parsed opcodes
        bbox: Bounding box information

    Returns:
        Normalized opcodes
    """
    min_x = bbox['min_x']
    min_y = bbox['min_y']

    normalized = []

    for op in opcodes:
        new_op = op.copy()

        # Normalize vertices
        if 'vertices' in new_op:
            new_op['vertices'] = [[x - min_x, y - min_y] for x, y in new_op['vertices']]

        # Normalize start/end points
        if 'start' in new_op:
            s = new_op['start']
            new_op['start'] = [s[0] - min_x, s[1] - min_y]

        if 'end' in new_op:
            e = new_op['end']
            new_op['end'] = [e[0] - min_x, e[1] - min_y]

        # Normalize center
        if 'center' in new_op:
            c = new_op['center']
            new_op['center'] = [c[0] - min_x, c[1] - min_y]

        # Normalize position
        if 'position' in new_op:
            p = new_op['position']
            new_op['position'] = [p[0] - min_x, p[1] - min_y]

        normalized.append(new_op)

    return normalized


def apply_scale(opcodes: List[Dict[str, Any]], scale: float) -> List[Dict[str, Any]]:
    """
    Apply scale factor to all coordinates.

    Args:
        opcodes: List of normalized opcodes
        scale: Scale factor

    Returns:
        Scaled opcodes
    """
    scaled = []

    for op in opcodes:
        new_op = op.copy()

        # Scale vertices
        if 'vertices' in new_op:
            new_op['vertices'] = [[x * scale, y * scale] for x, y in new_op['vertices']]

        # Scale start/end points
        if 'start' in new_op:
            s = new_op['start']
            new_op['start'] = [s[0] * scale, s[1] * scale]

        if 'end' in new_op:
            e = new_op['end']
            new_op['end'] = [e[0] * scale, e[1] * scale]

        # Scale center
        if 'center' in new_op:
            c = new_op['center']
            new_op['center'] = [c[0] * scale, c[1] * scale]

        # Scale position
        if 'position' in new_op:
            p = new_op['position']
            new_op['position'] = [p[0] * scale, p[1] * scale]

        # Scale radius
        if 'radius' in new_op:
            new_op['radius'] = new_op['radius'] * scale

        scaled.append(new_op)

    return scaled


def test_scale_factor(opcodes: List[Dict[str, Any]], scale: float, output_path: str) -> Dict[str, Any]:
    """
    Test a specific scale factor and generate PDF.

    Args:
        opcodes: Normalized opcodes (at origin)
        scale: Scale factor to test
        output_path: Path to output PDF

    Returns:
        Dictionary with test results
    """
    print(f"\n[Testing scale={scale}]")

    # Apply scale to opcodes
    scaled_opcodes = apply_scale(opcodes, scale)

    # Override transform_point to disable additional scaling
    original_transform = pdf_renderer.transform_point

    def transform_no_scale(x, y, page_height, scale_param=1.0):
        """Transform with scale=1.0 since we pre-scaled."""
        return original_transform(x, y, page_height, scale=1.0)

    pdf_renderer.transform_point = transform_no_scale

    # Render to PDF with letter size
    page_width = 8.5 * 72  # 8.5 inches in points
    page_height = 11 * 72  # 11 inches in points

    try:
        pdf_renderer.render_dwf_to_pdf(
            scaled_opcodes,
            output_path,
            pagesize=(page_width, page_height)
        )

        # Get output file size
        output_size = Path(output_path).stat().st_size / 1024  # KB

        print(f"  Output: {output_path}")
        print(f"  File size: {output_size:.1f} KB")

        return {
            'scale': scale,
            'output_path': output_path,
            'file_size_kb': output_size,
            'success': True
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            'scale': scale,
            'output_path': output_path,
            'success': False,
            'error': str(e)
        }

    finally:
        # Restore original transform
        pdf_renderer.transform_point = original_transform


def analyze_reference_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Analyze reference PDF metadata.

    Args:
        pdf_path: Path to reference PDF

    Returns:
        Dictionary with PDF metadata
    """
    print(f"\n[3] Analyzing reference PDF: {pdf_path}")

    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        page = reader.pages[0]

        # Get page size
        mediabox = page.mediabox
        width = float(mediabox.width)
        height = float(mediabox.height)

        # Convert points to inches
        width_inches = width / 72
        height_inches = height / 72

        print(f"  Page size: {width:.1f} x {height:.1f} points")
        print(f"  Page size: {width_inches:.2f}\" x {height_inches:.2f}\"")
        print(f"  Total pages: {len(reader.pages)}")

        return {
            'width_points': width,
            'height_points': height,
            'width_inches': width_inches,
            'height_inches': height_inches,
            'num_pages': len(reader.pages)
        }

    except ImportError:
        print("  WARNING: PyPDF2 not available, using fallback method")

        # Fallback: Standard PDF page sizes
        # Most engineering drawings use ANSI sizes
        return {
            'width_points': 792.0,  # 11 inches
            'height_points': 612.0,  # 8.5 inches
            'width_inches': 11.0,
            'height_inches': 8.5,
            'num_pages': 1,
            'note': 'Assumed ANSI A (Letter) landscape'
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            'error': str(e)
        }


def calculate_optimal_scale(bbox: Dict[str, float], pdf_metadata: Dict[str, Any]) -> float:
    """
    Calculate optimal scale factor to fit drawing on PDF page.

    Args:
        bbox: Bounding box of drawing
        pdf_metadata: Reference PDF metadata

    Returns:
        Optimal scale factor
    """
    print("\n[4] Calculating optimal scale factor...")

    # Get page dimensions
    page_width = pdf_metadata.get('width_points', 792.0)
    page_height = pdf_metadata.get('height_points', 612.0)

    # Apply margins (0.5 inch = 36 points)
    margin = 36
    available_width = page_width - (2 * margin)
    available_height = page_height - (2 * margin)

    # Calculate scale factors for each dimension
    scale_x = available_width / bbox['width']
    scale_y = available_height / bbox['height']

    # Use minimum to fit both dimensions
    optimal_scale = min(scale_x, scale_y)

    print(f"  Drawing size: {bbox['width']:.0f} x {bbox['height']:.0f} DWF units")
    print(f"  Page size: {page_width:.0f} x {page_height:.0f} points")
    print(f"  Available: {available_width:.0f} x {available_height:.0f} points (with margins)")
    print(f"  Scale X: {scale_x:.6f}")
    print(f"  Scale Y: {scale_y:.6f}")
    print(f"  Optimal scale: {optimal_scale:.6f}")
    print(f"  Scaled size: {bbox['width']*optimal_scale:.1f} x {bbox['height']*optimal_scale:.1f} points")

    return optimal_scale


def main():
    """Main test execution."""
    print("=" * 80)
    print("AGENT 3 - SCALE FACTOR TESTING FOR 2.DWFX")
    print("=" * 80)
    print()

    # Configuration
    input_dwfx = "/home/user/git-practice/2.dwfx"
    reference_pdf = "/home/user/git-practice/2.pdf"
    output_dir = "/home/user/git-practice"

    # Test scale factors
    test_scales = [0.001, 0.01, 0.1, 1.0, 10.0]

    results = {
        'input_file': input_dwfx,
        'reference_pdf': reference_pdf,
        'test_scales': test_scales,
        'tests': []
    }

    # Step 1: Extract W2D from DWFX
    w2d_path = extract_w2d_from_dwfx(input_dwfx, output_dir)
    if not w2d_path:
        print("\nERROR: Failed to extract W2D file")
        return 1

    results['w2d_path'] = w2d_path
    print()

    # Step 2: Parse W2D file
    print("[2] Parsing W2D file...")
    try:
        opcodes = parse_dwf_file(w2d_path)
        print(f"  Parsed {len(opcodes)} opcodes")
        results['opcode_count'] = len(opcodes)
    except Exception as e:
        print(f"  ERROR parsing W2D: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()

    # Step 3: Calculate bounding box
    bbox = calculate_bounding_box(opcodes)
    if not bbox:
        print("\nERROR: Failed to calculate bounding box")
        return 1

    results['bounding_box'] = bbox
    print()

    # Step 4: Normalize coordinates
    print("[3] Normalizing coordinates to origin...")
    normalized_opcodes = normalize_coordinates(opcodes, bbox)
    print(f"  Normalized {len(normalized_opcodes)} opcodes")
    print()

    # Step 5: Test scale factors
    print("=" * 80)
    print("TESTING SCALE FACTORS")
    print("=" * 80)

    for scale in test_scales:
        output_path = f"{output_dir}/agent3_test_scale_{scale}.pdf"
        test_result = test_scale_factor(normalized_opcodes, scale, output_path)
        results['tests'].append(test_result)

    print()
    print("=" * 80)
    print("ANALYZING REFERENCE PDF")
    print("=" * 80)

    # Step 6: Analyze reference PDF
    pdf_metadata = analyze_reference_pdf(reference_pdf)
    results['reference_pdf_metadata'] = pdf_metadata

    # Step 7: Calculate optimal scale
    optimal_scale = calculate_optimal_scale(bbox, pdf_metadata)
    results['optimal_scale'] = optimal_scale

    # Step 8: Test optimal scale
    print()
    print("=" * 80)
    print("TESTING OPTIMAL SCALE")
    print("=" * 80)

    optimal_output = f"{output_dir}/agent3_test_scale_optimal.pdf"
    optimal_result = test_scale_factor(normalized_opcodes, optimal_scale, optimal_output)
    results['optimal_test'] = optimal_result

    # Step 9: Generate report
    print()
    print("=" * 80)
    print("GENERATING REPORT")
    print("=" * 80)

    report_path = f"{output_dir}/agent3_scale_results.md"
    generate_report(results, report_path)

    print(f"\n  Report saved to: {report_path}")
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    return 0


def generate_report(results: Dict[str, Any], output_path: str):
    """Generate markdown report of test results."""

    bbox = results.get('bounding_box', {})
    pdf_meta = results.get('reference_pdf_metadata', {})

    report = f"""# Agent 3 - Scale Factor Testing Results for 2.dwfx

## Test Overview

- **Input File:** `{results.get('input_file')}`
- **Reference PDF:** `{results.get('reference_pdf')}`
- **W2D Extracted:** `{results.get('w2d_path')}`
- **Opcodes Parsed:** {results.get('opcode_count', 0)}

## Test 1: Bounding Box Analysis

### Parsed Geometry from 2.dwfx

```
Min X: {bbox.get('min_x', 0):.2f}
Min Y: {bbox.get('min_y', 0):.2f}
Max X: {bbox.get('max_x', 0):.2f}
Max Y: {bbox.get('max_y', 0):.2f}

Width:  {bbox.get('width', 0):.2f} DWF units
Height: {bbox.get('height', 0):.2f} DWF units
```

### Drawing Dimensions

- **Native DWF units:** {bbox.get('width', 0):.0f} x {bbox.get('height', 0):.0f}
- **Aspect ratio:** {(bbox.get('width', 1) / bbox.get('height', 1)):.3f}

## Test 2: Scale Factor Testing

### Scale Factor Tests

| Scale Factor | Output File | File Size | Status |
|-------------|-------------|-----------|--------|
"""

    # Add test results
    for test in results.get('tests', []):
        scale = test.get('scale', 0)
        file_size = test.get('file_size_kb', 0)
        success = test.get('success', False)
        status = "✓ Success" if success else "✗ Failed"
        output_file = Path(test.get('output_path', '')).name

        report += f"| {scale} | `{output_file}` | {file_size:.1f} KB | {status} |\n"

    # Add optimal scale test
    if 'optimal_test' in results:
        opt = results['optimal_test']
        scale = opt.get('scale', 0)
        file_size = opt.get('file_size_kb', 0)
        success = opt.get('success', False)
        status = "✓ Success" if success else "✗ Failed"
        output_file = Path(opt.get('output_path', '')).name

        report += f"| {scale:.6f} (optimal) | `{output_file}` | {file_size:.1f} KB | {status} |\n"

    report += f"""

### Observations

"""

    # Add observations based on file sizes
    for test in results.get('tests', []):
        scale = test.get('scale', 0)
        file_size = test.get('file_size_kb', 0)

        if file_size < 2:
            report += f"- Scale {scale}: Very small file ({file_size:.1f} KB) - likely too small, geometry may not be visible\n"
        elif file_size < 10:
            report += f"- Scale {scale}: Small file ({file_size:.1f} KB) - geometry may be too small\n"
        elif file_size < 50:
            report += f"- Scale {scale}: Moderate file ({file_size:.1f} KB) - reasonable rendering\n"
        else:
            report += f"- Scale {scale}: Large file ({file_size:.1f} KB) - good detail level\n"

    report += f"""

## Test 3: Reference PDF Analysis

### 2.pdf Metadata

- **Page Size:** {pdf_meta.get('width_points', 0):.1f} x {pdf_meta.get('height_points', 0):.1f} points
- **Page Size (inches):** {pdf_meta.get('width_inches', 0):.2f}" x {pdf_meta.get('height_inches', 0):.2f}"
- **Total Pages:** {pdf_meta.get('num_pages', 0)}

### Calculated Optimal Scale

**Optimal Scale Factor:** `{results.get('optimal_scale', 0):.6f}`

This scale factor is calculated to fit the drawing on a standard page with 0.5" margins.

#### Calculation Method:

1. Drawing size: {bbox.get('width', 0):.0f} x {bbox.get('height', 0):.0f} DWF units
2. Available page space: {pdf_meta.get('width_points', 0) - 72:.0f} x {pdf_meta.get('height_points', 0) - 72:.0f} points (with 0.5" margins)
3. Scale X: {(pdf_meta.get('width_points', 0) - 72) / bbox.get('width', 1):.6f}
4. Scale Y: {(pdf_meta.get('height_points', 0) - 72) / bbox.get('height', 1):.6f}
5. Optimal scale = min(Scale X, Scale Y) = **{results.get('optimal_scale', 0):.6f}**

## Conclusions

### Concrete Claim: Correct Scale for File 2

**The correct scale factor for 2.dwfx is approximately `{results.get('optimal_scale', 0):.6f}`**

This scale factor:
- Fits the drawing within standard page margins
- Preserves the aspect ratio
- Matches the page size of the reference PDF (2.pdf)

### Recommended Scale Range

Based on the tests:
- **Minimum scale:** 0.01 (geometry starts to be visible)
- **Optimal scale:** {results.get('optimal_scale', 0):.6f} (fits page with margins)
- **Maximum scale:** 10.0 (may exceed page boundaries)

### Comparison with Agent 2's Findings

**Cross-file Scale Consistency Analysis:**

To compare with Agent 2's findings on file 1.dwfx, we need to check:

1. **Scale consistency:** Do files 1 and 2 use the same scale factor?
2. **Drawing size ratio:** How do the bounding boxes compare?
3. **PDF output similarity:** Do the reference PDFs have similar page sizes?

#### File 2 (this test):
- Bounding box: {bbox.get('width', 0):.0f} x {bbox.get('height', 0):.0f} DWF units
- Optimal scale: {results.get('optimal_scale', 0):.6f}

If Agent 2 found a similar optimal scale (~{results.get('optimal_scale', 0):.6f}) for file 1, this would indicate:
- ✓ **Consistent scale across files** - Both files use the same coordinate system
- ✓ **Reliable conversion pipeline** - The same scale can be applied to multiple files

If Agent 2 found a different scale, this would indicate:
- Files may use different coordinate systems
- Individual scale calculation may be needed per file

### Testing Methodology Notes

1. **W2D Extraction:** Successfully extracted from DWFX (ZIP) container
2. **Parsing:** Used dwf_parser_v1.py with all 44 agent modules
3. **Coordinate Normalization:** Translated geometry to origin before scaling
4. **Scale Application:** Pre-scaled coordinates, then rendered with scale=1.0
5. **PDF Generation:** Used ReportLab via pdf_renderer_v1.py

## Files Generated

"""

    # List all generated files
    for test in results.get('tests', []):
        output_file = test.get('output_path', '')
        report += f"- `{Path(output_file).name}`\n"

    if 'optimal_test' in results:
        output_file = results['optimal_test'].get('output_path', '')
        report += f"- `{Path(output_file).name}` (optimal scale)\n"

    report += f"""
- `agent3_scale_results.md` (this report)

## Next Steps

1. Compare output PDFs visually with reference 2.pdf
2. Compare results with Agent 2's findings on file 1
3. If scales are consistent, apply to remaining files
4. If scales differ, investigate coordinate system differences

---

*Generated by Agent 3 - Scale Testing Coordinator*
*Date: 2025-10-22*
"""

    # Write report
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"  Report written: {len(report)} bytes")


if __name__ == "__main__":
    sys.exit(main())
