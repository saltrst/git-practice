#!/usr/bin/env python3
"""
Agent 8: Bounding Box Analysis
==============================

Calculates and compares expected vs actual bounding boxes for all test files:
- 1.dwfx (5.1MB) → 1.pdf (3.1MB)
- 2.dwfx (9.0MB) → 2.pdf (5.1MB)
- 3.dwf (9.4MB) → 3.pdf (3.2MB)

Analysis:
1. Parse all input files and calculate bounding boxes from geometry
2. Extract page sizes from reference PDFs
3. Compare aspect ratios (geometry vs PDF)
4. Generate detailed analysis report
"""

import sys
from pathlib import Path
from collections import defaultdict
import struct

# Add project paths
project_root = Path(__file__).parent / "dwf-to-pdf-project"
sys.path.insert(0, str(project_root / "integration"))

# Import parser (but we'll parse manually for more control)
from dwf_parser_v1 import parse_dwf_file


class BoundingBoxCalculator:
    """Calculate bounding box from parsed DWF geometry."""

    def __init__(self):
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')
        self.point_count = 0
        self.geometry_count = 0

    def add_point(self, x, y):
        """Add a point to the bounding box calculation."""
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)
        self.min_y = min(self.min_y, y)
        self.max_y = max(self.max_y, y)
        self.point_count += 1

    def process_opcode(self, opcode):
        """Process an opcode and extract geometry points."""
        opcode_type = opcode.get('type', '')

        # Line opcodes
        if opcode_type in ['line', 'line_16r']:
            if 'start' in opcode and 'end' in opcode:
                self.add_point(opcode['start'][0], opcode['start'][1])
                self.add_point(opcode['end'][0], opcode['end'][1])
                self.geometry_count += 1
            elif 'point1' in opcode and 'point2' in opcode:
                self.add_point(opcode['point1'][0], opcode['point1'][1])
                self.add_point(opcode['point2'][0], opcode['point2'][1])
                self.geometry_count += 1

        # Circle opcodes
        elif opcode_type in ['circle', 'circle_16r']:
            if 'center' in opcode and 'radius' in opcode:
                cx, cy = opcode['center']
                r = opcode['radius']
                self.add_point(cx - r, cy - r)
                self.add_point(cx + r, cy + r)
                self.geometry_count += 1

        # Ellipse opcodes
        elif opcode_type in ['ellipse', 'draw_ellipse']:
            if 'center' in opcode:
                cx, cy = opcode['center']
                rx = opcode.get('major_axis', opcode.get('radius_x', 10))
                ry = opcode.get('minor_axis', opcode.get('radius_y', 10))
                self.add_point(cx - rx, cy - ry)
                self.add_point(cx + rx, cy + ry)
                self.geometry_count += 1

        # Polygon/polyline opcodes
        elif opcode_type in ['polyline_polygon', 'polyline_polygon_16r', 'polytriangle',
                            'polytriangle_16r', 'polytriangle_32r', 'quad', 'quad_32r',
                            'gouraud_polytriangle', 'gouraud_polyline', 'contour']:
            vertices = opcode.get('vertices', opcode.get('points', []))
            for v in vertices:
                if len(v) >= 2:
                    self.add_point(v[0], v[1])
            if vertices:
                self.geometry_count += 1

        # Bezier curves
        elif opcode_type == 'bezier':
            control_points = opcode.get('control_points', [])
            for pt in control_points:
                if len(pt) >= 2:
                    self.add_point(pt[0], pt[1])
            if control_points:
                self.geometry_count += 1

        # Text opcodes (approximate with position)
        elif opcode_type in ['draw_text_basic', 'draw_text_complex']:
            if 'position' in opcode:
                pos = opcode['position']
                self.add_point(pos[0], pos[1])
                # Approximate text width/height
                text = opcode.get('text', '')
                font_size = opcode.get('font_size', 12)
                self.add_point(pos[0] + len(text) * font_size * 0.6, pos[1] + font_size)

    def get_bbox(self):
        """Get the calculated bounding box."""
        if self.point_count == 0:
            return None
        return {
            'min_x': self.min_x,
            'max_x': self.max_x,
            'min_y': self.min_y,
            'max_y': self.max_y,
            'width': self.max_x - self.min_x,
            'height': self.max_y - self.min_y,
            'aspect_ratio': (self.max_x - self.min_x) / (self.max_y - self.min_y) if (self.max_y - self.min_y) != 0 else 0,
            'point_count': self.point_count,
            'geometry_count': self.geometry_count
        }


def extract_pdf_page_size(pdf_path):
    """
    Extract page size from a PDF file.

    Returns:
        dict with 'width', 'height', 'aspect_ratio' in points
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            page = reader.pages[0]
            box = page.mediabox
            width = float(box.width)
            height = float(box.height)

            return {
                'width': width,
                'height': height,
                'aspect_ratio': width / height if height != 0 else 0,
                'page_count': len(reader.pages)
            }
    except ImportError:
        print("Warning: PyPDF2 not available, trying manual parsing...")
        return extract_pdf_page_size_manual(pdf_path)
    except Exception as e:
        print(f"Error extracting PDF page size: {e}")
        return None


def extract_pdf_page_size_manual(pdf_path):
    """
    Manually extract page size from PDF by parsing the file.
    Looks for /MediaBox entries.
    """
    try:
        with open(pdf_path, 'rb') as f:
            content = f.read()

        # Convert to string for searching (decode as latin-1 to preserve bytes)
        content_str = content.decode('latin-1', errors='ignore')

        # Look for MediaBox definition
        # Format: /MediaBox [x1 y1 x2 y2]
        import re
        matches = re.findall(r'/MediaBox\s*\[\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*\]', content_str)

        if matches:
            x1, y1, x2, y2 = map(float, matches[0])
            width = x2 - x1
            height = y2 - y1

            return {
                'width': width,
                'height': height,
                'aspect_ratio': width / height if height != 0 else 0,
                'page_count': content_str.count('/Type /Page')
            }

        print("Warning: Could not find MediaBox in PDF")
        return None

    except Exception as e:
        print(f"Error in manual PDF parsing: {e}")
        return None


def analyze_file(dwf_path, pdf_path):
    """
    Analyze a DWF/DWFX file and its reference PDF.

    Returns:
        dict with 'dwf_bbox', 'pdf_page', and comparison data
    """
    print(f"\n{'='*70}")
    print(f"Analyzing: {dwf_path.name} → {pdf_path.name}")
    print(f"{'='*70}")

    # Get file sizes
    dwf_size = dwf_path.stat().st_size / (1024 * 1024)
    pdf_size = pdf_path.stat().st_size / (1024 * 1024)
    print(f"DWF size: {dwf_size:.1f} MB")
    print(f"PDF size: {pdf_size:.1f} MB")

    # Parse DWF file
    print(f"\nParsing {dwf_path.name}...")
    try:
        opcodes = parse_dwf_file(str(dwf_path))
        print(f"✓ Parsed {len(opcodes)} opcodes")
    except Exception as e:
        print(f"✗ Error parsing: {e}")
        return None

    # Calculate bounding box from geometry
    print("Calculating bounding box from geometry...")
    calculator = BoundingBoxCalculator()

    for opcode in opcodes:
        calculator.process_opcode(opcode)

    bbox = calculator.get_bbox()

    if bbox:
        print(f"✓ Bounding box calculated:")
        print(f"  X range: [{bbox['min_x']:.2f}, {bbox['max_x']:.2f}]")
        print(f"  Y range: [{bbox['min_y']:.2f}, {bbox['max_y']:.2f}]")
        print(f"  Width: {bbox['width']:.2f} DWF units")
        print(f"  Height: {bbox['height']:.2f} DWF units")
        print(f"  Aspect ratio: {bbox['aspect_ratio']:.4f}")
        print(f"  Geometry objects: {bbox['geometry_count']}")
        print(f"  Total points: {bbox['point_count']}")
    else:
        print("✗ No geometry found")
        bbox = None

    # Extract PDF page size
    print(f"\nExtracting page size from {pdf_path.name}...")
    pdf_info = extract_pdf_page_size(str(pdf_path))

    if pdf_info:
        print(f"✓ PDF page size:")
        print(f"  Width: {pdf_info['width']:.2f} points")
        print(f"  Height: {pdf_info['height']:.2f} points")
        print(f"  Aspect ratio: {pdf_info['aspect_ratio']:.4f}")
        print(f"  Pages: {pdf_info['page_count']}")
    else:
        print("✗ Could not extract PDF page size")

    # Compare aspect ratios
    if bbox and pdf_info:
        dwf_ar = bbox['aspect_ratio']
        pdf_ar = pdf_info['aspect_ratio']
        ar_diff = abs(dwf_ar - pdf_ar)
        ar_diff_pct = (ar_diff / pdf_ar) * 100 if pdf_ar != 0 else 0

        print(f"\nAspect Ratio Comparison:")
        print(f"  DWF geometry: {dwf_ar:.4f}")
        print(f"  PDF page: {pdf_ar:.4f}")
        print(f"  Difference: {ar_diff:.4f} ({ar_diff_pct:.2f}%)")

        if ar_diff_pct < 1:
            print("  ✓ Aspect ratios MATCH (within 1%)")
            match = True
        elif ar_diff_pct < 5:
            print("  ⚠ Aspect ratios CLOSE (within 5%)")
            match = "close"
        else:
            print("  ✗ Aspect ratios DON'T MATCH")
            match = False
    else:
        match = None

    return {
        'dwf_path': str(dwf_path),
        'pdf_path': str(pdf_path),
        'dwf_size_mb': dwf_size,
        'pdf_size_mb': pdf_size,
        'dwf_bbox': bbox,
        'pdf_page': pdf_info,
        'aspect_match': match,
        'opcode_count': len(opcodes) if opcodes else 0
    }


def generate_markdown_report(results, output_path):
    """Generate comprehensive markdown analysis report."""

    lines = [
        "# Agent 8: Bounding Box Analysis Report",
        "",
        f"**Generated:** {Path(__file__).name}",
        "**Mission:** Calculate and compare expected vs actual bounding boxes for all test files.",
        "",
        "## Executive Summary",
        "",
        "This analysis examines the bounding boxes of parsed DWF/DWFX geometry and compares them to the page sizes of reference PDFs to determine if the aspect ratios match.",
        "",
        "## Test Files Analyzed",
        ""
    ]

    # File summary table
    lines.extend([
        "| File | Size | Reference PDF | Size |",
        "|------|------|--------------|------|"
    ])

    for result in results:
        if result:
            lines.append(f"| {Path(result['dwf_path']).name} | {result['dwf_size_mb']:.1f} MB | "
                        f"{Path(result['pdf_path']).name} | {result['pdf_size_mb']:.1f} MB |")

    lines.append("")

    # Test 1: Bounding Boxes from Parsed Geometry
    lines.extend([
        "## Test 1: Calculated Bounding Boxes (DWF Units)",
        "",
        "Parsed all input files, converted relative to absolute coordinates, and calculated min/max X/Y.",
        ""
    ])

    lines.extend([
        "| File | Min X | Max X | Min Y | Max Y | Width | Height | Aspect Ratio | Geometry Count |",
        "|------|-------|-------|-------|-------|-------|--------|--------------|----------------|"
    ])

    for result in results:
        if result and result['dwf_bbox']:
            bbox = result['dwf_bbox']
            lines.append(
                f"| {Path(result['dwf_path']).name} | "
                f"{bbox['min_x']:.2f} | {bbox['max_x']:.2f} | "
                f"{bbox['min_y']:.2f} | {bbox['max_y']:.2f} | "
                f"{bbox['width']:.2f} | {bbox['height']:.2f} | "
                f"{bbox['aspect_ratio']:.4f} | {bbox['geometry_count']} |"
            )

    lines.append("")

    # Test 2: PDF Page Sizes
    lines.extend([
        "## Test 2: Reference PDF Page Sizes (Points)",
        "",
        "Extracted page dimensions from the reference PDFs to determine actual output sizing.",
        ""
    ])

    lines.extend([
        "| PDF File | Width (pts) | Height (pts) | Width (in) | Height (in) | Aspect Ratio | Pages |",
        "|----------|-------------|--------------|------------|-------------|--------------|-------|"
    ])

    for result in results:
        if result and result['pdf_page']:
            pdf = result['pdf_page']
            width_in = pdf['width'] / 72
            height_in = pdf['height'] / 72
            lines.append(
                f"| {Path(result['pdf_path']).name} | "
                f"{pdf['width']:.2f} | {pdf['height']:.2f} | "
                f"{width_in:.2f} | {height_in:.2f} | "
                f"{pdf['aspect_ratio']:.4f} | {pdf['page_count']} |"
            )

    lines.append("")

    # Test 3: Aspect Ratio Comparison
    lines.extend([
        "## Test 3: Aspect Ratio Comparison",
        "",
        "Comparing (parsed_width / parsed_height) vs (pdf_width / pdf_height) to determine if geometry is being stretched or squashed.",
        ""
    ])

    lines.extend([
        "| File | DWF Aspect Ratio | PDF Aspect Ratio | Difference | % Difference | Match? |",
        "|------|------------------|------------------|------------|--------------|--------|"
    ])

    all_match = True
    for result in results:
        if result and result['dwf_bbox'] and result['pdf_page']:
            dwf_ar = result['dwf_bbox']['aspect_ratio']
            pdf_ar = result['pdf_page']['aspect_ratio']
            diff = abs(dwf_ar - pdf_ar)
            pct = (diff / pdf_ar * 100) if pdf_ar != 0 else 0

            if result['aspect_match'] == True:
                match_str = "✓ Yes"
            elif result['aspect_match'] == "close":
                match_str = "⚠ Close"
                all_match = False
            else:
                match_str = "✗ No"
                all_match = False

            lines.append(
                f"| {Path(result['dwf_path']).name} | "
                f"{dwf_ar:.4f} | {pdf_ar:.4f} | "
                f"{diff:.4f} | {pct:.2f}% | {match_str} |"
            )

    lines.append("")

    # Analysis and Claims
    lines.extend([
        "## Analysis and Findings",
        ""
    ])

    # Concrete claim about aspect ratios
    if all_match:
        lines.extend([
            "### Aspect Ratio Match Conclusion",
            "",
            "**Claim:** The aspect ratios DO MATCH between parsed geometry and reference PDFs.",
            "",
            "**Evidence:** All three test files show aspect ratio differences of less than 1%, indicating that:",
            "- The DWF parser correctly extracts geometry coordinates",
            "- The reference PDFs maintain the original drawing proportions",
            "- No significant stretching or squashing occurs in the conversion process",
            ""
        ])
    else:
        lines.extend([
            "### Aspect Ratio Match Conclusion",
            "",
            "**Claim:** The aspect ratios DON'T MATCH perfectly between parsed geometry and reference PDFs.",
            "",
            "**Evidence:** Differences detected in aspect ratios, which may indicate:",
            "- Coordinate transformation issues",
            "- Scale factor mismatches",
            "- Page size selection problems",
            "- Margin/padding adjustments in the reference PDFs",
            ""
        ])

    # Detailed findings per file
    lines.extend([
        "### Per-File Analysis",
        ""
    ])

    for result in results:
        if result and result['dwf_bbox'] and result['pdf_page']:
            name = Path(result['dwf_path']).name
            bbox = result['dwf_bbox']
            pdf = result['pdf_page']

            lines.extend([
                f"#### {name}",
                ""
            ])

            # Calculate scale factors
            scale_x = pdf['width'] / bbox['width'] if bbox['width'] != 0 else 0
            scale_y = pdf['height'] / bbox['height'] if bbox['height'] != 0 else 0

            lines.extend([
                f"- **Geometry:** {bbox['width']:.2f} × {bbox['height']:.2f} DWF units",
                f"- **PDF Page:** {pdf['width']:.2f} × {pdf['height']:.2f} points ({pdf['width']/72:.2f} × {pdf['height']/72:.2f} inches)",
                f"- **Scale Factor:** X={scale_x:.6f}, Y={scale_y:.6f}",
                f"- **Geometry Objects:** {bbox['geometry_count']} primitives, {bbox['point_count']} points",
                ""
            ])

            if result['aspect_match'] == True:
                lines.append(f"✓ Aspect ratios match - uniform scaling can be applied.")
            elif result['aspect_match'] == "close":
                lines.append(f"⚠ Aspect ratios are close but not perfect - may need adjustment.")
            else:
                lines.append(f"✗ Aspect ratios differ significantly - non-uniform scaling or page size issues.")

            lines.append("")

    # Recommendations
    lines.extend([
        "## Recommendations",
        ""
    ])

    if all_match:
        lines.extend([
            "### Recommended Page Sizing Strategy",
            "",
            "Since aspect ratios match, use **uniform scaling** with automatic page size selection:",
            "",
            "```python",
            "# Calculate scale factor to fit content with margin",
            "scale_x = (page_width - 2 * margin) / bbox_width",
            "scale_y = (page_height - 2 * margin) / bbox_height",
            "scale = min(scale_x, scale_y)  # Uniform scaling",
            "",
            "# Or use auto-sizing based on geometry:",
            "page_width = bbox_width * scale + 2 * margin",
            "page_height = bbox_height * scale + 2 * margin",
            "```",
            "",
            "### Recommended Scale Factors",
            ""
        ])

        for result in results:
            if result and result['dwf_bbox'] and result['pdf_page']:
                bbox = result['dwf_bbox']
                pdf = result['pdf_page']

                # Calculate optimal scale assuming 1-inch margins
                margin = 72  # 1 inch in points
                scale_x = (pdf['width'] - 2 * margin) / bbox['width'] if bbox['width'] != 0 else 0
                scale_y = (pdf['height'] - 2 * margin) / bbox['height'] if bbox['height'] != 0 else 0
                recommended_scale = min(scale_x, scale_y)

                lines.append(
                    f"- **{Path(result['dwf_path']).name}**: Scale = {recommended_scale:.6f} "
                    f"(fits in {pdf['width']/72:.1f} × {pdf['height']/72:.1f} inch page)"
                )
    else:
        lines.extend([
            "### Investigation Required",
            "",
            "Aspect ratio mismatches suggest potential issues:",
            "",
            "1. **Verify coordinate parsing** - Check if relative coordinates are correctly converted to absolute",
            "2. **Check for clipping/viewport** - Some geometry might be outside the visible area",
            "3. **Examine origin/units opcodes** - Coordinate transformations may affect bounds",
            "4. **Review page size selection** - Reference PDFs may use custom page sizes",
            "",
            "Recommended approach:",
            "- Use the bounding box from parsed geometry as the authoritative size",
            "- Apply uniform scaling to maintain aspect ratio",
            "- Add configurable margins",
            ""
        ])

    lines.extend([
        "",
        "## Methodology",
        "",
        "### Coordinate Extraction",
        "",
        "Extracted coordinates from these opcode types:",
        "- Lines: start and end points",
        "- Circles/Ellipses: center ± radius",
        "- Polygons/Polylines: all vertices",
        "- Triangles/Quads: all vertices",
        "- Bezier curves: all control points",
        "- Text: position (approximate bounds based on text length)",
        "",
        "### Coordinate Conversion",
        "",
        "- Relative coordinates converted to absolute using origin tracking",
        "- All coordinates accumulated to calculate min/max X/Y",
        "- Bounding box = [min_x, max_x] × [min_y, max_y]",
        "",
        "### PDF Analysis",
        "",
        "- Extracted /MediaBox from reference PDFs",
        "- Measured in points (1 point = 1/72 inch)",
        "- Calculated aspect ratio as width/height",
        "",
        "---",
        "",
        f"*Analysis completed by {Path(__file__).name}*"
    ])

    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"\n✓ Report written to: {output_path}")


def main():
    """Main analysis entry point."""
    print("="*70)
    print("AGENT 8: BOUNDING BOX ANALYSIS")
    print("="*70)

    # Define test files
    base_dir = Path(__file__).parent
    test_files = [
        (base_dir / "1.dwfx", base_dir / "1.pdf"),
        (base_dir / "2.dwfx", base_dir / "2.pdf"),
        (base_dir / "3.dwf", base_dir / "3.pdf"),
    ]

    # Check files exist
    missing = []
    for dwf, pdf in test_files:
        if not dwf.exists():
            missing.append(str(dwf))
        if not pdf.exists():
            missing.append(str(pdf))

    if missing:
        print(f"\n✗ Error: Missing files:")
        for f in missing:
            print(f"  - {f}")
        return 1

    # Analyze each file
    results = []
    for dwf_path, pdf_path in test_files:
        result = analyze_file(dwf_path, pdf_path)
        results.append(result)

    # Generate report
    output_path = base_dir / "agent8_bounding_box_analysis.md"
    print(f"\n{'='*70}")
    print("Generating analysis report...")
    print(f"{'='*70}")

    generate_markdown_report(results, output_path)

    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"\nReport: {output_path}")
    print("\nSummary:")

    for result in results:
        if result:
            name = Path(result['dwf_path']).name
            if result['aspect_match'] == True:
                print(f"  ✓ {name}: Aspect ratios MATCH")
            elif result['aspect_match'] == "close":
                print(f"  ⚠ {name}: Aspect ratios CLOSE")
            elif result['aspect_match'] == False:
                print(f"  ✗ {name}: Aspect ratios DON'T MATCH")
            else:
                print(f"  ? {name}: Analysis incomplete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
